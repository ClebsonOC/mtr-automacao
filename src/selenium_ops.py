import time
import os
import sys
import traceback
from selenium import webdriver
# A importação do Service não é mais estritamente necessária com o Selenium Manager, mas mantê-la não causa problemas.
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException, TimeoutException,
    NoSuchElementException, WebDriverException, ElementClickInterceptedException
)
# A importação do ChromeDriverManager foi removida, pois usaremos o Selenium Manager integrado.
from selenium.webdriver.chrome.options import Options
try:
    from pywinauto import Application # type: ignore
except ImportError:
    Application = None
import psutil
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Importações de módulos locais do projeto
from config_mtr import CONFIG, log_message, update_gui_progress_data
from file_ops import get_expected_filename, salvar_planilha

# Configuração de seletores adicionais para aguardar o carregamento de elementos
CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"] = [
    (By.CLASS_NAME, "ui-widget-overlay", 5),
]

def find_chrome_executable():
    """Tenta encontrar o executável do Google Chrome (chrome.exe) em locais comuns."""
    possible_paths = [
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google\\Chrome\\Application\\chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Google\\Chrome\\Application\\chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google\\Chrome\\Application\\chrome.exe")
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            log_message(f"Google Chrome executável encontrado em: {path}")
            return path
    return None

def esperar_elementos_de_carregamento_sumirem(driver, seletores_com_timeout, timeout_padrao_elemento=15):
    """Aguarda até que elementos de carregamento (overlays, spinners) fiquem invisíveis."""
    if not seletores_com_timeout: return
    for item_seletor in seletores_com_timeout:
        by_tipo, valor_seletor, *timeout_opt = item_seletor
        timeout_especifico = timeout_opt[0] if timeout_opt else timeout_padrao_elemento
        try:
            WebDriverWait(driver, timeout_especifico).until(EC.invisibility_of_element_located((by_tipo, valor_seletor)))
        except Exception:
            # Ignora exceções de timeout, pois o elemento pode já não estar visível
            pass

def iniciar_ou_reiniciar_navegador():
    """
    Inicia uma nova instância do Google Chrome usando o Selenium Manager integrado
    para baixar e gerenciar o ChromeDriver automaticamente, resolvendo problemas de compatibilidade.
    """
    config_mtr_module = __import__('config_mtr')

    if hasattr(config_mtr_module, 'navegador_global') and config_mtr_module.navegador_global:
        try:
            log_message("Fechando navegador anterior...")
            config_mtr_module.navegador_global.quit()
        except Exception: pass
        finally:
            config_mtr_module.navegador_global = None
            
    log_message("Iniciando Chrome com Selenium Manager...")
    chrome_options = Options()

    chrome_executable_path = find_chrome_executable()
    if chrome_executable_path:
        chrome_options.binary_location = chrome_executable_path
    else:
        log_message("ERRO CRÍTICO: O executável do Google Chrome (chrome.exe) não foi encontrado.", "error")
        return False

    if not os.path.exists(CONFIG["pasta_download_temporaria"]):
        try: os.makedirs(CONFIG["pasta_download_temporaria"])
        except Exception as e_mkdir:
            log_message(f"Falha ao criar pasta temporária: {e_mkdir}", "error")
            return False
            
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(CONFIG["pasta_download_temporaria"]),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    })
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        # --- LÓGICA SIMPLIFICADA USANDO SELENIUM MANAGER ---
        # Ao não especificar um 'service', o Selenium 4.6+ automaticamente usa
        # o Selenium Manager para baixar e configurar o driver correto.
        # Isso elimina a necessidade do webdriver-manager e resolve problemas de arquitetura.
        log_message("Deixando o Selenium Manager encontrar e gerenciar o ChromeDriver.")
        
        config_mtr_module.navegador_global = webdriver.Chrome(options=chrome_options)
        
        log_message("Chrome iniciado com sucesso pelo Selenium Manager.")
        time.sleep(2)
        return True
    except WebDriverException as wde:
        if "WinError 193" in str(wde):
             log_message("ERRO PERSISTENTE (WinError 193): Incompatibilidade de executável.", "error")
             log_message("O Selenium Manager não conseguiu resolver o problema. Verifique se há um antivírus ou política de segurança bloqueando a execução de drivers no seu computador.", "error")
        else:
             log_message(f"Falha crítica ao iniciar o Chrome (WebDriverException): {wde}", "error")
        config_mtr_module.navegador_global = None
        return False
    except Exception as e:
        log_message(f"Falha crítica inesperada ao iniciar o Chrome: {e}", "error")
        log_message(traceback.format_exc(), "error")
        config_mtr_module.navegador_global = None
        return False

def login_sistema(driver):
    """Executa o processo de login no sistema MTR INEA."""
    log_message("Acessando login MTR..."); driver.get(CONFIG["SITE_URL"])
    esperar_elementos_de_carregamento_sumirem(driver, [(By.ID, "divAguarde", 120)] + CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"])
    log_message("Página de login carregada.")
    try:
        # Foco na janela usando pywinauto, se disponível
        if Application:
            try:
                # Acessar o PID do navegador pode ser diferente sem um objeto de serviço explícito
                # Esta parte pode precisar de ajuste ou ser removida se causar problemas.
                if driver.service.process:
                    pid_nav = driver.service.process.pid; pid_real = None
                    for proc in psutil.process_iter(attrs=['pid', 'ppid', 'name']):
                        if proc.info['ppid'] == pid_nav and "chrome" in proc.info['name'].lower(): pid_real = proc.info['pid']; break
                    if pid_real:
                        log_message(f"Conectando Chrome PID: {pid_real} (pywinauto)...")
                        app = Application(backend="uia").connect(process=pid_real, timeout=10)
                        janela = app.top_window()
                        if janela.exists() and janela.is_visible(): janela.set_focus(); log_message("Foco na janela (pywinauto).")
                    else: log_message("AVISO: PID Chrome não encontrado (pywinauto).", "warning")
            except Exception as pywin_e: log_message(f"AVISO: Erro pywinauto: {pywin_e}", "warning")

        # Preenchimento do formulário de login
        WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="rdCnpj"]'))).click()
        cnpj_fld = WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.XPATH, '//*[@id="txtCnpj"]')))
        cnpj_fld.clear(); cnpj_fld.send_keys(CONFIG['CNPJ_EMPRESA']); cnpj_fld.send_keys(Keys.TAB); time.sleep(0.5)
        WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="divUnidade"]/td/table/tbody/tr[1]/td[3]/a/span'))).click()
        esperar_elementos_de_carregamento_sumirem(driver, CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=20)
        WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.ID, "exampleUsuarioUnidade_wrapper")))
        filtro_unidade = WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="exampleUsuarioUnidade_filter"]/input')))
        time.sleep(0.5); filtro_unidade.clear(); filtro_unidade.send_keys(CONFIG['CODIGO_OBRA']); time.sleep(0.8)
        esperar_elementos_de_carregamento_sumirem(driver, CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=15)
        xpath_obra = f"//td[@class='center' and normalize-space(text())='{CONFIG['CODIGO_OBRA']}']"
        WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, xpath_obra))).click(); time.sleep(0.5)
        esperar_elementos_de_carregamento_sumirem(driver, CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=15)
        cpf_fld = WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.XPATH, '//*[@id="txtCpfUsuario"]')))
        cpf_fld.clear(); cpf_fld.send_keys(CONFIG['CPF_USUARIO'])
        senha_fld = WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.XPATH, '//*[@id="txtSenha"]')))
        senha_fld.clear(); senha_fld.send_keys(CONFIG['SENHA_USUARIO'])
        WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btEntrar"]'))).click()
        esperar_elementos_de_carregamento_sumirem(driver, [(By.ID, "divAguarde", 60)] + CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=30)
        
        # Lida com possível popup de aviso após o login
        try:
            log_message("Procurando por popup de aviso após o login...")
            popup_button_xpath = "/html/body/div[15]/div[1]/button"
            popup_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, popup_button_xpath)))
            log_message("Botão do popup encontrado. Clicando para fechar.")
            popup_button.click(); time.sleep(1); log_message("Popup fechado.")
        except TimeoutException:
            log_message("Nenhum popup de aviso encontrado após o login (o que é normal).")
        except Exception as e:
            log_message(f"Erro ao tentar fechar o popup de aviso: {e}", "warning")
        
        # Navegação até a página "Meus MTRs"
        WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, '//li/a[text()="Manifesto"]'))).click()
        esperar_elementos_de_carregamento_sumirem(driver, CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=20)
        WebDriverWait(driver, 25).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="dv_principal_menu"]/ul/li[2]/ul/li[4]/a'))).click()
        esperar_elementos_de_carregamento_sumirem(driver, [(By.ID, "divAguarde", 45)] + CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=30)
        log_message("Navegado para 'Meus MTRs'."); return True
    except TimeoutException as te: log_message(f"Timeout durante login/navegação: {te}", "error"); return False
    except Exception as e: log_message(f"Erro inesperado durante login/navegação: {e}", "error"); return False

def esperar_download_concluir(pasta_destino, nome_arquivo, timeout=20):
    """Aguarda a conclusão do download de um arquivo, verificando se o tamanho parou de mudar."""
    t_ini = time.time(); path_arq = os.path.join(pasta_destino, nome_arquivo)
    log_message(f"Aguardando download '{nome_arquivo}'...")
    while time.time() - t_ini < timeout:
        if os.path.exists(path_arq):
            try:
                sz_ini = os.path.getsize(path_arq)
                if sz_ini == 0: time.sleep(1); continue
                time.sleep(2) # Espera um pouco para ver se o tamanho do arquivo muda
                if not os.path.exists(path_arq): log_message(f"AVISO: '{nome_arquivo}' desapareceu após verificação inicial.", "warning"); return False
                sz_fim = os.path.getsize(path_arq)
                if sz_fim == sz_ini and sz_fim > 0: log_message(f"'{nome_arquivo}' baixado com sucesso (Tamanho: {sz_fim}B)."); return True
            except FileNotFoundError: time.sleep(0.5); continue
            except Exception as e: log_message(f"Erro ao verificar tamanho do arquivo '{nome_arquivo}': {e}", "warning"); time.sleep(0.5); continue
        time.sleep(0.5)
    log_message(f"Timeout ao aguardar download do arquivo '{nome_arquivo}'.", "warning"); return False

def processar_downloads_para_pasta_temp(driver, planilha_df):
    """Processa a lista de MTRs da planilha, baixando os PDFs para uma pasta temporária."""
    log_message("Iniciando downloads para pasta temporária...")
    # Filtra MTRs que ainda não foram processados com sucesso
    mtr_processar = planilha_df[~planilha_df[CONFIG["coluna_status"]].astype(str).str.upper().isin(["OK","NAO ENCONTRADO","OK_TEMP"]) & \
                                ~planilha_df[CONFIG["coluna_status"]].astype(str).str.contains("ERRO",case=False,na=False)]
    total_nesta_rodada = len(mtr_processar); baixados_rodada = 0
    update_gui_progress_data(baixados_rodada, total_nesta_rodada, "Iniciando downloads...")
    
    for i in planilha_df.index:
        row = planilha_df.loc[i]; stat_pular = str(row[CONFIG["coluna_status"]]).upper()
        if stat_pular in ["OK", "NAO ENCONTRADO", "OK_TEMP"] or ("ERRO" in stat_pular and stat_pular != ""): continue
        
        num_mtr = str(row[CONFIG["coluna_manifesto"]]); nome_arq_esp = get_expected_filename(num_mtr)
        path_arq_temp = os.path.join(CONFIG["pasta_download_temporaria"], nome_arq_esp)
        
        tent_refresh = 0
        while True: # Loop de tentativa para cada MTR
            tent_refresh += 1; log_message(f"Processando MTR {num_mtr} (Tentativa {tent_refresh})...")
            try:
                # Lógica de busca e clique no MTR
                WebDriverWait(driver,25).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                esperar_elementos_de_carregamento_sumirem(driver,CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],15)
                in_mtr = WebDriverWait(driver,25).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                in_mtr.clear(); in_mtr.send_keys(num_mtr)
                WebDriverWait(driver,25).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="btnPesquisaMTR"]'))).click()
                esperar_elementos_de_carregamento_sumirem(driver,[(By.CLASS_NAME,"ui-widget-overlay",20)]+CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],30)
                
                xpath_dl = '//*[@id="tbMTR"]/tbody/tr/td[6]/img[2]'; dl_clicado = False
                for sub_tent in range(3): # Sub-tentativas para clicar no ícone de download
                    try:
                        esperar_elementos_de_carregamento_sumirem(driver,[(By.CLASS_NAME,"ui-widget-overlay",25)],5)
                        WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.XPATH,xpath_dl))).click()
                        dl_clicado=True; break
                    except StaleElementReferenceException:
                        log_message(f"Ícone de download instável (tentativa {sub_tent+1}). Retentando.","warning"); time.sleep(0.5)
                        if sub_tent==2: raise 
                    except TimeoutException:
                        log_message(f"Timeout ao buscar ícone de download (tentativa {sub_tent+1}).","warning")
                        try:
                            if driver.find_element(By.XPATH,"//*[@id='tbMTR']/tbody/tr/td[contains(text(),'Nenhum MTR encontrado')]").is_displayed():
                                log_message(f"MTR {num_mtr} NÃO ENCONTRADO no sistema.")
                                planilha_df.at[i,CONFIG["coluna_status"]]="NAO ENCONTRADO"; salvar_planilha(planilha_df); break 
                        except NoSuchElementException:
                            if sub_tent==2: raise 
                    except ElementClickInterceptedException:
                        log_message(f"Clique no ícone de download interceptado (tentativa {sub_tent+1}). Retentando.","warning"); time.sleep(1)
                        if sub_tent==2: raise 
                
                if planilha_df.at[i,CONFIG["coluna_status"]]=="NAO ENCONTRADO": 
                    baixados_rodada+=1; update_gui_progress_data(baixados_rodada,total_nesta_rodada,f"MTR {num_mtr}: Não Encontrado"); break 
                
                if dl_clicado:
                    if esperar_download_concluir(CONFIG["pasta_download_temporaria"],nome_arq_esp):
                        planilha_df.at[i,CONFIG["coluna_status"]]="OK_TEMP"
                        log_message(f"MTR {num_mtr} baixado para a pasta temporária.")
                        baixados_rodada+=1; update_gui_progress_data(baixados_rodada,total_nesta_rodada,f"MTR {num_mtr}: Baixado (temp)")
                    else:
                        log_message(f"Falha ao confirmar o download do MTR {num_mtr}.","error")
                        if os.path.exists(path_arq_temp):
                            try: os.remove(path_arq_temp)
                            except Exception as e_rem: log_message(f"Erro ao remover arquivo temporário corrompido: {e_rem}","error")
                        raise TimeoutException(f"Falha no download do MTR {num_mtr}, recarregando página.")
                    salvar_planilha(planilha_df); break 
                else: 
                    if planilha_df.at[i, CONFIG["coluna_status"]] != "NAO ENCONTRADO":
                        log_message(f"Não foi possível clicar no ícone de download para o MTR {num_mtr} após várias tentativas.","error")
                        raise TimeoutException(f"Falha ao clicar no download do MTR {num_mtr}, recarregando página.")
            
            except (TimeoutException,StaleElementReferenceException,NoSuchElementException,ElementClickInterceptedException) as e_int:
                log_message(f"Erro ({type(e_int).__name__}) ao processar MTR {num_mtr}. Recarregando a página...","warning")
                try:
                    driver.refresh()
                    WebDriverWait(driver,35).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                    esperar_elementos_de_carregamento_sumirem(driver,[(By.ID,"divAguarde",45)]+CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],25)
                except Exception as e_ref: 
                    log_message(f"ERRO CRÍTICO ao recarregar a página: {e_ref}. Reiniciando navegador.","error"); return False 
            except WebDriverException as wde_g: 
                log_message(f"WebDriverException GRAVE no MTR {num_mtr}: {wde_g}. Reiniciando navegador.","error"); return False 
            except Exception as e_inesp:
                log_message(f"Erro INESPERADO ({type(e_inesp).__name__}) no MTR {num_mtr}.","error")
                try:
                    driver.refresh()
                    WebDriverWait(driver,35).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                    esperar_elementos_de_carregamento_sumirem(driver,[(By.ID,"divAguarde",45)]+CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],25)
                except Exception as e_ref_i: 
                    log_message(f"ERRO CRÍTICO ao recarregar página após erro inesperado: {e_ref_i}. Reiniciando navegador.","error"); return False 
        time.sleep(1.0)
    
    log_message("Downloads da rodada concluídos.")
    update_gui_progress_data(baixados_rodada,total_nesta_rodada,"Downloads da rodada concluídos.")
    return True
