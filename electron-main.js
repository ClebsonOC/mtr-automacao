// electron-main.js - Processo principal do Electron

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log'); // Importa o electron-log

let mainWindow;
let pythonProcess = null;

// Configuração de logs para o autoUpdater
autoUpdater.logger = log;
autoUpdater.logger.transports.file.level = "info";
log.info('App starting...');

/**
 * Cria a janela principal da aplicação.
 */
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 950,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
        icon: path.join(__dirname, 'public/logo_inea.jpg')
    });

    mainWindow.loadFile('public/index.html');
    
    mainWindow.once('ready-to-show', () => {
        autoUpdater.checkForUpdatesAndNotify();
    });
}

// --- Ciclo de Vida da Aplicação ---

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

// --- Handlers do Auto-Updater ---

autoUpdater.on('update-available', () => {
    mainWindow.webContents.send('update-message', { message: 'Nova atualização disponível. A descarregar...' });
});

autoUpdater.on('update-downloaded', () => {
    mainWindow.webContents.send('update-message', { message: 'Atualização descarregada. Será instalada ao reiniciar a aplicação.' });
});

autoUpdater.on('error', (err) => {
    mainWindow.webContents.send('update-message', { message: `Erro na atualização: ${err.toString()}`, level: 'error' });
});


// --- Comunicação Inter-Processos (IPC) ---

ipcMain.on('start-automation', (event, config) => {
    const isDev = !app.isPackaged;

    const pythonExecutable = isDev
        ? path.join(__dirname, 'vendor', 'python-portable', 'python.exe')
        : path.join(process.resourcesPath, 'vendor', 'python-portable', 'python.exe');

    const pythonScriptsDir = isDev
        ? path.join(__dirname, 'src')
        : path.join(process.resourcesPath, 'src');

    const scriptPath = path.join(pythonScriptsDir, 'main.py');

    try {
        require('fs').accessSync(pythonExecutable);
    } catch (e) {
        mainWindow.webContents.send('log-message', { 
            message: `[CRITICAL ERROR]: Python executable not found at ${pythonExecutable}.`, 
            level: 'error' 
        });
        mainWindow.webContents.send('automation-finished');
        return;
    }

    // *** CORREÇÃO IMPORTANTE AQUI ***
    // Adicionamos a opção `cwd` (Current Working Directory) para dizer ao Python
    // para executar a partir da pasta 'src'. Isto resolve o 'ModuleNotFoundError'.
    pythonProcess = spawn(pythonExecutable, [scriptPath], {
        cwd: pythonScriptsDir
    });

    pythonProcess.stdin.write(JSON.stringify(config));
    pythonProcess.stdin.end();

    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString();
        output.split('\n').forEach(line => {
            if (line) {
                try {
                    const jsonData = JSON.parse(line);
                    if (jsonData.type === 'log') {
                        mainWindow.webContents.send('log-message', jsonData.payload);
                    } else if (jsonData.type === 'progress') {
                        mainWindow.webContents.send('progress-update', jsonData.payload);
                    }
                } catch (e) {
                    mainWindow.webContents.send('log-message', { message: `[Python Raw]: ${line}`, level: 'warning' });
                }
            }
        });
    });

    pythonProcess.stderr.on('data', (data) => {
        mainWindow.webContents.send('log-message', { message: `[Python Error]: ${data.toString()}`, level: 'error' });
    });

    pythonProcess.on('close', (code) => {
        mainWindow.webContents.send('log-message', { message: `Script Python finalizado com código ${code}.`, level: 'info' });
        mainWindow.webContents.send('automation-finished');
        pythonProcess = null;
    });
});

// --- Handlers para Diálogos Nativos ---

ipcMain.handle('dialog:selectExcel', () => {
    const result = dialog.showOpenDialogSync(mainWindow, {
        title: 'Selecionar Planilha Excel',
        properties: ['openFile'],
        filters: [{ name: 'Planilhas Excel', extensions: ['xlsx', 'xls'] }]
    });
    return result ? result[0] : null;
});

ipcMain.handle('dialog:selectFolder', () => {
    const result = dialog.showOpenDialogSync(mainWindow, {
        title: 'Selecionar Pasta Raiz para Downloads',
        properties: ['openDirectory']
    });
    return result ? result[0] : null;
});

ipcMain.handle('dialog:showAbout', () => {
    dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Sobre a Automação MTR',
        message: 'Automação MTR INEA v2.2.1 (Electron)',
        detail: 'Desenvolvido por: Clebson de Oliveira Correia\nEmail: oliveiraclebson007@gmail.com'
    });
});

ipcMain.handle('dialog:showError', (event, title, content) => {
    dialog.showErrorBox(title, content);
});
