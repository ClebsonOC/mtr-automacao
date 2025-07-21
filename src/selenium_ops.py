import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException, TimeoutException,
    NoSuchElementException, WebDriverException, ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
try:
    from pywinauto import Application # type: ignore
except ImportError:
    Application = None
import psutil
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from config_mtr import CONFIG, log_message, update_gui_progress_data, navegador_global # Importa de config_mtr
from file_ops import get_expected_filename, salvar_planilha # Importa de file_ops

# Definindo os seletores de carregamento aqui, pois são específicos do Selenium
CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"] = [
    (By.CLASS_NAME, "ui-widget-overlay", 5),
]

def esperar_elementos_de_carregamento_sumirem(driver, seletores_com_timeout, timeout_padrao_elemento=15):
    if not seletores_com_timeout: return
    for item_seletor in seletores_com_timeout:
        by_tipo, valor_seletor, *timeout_opt = item_seletor
        timeout_especifico = timeout_opt[0] if timeout_opt else timeout_padrao_elemento
        try:
            WebDriverWait(driver, timeout_especifico).until(EC.invisibility_of_element_located((by_tipo, valor_seletor)))
        except TimeoutException:
            log_message(f"ALERTA: Elemento '{valor_seletor}' não sumiu em {timeout_especifico}s.", "warning")
        except Exception as e:
            log_message(f"Erro ao esperar carregador '{valor_seletor}': {e}", "error")

def iniciar_ou_reiniciar_navegador():
    # Acessa e modifica o navegador_global de config_mtr
    config_mtr_module = __import__('config_mtr') # Para poder modificar a variável global
    
    if config_mtr_module.navegador_global:
        try:
            log_message("Fechando navegador anterior..."); config_mtr_module.navegador_global.quit()
        except WebDriverException as wde:
            log_message(f"Exceção ao fechar navegador: {wde}", "warning")
        except Exception as e:
            log_message(f"Erro inesperado ao fechar navegador: {e}", "error")
        finally:
            config_mtr_module.navegador_global = None
    log_message("Iniciando Chrome...")
    chrome_options = Options()
    if not os.path.exists(CONFIG["pasta_download_temporaria"]):
        try: os.makedirs(CONFIG["pasta_download_temporaria"])
        except Exception as e_mkdir: log_message(f"Falha criar pasta temp: {e_mkdir}", "error"); return False
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": CONFIG["pasta_download_temporaria"],
        "download.prompt_for_download": False, "download.directory_upgrade": True,
        "safeBrowse.enabled": True
    })
    chrome_options.add_argument("--log-level=3") # Reduz logs do ChromeDriver
    # chrome_options.add_argument("--headless") # Descomente para rodar sem interface gráfica
    # chrome_options.add_argument("--disable-gpu") # Útil em alguns ambientes headless
    # chrome_options.add_argument("--window-size=1920,1080") # Útil para headless

    try:
        servico = Service(ChromeDriverManager().install())
        config_mtr_module.navegador_global = webdriver.Chrome(service=servico, options=chrome_options)
        log_message("Chrome iniciado."); time.sleep(2); return True
    except Exception as e:
        log_message(f"Falha crítica ao iniciar Chrome: {e}", "error"); config_mtr_module.navegador_global = None; return False

def login_sistema(driver):
    log_message("Acessando login MTR..."); driver.get(CONFIG["SITE_URL"])
    esperar_elementos_de_carregamento_sumirem(driver, [(By.ID, "divAguarde", 120)] + CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"])
    log_message("Página de login carregada.")
    try:
        if Application: # pywinauto
            try:
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
        
        # --- INÍCIO DA ADIÇÃO ---
        # Adicionado para clicar no botão de popup que pode aparecer após o login.
        try:
            log_message("Procurando por popup de aviso após o login...")
            # O XPath fornecido é absoluto e pode quebrar se a estrutura do site mudar.
            # Usamos um timeout curto para não atrasar o processo se o popup não existir.
            popup_button_xpath = "/html/body/div[15]/div[1]/button"
            popup_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, popup_button_xpath))
            )
            log_message("Botão do popup encontrado. Clicando para fechar.")
            popup_button.click()
            time.sleep(1) # Pausa para garantir que o popup foi fechado.
            log_message("Popup fechado.")
        except TimeoutException:
            log_message("Nenhum popup de aviso encontrado após o login (o que é normal).")
        except Exception as e:
            log_message(f"Erro ao tentar fechar o popup de aviso: {e}", "warning")
        # --- FIM DA ADIÇÃO ---
        
        WebDriverWait(driver, 25).until(EC.element_to_be_clickable((By.XPATH, '//li/a[text()="Manifesto"]'))).click()
        esperar_elementos_de_carregamento_sumirem(driver, CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=20)
        WebDriverWait(driver, 25).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="dv_principal_menu"]/ul/li[2]/ul/li[4]/a'))).click()
        esperar_elementos_de_carregamento_sumirem(driver, [(By.ID, "divAguarde", 45)] + CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"], timeout_padrao_elemento=30)
        log_message("Navegado para 'Meus MTRs'."); return True
    except TimeoutException as te: log_message(f"Timeout login/navegação: {te}", "error"); return False
    except Exception as e: log_message(f"Erro login/navegação: {e}", "error"); return False

def esperar_download_concluir(pasta_destino, nome_arquivo, timeout=15):
    t_ini = time.time(); path_arq = os.path.join(pasta_destino, nome_arquivo)
    log_message(f"Aguardando download '{nome_arquivo}'...")
    while time.time() - t_ini < timeout:
        if os.path.exists(path_arq):
            try:
                sz_ini = os.path.getsize(path_arq)
                if sz_ini == 0: time.sleep(1); continue
                time.sleep(2) # Pausa original para estabilidade
                if not os.path.exists(path_arq): log_message(f"AVISO: '{nome_arquivo}' sumiu.", "warning"); return False
                sz_fim = os.path.getsize(path_arq)
                if sz_fim == sz_ini and sz_fim > 0: log_message(f"'{nome_arquivo}' baixado (Tam: {sz_fim}B)."); return True
            except FileNotFoundError: time.sleep(0.5); continue
            except Exception as e: log_message(f"Erro verificar tam '{nome_arquivo}': {e}", "warning"); time.sleep(0.5); continue
        time.sleep(0.5)
    log_message(f"Timeout download '{nome_arquivo}'.", "warning"); return False

# Dentro de selenium_ops.py
# ... (imports e outras funções do selenium_ops.py) ...

def processar_downloads_para_pasta_temp(driver, planilha_df):
    log_message("Iniciando downloads para pasta temp...")
    mtr_processar = planilha_df[~planilha_df[CONFIG["coluna_status"]].astype(str).str.upper().isin(["OK","NAO ENCONTRADO","OK_TEMP"]) & \
                                ~planilha_df[CONFIG["coluna_status"]].astype(str).str.contains("ERRO",case=False,na=False)]
    total_nesta_rodada = len(mtr_processar); baixados_rodada = 0
    update_gui_progress_data(baixados_rodada, total_nesta_rodada, "Iniciando downloads...")
    for i in planilha_df.index:
        row = planilha_df.loc[i]; stat_pular = str(row[CONFIG["coluna_status"]]).upper()
        if stat_pular in ["OK","NAO ENCONTRADO","OK_TEMP"] or ("ERRO" in stat_pular and stat_pular!=""): continue
        num_mtr = str(row[CONFIG["coluna_manifesto"]]); nome_arq_esp = get_expected_filename(num_mtr)
        path_arq_temp = os.path.join(CONFIG["pasta_download_temporaria"], nome_arq_esp)
        tent_refresh = 0
        while True:
            tent_refresh+=1; log_message(f"Processando MTR {num_mtr} (Tentativa {tent_refresh})...")
            try:
                WebDriverWait(driver,25).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                esperar_elementos_de_carregamento_sumirem(driver,CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],15)
                in_mtr = WebDriverWait(driver,25).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                in_mtr.clear(); in_mtr.send_keys(num_mtr)
                WebDriverWait(driver,25).until(EC.element_to_be_clickable((By.XPATH,'//*[@id="btnPesquisaMTR"]'))).click()
                esperar_elementos_de_carregamento_sumirem(driver,[(By.CLASS_NAME,"ui-widget-overlay",20)]+CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],30)
                xpath_dl = '//*[@id="tbMTR"]/tbody/tr/td[6]/img[2]'; dl_clicado = False
                for sub_tent in range(3):
                    try:
                        esperar_elementos_de_carregamento_sumirem(driver,[(By.CLASS_NAME,"ui-widget-overlay",25)],5)
                        WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.XPATH,xpath_dl))).click()
                        dl_clicado=True; break
                    except StaleElementReferenceException:
                        log_message(f"Stale ícone (sub {sub_tent+1}).","warning")
                        if sub_tent==2: raise 
                        time.sleep(0.5)
                    except TimeoutException:
                        log_message(f"Timeout ícone (sub {sub_tent+1}).","warning")
                        try:
                            if driver.find_element(By.XPATH,"//*[@id='tbMTR']/tbody/tr/td[contains(text(),'Nenhum MTR encontrado')]").is_displayed():
                                log_message(f"MTR {num_mtr} NÃO ENCONTRADO.")
                                planilha_df.at[i,CONFIG["coluna_status"]]="NAO ENCONTRADO"
                                salvar_planilha(planilha_df)
                                break # Sai do loop de sub_tentativas
                        except NoSuchElementException:
                            if sub_tent==2: raise # Re-levanta a TimeoutException original
                    except ElementClickInterceptedException as eci:
                        log_message(f"Clique ícone interceptado (sub {sub_tent+1}).","warning")
                        if sub_tent==2: raise 
                        time.sleep(1)
                if planilha_df.at[i,CONFIG["coluna_status"]]=="NAO ENCONTRADO": 
                    baixados_rodada+=1
                    update_gui_progress_data(baixados_rodada,total_nesta_rodada,f"MTR {num_mtr}: Não Encontrado")
                    break # Sai do while True para este MTR
                if dl_clicado:
                    if esperar_download_concluir(CONFIG["pasta_download_temporaria"],nome_arq_esp):
                        planilha_df.at[i,CONFIG["coluna_status"]]="OK_TEMP"
                        log_message(f"MTR {num_mtr} baixado para temp.")
                        baixados_rodada+=1
                        update_gui_progress_data(baixados_rodada,total_nesta_rodada,f"MTR {num_mtr}: Baixado temp")
                    else:
                        log_message(f"Falha confirmar download {num_mtr}.","error")
                        if os.path.exists(path_arq_temp):
                            try:
                                os.remove(path_arq_temp)
                            except Exception as e_rem:
                                log_message(f"Erro remover temp: {e_rem}","error")
                        raise TimeoutException(f"Falha download MTR {num_mtr}, refresh.")
                    salvar_planilha(planilha_df) # Salva OK_TEMP
                    break # Sai do while True para este MTR
                else: # Se não foi clicado e não é "NAO ENCONTRADO"
                    if planilha_df.at[i, CONFIG["coluna_status"]] != "NAO ENCONTRADO":
                        log_message(f"Não clicou download {num_mtr} (sub-tentativas).","error")
                        raise TimeoutException(f"Falha clicar download MTR {num_mtr}, refresh.")
            except (TimeoutException,StaleElementReferenceException,NoSuchElementException,ElementClickInterceptedException) as e_int:
                log_message(f"Erro ({type(e_int).__name__}) MTR {num_mtr}. Recarregando...","warning")
                try:
                    driver.refresh()
                    WebDriverWait(driver,35).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                    esperar_elementos_de_carregamento_sumirem(driver,[(By.ID,"divAguarde",45)]+CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],25)
                except Exception as e_ref: 
                    log_message(f"ERRO CRÍTICO refresh: {e_ref}.","error")
                    return False # Sinaliza para reiniciar o navegador
            except WebDriverException as wde_g: 
                log_message(f"WebDriverException GRAVE MTR {num_mtr}: {wde_g}.","error")
                return False # Sinaliza para reiniciar o navegador
            except Exception as e_inesp:
                log_message(f"Erro INESPERADO ({type(e_inesp).__name__}) MTR {num_mtr}.","error")
                try:
                    driver.refresh()
                    WebDriverWait(driver,35).until(EC.presence_of_element_located((By.XPATH,'//*[@id="txtNumeroManifesto"]')))
                    esperar_elementos_de_carregamento_sumirem(driver,[(By.ID,"divAguarde",45)]+CONFIG["SELETORES_DE_CARREGAMENTO_ADICIONAIS"],25)
                except Exception as e_ref_i: 
                    log_message(f"ERRO CRÍTICO refresh pós erro: {e_ref_i}.","error")
                    return False # Sinaliza para reiniciar o navegador
        time.sleep(1.0)
    log_message("Downloads da rodada concluídos.")
    update_gui_progress_data(baixados_rodada,total_nesta_rodada,"Downloads da rodada concluídos.")
    return True
