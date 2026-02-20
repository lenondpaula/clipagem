"""
Scraper de Diário Oficial - Automação de Download de PDF
Automatiza o login em plataforma de diário oficial e download diário de PDFs
"""

import os
import sys
import time
import glob
import stat
import re
from datetime import datetime
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
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    
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
        driver_path = Path(ChromeDriverManager().install())
        if driver_path.name.startswith("THIRD_PARTY_NOTICES"):
            candidate = driver_path.with_name("chromedriver")
            if candidate.exists():
                driver_path = candidate
        
        # Garantir permissões de execução (fix para GitHub Actions)
        os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IEXEC)
        print(f"[CHROME] Permissões de execução aplicadas")
        
        service = Service(str(driver_path))
        print(f"[CHROME] ChromeDriver instalado: {service.path}")
        
        driver = webdriver.Chrome(service=service, options=options)
        print("[CHROME] ChromeDriver configurado com sucesso")
        
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


def find_element_with_fallback_any_frame(driver, selectors, timeout=LOGIN_TIMEOUT):
    """
    Procura elemento no documento principal e em iframes.
    Mantem o contexto no frame onde o elemento for encontrado.
    """
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    element = find_element_with_fallback(driver, selectors, timeout)
    if element:
        return element

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, frame in enumerate(frames):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
        except Exception:
            continue

        element = find_element_with_fallback(driver, selectors, max(5, timeout // 2))
        if element:
            print(f"[LOGIN] Elemento encontrado dentro do iframe {idx}")
            return element

    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    return None


def find_clickable_element_with_fallback_any_frame(driver, selectors, timeout=LOGIN_TIMEOUT):
    """
    Procura elemento clicavel no documento principal e em iframes.
    Mantem o contexto no frame onde o elemento for encontrado.
    """
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    element = find_clickable_element_with_fallback(driver, selectors, timeout)
    if element:
        return element

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, frame in enumerate(frames):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
        except Exception:
            continue

        element = find_clickable_element_with_fallback(driver, selectors, max(5, timeout // 2))
        if element:
            print(f"[LOGIN] Elemento clicavel encontrado dentro do iframe {idx}")
            return element

    try:
        driver.switch_to.default_content()
    except Exception:
        pass
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
            "//input[@placeholder='Usuario']",
            "//input[contains(@placeholder, 'E-mail')]",
            "//input[contains(@placeholder, 'Email')]",
            "//input[contains(@placeholder, 'Usuário')]",
            "//input[contains(@placeholder, 'Usuario')]",
            "//input[contains(@placeholder, 'Login')]",
            
            # Por atributo type=email
            "//input[@type='email']",
            "//input[contains(@type, 'email')]",
            
            # Por atributo name/id
            "//input[contains(@name, 'email')]",
            "//input[contains(@name, 'user')]",
            "//input[contains(@name, 'login')]",
            "//input[contains(@id, 'email')]",
            "//input[contains(@id, 'user')]",
            "//input[contains(@id, 'login')]",
            
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
        
        username_field = find_element_with_fallback_any_frame(driver, username_selectors, LOGIN_TIMEOUT)
        
        if not username_field:
            print("[LOGIN] Nenhum campo de usuário encontrado!")
            print("[LOGIN] Tentando screenshot para debug...")
            print(f"[LOGIN] URL atual: {driver.current_url}")
            try:
                driver.save_screenshot("/tmp/login_error.png")
                with open("/tmp/login_error.html", "w", encoding="utf-8") as handle:
                    handle.write(driver.page_source)
            except Exception:
                pass
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
            "//input[contains(@placeholder, 'Senha')]",
            "//input[contains(@placeholder, 'Password')]",
            
            # Por type=password
            "//input[@type='password']",
            "//input[contains(@type, 'password')]",
            
            # Por atributo name/id
            "//input[contains(@name, 'pass')]",
            "//input[contains(@name, 'senha')]",
            "//input[contains(@id, 'pass')]",
            "//input[contains(@id, 'senha')]",
            
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
        
        password_field = find_element_with_fallback_any_frame(driver, password_selectors, LOGIN_TIMEOUT)
        
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
        
        login_button = find_clickable_element_with_fallback_any_frame(driver, button_selectors, LOGIN_TIMEOUT)
        
        if not login_button:
            print("[LOGIN] Nenhum botão de entrar encontrado!")
            raise Exception("Botão 'Entrar' não encontrado com nenhum seletor")
        
        print(f"[LOGIN] Botão 'Entrar' encontrado")
        driver.execute_script("arguments[0].click();", login_button)
        print(f"[LOGIN] Botão clicado. Aguardando redirecionamento...")
        
        # Aguardar login ser completado
        time.sleep(5)
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
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
        # Aguardar página carregar completamente
        time.sleep(3)
        
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
        
        # Estratégia 1: Encontrar o combobox pelo label "Public. Legal"
        # Primeiro encontrar o label
        label_selectors = [
            "//label[contains(text(), 'Public. Legal')]",
            "//*[contains(text(), 'Public. Legal') and (self::label or self::div or self::span)]",
        ]
        
        dropdown_input = None
        for label_selector in label_selectors:
            try:
                label_element = driver.find_element(By.XPATH, label_selector)
                label_id = label_element.get_attribute("id")
                print(f"[FILTRO] Label encontrado com id: {label_id}")
                
                # Agora encontrar o input que usa esse label
                if label_id:
                    dropdown_input = driver.find_element(By.XPATH, 
                        f"//input[@aria-labelledby='{label_id}']")
                    print(f"[FILTRO] Dropdown encontrado via label")
                    break
            except:
                continue
        
        # Estratégia 2: Encontrar pelo texto do container
        if not dropdown_input:
            try:
                # Procurar pelo container que tem "Public. Legal" e depois o input dentro
                container = driver.find_element(By.XPATH, 
                    "//div[contains(., 'Public. Legal') and contains(@class, 'v-input')]")
                dropdown_input = container.find_element(By.XPATH, 
                    ".//input[@role='combobox']")
                print(f"[FILTRO] Dropdown encontrado via container")
            except:
                pass

        # Estratégia 2.1: Vuetify v-select/v-field
        if not dropdown_input:
            try:
                container = driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, 'v-select') and .//label[contains(., 'Public. Legal')]]",
                )
                dropdown_input = container.find_element(By.XPATH, ".//input[@role='combobox']")
                print("[FILTRO] Dropdown encontrado via v-select")
            except Exception:
                pass
        
        # Estratégia 3: Se há apenas um combobox, usar ele
        if not dropdown_input:
            try:
                combos = driver.find_elements(By.XPATH, "//input[@role='combobox']")
                if len(combos) == 1:
                    dropdown_input = combos[0]
                    print(f"[FILTRO] Usando único combobox disponível")
                elif len(combos) > 1:
                    # Pegar o primeiro que está visível
                    for combo in combos:
                        if combo.is_displayed():
                            dropdown_input = combo
                            print(f"[FILTRO] Usando primeiro combobox visível")
                            break
            except:
                pass
        
        if not dropdown_input:
            print("[FILTRO] AVISO: Dropdown não encontrado, continuando sem filtro...")
            return
        
        # Clicar no dropdown para abrir as opções
        driver.execute_script("arguments[0].click();", dropdown_input)
        print("[FILTRO] Dropdown clicado, aguardando opções...")
        time.sleep(5)  # Aumentar tempo de espera
        
        # Tentar scroll ou foco para forçar carregamento
        try:
            driver.execute_script("arguments[0].scrollIntoView();", dropdown_input)
            time.sleep(2)
        except:
            pass
        
        # Debug: Listar todas as opções disponíveis
        try:
            all_options = driver.find_elements(By.XPATH, "//*[@role='option'] | //div[@role='listitem'] | //div[contains(@class, 'v-list-item')]")
            print(f"[FILTRO] Total de opções no menu: {len(all_options)}")
            for idx, opt in enumerate(all_options):
                opt_text = opt.text.strip()
                print(f"[FILTRO]   Opção {idx}: '{opt_text}'")
        except Exception as e:
            print(f"[FILTRO] Erro ao listar opções: {e}")
        
        # Se ainda não há opções, tentar clicar novamente
        if len(all_options) == 0:
            print("[FILTRO] Nenhuma opção encontrada, tentando clicar novamente...")
            driver.execute_script("arguments[0].click();", dropdown_input)
            time.sleep(3)
            all_options = driver.find_elements(By.XPATH, "//*[@role='option'] | //div[@role='listitem'] | //div[contains(@class, 'v-list-item')]")
            print(f"[FILTRO] Após segundo clique - Total de opções: {len(all_options)}")
        
        # Seletores para encontrar a opção "Exceto"
        exceto_selectors = [
            # Texto exato (case sensitive)
            "//div[@role='option' and text()='Exceto']",
            "//div[@role='option']//div[text()='Exceto']",
            
            # Contém texto
            "//div[@role='option' and contains(., 'Exceto')]",
            "//div[contains(@class, 'v-list-item') and contains(., 'Exceto')]",
            
            # Case insensitive
            "//*[@role='option' and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'exceto')]",
            
            # Outros roles
            "//*[@role='listitem' and contains(., 'Exceto')]",
            "//span[text()='Exceto']",
        ]
        
        print("[FILTRO] Procurando opção 'Exceto'...")
        exceto_option = None
        for selector in exceto_selectors:
            try:
                exceto_option = WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"[FILTRO] Opção 'Exceto' encontrada com seletor: {selector}")
                break
            except:
                continue
        
        if not exceto_option:
            print("[FILTRO] AVISO: Opção 'Exceto' não encontrada, continuando sem filtro...")
            # Tentar buscar por qualquer opção que contenha "exceto" (última tentativa)
            try:
                all_opts = driver.find_elements(By.XPATH, "//*[@role='option']")
                for opt in all_opts:
                    if 'exceto' in opt.text.lower():
                        exceto_option = opt
                        print(f"[FILTRO] Opção encontrada por busca manual: '{opt.text}'")
                        break
            except:
                pass
        
        if not exceto_option:
            print("[FILTRO] ERRO: Não foi possível encontrar a opção 'Exceto'")
            return
        
        # Clicar na opção "Exceto"
        driver.execute_script("arguments[0].click();", exceto_option)
        print("[FILTRO] Opção 'Exceto' selecionada!")
        
        # Aguardar filtro ser aplicado
        time.sleep(2)
        
        # Validação: Verificar se filtro foi aplicado
        try:
            current_value = dropdown_input.get_attribute("value")
            print(f"[FILTRO] Valor atual do dropdown: '{current_value}'")
            if "exceto" in current_value.lower():
                print("[FILTRO] ✓ Filtro aplicado com sucesso!")
            else:
                print("[FILTRO] ⚠️ AVISO: Filtro pode não ter sido aplicado corretamente")
        except Exception as e:
            print(f"[FILTRO] Não foi possível validar filtro: {e}")
        
        print("[FILTRO] Filtro 'Public. Legal' configurado como 'Exceto'")
        
        # Aguardar filtro ser aplicado
        time.sleep(3)
        print("[FILTRO] Filtro aplicado com sucesso - exibindo apenas edições jornalísticas")
        
    except Exception as e:
        print(f"[FILTRO] ERRO ao configurar filtro: {e}")
        print("[FILTRO] Continuando sem filtro...")


# ==================== ACESSO E DOWNLOAD DO PDF ====================
def _parse_card_date_ddmmyyyy(text):
    """Extrai data no formato DD/MM/YYYY de um texto de card."""
    match = re.search(r"Data\s*Edi[çc][ãa]o\s*:\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y")
    except ValueError:
        return None


def _parse_card_edition_number(text):
    """Extrai número da edição a partir de texto como 'Edição Nº 7342'."""
    match = re.search(r"Edi[çc][ãa]o\s*N[ºo]?\s*(\d+)", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def access_and_download_pdf(driver):
    """Acessa a URL de download, aplica filtro e clica no ícone PDF da edição JORNAL mais recente"""
    print(f"[PDF] Navegando para {DIARIO_ACCESS_URL}...")
    driver.get(DIARIO_ACCESS_URL)
    
    try:
        # Aguardar página carregar
        time.sleep(5)
        print("[PDF] Página de acesso carregada")
        
        # Aplicar filtro "Public. Legal" = "Exceto"
        set_publication_filter(driver)
        
        # Aguardar após aplicar filtro para lista atualizar
        time.sleep(3)
        
        # Estratégia determinística: usar o card específico da grade de edições
        print("[PDF] Localizando cards de edição e selecionando JORNAL mais recente...")

        candidate_cards = driver.find_elements(
            By.XPATH,
            "//div[contains(@class,'suita-block-home') and contains(@class,'v-card')]",
        )
        print(f"[PDF] Cards do grid encontrados: {len(candidate_cards)}")

        jornal_candidates = []
        for idx, card in enumerate(candidate_cards):
            card_text = (card.text or "").strip()
            card_text_lower = card_text.lower()

            if not card_text:
                continue

            # Filtra somente JORNAL e exclui categorias indesejadas
            if "jornal" not in card_text_lower:
                continue
            if any(tag in card_text_lower for tag in ["valvi", "folheto", "classificados", "classificado"]):
                continue

            edition_number = _parse_card_edition_number(card_text)
            edition_date = _parse_card_date_ddmmyyyy(card_text)

            try:
                pdf_icon = card.find_element(
                    By.XPATH,
                    ".//i[contains(@class,'mdi-file-pdf-box') and contains(@class,'v-icon--clickable')]",
                )
            except Exception:
                continue

            jornal_candidates.append(
                {
                    "card": card,
                    "pdf_icon": pdf_icon,
                    "edition_number": edition_number if edition_number is not None else -1,
                    "edition_date": edition_date,
                    "debug": card_text.replace("\n", " | ")[:220],
                }
            )
            print(
                f"[PDF] Candidato {idx}: edição={edition_number}, data={edition_date.strftime('%d/%m/%Y') if edition_date else 'N/A'}"
            )

        if not jornal_candidates:
            raise Exception("Nenhum card de JORNAL válido com ícone PDF foi encontrado")

        # Ordena por data e depois por número da edição (desc) para pegar o mais recente hoje/amanhã
        jornal_candidates.sort(
            key=lambda item: (
                item["edition_date"] if item["edition_date"] is not None else datetime.min,
                item["edition_number"],
            ),
            reverse=True,
        )

        selected = jornal_candidates[0]
        pdf_icon = selected["pdf_icon"]
        print(
            "[PDF] Selecionado card JORNAL mais recente: "
            f"edição={selected['edition_number']}, "
            f"data={selected['edition_date'].strftime('%d/%m/%Y') if selected['edition_date'] else 'N/A'}"
        )
        print(f"[PDF] Card selecionado (debug): {selected['debug']}")
        
        # Clicar no ícone para iniciar download
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
            downloaded_file = pdf_files[0]
            print(f"[DOWNLOAD] PDF detectado: {downloaded_file}")
            
            # Validação do arquivo baixado
            if validate_downloaded_file(downloaded_file):
                print(f"[DOWNLOAD] ✓ Arquivo validado com sucesso!")
                return downloaded_file
            else:
                print(f"[DOWNLOAD] ✗ Arquivo inválido detectado, removendo...")
                try:
                    os.remove(downloaded_file)
                    print(f"[DOWNLOAD] Arquivo removido: {downloaded_file}")
                except Exception as e:
                    print(f"[DOWNLOAD] Erro ao remover arquivo: {e}")
                raise Exception("Arquivo baixado não é um JORNAL válido")
        
        time.sleep(1)
    
    raise Exception(f"Timeout: Download não concluído em {DOWNLOAD_TIMEOUT} segundos")


def validate_downloaded_file(filepath):
    """Valida se o arquivo baixado é um JORNAL válido (não VALVI, FOLHETO, etc.)"""
    filename = os.path.basename(filepath).lower()
    
    print(f"[VALIDAÇÃO] Verificando arquivo: {filename}")
    
    # Regras de validação
    valid_indicators = ["jornal", "diario", "oficial"]
    invalid_indicators = ["valvi", "folheto", "classificado", "publicacao", "legal", "lei", "decreto"]
    
    # Verificar indicadores válidos
    has_valid = any(indicator in filename for indicator in valid_indicators)
    
    # Verificar indicadores inválidos
    has_invalid = any(indicator in filename for indicator in invalid_indicators)
    
    if has_valid and not has_invalid:
        print("[VALIDAÇÃO] ✓ Arquivo parece ser JORNAL válido")
        return True
    elif has_invalid:
        print(f"[VALIDAÇÃO] ✗ Arquivo contém indicador inválido: {filename}")
        return False
    else:
        print(f"[VALIDAÇÃO] ? Arquivo sem indicadores claros: {filename}")
        # Se não tem indicadores claros, assumir válido por enquanto
        return True


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
