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
    logWrapper: document.getElementById('log-wrapper'), // O contentor da área de log
    robotAnimation: document.getElementById('robot-animation'), // A animação do robô
};

// --- Funções de Atualização da UI ---

/**
 * Adiciona uma mensagem de log à área de logs na tela e garante o auto-scroll.
 * @param {string} message - A mensagem a ser exibida.
 * @param {string} level - O nível do log (e.g., 'info', 'error', 'warning').
 */
function addLog(message, level = 'info') {
    if (elements.logArea.innerHTML.includes('Logs da execução aparecerão aqui...')) {
        elements.logArea.innerHTML = '';
    }
    const logEntry = document.createElement('div');
    logEntry.className = `log-${level}`;
    logEntry.textContent = message;
    elements.logArea.appendChild(logEntry);
    
    // *** AJUSTE DO AUTO-SCROLL ***
    // Rola o contentor para o final para mostrar sempre a última mensagem.
    elements.logWrapper.scrollTop = elements.logWrapper.scrollHeight;
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
 * Habilita ou desabilita os controlos da UI e a animação do robô.
 * @param {boolean} isEnabled - True para habilitar, false para desabilitar.
 */
function setControlsEnabled(isEnabled) {
    elements.startBtn.disabled = !isEnabled;
    elements.aboutBtn.disabled = !isEnabled;
    elements.selectExcelBtn.disabled = !isEnabled;
    elements.selectFolderBtn.disabled = !isEnabled;
    
    const inputs = [elements.cnpj, elements.obra, elements.cpf, elements.senha];
    inputs.forEach(input => input.disabled = !isEnabled);

    // Mostra ou esconde a animação do robô
    if (isEnabled) {
        elements.robotAnimation.classList.add('hidden');
    } else {
        elements.robotAnimation.classList.remove('hidden');
    }
}


// --- Event Listeners para Interação do Utilizador ---

elements.selectExcelBtn.addEventListener('click', async () => {
    const filePath = await window.electronAPI.selectExcelFile();
    if (filePath) {
        elements.excelPath.value = filePath;
    }
});

elements.selectFolderBtn.addEventListener('click', async () => {
    const folderPath = await window.electronAPI.selectRootFolder();
    if (folderPath) {
        elements.rootFolder.value = folderPath;
    }
});

elements.aboutBtn.addEventListener('click', () => {
    window.electronAPI.showAboutDialog();
});

elements.startBtn.addEventListener('click', () => {
    const config = {
        CNPJ_EMPRESA: elements.cnpj.value,
        CODIGO_OBRA: elements.obra.value,
        CPF_USUARIO: elements.cpf.value,
        SENHA_USUARIO: elements.senha.value,
        caminho_arquivo_excel: elements.excelPath.value,
        pasta_raiz_motoristas: elements.rootFolder.value,
    };

    for (const key in config) {
        if (!config[key]) {
            addLog(`ERRO: O campo "${key}" é obrigatório.`, 'error');
            window.electronAPI.showErrorDialog('Campo Obrigatório', `Por favor, preencha o campo: ${key}`);
            return;
        }
    }

    setControlsEnabled(false);
    addLog('Iniciando automação...', 'info_final');
    updateProgress(0, 0, 'Iniciando...');
    
    window.electronAPI.startAutomation(config);
});


// --- Handlers para Eventos Vindos do Processo Principal (Python e Atualizações) ---

window.electronAPI.onLogMessage((_event, { message, level }) => {
    addLog(message, level);
});

window.electronAPI.onProgressUpdate((_event, { current, total, message }) => {
    updateProgress(current, total, message);
});

window.electronAPI.onAutomationFinished(() => {
    addLog('Automação finalizada.', 'info_final');
    setControlsEnabled(true);
});

// Ouve por mensagens do sistema de auto-update
window.electronAPI.onUpdateMessage((_event, { message, level }) => {
    addLog(`[UPDATE] ${message}`, level || 'info');
});
