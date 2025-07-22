// electron-main.js - Processo principal do Electron

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Variável para verificar se estamos em ambiente de desenvolvimento ou produção (empacotado)
const isDev = !app.isPackaged;

let mainWindow;
let pythonProcess = null;

/**
 * Cria a janela principal da aplicação.
 */
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 850,
        height: 950,
        webPreferences: {
            // Anexa o script de 'preload' à janela para expor APIs de forma segura
            preload: path.join(__dirname, 'preload.js'),
            // É recomendado manter contextIsolation e nodeIntegration desabilitados por segurança
            contextIsolation: true,
            nodeIntegration: false,
        },
        icon: path.join(__dirname, 'public/logo_inea.jpg') // Adiciona o ícone
    });

    // Carrega o arquivo HTML principal
    mainWindow.loadFile('public/index.html');
    
    // Opcional: Abre o DevTools para depuração apenas em desenvolvimento
    if (isDev) {
        mainWindow.webContents.openDevTools();
    }
}

// --- Ciclo de Vida da Aplicação ---

app.whenReady().then(() => {
    createWindow();

    // Handler para macOS: recria a janela se o app estiver no dock
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// Encerra a aplicação quando todas as janelas forem fechadas (exceto no macOS)
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
    // Garante que o processo python seja encerrado ao fechar o app
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

// --- Comunicação Inter-Processos (IPC) ---

// Ouve o evento 'start-automation' vindo do renderer.js
ipcMain.on('start-automation', (event, config) => {
    // Caminho dinâmico para o executável do Python portátil
    const pythonExecutable = isDev
      ? path.join(__dirname, 'vendor', 'python-portable', 'python.exe') // Caminho para desenvolvimento
      : path.join(process.resourcesPath, 'app.asar.unpacked', 'vendor', 'python-portable', 'python.exe'); // Caminho para produção

    // Caminho dinâmico para o script Python principal
    const scriptPath = isDev 
      ? path.join(__dirname, 'src', 'main.py') // Caminho para desenvolvimento
      : path.join(process.resourcesPath, 'app.asar.unpacked', 'src', 'main.py'); // Caminho para produção

    // Inicia o script Python como um processo filho
    pythonProcess = spawn(pythonExecutable, [scriptPath]);

    // Envia a configuração para o script Python via stdin
    pythonProcess.stdin.write(JSON.stringify(config));
    pythonProcess.stdin.end();

    // Ouve a saída padrão (stdout) do processo Python
    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString();
        // Processa cada linha JSON recebida
        output.split('\n').forEach(line => {
            if (line) {
                try {
                    const jsonData = JSON.parse(line);
                    // Envia os dados para a janela (renderer) com base no tipo
                    if (jsonData.type === 'log') {
                        mainWindow.webContents.send('log-message', jsonData.payload);
                    } else if (jsonData.type === 'progress') {
                        mainWindow.webContents.send('progress-update', jsonData.payload);
                    }
                } catch (e) {
                    // Se não for JSON, trata como um log de sistema
                    mainWindow.webContents.send('log-message', { message: `[Python Raw]: ${line}`, level: 'warning' });
                }
            }
        });
    });

    // Ouve a saída de erro (stderr) do processo Python
    pythonProcess.stderr.on('data', (data) => {
        mainWindow.webContents.send('log-message', { message: `[Python Error]: ${data.toString()}`, level: 'error' });
    });

    // Ouve o evento de finalização do processo Python
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
        message: 'Automação MTR INEA v2.0 (Electron)',
        detail: 'Desenvolvido por: Clebson de Oliveira Correia\nEmail: oliveiraclebson007@gmail.com'
    });
});

ipcMain.handle('dialog:showError', (event, title, content) => {
    dialog.showErrorBox(title, content);
});
