import sys
import os
import json
import time

# --- CORREÇÃO CRUCIAL ---
# Adiciona o diretório onde este script (main.py) está localizado ao path do Python.
# Isto garante que, mesmo quando o programa está instalado e é executado de um
# local diferente (ex: C:\Program Files\...), o Python consegue encontrar
# os outros ficheiros .py (config_mtr, file_ops, etc.) que estão na mesma pasta.
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)
# --- FIM DA CORREÇÃO ---


# Agora, as importações locais irão funcionar corretamente
from config_mtr import CONFIG, log_message
from file_ops import (
    carregar_planilha, tentar_mover_arquivos_da_pasta_temporaria_pendentes,
    verificar_estado_inicial_manifestos_e_atualizar_planilha,
    verificar_downloads_na_pasta_temp, mover_arquivos_para_pastas_motoristas,
    verificar_arquivos_nas_pastas_motoristas_final
)
from selenium_ops import (
    iniciar_ou_reiniciar_navegador, login_sistema,
    processar_downloads_para_pasta_temp
)
from selenium.common.exceptions import WebDriverException

def run_automation_logic():
    """
    Função principal que executa toda a lógica de automação.
    """
    config_module = __import__('config_mtr')

    if not os.path.exists(CONFIG["pasta_download_temporaria"]):
        try:
            os.makedirs(CONFIG["pasta_download_temporaria"])
            log_message(f"Pasta temp criada: '{CONFIG['pasta_download_temporaria']}'")
        except Exception as e_mk:
            log_message(f"ERRO CRÍTICO ao criar pasta temp: {e_mk}", "error")
            return

    ciclo = 0
    while True:
        ciclo += 1
        log_message(f"\n--- CICLO Nº {ciclo} ---")
        try:
            planilha_df = carregar_planilha()
        except Exception:
            log_message("Falha crítica ao carregar a planilha. Verifique o caminho e o arquivo.", "error")
            break
        
        tentar_mover_arquivos_da_pasta_temporaria_pendentes(planilha_df)
        planilha_df = carregar_planilha()
        
        if verificar_estado_inicial_manifestos_e_atualizar_planilha(planilha_df):
            log_message("Todos os MTRs já estão processados. Encerrando.", "info_final")
            break
        
        reiniciar_nav = False
        if config_module.navegador_global is None:
            reiniciar_nav = True
        else:
            try:
                _ = config_module.navegador_global.window_handles
            except WebDriverException:
                log_message("Navegador não está respondendo. Reiniciando.", "warning")
                reiniciar_nav = True
        
        if reiniciar_nav:
            if not iniciar_ou_reiniciar_navegador():
                log_message("Não foi possível iniciar o navegador. Tentando novamente no próximo ciclo.", "error")
                time.sleep(5)
                continue
            if not login_sistema(config_module.navegador_global):
                log_message("Falha no login. O navegador será fechado. Tentando novamente no próximo ciclo.", "error")
                if config_module.navegador_global:
                    try: config_module.navegador_global.quit()
                    except Exception: pass
                config_module.navegador_global = None
                time.sleep(5)
                continue
        
        if not processar_downloads_para_pasta_temp(config_module.navegador_global, planilha_df):
            log_message("Ocorreu um problema crítico durante o download que requer o reinício do navegador.", "error")
            if config_module.navegador_global:
                try: config_module.navegador_global.quit()
                except Exception: pass
            config_module.navegador_global = None
            time.sleep(4)
            continue
            
        planilha_df = carregar_planilha()
        if not verificar_downloads_na_pasta_temp(planilha_df):
            log_message("Verificação na pasta temporária falhou. Reiniciando ciclo.", "warning")
            time.sleep(3)
            continue
            
        planilha_df = carregar_planilha()
        if not mover_arquivos_para_pastas_motoristas(planilha_df):
            log_message("Falha ao mover arquivos para as pastas dos motoristas. Reiniciando ciclo.", "warning")
            time.sleep(3)
            continue
            
        planilha_df = carregar_planilha()
        if verificar_arquivos_nas_pastas_motoristas_final(planilha_df):
            log_message("SUCESSO! Todos os MTRs foram baixados e organizados corretamente.", "info_final")
            break
        else:
            log_message("Verificação final falhou. Alguns arquivos não foram encontrados. Reiniciando ciclo.", "warning")
            time.sleep(3)
            
    if config_module.navegador_global:
        try:
            log_message("Encerrando navegador...")
            config_module.navegador_global.quit()
            config_module.navegador_global = None
        except Exception as e_q:
            log_message(f"Erro ao fechar o navegador: {e_q}", "warning")
            config_module.navegador_global = None
            
    log_message("Script finalizado.", "info_final")

if __name__ == "__main__":
    try:
        input_data = sys.stdin.read()
        config_from_electron = json.loads(input_data)
        
        CONFIG.update(config_from_electron)
        
        CONFIG["pasta_download_temporaria"] = os.path.join(CONFIG["pasta_raiz_motoristas"], "temp_downloads")

        run_automation_logic()

    except Exception as e:
        import traceback
        log_message(f"ERRO FATAL NO SCRIPT PYTHON: {e}", "error")
        log_message(traceback.format_exc(), "error")

