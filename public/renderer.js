// renderer.js - Lida com a lógica da interface (janela do Electron)

// --- Mapeamento dos Elementos do DOM ---
const elements = {
    cnpj: document.getElementById('cnpj'),
    obra: document.getElementById('obra'),
    cpf: document.getElementById('cpf'),
    senha: document.getElementById('senha'),
    excelPath: document.getElementById('excel-path'),
    rootFolder: document.getElementById('root-folder'),
    selectExcelBtn: document.getElementById('select-excel-btn'),
    selectFolderBtn: document.getElementById('select-folder-btn'),
    startBtn: document.getElementById('start-btn'),
    aboutBtn: document.getElementById('about-btn'),
    progressMessage: document.getElementById('progress-message'),
    progressBar: document.getElementById('progress-bar'),
    progressLabel: document.getElementById('progress-label'),
    logArea: document.getElementById('log-area'),
};

// --- Funções de Atualização da UI ---

/**
 * Adiciona uma mensagem de log à área de logs na tela.
 * @param {string} message - A mensagem a ser exibida.
 * @param {string} level - O nível do log (e.g., 'info', 'error', 'warning').
 */
function addLog(message, level = 'info') {
    if (elements.logArea.innerHTML === 'Logs da execução aparecerão aqui...') {
        elements.logArea.innerHTML = '';
    }
    const logEntry = document.createElement('div');
    logEntry.className = `log-${level}`; // Aplica a classe CSS para a cor
    logEntry.textContent = message;
    elements.logArea.appendChild(logEntry);
    // Rola para o final da área de logs
    elements.logArea.scrollTop = elements.logArea.scrollHeight;
}

/**
 * Atualiza a barra de progresso e as mensagens relacionadas.
 * @param {number} current - O valor atual do progresso.
 * @param {number} total - O valor total para o progresso.
 * @param {string} message - A mensagem de status a ser exibida.
 */
function updateProgress(current, total, message) {
    const percentage = total > 0 ? (current / total) * 100 : 0;
    elements.progressBar.style.width = `${percentage}%`;
    elements.progressLabel.textContent = `${current}/${total} (${percentage.toFixed(0)}%)`;
    elements.progressMessage.textContent = message;
}

/**
 * Habilita ou desabilita os botões e campos de entrada.
 * @param {boolean} isEnabled - True para habilitar, false para desabilitar.
 */
function setControlsEnabled(isEnabled) {
    elements.startBtn.disabled = !isEnabled;
    elements.aboutBtn.disabled = !isEnabled;
    elements.selectExcelBtn.disabled = !isEnabled;
    elements.selectFolderBtn.disabled = !isEnabled;
    
    const inputs = [elements.cnpj, elements.obra, elements.cpf, elements.senha];
    inputs.forEach(input => input.disabled = !isEnabled);
}


// --- Event Listeners para Interação do Usuário ---

// Botão para selecionar o arquivo Excel
elements.selectExcelBtn.addEventListener('click', async () => {
    const filePath = await window.electronAPI.selectExcelFile();
    if (filePath) {
        elements.excelPath.value = filePath;
    }
});

// Botão para selecionar a pasta raiz
elements.selectFolderBtn.addEventListener('click', async () => {
    const folderPath = await window.electronAPI.selectRootFolder();
    if (folderPath) {
        elements.rootFolder.value = folderPath;
    }
});

// Botão de "Sobre"
elements.aboutBtn.addEventListener('click', () => {
    window.electronAPI.showAboutDialog();
});

// Botão para iniciar a automação
elements.startBtn.addEventListener('click', () => {
    // Coleta todos os dados dos campos de entrada
    const config = {
        CNPJ_EMPRESA: elements.cnpj.value,
        CODIGO_OBRA: elements.obra.value,
        CPF_USUARIO: elements.cpf.value,
        SENHA_USUARIO: elements.senha.value,
        caminho_arquivo_excel: elements.excelPath.value,
        pasta_raiz_motoristas: elements.rootFolder.value,
    };

    // Validação simples para garantir que todos os campos estão preenchidos
    for (const key in config) {
        if (!config[key]) {
            addLog(`ERRO: O campo "${key}" é obrigatório.`, 'error');
            window.electronAPI.showErrorDialog('Campo Obrigatório', `Por favor, preencha o campo: ${key}`);
            return;
        }
    }

    // Desabilita os controles e inicia o processo
    setControlsEnabled(false);
    addLog('Iniciando automação...', 'info_final');
    updateProgress(0, 0, 'Iniciando...');
    
    // Envia a configuração para o processo principal do Electron
    window.electronAPI.startAutomation(config);
});


// --- Handlers para Eventos Vindos do Processo Principal (Python) ---

// Ouve por novas mensagens de log
window.electronAPI.onLogMessage((_event, { message, level }) => {
    addLog(message, level);
});

// Ouve por atualizações na barra de progresso
window.electronAPI.onProgressUpdate((_event, { current, total, message }) => {
    updateProgress(current, total, message);
});

// Ouve pelo sinal de que a automação terminou
window.electronAPI.onAutomationFinished(() => {
    addLog('Automação finalizada.', 'info_final');
    setControlsEnabled(true);
});
