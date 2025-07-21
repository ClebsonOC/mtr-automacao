// preload.js - Expõe APIs do Node.js/Electron para o renderer de forma segura

const { contextBridge, ipcRenderer } = require('electron');

// Expõe um objeto 'electronAPI' para a janela do renderer (window.electronAPI)
contextBridge.exposeInMainWorld('electronAPI', {
    // Funções que o renderer pode invocar (comunicação Renderer -> Main)
    startAutomation: (config) => ipcRenderer.send('start-automation', config),
    selectExcelFile: () => ipcRenderer.invoke('dialog:selectExcel'),
    selectRootFolder: () => ipcRenderer.invoke('dialog:selectFolder'),
    showAboutDialog: () => ipcRenderer.invoke('dialog:showAbout'),
    showErrorDialog: (title, content) => ipcRenderer.invoke('dialog:showError', title, content),

    // Funções para o renderer ouvir eventos do processo principal (Main -> Renderer)
    onLogMessage: (callback) => ipcRenderer.on('log-message', callback),
    onProgressUpdate: (callback) => ipcRenderer.on('progress-update', callback),
    onAutomationFinished: (callback) => ipcRenderer.on('automation-finished', callback),
    onUpdateMessage: (callback) => ipcRenderer.on('update-message', callback), // NOVO
});