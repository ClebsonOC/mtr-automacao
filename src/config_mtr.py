import json
import sys
import time

# --- Dicionário de Configuração Global ---
# Valores padrão que serão sobrescritos pelos dados da interface Electron.
CONFIG = {
    "pasta_raiz_motoristas": "",
    "pasta_download_temporaria": "",
    "caminho_arquivo_excel": "",
    "coluna_manifesto": 'MTR Nº',
    "coluna_status": 'STATUS BAIXADO',
    "coluna_motorista": 'Motorista',
    "CNPJ_EMPRESA": "",
    "CODIGO_OBRA": "",
    "CPF_USUARIO": "",
    "SENHA_USUARIO": "",
    "SITE_URL": "http://mtr.inea.rj.gov.br/index.jsp?page=login.jsp",
    "SELETORES_DE_CARREGAMENTO_ADICIONAIS": [] # Preenchido no selenium_ops
}

# Variável global para manter a instância do navegador
navegador_global = None

# --- Funções de Comunicação com o Frontend (via stdout) ---

def _send_to_electron(data_type, payload):
    """
    Envia um objeto JSON para o stdout para ser capturado pelo Electron.
    Garante que a saída seja 'flushed' para envio imediato.
    """
    message = json.dumps({"type": data_type, "payload": payload})
    print(message, flush=True)

def log_message(message, level="info"):
    """
    Envia uma mensagem de log para o frontend.
    Args:
        message (str): A mensagem de log.
        level (str): O nível do log ('info', 'warning', 'error', 'info_final').
    """
    timestamp = time.strftime('%H:%M:%S')
    formatted_message = f"[{timestamp}] {message}"
    _send_to_electron("log", {"message": formatted_message, "level": level})

def update_gui_progress_data(current, total, message=""):
    """
    Envia dados de progresso para o frontend.
    Args:
        current (int): O número atual de itens processados.
        total (int): O número total de itens a processar.
        message (str): Uma mensagem descritiva do estado atual.
    """
    _send_to_electron("progress", {"current": current, "total": total, "message": message})
