import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox # Adicionado messagebox
import os
import time
import queue
import threading

# Importações da Pillow para manipulação de imagens
from PIL import Image, ImageTk

from config_mtr import CONFIG, gui_queue, log_message

class ApplicationGUI:
    def __init__(self, root_window, start_automation_callback):
        self.root = root_window
        self.start_automation_callback = start_automation_callback
        self.root.title("Automação MTR INEA v1.7")
        # Aumentei um pouco a altura padrão para acomodar a imagem do logo e o botão Sobre
        self.root.geometry("750x820") # Ajuste conforme necessário

        self.dialog_is_open = False
        style = ttk.Style(self.root)
        style.theme_use('clam') # Ou outro tema como 'alt', 'default', 'classic'

        # --- Bloco para Adicionar o Logo do INEA ---
        try:
            # Certifique-se que o arquivo 'logo_inea.jpg' está na mesma pasta do script
            image_path = "logo_inea.jpg"
            pil_image_original = Image.open(image_path)

            # Redimensionar a imagem para um tamanho adequado para a GUI
            # Mantendo a proporção. Ajuste 'target_width' conforme necessário.
            target_width = 200 # Largura desejada para o logo na GUI
            original_width, original_height = pil_image_original.size
            aspect_ratio = original_height / original_width
            target_height = int(target_width * aspect_ratio)
            
            pil_image_resized = pil_image_original.resize((target_width, target_height), Image.Resampling.LANCZOS)

            self.logo_tk_image = ImageTk.PhotoImage(pil_image_resized)

            logo_label = ttk.Label(self.root, image=self.logo_tk_image)
            logo_label.pack(pady=(10, 5)) # pady adiciona espaço vertical acima e abaixo do logo

        except FileNotFoundError:
            self.logo_tk_image = None
            log_message(f"AVISO: Arquivo de imagem do logo ('{image_path}') não encontrado. Verifique o nome e o local do arquivo.", "warning")
        except Exception as e:
            self.logo_tk_image = None
            log_message(f"ERRO ao carregar ou processar a imagem do logo: {e}", "error")
        # --- Fim do Bloco do Logo ---

        input_frame = ttk.LabelFrame(self.root, text="Config. Acesso e Arquivos", padding="10")
        input_frame.pack(padx=10, pady=(5, 5), fill="x")

        fields = {"CNPJ Empresa:": "cnpj_var", "Código Obra:": "obra_var", "CPF Usuário:": "cpf_var", "Senha Usuário:": "senha_var"}
        r_idx = 0
        for lbl_txt, var_n in fields.items():
            ttk.Label(input_frame, text=lbl_txt).grid(row=r_idx, column=0, padx=5, pady=5, sticky="w")
            setattr(self, var_n, tk.StringVar())
            entry = ttk.Entry(input_frame, textvariable=getattr(self, var_n), width=40, show="*" if "Senha" in lbl_txt else "")
            entry.grid(row=r_idx, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
            r_idx += 1

        ttk.Label(input_frame, text="Planilha Excel:").grid(row=r_idx, column=0, padx=5, pady=5, sticky="w")
        self.excel_path_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.excel_path_var, width=50).grid(row=r_idx, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(input_frame, text="Selecionar...", command=self.select_excel_file).grid(row=r_idx, column=2, padx=5, pady=5)
        r_idx += 1

        ttk.Label(input_frame, text="Pasta Raiz Downloads:").grid(row=r_idx, column=0, padx=5, pady=5, sticky="w")
        self.root_folder_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.root_folder_var, width=50).grid(row=r_idx, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
        input_frame.columnconfigure(1, weight=1)

        # Frame para os botões de ação
        action_buttons_frame = ttk.Frame(self.root)
        action_buttons_frame.pack(pady=(5,10))

        self.start_button = ttk.Button(action_buttons_frame, text="Iniciar Automação", command=self.trigger_start_automation_thread, style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, ipadx=10, ipady=5, padx=(0,5))

        # Botão Sobre
        self.about_button = ttk.Button(action_buttons_frame, text="Sobre", command=self.show_about_dialog)
        self.about_button.pack(side=tk.LEFT, ipadx=10, ipady=5, padx=(5,0))

        prog_frame = ttk.Frame(self.root, padding="5")
        prog_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.prog_msg_var = tk.StringVar(value="Aguardando início...")
        ttk.Label(prog_frame, textvariable=self.prog_msg_var, anchor="w").pack(fill="x", pady=(0, 2))
        self.prog_bar = ttk.Progressbar(prog_frame, orient="horizontal", length=300, mode="determinate")
        self.prog_bar.pack(fill="x", expand=True, pady=(0, 2))
        self.prog_lbl_var = tk.StringVar(value="0/0")
        ttk.Label(prog_frame, textvariable=self.prog_lbl_var, anchor="e").pack(fill="x")

        log_frame = ttk.LabelFrame(self.root, text="Logs da Execução", padding="10")
        log_frame.pack(padx=10, pady=(5, 10), fill="both", expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, width=80, font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)
        self.log_area.tag_config("error", foreground="red")
        self.log_area.tag_config("warning", foreground="orange")
        self.log_area.tag_config("info_final", foreground="blue", font=("Consolas", 9, "bold"))
        self.log_area.configure(state='disabled')

        self.process_gui_queue()

    def show_about_dialog(self):
        # Certifique-se de que o diálogo de seleção de arquivo não está aberto
        if self.dialog_is_open:
            log_message("Por favor, feche o diálogo de seleção de arquivo primeiro.", "warning")
            return

        # Informações do desenvolvedor
        dev_name = "Clebson de Oliveira Correia"
        dev_email = "oliveiraclebson007@gmail.com"
        app_version = "1.7" # Você pode pegar da setup.py ou definir aqui

        messagebox.showinfo(
            "Sobre AutomacaoMTR", # Título da janela
            f"Automação MTR INEA v{app_version}\n\n"
            f"Desenvolvido por: {dev_name}\n"
            f"Email: {dev_email}\n"
        )
        log_message("Janela 'Sobre' exibida.")


    def select_excel_file(self):
        log_message("Botão 'Selecionar Planilha Excel' clicado.")
        self.dialog_is_open = True
        self.root.update_idletasks()
        try:
            f_path = filedialog.askopenfilename(parent=self.root, title="Selecionar Planilha", filetypes=(("Excel", "*.xlsx *.xls"), ("Todos os arquivos", "*.*")))
            if f_path:
                self.excel_path_var.set(f_path)
                log_message(f"Planilha selecionada: {f_path}")
            else:
                log_message("Seleção de planilha cancelada.")
        except Exception as e:
            log_message(f"Erro diálogo planilha: {e}", "error")
        finally:
            self.dialog_is_open = False
            # A fila será processada pelo loop principal em self.root.after

    def update_log_area(self, message, level="info"):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n", level)
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

    def update_progress_bar_display(self, current, total, message=""):
        perc = (current / total) * 100 if total > 0 else 0
        self.prog_bar['value'] = perc
        self.prog_lbl_var.set(f"{current}/{total} ({perc:.0f}%)")
        if message: self.prog_msg_var.set(message)
        elif total > 0 and current < total: self.prog_msg_var.set("Processando manifestos...")
        elif total > 0 and current == total: self.prog_msg_var.set("Processamento da rodada concluído.")
        self.root.update_idletasks()

    def process_gui_queue(self):
        if not self.dialog_is_open:
            try:
                while True: # Processa todas as mensagens pendentes na fila
                    msg_type, data = gui_queue.get_nowait()
                    if msg_type == "log": msg, lvl = data; self.update_log_area(msg, lvl)
                    elif msg_type == "progress": curr, tot, msg = data; self.update_progress_bar_display(curr, tot, msg)
                    elif msg_type == "enable_start_button":
                        self.start_button.config(state=tk.NORMAL)
                        self.about_button.config(state=tk.NORMAL) # Habilitar botão sobre também
                        self.prog_msg_var.set("Pronto ou aguardando.")
            except queue.Empty:
                pass # Nenhuma mensagem na fila

        # Reagenda a verificação da fila
        self.root.after(100, self.process_gui_queue)

    def trigger_start_automation_thread(self):
        CONFIG["CNPJ_EMPRESA"] = self.cnpj_var.get().strip()
        CONFIG["CODIGO_OBRA"] = self.obra_var.get().strip()
        CONFIG["CPF_USUARIO"] = self.cpf_var.get().strip()
        CONFIG["SENHA_USUARIO"] = self.senha_var.get().strip()
        CONFIG["caminho_arquivo_excel"] = self.excel_path_var.get().strip()
        CONFIG["pasta_raiz_motoristas"] = self.root_folder_var.get().strip()

        if not all([CONFIG[k] for k in ["CNPJ_EMPRESA", "CODIGO_OBRA", "CPF_USUARIO", "SENHA_USUARIO", "caminho_arquivo_excel", "pasta_raiz_motoristas"]]):
            self.update_log_area("ERRO: Todos os campos devem ser preenchidos!", "error"); return
        if not os.path.isfile(CONFIG["caminho_arquivo_excel"]):
            self.update_log_area(f"ERRO: Excel não achado: '{CONFIG['caminho_arquivo_excel']}'", "error"); return
        if not os.path.isdir(CONFIG["pasta_raiz_motoristas"]):
            self.update_log_area(f"ERRO: Pasta raiz não achada ou inválida: '{CONFIG['pasta_raiz_motoristas']}'", "error"); return

        CONFIG["pasta_download_temporaria"] = os.path.join(CONFIG["pasta_raiz_motoristas"], "temp_downloads")
        self.update_log_area("Iniciando automação...", "info")
        self.start_button.config(state=tk.DISABLED)
        self.about_button.config(state=tk.DISABLED) # Desabilitar botão sobre durante a automação
        self.update_progress_bar_display(0, 0, "Iniciando...")

        threading.Thread(target=self.start_automation_callback, daemon=True).start()

# Comentários para o bloco de teste direto (if __name__ == "__main__":) permanecem os mesmos
# if __name__ == '__main__':
#     def dummy_start_automation():
#         print("Dummy automation started")
#         for i in range(5): # Reduzido para teste rápido
#             time.sleep(1)
#             log_message(f"Dummy log {i+1}", "info") # Usa a função importada
#             if gui_queue:
#                 # Atualiza a GUI através da fila
#                 gui_queue.put(("progress", (i+1, 5, f"Processando item {i+1}")))
#             else:
#                 print(f"PROGRESS: {i+1}/5 - Processing item {i+1}")
#
#         if gui_queue:
#             gui_queue.put(("enable_start_button", None))
#         else:
#             print("ENABLE START BUTTON (dummy)")

#     root = tk.Tk()
#     # Para testar, você precisaria inicializar gui_queue de config_mtr ou mocká-la
#     # gui_queue = queue.Queue() # Se config_mtr.gui_queue não estiver acessível diretamente
#     app = ApplicationGUI(root, start_automation_callback=dummy_start_automation)
#     root.mainloop()