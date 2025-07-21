import os
import shutil
import pandas as pd
from config_mtr import CONFIG, log_message # Importa CONFIG e log_message

def get_expected_filename(manifesto_numero):
    return f"manifesto_{manifesto_numero}.pdf"

def carregar_planilha():
    try:
        planilha = pd.read_excel(CONFIG["caminho_arquivo_excel"], engine='openpyxl')
        if CONFIG["coluna_status"] not in planilha.columns:
            planilha[CONFIG["coluna_status"]] = ""
        planilha[CONFIG["coluna_status"]] = planilha[CONFIG["coluna_status"]].astype(str).fillna("")
        if CONFIG["coluna_manifesto"] not in planilha.columns:
            raise ValueError(f"ERRO CRÍTICO: A coluna '{CONFIG['coluna_manifesto']}' não foi encontrada.")
        planilha[CONFIG["coluna_manifesto"]] = planilha[CONFIG["coluna_manifesto"]].astype(str).str.strip()
        if CONFIG["coluna_motorista"] not in planilha.columns:
            raise ValueError(f"ERRO CRÍTICO: A coluna '{CONFIG['coluna_motorista']}' não foi encontrada.")
        planilha[CONFIG["coluna_motorista"]] = planilha[CONFIG["coluna_motorista"]].astype(str).fillna("").str.strip()
        return planilha
    except FileNotFoundError:
        log_message(f"ERRO CRÍTICO: Arquivo Excel não encontrado: {CONFIG['caminho_arquivo_excel']}", "error"); raise
    except ValueError as ve:
        log_message(str(ve), "error"); raise
    except Exception as e:
        log_message(f"ERRO CRÍTICO ao carregar planilha: {e}", "error"); raise

def salvar_planilha(planilha_df):
    try:
        planilha_df.to_excel(CONFIG["caminho_arquivo_excel"], index=False, engine='openpyxl')
    except Exception as e:
        log_message(f"ERRO ao salvar planilha: {e}", "error")

def verificar_estado_inicial_manifestos_e_atualizar_planilha(planilha_df):
    log_message("Verificando estado inicial MTRs..."); alt = False; todos_ok = True
    for idx, row in planilha_df.iterrows():
        num_mtr = str(row[CONFIG["coluna_manifesto"]]); mot = str(row[CONFIG["coluna_motorista"]]); stat = str(row[CONFIG["coluna_status"]])
        if not mot or mot.lower() == 'nan':
            if stat=="OK": planilha_df.at[idx,CONFIG["coluna_status"]] = ""; alt=True
            todos_ok=False; continue
        path_final = os.path.join(CONFIG["pasta_raiz_motoristas"], mot, get_expected_filename(num_mtr))
        if os.path.exists(path_final):
            if stat!="OK": planilha_df.at[idx,CONFIG["coluna_status"]]="OK"; alt=True; log_message(f"MTR {num_mtr} ({mot}) já existe. OK.")
        else:
            if stat=="OK": planilha_df.at[idx,CONFIG["coluna_status"]]=""; alt=True; log_message(f"MTR {num_mtr} ({mot}) OK mas não achado. Revertido.", "warning")
            todos_ok=False
        if planilha_df.at[idx,CONFIG["coluna_status"]]!="OK": todos_ok=False
    if alt: salvar_planilha(planilha_df)
    log_message(f"Verif. inicial: {'Todos OK.' if todos_ok else 'Pendências encontradas.'}")
    return todos_ok

def tentar_mover_arquivos_da_pasta_temporaria_pendentes(planilha_df):
    log_message("Movendo MTRs pendentes da temp...");
    if not os.path.exists(CONFIG["pasta_download_temporaria"]): log_message(f"Pasta temp não existe.", "warning"); return
    arq_temp = [f for f in os.listdir(CONFIG["pasta_download_temporaria"]) if f.startswith("manifesto_") and f.endswith(".pdf")]
    alt_plan = False
    if not arq_temp: log_message("Nenhum MTR na temp para recuperar."); return
    for nome_arq in arq_temp:
        try:
            num_mtr = nome_arq.replace("manifesto_","").replace(".pdf","")
            if not num_mtr.isdigit(): continue
            linhas = planilha_df[planilha_df[CONFIG["coluna_manifesto"]]==num_mtr]
            if linhas.empty: log_message(f"MTR {num_mtr} ('{nome_arq}') na temp, não na planilha.", "warning"); continue
            idx_mtr = linhas.index[0]; mot = str(planilha_df.at[idx_mtr, CONFIG["coluna_motorista"]]); stat_plan = str(planilha_df.at[idx_mtr, CONFIG["coluna_status"]])
            if not mot or mot.lower()=='nan': log_message(f"MTR {num_mtr} na temp, sem motorista.", "warning"); continue
            orig = os.path.join(CONFIG["pasta_download_temporaria"], nome_arq); pasta_dest_mot = os.path.join(CONFIG["pasta_raiz_motoristas"], mot); dest_final = os.path.join(pasta_dest_mot, nome_arq)
            if not os.path.exists(pasta_dest_mot):
                try: os.makedirs(pasta_dest_mot)
                except Exception as e_mkdir: log_message(f"Erro criar pasta '{pasta_dest_mot}': {e_mkdir}","error"); continue
            shutil.move(orig, dest_final); log_message(f"MTR {num_mtr} ('{nome_arq}') MOVIDO da temp para '{mot}'.")
            if stat_plan!="OK": planilha_df.at[idx_mtr, CONFIG["coluna_status"]]="OK"; alt_plan=True
        except Exception as e: log_message(f"Erro mover '{nome_arq}' da temp: {e}", "error")
    if alt_plan: salvar_planilha(planilha_df)
    log_message("Mov. MTRs pendentes da temp concluído.")

def verificar_downloads_na_pasta_temp(planilha_df):
    log_message("Verificando downloads na temp..."); todos_ok_temp=True; alt_plan=False
    for i in planilha_df.index:
        row=planilha_df.loc[i]
        if str(row[CONFIG["coluna_status"]])=="OK_TEMP":
            num_mtr=str(row[CONFIG["coluna_manifesto"]]);nome_arq=get_expected_filename(num_mtr)
            path_temp=os.path.join(CONFIG["pasta_download_temporaria"],nome_arq)
            if not os.path.exists(path_temp):
                log_message(f"ERRO TEMP: MTR {num_mtr} OK_TEMP, mas NÃO achado. Revertido.","error")
                planilha_df.at[i,CONFIG["coluna_status"]]="";todos_ok_temp=False;alt_plan=True
    if alt_plan:salvar_planilha(planilha_df)
    log_message(f"Verif. temp: {'OK_TEMP encontrados.' if todos_ok_temp else 'Alguns OK_TEMP não achados. Reprocessar.'}")
    return todos_ok_temp

def mover_arquivos_para_pastas_motoristas(planilha_df):
    log_message("Movendo arquivos temp para pastas finais..."); suc_total=True;alt_plan=False
    for i in planilha_df.index:
        row=planilha_df.loc[i]
        if str(row[CONFIG["coluna_status"]])=="OK_TEMP":
            num_mtr=str(row[CONFIG["coluna_manifesto"]]);mot=str(row[CONFIG["coluna_motorista"]])
            if not mot or mot.lower()=='nan':
                log_message(f"ERRO MOVER: MTR {num_mtr} OK_TEMP, sem motorista. Revertido.","error")
                planilha_df.at[i,CONFIG["coluna_status"]]="";suc_total=False;alt_plan=True;continue
            nome_arq=get_expected_filename(num_mtr);orig=os.path.join(CONFIG["pasta_download_temporaria"],nome_arq)
            pasta_dest_mot=os.path.join(CONFIG["pasta_raiz_motoristas"],mot);dest_final=os.path.join(pasta_dest_mot,nome_arq)
            if not os.path.exists(pasta_dest_mot):
                try:os.makedirs(pasta_dest_mot);log_message(f"Pasta motorista '{pasta_dest_mot}' criada.")
                except Exception as e_mkdir:log_message(f"Erro criar pasta '{pasta_dest_mot}':{e_mkdir}","error");planilha_df.at[i,CONFIG["coluna_status"]]="";suc_total=False;alt_plan=True;continue
            if os.path.exists(orig):
                try:
                    if os.path.exists(dest_final):log_message(f"'{nome_arq}' já existe em '{pasta_dest_mot}'.Substituindo.","warning");os.remove(dest_final)
                    shutil.move(orig,dest_final);log_message(f"MTR {num_mtr} MOVIDO para '{pasta_dest_mot}'.")
                    planilha_df.at[i,CONFIG["coluna_status"]]="OK"
                except Exception as e_mov:log_message(f"Erro mover '{nome_arq}':{e_mov}","error");planilha_df.at[i,CONFIG["coluna_status"]]="";suc_total=False;alt_plan=True
            else:
                log_message(f"ERRO INESP. MOVER: '{nome_arq}' (MTR {num_mtr}) NÃO achado na temp. Revertido.","error")
                planilha_df.at[i,CONFIG["coluna_status"]]="";suc_total=False;alt_plan=True
    if alt_plan:salvar_planilha(planilha_df)
    return suc_total

def verificar_arquivos_nas_pastas_motoristas_final(planilha_df):
    log_message("Verificando arquivos pastas finais (pós-movimentação)...");todos_ok_final=True;alt_plan=False
    for i in planilha_df.index:
        row=planilha_df.loc[i]
        if str(row[CONFIG["coluna_status"]])=="OK":
            num_mtr=str(row[CONFIG["coluna_manifesto"]]);mot=str(row[CONFIG["coluna_motorista"]])
            if not mot or mot.lower()=='nan':
                log_message(f"ERRO VERIF. FINAL: MTR {num_mtr} OK, sem motorista. Revertido.","error")
                planilha_df.at[i,CONFIG["coluna_status"]]="";todos_ok_final=False;alt_plan=True;continue
            nome_arq=get_expected_filename(num_mtr);pasta_final_mot=os.path.join(CONFIG["pasta_raiz_motoristas"],mot)
            path_final_arq=os.path.join(pasta_final_mot,nome_arq)
            if not os.path.exists(path_final_arq):
                log_message(f"ERRO VERIF. FINAL: MTR {num_mtr} ({mot}) OK, mas NÃO achado. Revertido.","error")
                planilha_df.at[i,CONFIG["coluna_status"]]="";todos_ok_final=False;alt_plan=True
    if alt_plan:salvar_planilha(planilha_df)
    log_message(f"Verif. final: {'SUCESSO! Todos MTRs OK.' if todos_ok_final else 'FALHA! Alguns MTRs OK não achados. Reprocessar.'}")
    return todos_ok_final