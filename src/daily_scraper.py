"""
Scraper de Diário Oficial - Automação de Download de PDF
Automatiza o login em plataforma de diário oficial e download diário de PDFs
"""

import os
import sys
import time
import random
import glob
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ==================== CARREGAMENTO DE VARIÁVEIS DE AMBIENTE ====================
# Carregar variáveis do arquivo .env
env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_file):
    print(f"[ENV] Carregando variáveis de {env_file}")
    load_dotenv(env_file, override=True)
else:
    print(f"[ENV] Arquivo .env não encontrado em {env_file}, usando variáveis do sistema")
    load_dotenv(override=True)  # Tenta carregar do .env na raiz do projeto


# ==================== CONFIGURAÇÕES ====================
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
DOWNLOAD_TIMEOUT = 30
LOGIN_TIMEOUT = 15
PDF_WAIT_TIMEOUT = 20
PDF_FILENAME = "diario_sm_atual.pdf"

DIARIO_LOGIN_URL = os.getenv("DIARIO_LOGIN_URL", "")
DIARIO_ACCESS_URL = os.getenv("DIARIO_ACCESS_URL", "")
DIARIO_USER = os.getenv("DIARIO_USER", "")
DIARIO_PASSWORD = os.getenv("DIARIO_PASS", "")


# ==================== LIMPEZA INICIAL ====================
def cleanup_old_pdfs():
    """Remove arquivos PDF antigos da pasta data/"""
    print("[CLEANUP] Iniciando limpeza de PDFs antigos...")
    
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        print(f"[CLEANUP] Pasta {DATA_FOLDER} não existia. Criada.")
        return
    
    pdf_files = glob.glob(os.path.join(DATA_FOLDER, "*.pdf"))
    
    if not pdf_files:
        print("[CLEANUP] Nenhum PDF encontrado para deletar.")
        return
    
    for pdf_file in pdf_files:
        try:
            os.remove(pdf_file)
            print(f"[CLEANUP] Deletado: {pdf_file}")
        except Exception as e:
            print(f"[CLEANUP] Erro ao deletar {pdf_file}: {e}")


# ==================== CONFIGURAÇÃO DO CHROME ====================
def setup_chrome_driver():
    """Configura e retorna instância do ChromeDriver com opções customizadas"""
    print("[CHROME] Configurando ChromeDriver...")
    
    # Encontrar binário do Chrome no sistema
    chrome_binary = None
    possible_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            chrome_binary = path
            print(f"[CHROME] Binário do Chrome encontrado: {chrome_binary}")
            break
    
    if not chrome_binary:
        print("[CHROME] AVISO: Binário do Chrome não encontrado em locais conhecidos")
        print("[CHROME] Tentando usar caminho padrão do sistema...")
    
    options = Options()
    
    # Definir caminho do binário se encontrado
    if chrome_binary:
        options.binary_location = chrome_binary
        print(f"[CHROME] Usando binário: {chrome_binary}")
    
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    
    # Configurar pasta de download automático
    prefs = {
        "download.default_directory": os.path.abspath(DATA_FOLDER),
        "download.prompt_for_download": False,
        "profile.default_content_settings.popups": 0,
        "safebrowsing.enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    try:
        service = Service(ChromeDriverManager().install())
        print(f"[CHROME] ChromeDriver instalado: {service.path}")
        
        driver = webdriver.Chrome(service=service, options=options)
        print("[CHROME] ChromeDriver configurado com sucesso")
        
        # Remover indicio de automacao exposto via webdriver
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        
        return driver
    
    except Exception as e:
        print(f"[CHROME] ERRO ao configurar ChromeDriver: {e}")
        print("[CHROME] Informações de debug:")
        print(f"  - Plataforma: {os.sys.platform}")
        print(f"  - Chrome encontrado: {chrome_binary}")
        print(f"  - Caminho absoluto data: {os.path.abspath(DATA_FOLDER)}")
        raise


# ==================== LÓGICA DE LOGIN ====================
def find_element_with_fallback(driver, selectors, timeout=LOGIN_TIMEOUT):
    """
    Tenta encontrar um elemento usando múltiplos seletores XPATH.
    Útil para lidar com IDs dinâmicos e layouts variáveis.
    
    Args:
        driver: WebDriver instance
        selectors: Lista de XPath selectors para tentar
        timeout: Tempo de espera
    
    Returns:
        WebElement ou None
    """
    for selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
            return element
        except:
            continue
    return None


def find_clickable_element_with_fallback(driver, selectors, timeout=LOGIN_TIMEOUT):
    """
    Tenta encontrar e clicar em um elemento usando múltiplos seletores XPATH.
    """
    for selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, selector))
            )
            return element
        except:
            continue
    return None


def perform_login(driver):
    """
    Realiza login na plataforma do diário oficial com seletores robustos.
    Usa múltiplas estratégias para encontrar campos mesmo com IDs dinâmicos.
    """
    print(f"[LOGIN] Navegando para {DIARIO_LOGIN_URL}...")
    driver.get(DIARIO_LOGIN_URL)
    
    try:
        # Aguardar página carregar
        time.sleep(3)
        print("[LOGIN] Página de login carregada")
        
        # ==================== CAMPO DE USUÁRIO ====================
        print("[LOGIN] Procurando campo de E-mail/Usuário...")
        
        # Seletores para campo de usuário (em ordem de preferência)
        username_selectors = [
            # Por placeholder
            "//input[@placeholder='E-mail']",
            "//input[@placeholder='Email']",
            "//input[@placeholder='e-mail']",
            "//input[@placeholder='Usuário']",
            
            # Por atributo type=email
            "//input[@type='email']",
            
            # Por atributo type=text com identificadores
            "//input[@type='text' and @maxlength='100']",
            "//input[@type='text'][position()=1]",
            
            # Por label (procura label com 'E-mail' e depois o input)
            "//label[contains(text(), 'E-mail')]/following::input[@type='text'][1]",
            "//label[contains(text(), 'E-mail')]/following::input[1]",
            "//label[contains(text(), 'Usuário')]/following::input[@type='text'][1]",
            
            # Por aria-label
            "//input[@aria-label='E-mail']",
            "//input[@aria-label='Email']",
            "//input[@aria-label='Usuário']",
            
            # Fallback - primeiro input type=text
            "//input[@type='text'][1]",
            "//input[1]",
        ]
        
        username_field = find_element_with_fallback(driver, username_selectors, LOGIN_TIMEOUT)
        
        if not username_field:
            print("[LOGIN] Nenhum campo de usuário encontrado!")
            print("[LOGIN] Tentando screenshot para debug...")
            driver.save_screenshot("/tmp/login_error.png")
            raise Exception("Campo de usuário não encontrado com nenhum seletor")
        
        print(f"[LOGIN] Campo de Usuário encontrado")
        username_field.clear()
        username_field.send_keys(DIARIO_USER)
        time.sleep(0.5)
        print(f"[LOGIN] Usuário preenchido: {DIARIO_USER[:3]}***")
        
        # ==================== CAMPO DE SENHA ====================
        print("[LOGIN] Procurando campo de Senha...")
        
        # Seletores para campo de senha (em ordem de preferência)
        password_selectors = [
            # Por placeholder
            "//input[@placeholder='Senha']",
            "//input[@placeholder='senha']",
            "//input[@placeholder='Password']",
            
            # Por type=password
            "//input[@type='password']",
            
            # Por atributo type=text com identificadores
            "//input[@type='text' and @maxlength='20']",
            
            # Por label (procura label com 'Senha' e depois o input)
            "//label[contains(text(), 'Senha')]/following::input[@type='password'][1]",
            "//label[contains(text(), 'Senha')]/following::input[@type='text'][1]",
            "//label[contains(text(), 'Senha')]/following::input[1]",
            
            # Por aria-label
            "//input[@aria-label='Senha']",
            "//input[@aria-label='Password']",
            
            # Fallback - segundo input (se primeiro era email)
            "//input[@type='text'][2]",
            "//input[2]",
        ]
        
        password_field = find_element_with_fallback(driver, password_selectors, LOGIN_TIMEOUT)
        
        if not password_field:
            print("[LOGIN] Nenhum campo de senha encontrado!")
            raise Exception("Campo de senha não encontrado com nenhum seletor")
        
        print(f"[LOGIN] Campo de Senha encontrado")
        password_field.clear()
        password_field.send_keys(DIARIO_PASSWORD)
        time.sleep(0.5)
        print(f"[LOGIN] Senha preenchida")
        
        # ==================== BOTÃO DE ENTRAR ====================
        print("[LOGIN] Procurando botão de Entrar...")
        
        # Seletores para botão de login (em ordem de preferência)
        button_selectors = [
            # Por texto exato
            "//button[text()='Entrar']",
            "//button[normalize-space()='Entrar']",
            "//span[text()='Entrar']/ancestor::button",
            "//span[normalize-space()='Entrar']/ancestor::button",
            
            # Por texto case-insensitive
            "//button[contains(text(), 'Entrar')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'entrar')]",
            
            # Por aria-label
            "//button[@aria-label='Entrar']",
            
            # Por classe (comum em Vue/React)
            "//button[contains(@class, 'btn-login')]",
            "//button[contains(@class, 'login')]",
            "//button[@type='submit']",
            
            # Fallback - primeiro button
            "//button[1]",
        ]
        
        login_button = find_clickable_element_with_fallback(driver, button_selectors, LOGIN_TIMEOUT)
        
        if not login_button:
            print("[LOGIN] Nenhum botão de entrar encontrado!")
            raise Exception("Botão 'Entrar' não encontrado com nenhum seletor")
        
        print(f"[LOGIN] Botão 'Entrar' encontrado")
        time.sleep(random.uniform(2, 5))
        driver.execute_script("arguments[0].click();", login_button)
        print(f"[LOGIN] Botão clicado. Aguardando redirecionamento...")
        
        # Aguardar login ser completado
        time.sleep(5)
        print("[LOGIN] Login realizado com sucesso")
        
    except Exception as e:
        print(f"[LOGIN] ERRO durante login: {e}")
        print(f"[LOGIN] Tipo de erro: {type(e).__name__}")
        raise


# ==================== FILTRO DE PUBLICAÇÕES ====================
def set_publication_filter(driver):
    """Configura o filtro 'Public. Legal' como 'Exceto' para exibir apenas edições jornalísticas"""
    print("[FILTRO] Configurando filtro 'Public. Legal' como 'Exceto'...")
    
    try:
        wait = WebDriverWait(driver, LOGIN_TIMEOUT)
        
        # Aguardar página carregar completamente
        wait.until(EC.presence_of_element_located((By.XPATH, "//body")))
        
        # Debug: Salvar screenshot para análise
        try:
            driver.save_screenshot("/tmp/filtro_debug.png")
            print("[FILTRO] Screenshot salvo em /tmp/filtro_debug.png")
        except:
            pass
        
        # Debug: Buscar todos os inputs combobox
        try:
            all_combos = driver.find_elements(By.XPATH, "//input[@role='combobox']")
            print(f"[FILTRO] Total de combobox encontrados: {len(all_combos)}")
            for i, combo in enumerate(all_combos):
                label_id = combo.get_attribute("aria-labelledby")
                value = combo.get_attribute("value")
                print(f"[FILTRO]   Combobox {i}: labelledby='{label_id}', value='{value}'")
        except Exception as e:
            print(f"[FILTRO] Erro no debug: {e}")
        
        # Estratégia 1: Encontrar o label "Public. Legal"
        label_selectors = [
            "//label[contains(normalize-space(), 'Public. Legal')]",
            "//*[contains(normalize-space(), 'Public. Legal') and (self::label or self::div or self::span)]",
        ]
        
        label_element = None
        for label_selector in label_selectors:
            try:
                label_element = wait.until(
                    EC.presence_of_element_located((By.XPATH, label_selector))
                )
                if label_element:
                    print("[FILTRO] Label 'Public. Legal' encontrado")
                    break
            except:
                continue
        
        # Estratégia 2: Localizar o combobox por diferentes relações com o label
        dropdown_selectors = []
        if label_element:
            label_id = label_element.get_attribute("id")
            if label_id:
                dropdown_selectors.append(
                    f"//input[@role='combobox' and @aria-labelledby='{label_id}']"
                )
            dropdown_selectors.extend([
                "//*[contains(@class, 'v-input') or contains(@class, 'v-select')]"
                "[.//*[contains(normalize-space(), 'Public. Legal')]]"
                "//input[@role='combobox']",
                "(//*[contains(normalize-space(), 'Public. Legal')])[1]"
                "/following::input[@role='combobox'][1]",
            ])
        
        dropdown_selectors.extend([
            "//input[@role='combobox' and contains(@aria-label, 'Public')]",
            "//input[@role='combobox' and contains(@aria-label, 'Legal')]",
            "//input[@role='combobox']",
        ])
        
        dropdown_input = None
        for selector in dropdown_selectors:
            try:
                candidates = driver.find_elements(By.XPATH, selector)
                for candidate in candidates:
                    if candidate.is_displayed():
                        dropdown_input = candidate
                        print("[FILTRO] Dropdown encontrado")
                        break
                if dropdown_input:
                    break
            except:
                continue
        
        if not dropdown_input:
            print("[FILTRO] AVISO: Dropdown não encontrado, continuando sem filtro...")
            return
        
        current_value = (dropdown_input.get_attribute("value") or "").strip()
        if "Exceto" in current_value:
            print("[FILTRO] Filtro ja estava em 'Exceto'")
            return
        
        # Clicar no dropdown para abrir as opções
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dropdown_input)
        driver.execute_script("arguments[0].click();", dropdown_input)
        print("[FILTRO] Dropdown clicado, aguardando opções...")
        time.sleep(1.5)
        
        # Seletores para encontrar a opção "Exceto"
        exceto_selectors = [
            "//div[@role='option' and normalize-space()='Exceto']",
            "//span[normalize-space()='Exceto']/ancestor::div[@role='option'][1]",
            "//div[contains(@class, 'v-list-item')][.//div[normalize-space()='Exceto']]",
            "//div[contains(@class, 'v-list-item')][.//span[normalize-space()='Exceto']]",
            "//div[@role='listbox']//div[normalize-space()='Exceto']",
        ]
        
        print("[FILTRO] Procurando opção 'Exceto'...")
        exceto_option = None
        for selector in exceto_selectors:
            try:
                exceto_option = wait.until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print("[FILTRO] Opção 'Exceto' encontrada")
                break
            except:
                continue
        
        if not exceto_option:
            print("[FILTRO] AVISO: Opção 'Exceto' não encontrada, continuando sem filtro...")
            return
        
        # Clicar na opção "Exceto"
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", exceto_option)
        driver.execute_script("arguments[0].click();", exceto_option)
        print("[FILTRO] Opção 'Exceto' selecionada!")
        
        # Aguardar filtro ser aplicado
        time.sleep(3)
        print("[FILTRO] Filtro aplicado com sucesso - exibindo apenas edições jornalísticas")
        
    except Exception as e:
        print(f"[FILTRO] ERRO ao configurar filtro: {e}")
        print("[FILTRO] Continuando sem filtro...")


# ==================== ACESSO E DOWNLOAD DO PDF ====================
def access_and_download_pdf(driver):
    """Acessa a URL de download, aplica filtro e clica no ícone PDF"""
    print(f"[PDF] Navegando para {DIARIO_ACCESS_URL}...")
    driver.get(DIARIO_ACCESS_URL)
    
    try:
        # Aguardar página carregar
        time.sleep(5)
        print("[PDF] Página de acesso carregada")
        
        # Aplicar filtro "Public. Legal" = "Exceto"
        set_publication_filter(driver)
        
        # Procurar pelo ícone PDF (classe mdi-file-pdf-box)
        print("[PDF] Procurando ícone de PDF (mdi-file-pdf-box)...")
        pdf_icon = WebDriverWait(driver, PDF_WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//*[contains(@class, 'mdi-file-pdf-box')]"
            ))
        )
        print("[PDF] Ícone de PDF encontrado")
        
        # Clicar no ícone para iniciar download
        time.sleep(random.uniform(2, 5))
        driver.execute_script("arguments[0].click();", pdf_icon)
        print("[PDF] Clique no ícone realizado. Aguardando download...")
        
    except Exception as e:
        print(f"[PDF] ERRO ao acessar PDF: {e}")
        raise


# ==================== PÓS-PROCESSAMENTO ====================
def wait_for_download_completion():
    """Aguarda o download ser completado monitorando a pasta data/"""
    print("[DOWNLOAD] Aguardando conclusão do download...")
    
    start_time = time.time()
    while time.time() - start_time < DOWNLOAD_TIMEOUT:
        # Procurar por arquivos .crdownload (indicam download em progresso)
        crdownload_files = glob.glob(os.path.join(DATA_FOLDER, "*.crdownload"))
        # Procurar por arquivos .pdf
        pdf_files = glob.glob(os.path.join(DATA_FOLDER, "*.pdf"))
        
        if crdownload_files:
            print(f"[DOWNLOAD] Arquivo em download: {crdownload_files[0]}")
            time.sleep(1)
            continue
        
        if pdf_files:
            print(f"[DOWNLOAD] PDF detectado, download concluído!")
            return pdf_files[0]
        
        time.sleep(1)
    
    raise TimeoutError(f"Download não foi completado em {DOWNLOAD_TIMEOUT} segundos")


def rename_pdf_file(old_path):
    """Renomeia o arquivo PDF baixado para nome padronizado"""
    new_path = os.path.join(DATA_FOLDER, PDF_FILENAME)
    
    try:
        # Se arquivo com novo nome já existe, deletar
        if os.path.exists(new_path):
            os.remove(new_path)
            print(f"[RENAME] Arquivo anterior deletado: {new_path}")
        
        os.rename(old_path, new_path)
        print(f"[RENAME] Arquivo renomeado: {old_path} -> {new_path}")
        return new_path
        
    except Exception as e:
        print(f"[RENAME] ERRO ao renomear arquivo: {e}")
        raise


# ==================== DIAGNÓSTICO DO SISTEMA ====================
def diagnose_system():
    """Diagnóstico pré-execução para verificar dependências"""
    print("[DIAGNÓSTICO] Verificando ambiente do sistema...")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Plataforma: {sys.platform}")
    print(f"  Diretório atual: {os.getcwd()}")
    
    # Verificar Chrome
    chrome_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    ]
    
    chrome_found = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_found = path
            try:
                import subprocess
                version = subprocess.check_output([chrome_found, "--version"], 
                                                stderr=subprocess.DEVNULL).decode().strip()
                print(f"  Chrome: ✓ {path}")
                print(f"           {version}")
            except:
                print(f"  Chrome: ✓ {path}")
            break
    
    if not chrome_found:
        print(f"  Chrome: ✗ NÃO ENCONTRADO")
        print(f"  Locais procurados:")
        for path in chrome_paths:
            print(f"    - {path}")
    
    # Verificar pasta data
    if os.path.exists(DATA_FOLDER):
        print(f"  Pasta data/: ✓ {os.path.abspath(DATA_FOLDER)}")
    else:
        print(f"  Pasta data/: ✗ será criada na primeira execução")
    
    # Verificar Selenium
    try:
        import selenium
        print(f"  Selenium: ✓ {selenium.__version__}")
    except ImportError:
        print(f"  Selenium: ✗ NÃO INSTALADO")
    
    # Verificar webdriver-manager
    try:
        import webdriver_manager
        print(f"  webdriver-manager: ✓ OK")
    except ImportError:
        print(f"  webdriver-manager: ✗ NÃO INSTALADO")
    
    print()


# ==================== EXECUÇÃO PRINCIPAL ====================
def main():
    """Função principal do scraper"""
    print("=" * 60)
    print("INICIANDO SCRAPER DE DIÁRIO OFICIAL")
    print("=" * 60)
    print()
    
    # Diagnóstico do sistema
    diagnose_system()
    
    # Validar variáveis de ambiente
    if not all([DIARIO_LOGIN_URL, DIARIO_ACCESS_URL, DIARIO_USER, DIARIO_PASSWORD]):
        print("[ERROR] Variáveis de ambiente não configuradas!")
        print(f"  DIARIO_LOGIN_URL: {bool(DIARIO_LOGIN_URL)}")
        print(f"  DIARIO_ACCESS_URL: {bool(DIARIO_ACCESS_URL)}")
        print(f"  DIARIO_USER: {bool(DIARIO_USER)}")
        print(f"  DIARIO_PASSWORD: {bool(DIARIO_PASSWORD)}")
        raise ValueError("Credenciais ou URLs não encontradas em variáveis de ambiente")
    
    # Etapa 1: Limpeza
    cleanup_old_pdfs()
    
    driver = None
    try:
        # Etapa 2: Setup Chrome
        driver = setup_chrome_driver()
        
        # Etapa 3: Login
        perform_login(driver)
        
        # Etapa 4: Acesso, Filtro e Download
        access_and_download_pdf(driver)
        
        # Etapa 5: Aguardar Download
        pdf_path = wait_for_download_completion()
        
        # Etapa 6: Renomear
        final_path = rename_pdf_file(pdf_path)
        
        print("=" * 60)
        print(f"✓ SUCESSO! PDF salvo em: {final_path}")
        print("=" * 60)
        
    except Exception as e:
        print("=" * 60)
        print(f"✗ ERRO DURANTE EXECUÇÃO: {e}")
        print("=" * 60)
        raise
        
    finally:
        if driver:
            print("[CLEANUP] Fechando browser...")
            driver.quit()
            print("[CLEANUP] Browser fechado")


if __name__ == "__main__":
    main()
