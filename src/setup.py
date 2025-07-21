from cx_Freeze import setup, Executable

# --- OPÇÕES DE BUILD ---
# Lista de pacotes que seu projeto utiliza diretamente e que o cx_Freeze deve incluir.
packages_to_include = [
    "tkinter",        # Essencial para a sua GUI
    "selenium",       # Usado para automação web
    "os",             # Funções do sistema operacional
    "sys",            # Parâmetros e funções específicas do sistema
    "time",           # Funções de tempo
    "queue",          # Usado para comunicação entre threads (config_mtr.py, gui.py)
    "pandas",         # Para manipulação de planilhas Excel (file_ops.py)
    "openpyxl",       # Motor para o pandas ler/escrever arquivos .xlsx (file_ops.py)
    "psutil",         # Para interagir com processos do sistema (selenium_ops.py)
    "webdriver_manager", # Para gerenciar drivers do Selenium (selenium_ops.py)
    "PIL",            # Para manipulação de imagens (ex: logo na GUI)
    # "pywinauto" foi removido pois é uma dependência opcional e não estava instalada.
]

# Lista de pacotes que você deseja excluir explicitamente.
packages_to_exclude = [
    "PySide6",
    "PyQt5",
    "PyQt6",
]

# Arquivos adicionais que precisam ser incluídos (ex: ícones, arquivos de dados).
# Se a imagem do logo não estiver na mesma pasta do script principal ao ser executado,
# você pode precisar incluí-la aqui, mas como vamos carregá-la a partir do diretório
# do script, geralmente não é necessário para este caso específico.
include_files = [
    # "logo_inea.jpg", # Geralmente não necessário se o script acessa a imagem no mesmo diretório
    # Exemplo: "seu_icone.ico", ("pasta_de_dados/", "pasta_de_dados_no_build/")
]

build_exe_options = {
    "packages": packages_to_include,
    "excludes": packages_to_exclude,
    "include_files": include_files,
}

# --- DEFINIÇÃO DO EXECUTÁVEL ---
script_principal = "main.py"
nome_do_executavel = "AutomacaoMTR.exe"
base = "Win32GUI" # Para aplicações com interface gráfica (sem console)

setup(
    name="AutomacaoMTR",
    version="1.7",
    description="Automação de Manifesto de Transporte de Resíduos (MTR INEA)",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script_principal,
            base=base,
            target_name=nome_do_executavel
            # icon="seu_icone.ico" # Descomente e adicione se tiver um ícone
        )
    ],
)
