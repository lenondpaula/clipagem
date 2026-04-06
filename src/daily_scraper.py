"""
Scraper de Diário Oficial - Automação de Download de PDF
Automatiza o login em plataforma de diário oficial e download diário de PDFs
"""

import os
import sys
import time
import glob
import random
import re
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


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
LOGIN_TOTAL_TIMEOUT = int(os.getenv("LOGIN_TOTAL_TIMEOUT", "45"))
LOGIN_FIELD_TIMEOUT = int(os.getenv("LOGIN_FIELD_TIMEOUT", "8"))
LOGIN_BUTTON_TIMEOUT = int(os.getenv("LOGIN_BUTTON_TIMEOUT", "6"))
PDF_WAIT_TIMEOUT = 20
LISTING_READY_TIMEOUT = int(os.getenv("LISTING_READY_TIMEOUT", str(PDF_WAIT_TIMEOUT)))
CARD_DISCOVERY_TIMEOUT = int(os.getenv("CARD_DISCOVERY_TIMEOUT", "12"))
FAST_PDF_CLICK_TIMEOUT = int(os.getenv("FAST_PDF_CLICK_TIMEOUT", "14"))
FILTER_TOTAL_TIMEOUT = int(os.getenv("FILTER_TOTAL_TIMEOUT", "10"))
PDF_FILENAME = "diario_sm_atual.pdf"
APPLY_PUBLIC_LEGAL_FILTER = os.getenv("APPLY_PUBLIC_LEGAL_FILTER", "false").strip().lower() in ("1", "true", "yes", "on")
PLAYWRIGHT_DEFAULT_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_DEFAULT_TIMEOUT_MS", "15000"))

DIARIO_LOGIN_URL = os.getenv("DIARIO_LOGIN_URL", "")
DIARIO_ACCESS_URL = os.getenv("DIARIO_ACCESS_URL", "")
DIARIO_USER = os.getenv("DIARIO_USER", "")
DIARIO_PASSWORD = os.getenv("DIARIO_PASS", "")


def _save_debug_html(file_name, html_content):
    """Salva HTML de debug em /tmp para inspeção em falhas de seleção."""
    if not html_content:
        return
    try:
        file_path = os.path.join("/tmp", file_name)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(html_content)
        print(f"[DEBUG] HTML salvo: {file_path}")
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar {file_name}: {e}")


def _save_element_html(driver, element, file_name):
    """Salva outerHTML de um elemento Web para depuração."""
    try:
        outer_html = driver.execute_script("return arguments[0].outerHTML;", element)
        _save_debug_html(file_name, outer_html)
    except Exception as e:
        print(f"[DEBUG] Falha ao extrair outerHTML ({file_name}): {e}")


def _save_icon_context_html(driver, icon_element, file_name, levels=3):
    """Salva HTML do ícone PDF e seus ancestrais para depuração estrutural."""
    try:
        context_html = driver.execute_script(
            """
            const el = arguments[0];
            const maxLevels = arguments[1];
            const parts = [];
            let node = el;
            let level = 0;
            while (node && level <= maxLevels) {
                parts.push(`<!-- level ${level} -->\n${node.outerHTML}`);
                node = node.parentElement;
                level += 1;
            }
            return parts.join("\n\n");
            """,
            icon_element,
            levels,
        )
        _save_debug_html(file_name, context_html)
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar contexto do ícone PDF: {e}")


def _save_listing_page_debug(driver):
    """Salva HTML da listagem logada e screenshot da tela atual."""
    try:
        driver.save_screenshot("/tmp/listagem_logada.png")
        print("[DEBUG] Screenshot salvo: /tmp/listagem_logada.png")
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar screenshot da listagem: {e}")

    try:
        _save_debug_html("listagem_logada.html", driver.page_source)
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar HTML da listagem: {e}")


def _save_page_debug(driver, file_prefix):
    """Salva screenshot e HTML da página atual com um prefixo específico."""
    try:
        driver.save_screenshot(f"/tmp/{file_prefix}.png")
        print(f"[DEBUG] Screenshot salvo: /tmp/{file_prefix}.png")
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar screenshot {file_prefix}: {e}")

    try:
        _save_debug_html(f"{file_prefix}.html", driver.page_source)
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar HTML {file_prefix}: {e}")


def _save_page_debug_playwright(page, file_prefix):
    """Salva screenshot e HTML da página atual via Playwright."""
    try:
        file_path = f"/tmp/{file_prefix}.png"
        page.screenshot(path=file_path, full_page=True)
        print(f"[DEBUG] Screenshot salvo: {file_path}")
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar screenshot {file_prefix}: {e}")

    try:
        _save_debug_html(f"{file_prefix}.html", page.content())
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar HTML {file_prefix}: {e}")


def _write_stage_marker(stage, details=""):
    """Registra a etapa atual do scraper em /tmp para diagnóstico em CI."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | {stage}"
    if details:
        message = f"{message} | {details}"

    try:
        with open("/tmp/scraper_stage.txt", "w", encoding="utf-8") as handle:
            handle.write(message + "\n")
        with open("/tmp/scraper_stage_history.txt", "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception as e:
        print(f"[STAGE] Falha ao registrar etapa '{stage}': {e}")

    print(f"[STAGE] {message}")


def _human_pause(min_seconds=0.25, max_seconds=0.9):
    """Pausa curta com jitter para reduzir padrão rígido de automação."""
    time.sleep(random.uniform(min_seconds, max_seconds))


def _human_scroll_into_view(driver, element):
    """Rola até o elemento com pequenas pausas para simular navegação humana."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        _human_pause(0.2, 0.5)
    except Exception as e:
        print(f"[HUMAN] Falha ao rolar até elemento: {e}")


def _human_click(driver, element, label="elemento"):
    """Tenta clicar de forma natural com fallback para clique via JavaScript."""
    _human_scroll_into_view(driver, element)
    _human_pause(0.15, 0.45)
    try:
        ActionChains(driver).move_to_element(element).pause(random.uniform(0.1, 0.4)).click().perform()
        print(f"[HUMAN] Clique realizado com ActionChains em {label}")
        return
    except Exception:
        pass

    try:
        element.click()
        print(f"[HUMAN] Clique direto realizado em {label}")
        return
    except Exception:
        pass

    driver.execute_script("arguments[0].click();", element)
    print(f"[HUMAN] Clique via JavaScript realizado em {label}")


def _parse_edition_date_from_card(driver, card_element):
    """Extrai data da edição no formato dd/mm/yyyy a partir do texto do card."""
    try:
        card_text = driver.execute_script("return arguments[0].innerText;", card_element) or ""
    except Exception:
        card_text = ""

    match = re.search(r"Data\s*Edi(?:ç|c)[aã]o\s*:\s*(\d{2}/\d{2}/\d{4})", card_text, flags=re.IGNORECASE)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y")
    except ValueError:
        return None


def _is_jornal_card(driver, card_element):
    """Valida se o card corresponde a uma edição do tipo JORNAL."""
    try:
        card_type = (driver.execute_script("return arguments[0].querySelector('h5')?.innerText || '';", card_element) or "").strip().upper()
        if card_type == "JORNAL":
            return True
    except Exception:
        pass

    try:
        img_src = driver.execute_script("return arguments[0].querySelector('img')?.getAttribute('src') || '';", card_element) or ""
        return "/JORNAL/" in img_src.upper()
    except Exception:
        return False


def _select_latest_jornal_card(driver):
    """Seleciona o card JORNAL com data mais recente entre os cards visíveis."""
    cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'suita-block-home') or contains(@class, 'v-card')]")
    candidates = []

    for card in cards:
        if not _is_jornal_card(driver, card):
            continue
        edition_date = _parse_edition_date_from_card(driver, card)
        if edition_date is None:
            continue
        candidates.append((edition_date, card))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    latest_date, latest_card = candidates[0]
    print(f"[PDF] Card JORNAL mais recente selecionado: {latest_date.strftime('%d/%m/%Y')}")
    return latest_card


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
    
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
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
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {
                "behavior": "allow",
                "downloadPath": os.path.abspath(DATA_FOLDER),
            },
        )
        print(f"[CHROME] Download em headless habilitado via CDP: {os.path.abspath(DATA_FOLDER)}")
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
    deadline = time.monotonic() + timeout

    for selector in selectors:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        wait_timeout = min(1.5, remaining)
        try:
            element = WebDriverWait(driver, wait_timeout, poll_frequency=0.2).until(
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
    deadline = time.monotonic() + timeout

    for selector in selectors:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        wait_timeout = min(1.5, remaining)
        try:
            element = WebDriverWait(driver, wait_timeout, poll_frequency=0.2).until(
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
    deadline = time.monotonic() + timeout

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    main_document_timeout = max(0.5, deadline - time.monotonic())
    element = find_element_with_fallback(driver, selectors, main_document_timeout)
    if element:
        return element

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, frame in enumerate(frames):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
        except Exception:
            continue

        frame_timeout = min(2.0, remaining)
        element = find_element_with_fallback(driver, selectors, frame_timeout)
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
    deadline = time.monotonic() + timeout

    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    main_document_timeout = max(0.5, deadline - time.monotonic())
    element = find_clickable_element_with_fallback(driver, selectors, main_document_timeout)
    if element:
        return element

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for idx, frame in enumerate(frames):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(frame)
        except Exception:
            continue

        frame_timeout = min(2.0, remaining)
        element = find_clickable_element_with_fallback(driver, selectors, frame_timeout)
        if element:
            print(f"[LOGIN] Elemento clicavel encontrado dentro do iframe {idx}")
            return element

    try:
        driver.switch_to.default_content()
    except Exception:
        pass
    return None


def _is_user_logged_in(driver):
    """
    Valida se o usuário está realmente logado verificando elementos que só existem quando autenticado.
    Retorna True se logado, False se não logado, levanta Exception se não conseguir determinar.
    """
    try:
        driver.switch_to.default_content()
    except Exception:
        pass

    current_url = (driver.current_url or "").lower()

    # Estratégia 0: URL de área autenticada é sinal forte de sucesso.
    if "/assinante/newflip" in current_url:
        print(f"[LOGIN] ✓ URL autenticada detectada: {driver.current_url}")
        return True

    # Estratégia 1: Procurar por elementos que indicam "usuário logado"
    # Exemplos comuns: nome do usuário, botão "Sair", menu de perfil, etc.
    logged_in_indicators = [
        "//button[contains(text(), 'Sair')]",
        "//button[contains(text(), 'Logout')]",
        "//a[contains(@href, 'logout')]",
        "//a[contains(@href, '/assinante/logout')]",
        "//*[contains(text(), 'Bem-vindo')] | //*[contains(text(), 'welcome')]",
        "//div[contains(@class, 'user-profile')]",
        "//div[contains(@class, 'logged-in')]",
        "//span[contains(@class, 'username')]",
    ]

    for indicator_selector in logged_in_indicators:
        try:
            elements = driver.find_elements(By.XPATH, indicator_selector)
            if elements:
                print(f"[LOGIN] ✓ Indicador de login encontrado: {indicator_selector.split('[')[0]}")
                return True
        except Exception:
            continue

    # Estratégia 2: Procurar por mensagens de ERRO de login (somente fatais).
    # Evita falso negativo com mensagens de validação suave, ex.: "Obrigatório".
    error_indicators = [
        "//*[contains(@class, 'v-messages__message') or contains(@class, 'v-field__error') or contains(@class, 'error') or contains(@class, 'alert') or contains(@role, 'alert')]",
    ]

    fatal_keywords = (
        "inválid", "inval", "incorret", "não confere", "nao confere",
        "acesso negado", "captcha", "bloque", "tentativa", "falhou", "credenc"
    )
    soft_keywords = ("obrigat", "preencha", "campo obrigatório", "campo obrigatorio")

    for error_selector in error_indicators:
        try:
            elements = driver.find_elements(By.XPATH, error_selector)
        except Exception:
            continue

        for element in elements:
            try:
                if not element.is_displayed():
                    continue
                error_text = " ".join((element.text or "").split())
                if not error_text:
                    continue

                lowered = error_text.lower()
                if any(k in lowered for k in soft_keywords):
                    continue
                if any(k in lowered for k in fatal_keywords):
                    print(f"[LOGIN] ✗ Erro de login detectado: {error_text}")
                    return False
            except Exception:
                continue

    # Estratégia 3: Formulário ainda visível significa estado possivelmente transitório
    # (não tratar como falha imediata para evitar falso negativo logo após o clique).
    login_form_indicators = [
        "//input[@type='email'] | //input[@type='text'][contains(@placeholder, 'E-mail')]",
        "//input[@type='password'] | //input[@type='text'][contains(@placeholder, 'Senha')]",
        "//label[contains(text(), 'Entre com seu E-mail')]",
    ]

    visible_form_fields = 0
    for form_selector in login_form_indicators:
        try:
            elements = driver.find_elements(By.XPATH, form_selector)
            for elem in elements:
                if elem.is_displayed():
                    visible_form_fields += 1
                    break
        except Exception:
            continue

    if visible_form_fields >= 2:
        print(f"[LOGIN] ⚠ Formulário de login ainda visível ({visible_form_fields} campos) - aguardando")
        return None

    # Estratégia 4: Se ainda está em /login, pode estar processando; manter como ambíguo.
    if '/login' in current_url and '/assinante/login' in current_url:
        print(f"[LOGIN] ⚠ Ainda em página de login: {current_url} (aguardando transição)")
        return None

    # Se conseguiu passar por tudo mas não achou indicadores de login, é ambíguo
    print(f"[LOGIN] ⚠ Incerto: Não encontrou indicadores de login nem erros. URL: {driver.current_url}")
    return None  # Ambíguo


def _wait_login_validation(driver, timeout_seconds=8, label="submit"):
    """Valida login por uma janela curta após uma tentativa de submit."""
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    saw_explicit_error = False

    while time.monotonic() < deadline:
        attempts += 1
        _human_pause(0.5, 0.9)
        validation_result = _is_user_logged_in(driver)

        if validation_result is True:
            print(f"[LOGIN] ✓ Login validado após {label} (tentativa {attempts})")
            return True, saw_explicit_error
        if validation_result is False:
            saw_explicit_error = True
            print(f"[LOGIN] ✗ Erro explícito de login após {label}")
            return False, saw_explicit_error

        print(f"[LOGIN] ⚠ Aguardando confirmação de login após {label} (tentativa {attempts})...")

    return None, saw_explicit_error


def perform_login(driver):
    """
    Realiza login na plataforma do diário oficial com seletores robustos.
    Usa múltiplas estratégias para encontrar campos mesmo com IDs dinâmicos.
    DIFERENÇA CRÍTICA: Aguarda validação ativa de login bem-sucedido, não apenas 5s.
    """
    print(f"[LOGIN] Navegando para {DIARIO_LOGIN_URL}...")
    _write_stage_marker("login:start", DIARIO_LOGIN_URL)
    driver.get(DIARIO_LOGIN_URL)
    
    try:
        # Aguardar página carregar
        time.sleep(3)
        print("[LOGIN] Página de login carregada")
        _save_page_debug(driver, "login_page_loaded")

        login_deadline = time.monotonic() + LOGIN_TOTAL_TIMEOUT

        def reserve_login_budget(step_name, preferred_timeout):
            remaining_total = login_deadline - time.monotonic()
            if remaining_total <= 0:
                raise TimeoutError(f"Tempo total do login esgotado antes de localizar {step_name}")

            wait_timeout = min(preferred_timeout, remaining_total)
            print(
                f"[LOGIN] Orçamento para {step_name}: {wait_timeout:.1f}s "
                f"(restante total {remaining_total:.1f}s)"
            )
            return wait_timeout

        def _is_visible_editable_input(field):
            if not field:
                return False
            try:
                field_type = (field.get_attribute("type") or "").strip().lower()
                if field_type == "hidden":
                    return False
                if not field.is_displayed() or not field.is_enabled():
                    return False
                readonly_attr = (field.get_attribute("readonly") or "").strip().lower()
                aria_hidden = (field.get_attribute("aria-hidden") or "").strip().lower()
                return readonly_attr not in ("true", "readonly") and aria_hidden not in ("true", "1")
            except Exception:
                return False

        def _find_visible_editable_field_any_frame(selectors, timeout, field_name):
            deadline = time.monotonic() + timeout

            try:
                driver.switch_to.default_content()
            except Exception:
                pass

            while time.monotonic() < deadline:
                for selector in selectors:
                    try:
                        for candidate in driver.find_elements(By.XPATH, selector):
                            if _is_visible_editable_input(candidate):
                                return candidate
                    except Exception:
                        continue

                try:
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                except Exception:
                    frames = []

                for idx, frame in enumerate(frames):
                    if time.monotonic() >= deadline:
                        break
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(frame)
                    except Exception:
                        continue

                    for selector in selectors:
                        try:
                            for candidate in driver.find_elements(By.XPATH, selector):
                                if _is_visible_editable_input(candidate):
                                    print(f"[LOGIN] {field_name} encontrado em iframe {idx}")
                                    return candidate
                        except Exception:
                            continue

                _human_pause(0.15, 0.25)

            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return None
        
        # ==================== CAMPO DE USUÁRIO ====================
        print("[LOGIN] Procurando campo de E-mail/Usuário...")
        
        # Seletores para campo de usuário (em ordem de preferência)
        username_selectors = [
            # Markup Vuetify atual do site
            "//label[contains(., 'Entre com seu E-mail ou CPF/CNPJ')]/ancestor::div[contains(@class, 'v-field')][1]//input[contains(@class, 'v-field__input') and not(@type='hidden')]",
            "//input[contains(@class, 'v-field__input') and @type='text' and @maxlength='100']",
            "//input[@type='text' and contains(@aria-labelledby, '-label') and @maxlength='100']",

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
        ]
        
        username_field = _find_visible_editable_field_any_frame(
            username_selectors,
            reserve_login_budget("campo de usuário", LOGIN_FIELD_TIMEOUT),
            "campo de usuário",
        )
        
        if not username_field:
            print("[LOGIN] Nenhum campo de usuário encontrado!")
            print("[LOGIN] Tentando screenshot para debug...")
            print(f"[LOGIN] URL atual: {driver.current_url}")
            _save_page_debug(driver, "login_username_not_found")
            _save_page_debug(driver, "login_error")
            raise Exception("Campo de usuário não encontrado com nenhum seletor")
        
        print(f"[LOGIN] Campo de Usuário encontrado")
        _write_stage_marker("login:username_found")
        _human_scroll_into_view(driver, username_field)
        username_field.clear()
        _human_pause(0.15, 0.4)
        username_field.send_keys(DIARIO_USER)
        _human_pause(0.25, 0.7)
        print(f"[LOGIN] Usuário preenchido: {DIARIO_USER[:3]}***")
        
        # ==================== CAMPO DE SENHA ====================
        print("[LOGIN] Procurando campo de Senha...")
        
        # Seletores para campo de senha (em ordem de preferência)
        password_selectors = [
            # Markup Vuetify atual do site
            "//label[contains(., 'Senha')]/ancestor::div[contains(@class, 'v-field')][1]//input[contains(@class, 'v-field__input') and (@type='password' or @type='text') and not(@type='hidden')]",
            "//input[contains(@class, 'v-field__input') and @type='password' and @maxlength='20']",
            "//input[@type='password' and contains(@aria-labelledby, '-label') and @maxlength='20']",

            # Por type=password
            "//input[@type='password']",
            "//input[contains(@type, 'password')]",

            # Por placeholder
            "//input[@placeholder='Senha']",
            "//input[@placeholder='senha']",
            "//input[@placeholder='Password']",
            "//input[contains(@placeholder, 'Senha')]",
            "//input[contains(@placeholder, 'Password')]",
            
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
        ]
        
        password_field = _find_visible_editable_field_any_frame(
            password_selectors,
            reserve_login_budget("campo de senha", LOGIN_FIELD_TIMEOUT),
            "campo de senha",
        )
        
        if not password_field:
            print("[LOGIN] Nenhum campo de senha encontrado!")
            _save_page_debug(driver, "login_password_not_found")
            _save_page_debug(driver, "login_error")
            raise Exception("Campo de senha não encontrado com nenhum seletor")
        
        print(f"[LOGIN] Campo de Senha encontrado")
        _write_stage_marker("login:password_found")
        _human_scroll_into_view(driver, password_field)
        password_field.clear()
        _human_pause(0.15, 0.4)
        password_field.send_keys(DIARIO_PASSWORD)
        _human_pause(0.25, 0.7)
        print(f"[LOGIN] Senha preenchida")

        def _dispatch_reactive_events(target):
            """Dispara eventos para frameworks reativos (ex.: Vuetify) validarem o formulário."""
            try:
                driver.execute_script(
                    """
                    const el = arguments[0];
                    ['input', 'change', 'blur'].forEach((evtName) => {
                        el.dispatchEvent(new Event(evtName, { bubbles: true }));
                    });
                    """,
                    target,
                )
            except Exception as e:
                print(f"[LOGIN] Aviso: falha ao disparar eventos reativos: {e}")

        def _get_input_value(target):
            try:
                return driver.execute_script("return arguments[0].value || '';", target) or ""
            except Exception:
                try:
                    return target.get_attribute("value") or ""
                except Exception:
                    return ""

        def _set_input_value_js(target, value):
            try:
                driver.execute_script(
                    """
                    const el = arguments[0];
                    const val = arguments[1];
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                    if (setter) {
                        setter.call(el, val);
                    } else {
                        el.value = val;
                    }
                    ['input', 'change', 'blur'].forEach((evtName) => {
                        el.dispatchEvent(new Event(evtName, { bubbles: true }));
                    });
                    """,
                    target,
                    value,
                )
                return True
            except Exception as e:
                print(f"[LOGIN] Aviso: falha ao setar valor via JS: {e}")
                return False

        def _ensure_field_value(field, expected_value, field_name, mask=False):
            actual = (_get_input_value(field) or "").strip()
            if actual == expected_value:
                shown = f"len={len(actual)}" if mask else (actual[:3] + "***" if actual else "")
                print(f"[LOGIN] Valor confirmado em {field_name}: {shown}")
                return True

            print(
                f"[LOGIN] Aviso: valor de {field_name} diferente do esperado após send_keys "
                f"(len_atual={len(actual)} len_esperado={len(expected_value)}). Tentando fallback JS..."
            )
            if not _set_input_value_js(field, expected_value):
                return False

            actual_after_js = (_get_input_value(field) or "").strip()
            if actual_after_js == expected_value:
                shown = f"len={len(actual_after_js)}" if mask else (actual_after_js[:3] + "***" if actual_after_js else "")
                print(f"[LOGIN] Valor confirmado em {field_name} após fallback JS: {shown}")
                return True

            print(
                f"[LOGIN] ERRO: não foi possível confirmar valor em {field_name} "
                f"(len_final={len(actual_after_js)} len_esperado={len(expected_value)})"
            )
            return False

        def _resolve_active_login_container():
            """Localiza o container ativo do login a partir dos campos já encontrados."""
            if not _safe_element_ref(username_field) or not _safe_element_ref(password_field):
                return None
            try:
                container = driver.execute_script(
                    """
                    const userField = arguments[0];
                    const passField = arguments[1];

                    function isVisible(el) {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                            return false;
                        }
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }

                    let node = userField;
                    while (node) {
                        if (
                            node.contains(passField) &&
                            isVisible(node) &&
                            node.querySelector("button")
                        ) {
                            return node;
                        }
                        node = node.parentElement;
                    }

                    return null;
                    """,
                    username_field,
                    password_field,
                )
                return container
            except Exception:
                return None

        def _detect_visible_login_error():
            """Busca mensagens visíveis de erro para distinguir falha de autenticação de timeout de navegação."""
            login_container = _resolve_active_login_container()
            error_selectors = [
                ".//*[contains(@class, 'v-messages__message') and normalize-space()]",
                ".//*[contains(@class, 'v-field__error') and normalize-space()]",
                ".//*[contains(@class, 'error') and normalize-space()]",
                ".//*[contains(@class, 'alert') and normalize-space()]",
                ".//*[contains(@role, 'alert') and normalize-space()]",
                ".//*[contains(@aria-live, 'assertive') and normalize-space()]",
            ]
            fatal_keywords = (
                "inválid", "inval", "incorret", "não confere", "nao confere",
                "acesso negado", "captcha", "bloque", "tentativa", "falhou", "credenc"
            )

            soft_keywords = ("obrigat", "preencha", "campo obrigatório", "campo obrigatorio")

            snippets = []
            search_root = login_container if login_container else driver

            for selector in error_selectors:
                try:
                    elements = search_root.find_elements(By.XPATH, selector)
                except Exception:
                    continue
                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue
                        text = " ".join((element.text or "").split())
                        if not text:
                            continue
                        lowered = text.lower()
                        if len(lowered) > 260:
                            continue
                        if lowered in ("senha", "e-mail", "email", "usuário", "usuario"):
                            continue
                        if "já possuo cadastro" in lowered:
                            continue

                        if any(k in lowered for k in fatal_keywords):
                            snippets.append(text[:220])
                            if len(snippets) >= 3:
                                break

                        if any(k in lowered for k in soft_keywords):
                            print(f"[LOGIN] Mensagem de validação não-fatal detectada: {text[:120]}")
                    except Exception:
                        continue
                if len(snippets) >= 3:
                    break

            if snippets:
                dedup = []
                for msg in snippets:
                    if msg not in dedup:
                        dedup.append(msg)
                return " | ".join(dedup)
            return None

        def _has_logged_area_markers():
            markers = [
                "//*[contains(., 'Public. Legal')]",
                "//*[contains(., 'Data Edição') or contains(., 'Data Edicao')]",
                "//h5[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'JORNAL')]",
                "//button[contains(., 'PDF')]",
            ]
            for selector in markers:
                try:
                    matches = driver.find_elements(By.XPATH, selector)
                    if any(m.is_displayed() for m in matches):
                        return True
                except Exception:
                    continue
            return False

        if not _ensure_field_value(username_field, DIARIO_USER, "usuário"):
            _save_page_debug(driver, "login_username_value_mismatch")
            raise Exception("Campo de usuário não manteve o valor esperado antes do submit")

        if not _ensure_field_value(password_field, DIARIO_PASSWORD, "senha", mask=True):
            _save_page_debug(driver, "login_password_value_mismatch")
            raise Exception("Campo de senha não manteve o valor esperado antes do submit")

        def _button_state_snapshot(button):
            try:
                disabled_attr = button.get_attribute("disabled")
                aria_disabled = button.get_attribute("aria-disabled")
                classes = button.get_attribute("class") or ""
                return {
                    "disabled_attr": (disabled_attr or "").strip().lower(),
                    "aria_disabled": (aria_disabled or "").strip().lower(),
                    "classes": classes,
                    "is_enabled": button.is_enabled(),
                }
            except Exception as e:
                return {
                    "disabled_attr": "",
                    "aria_disabled": "",
                    "classes": "",
                    "is_enabled": False,
                    "error": str(e),
                }

        def _is_login_button_enabled(button):
            state = _button_state_snapshot(button)
            return (
                state.get("disabled_attr", "") in ("", "false", "0")
                and state.get("aria_disabled", "") not in ("true", "1")
                and "v-btn--disabled" not in state.get("classes", "")
                and bool(state.get("is_enabled"))
            )

        def _log_field_lengths(stage_label):
            try:
                user_len = len((_get_input_value(username_field) or "").strip())
            except Exception:
                user_len = -1
            try:
                pass_len = len((_get_input_value(password_field) or "").strip())
            except Exception:
                pass_len = -1
            print(f"[LOGIN] {stage_label}: user_len={user_len}, pass_len={pass_len}")
            return user_len, pass_len

        def _safe_element_ref(element):
            if not element:
                return False
            try:
                _ = element.tag_name
                return True
            except Exception:
                return False

        def _reacquire_timeout_budget():
            remaining_total = max(0.0, login_deadline - time.monotonic())
            short_timeout = min(2.0, max(0.7, remaining_total / 6 if remaining_total > 0 else 0.7))
            print(
                f"[LOGIN] Janela curta de recuperação: {short_timeout:.1f}s "
                f"(restante total {remaining_total:.1f}s)"
            )
            return short_timeout

        def _reacquire_login_fields_and_button(label):
            nonlocal username_field, password_field, login_button

            short_timeout = _reacquire_timeout_budget()

            recovered_username = _find_visible_editable_field_any_frame(
                username_selectors,
                short_timeout,
                "campo de usuário",
            )
            if recovered_username:
                username_field = recovered_username
            else:
                print(f"[LOGIN] {label}: aviso ao relocalizar usuário, mantendo referência atual")

            recovered_password = _find_visible_editable_field_any_frame(
                password_selectors,
                short_timeout,
                "campo de senha",
            )
            if recovered_password:
                password_field = recovered_password
            else:
                print(f"[LOGIN] {label}: aviso ao relocalizar senha, mantendo referência atual")

            recovered_button = find_element_with_fallback_any_frame(
                driver,
                button_selectors,
                short_timeout,
            )
            if recovered_button:
                login_button = recovered_button
            else:
                print(f"[LOGIN] {label}: aviso ao relocalizar botão Entrar, mantendo referência atual")

        def _prepare_submit_attempt(label):
            _reacquire_login_fields_and_button(label)
            _log_field_lengths(f"{label} pre-submit (antes de revalidar)")

            if not _safe_element_ref(username_field) or not _safe_element_ref(password_field):
                print(f"[LOGIN] {label}: campos indisponíveis para revalidação")
                return False

            user_current = (_get_input_value(username_field) or "").strip()
            pass_current = (_get_input_value(password_field) or "").strip()

            if not user_current:
                print(f"[LOGIN] {label}: usuário vazio/resetado, reaplicando valor")
                _human_scroll_into_view(driver, username_field)
                username_field.clear()
                _human_pause(0.1, 0.25)
                username_field.send_keys(DIARIO_USER)
                _human_pause(0.15, 0.35)

            if not pass_current:
                print(f"[LOGIN] {label}: senha vazia/resetada, reaplicando valor")
                _human_scroll_into_view(driver, password_field)
                password_field.clear()
                _human_pause(0.1, 0.25)
                password_field.send_keys(DIARIO_PASSWORD)
                _human_pause(0.15, 0.35)

            user_ok = _ensure_field_value(username_field, DIARIO_USER, "usuário")
            pass_ok = _ensure_field_value(password_field, DIARIO_PASSWORD, "senha", mask=True)

            if user_ok and pass_ok:
                _dispatch_reactive_events(username_field)
                _human_pause(0.1, 0.25)
                _dispatch_reactive_events(password_field)
                _human_pause(0.15, 0.35)
            _log_field_lengths(f"{label} pre-submit (depois de revalidar)")
            return user_ok and pass_ok

        def _is_field_interactable(field):
            if not _safe_element_ref(field):
                return False
            try:
                if not field.is_displayed() or not field.is_enabled():
                    return False
                disabled_attr = (field.get_attribute("disabled") or "").strip().lower()
                readonly_attr = (field.get_attribute("readonly") or "").strip().lower()
                aria_disabled = (field.get_attribute("aria-disabled") or "").strip().lower()
                return (
                    disabled_attr in ("", "false", "0")
                    and readonly_attr not in ("true", "readonly")
                    and aria_disabled not in ("true", "1")
                )
            except Exception:
                return False

        def _is_form_locked_for_processing():
            user_ok = _is_field_interactable(username_field)
            pass_ok = _is_field_interactable(password_field)
            btn_ok = _safe_element_ref(login_button) and _is_login_button_enabled(login_button)
            return not (user_ok and pass_ok and btn_ok)

        def _wait_submit_outcome(label, preferred_seconds):
            remaining_total = login_deadline - time.monotonic()
            if remaining_total <= 0.5:
                print(f"[LOGIN] Sem orçamento para validação pós-{label} (restante {remaining_total:.1f}s)")
                return "timeout", False

            effective_timeout = min(preferred_seconds, max(2.0, remaining_total - 1.0))
            print(
                f"[LOGIN] Janela de validação pós-{label}: {effective_timeout:.1f}s "
                f"(restante total {remaining_total:.1f}s)"
            )

            deadline = time.monotonic() + effective_timeout
            saw_locked = False
            unlocked_polls = 0

            while time.monotonic() < deadline:
                validation_result = _is_user_logged_in(driver)
                if validation_result is True:
                    return "success", False
                if validation_result is False:
                    return "error", True

                visible_error = _detect_visible_login_error()
                if visible_error:
                    print(f"[LOGIN] Mensagem visível após {label}: {visible_error}")
                    return "error", True

                locked = _is_form_locked_for_processing()
                if locked:
                    saw_locked = True
                    unlocked_polls = 0
                    print(f"[LOGIN] {label}: formulário bloqueado/processando, aguardando...")
                else:
                    unlocked_polls += 1
                    if saw_locked and unlocked_polls >= 2:
                        print(f"[LOGIN] {label}: formulário voltou a ficar interagível")
                        return "ready_retry", False

                _human_pause(0.6, 0.95)

            return "timeout", False
        
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
        
        login_button = None

        # Prioriza botão dentro do container ativo (mesmo contexto dos campos usuário/senha).
        login_container = _resolve_active_login_container()
        if login_container:
            for selector in [
                ".//button[normalize-space()='Entrar']",
                ".//span[normalize-space()='Entrar']/ancestor::button",
                ".//button[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'entrar')]",
                ".//button[@type='submit']",
            ]:
                try:
                    for candidate in login_container.find_elements(By.XPATH, selector):
                        if candidate.is_displayed():
                            login_button = candidate
                            break
                except Exception:
                    continue
                if login_button:
                    break

        if not login_button:
            login_button = find_clickable_element_with_fallback_any_frame(
                driver,
                button_selectors,
                reserve_login_budget("botão Entrar", LOGIN_BUTTON_TIMEOUT),
            )
        
        if not login_button:
            print("[LOGIN] Nenhum botão de entrar encontrado!")
            _save_page_debug(driver, "login_button_not_found")
            _save_page_debug(driver, "login_error")
            raise Exception("Botão 'Entrar' não encontrado com nenhum seletor")
        
        print(f"[LOGIN] Botão 'Entrar' encontrado")
        _write_stage_marker("login:button_found")

        # Força validação reativa dos campos antes de qualquer tentativa de submit.
        _dispatch_reactive_events(username_field)
        _human_pause(0.15, 0.35)
        _dispatch_reactive_events(password_field)
        _human_pause(0.2, 0.5)

        enable_wait_deadline = time.monotonic() + 10.0
        login_button_enabled = _is_login_button_enabled(login_button)
        while not login_button_enabled and time.monotonic() < enable_wait_deadline:
            _dispatch_reactive_events(password_field)
            _human_pause(0.15, 0.3)
            try:
                _human_scroll_into_view(driver, login_button)
            except Exception:
                pass
            login_button_enabled = _is_login_button_enabled(login_button)

        button_state = _button_state_snapshot(login_button)
        print(
            "[LOGIN] Estado botão antes do submit: "
            f"disabled='{button_state.get('disabled_attr', '')}', "
            f"aria-disabled='{button_state.get('aria_disabled', '')}', "
            f"enabled={button_state.get('is_enabled', False)}, "
            f"class='{button_state.get('classes', '')}'"
        )

        if not login_button_enabled:
            _save_page_debug(driver, "login_button_still_disabled")
            raise TimeoutError(
                "Botão 'Entrar' permaneceu desabilitado após preenchimento e eventos reativos. "
                "A validação de frontend não confirmou o formulário."
            )

        saw_explicit_error = False
        login_validated = False

        # Fluxo simplificado: um submit principal + um retry JS apenas se o formulário destravar.
        if not login_validated and not saw_explicit_error:
            try:
                _prepare_submit_attempt("tentativa_1_click_humanizado")
                if _safe_element_ref(login_button):
                    _human_click(driver, login_button, label="botão Entrar")
                    print("[LOGIN] Submit principal realizado (ActionChains)")
                    _write_stage_marker("login:submitted_click", driver.current_url)
                    _log_field_lengths("tentativa_1_click_humanizado pos-submit")

                    outcome, explicit_error = _wait_submit_outcome("ActionChains click", preferred_seconds=30.0)
                    saw_explicit_error = saw_explicit_error or explicit_error
                    if outcome == "success":
                        login_validated = True
                    elif outcome == "ready_retry" and not saw_explicit_error:
                        print("[LOGIN] Formulário desbloqueou sem sucesso; executando retry único via JS click")
                        _prepare_submit_attempt("tentativa_2_js_click_fallback")
                        if _safe_element_ref(login_button):
                            driver.execute_script("arguments[0].click();", login_button)
                            _write_stage_marker("login:submitted_js_click", driver.current_url)
                            _log_field_lengths("tentativa_2_js_click_fallback pos-submit")
                            retry_outcome, retry_explicit_error = _wait_submit_outcome("JS click fallback", preferred_seconds=10.0)
                            saw_explicit_error = saw_explicit_error or retry_explicit_error
                            if retry_outcome == "success":
                                login_validated = True
                        else:
                            print("[LOGIN] Retry JS ignorado: botão indisponível")
                else:
                    print("[LOGIN] Botão indisponível antes do submit principal")
            except Exception as e:
                print(f"[LOGIN] Aviso: fluxo de submit simplificado falhou: {e}")

        if not login_validated:
            try:
                if _has_logged_area_markers():
                    print("[LOGIN] ✓ Marcadores de área logada detectados mesmo sem mudança clara de URL")
                    login_validated = True
            except Exception:
                pass

        if not login_validated:
            print("[LOGIN] ✗ Login não validado após todas as estratégias de submit")
            _save_page_debug(driver, "login_timeout_validation")
            if saw_explicit_error:
                _save_page_debug(driver, "login_failed_after_click")
                raise Exception(
                    "Login falhou após múltiplas tentativas de submit: mensagem de erro explícita detectada. "
                    "Verifique credenciais ou mudança de layout."
                )
            raise TimeoutError(
                "Não foi possível validar login após múltiplas estratégias de submit. "
                "Possível bloqueio por anti-bot ou evento de clique não disparando no CI."
            )

        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        print(f"[LOGIN] ✓ Login realizado e validado com sucesso. URL: {driver.current_url}")
        _write_stage_marker("login:completed", driver.current_url)
        
    except Exception as e:
        print(f"[LOGIN] ERRO durante login: {e}")
        print(f"[LOGIN] Tipo de erro: {type(e).__name__}")
        _save_page_debug(driver, "login_error")
        _write_stage_marker("login:error", str(e))
        raise


# ==================== FILTRO DE PUBLICAÇÕES ====================
def set_publication_filter(driver):
    """Configura o filtro 'Public. Legal' como 'Exceto' para exibir apenas edições jornalísticas"""
    print("[FILTRO] Configurando filtro 'Public. Legal' como 'Exceto'...")
    start_ts = time.monotonic()
    deadline = start_ts + FILTER_TOTAL_TIMEOUT

    def remaining_budget():
        return max(0.0, deadline - time.monotonic())
    
    try:
        # Evita bloquear a execução por muito tempo nesta etapa.
        _human_pause(0.25, 0.7)
        
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

        # Item de debug: HTML do elemento do filtro identificado
        _save_element_html(driver, dropdown_input, "public_legal_filter_input.html")

        current_value = (dropdown_input.get_attribute("value") or "").strip().lower()
        if current_value == "exceto":
            print("[FILTRO] Filtro já está em 'Exceto'")
            _save_debug_html("public_legal_filter_after.html", driver.page_source)
            return
        
        # Clicar no dropdown para abrir as opções
        _human_click(driver, dropdown_input, label="filtro Public. Legal")
        print("[FILTRO] Dropdown clicado, aguardando opções...")
        _human_pause(0.25, 0.6)
        # Tentar foco adicional para forçar carregamento de opções em layouts instáveis
        try:
            driver.execute_script("arguments[0].scrollIntoView();", dropdown_input)
            _human_pause(0.15, 0.35)
        except Exception:
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
            _human_pause(0.25, 0.6)
            all_options = driver.find_elements(By.XPATH, "//*[@role='option'] | //div[@role='listitem'] | //div[contains(@class, 'v-list-item')]")
            print(f"[FILTRO] Após segundo clique - Total de opções: {len(all_options)}")

        if len(all_options) == 0:
            print("[FILTRO] AVISO: Menu sem opções detectáveis; seguindo sem filtro para não estourar timeout")
            return
        
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
            budget = remaining_budget()
            if budget <= 0:
                break
            try:
                exceto_option = WebDriverWait(driver, min(1.2, budget), poll_frequency=0.2).until(
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
        _human_click(driver, exceto_option, label="opção Exceto")
        print("[FILTRO] Opção 'Exceto' selecionada!")
        
        # Aguardar filtro ser aplicado
        _human_pause(0.25, 0.7)
        # Validação: conferir valor final do dropdown
        try:
            current_value = dropdown_input.get_attribute("value")
            print(f"[FILTRO] Valor atual do dropdown: '{current_value}'")
            if current_value and "exceto" in current_value.lower():
                print("[FILTRO] ✓ Filtro aplicado com sucesso!")
            else:
                print("[FILTRO] ⚠️ AVISO: Filtro pode não ter sido aplicado corretamente")
        except Exception as e:
            print(f"[FILTRO] Não foi possível validar filtro: {e}")
        print("[FILTRO] Filtro aplicado com sucesso - exibindo apenas edições jornalísticas")
        _save_debug_html("public_legal_filter_after.html", driver.page_source)
        elapsed = time.monotonic() - start_ts
        print(f"[FILTRO] Tempo total da etapa: {elapsed:.1f}s")
        
    except Exception as e:
        print(f"[FILTRO] ERRO ao configurar filtro: {e}")
        print("[FILTRO] Continuando sem filtro...")


# ==================== ACESSO E DOWNLOAD DO PDF ====================
def _parse_card_date_ddmmyyyy(text):
    """Extrai data no formato DD/MM/YYYY de um texto de card."""
    match = re.search(r"Data\s*Edi[çc][ãa]o\s*:\s*(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y")
    except ValueError:
        return None


def _parse_card_edition_number(text):
    """Extrai número da edição a partir de texto como 'Edição Nº 7342'."""
    match = re.search(r"Edi[çc][ãa]o\s*N[º°o]?\s*(\d+)", text, re.IGNORECASE)
    if not match:
        match = re.search(r"\bN[º°o]?\s*(\d{3,})\b", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _is_probable_jornal_card(card, card_text_lower):
    """Determina se o card parece ser de JORNAL, mesmo com variações de layout."""
    try:
        # Busca H5 dentro de v-card-title para confirmar se é JORNAL.
        # <div class="v-card-title ..."><h5>JORNAL</h5></div>
        # Isso garante que não é CLASSIFICADOS, VALVI, etc.
        h5_elements = card.find_elements(
            By.XPATH,
            ".//div[contains(@class, 'v-card-title')]//h5",
        )
        for h5 in h5_elements:
            h5_text = (h5.text or "").strip().upper()
            if h5_text == "JORNAL":
                return True
    except Exception:
        pass

    blocked_terms = ["valvi", "folheto", "classificados", "classificado", "public. legal", "publicacao legal"]
    if any(tag in card_text_lower for tag in blocked_terms):
        return False

    if "jornal" in card_text_lower:
        return True

    try:
        img_elements = card.find_elements(By.XPATH, ".//img")
        for img in img_elements:
            src = (img.get_attribute("src") or "").lower()
            alt = (img.get_attribute("alt") or "").lower()
            if "jornal" in src or "jornal" in alt:
                return True
    except Exception:
        pass

    try:
        headings = card.find_elements(By.XPATH, ".//*[self::h4 or self::h5 or self::h6 or contains(@class,'title')]")
        for heading in headings:
            htxt = (heading.text or "").strip().lower()
            if "jornal" in htxt:
                return True
    except Exception:
        pass

    return False


def _write_cards_summary(driver, cards):
    """Gera resumo textual dos cards renderizados para acelerar diagnóstico em CI."""
    lines = [f"total_cards={len(cards)}"]
    for idx, card in enumerate(cards[:20]):
        try:
            txt = (card.text or card.get_attribute("innerText") or "").strip().replace("\n", " | ")
            txt = re.sub(r"\s+", " ", txt)
            txt = txt[:260]
            # Tenta identificar titulo do card (H5 em v-card-title)
            card_title = "?"
            try:
                h5_elem = card.find_element(By.XPATH, ".//div[contains(@class, 'v-card-title')]//h5")
                card_title = (h5_elem.text or "").strip().upper()
            except Exception:
                pass
            has_pdf = bool(
                card.find_elements(
                    By.XPATH,
                    ".//*[contains(translate(@title, 'PDF', 'pdf'), 'pdf') or "
                    "contains(translate(@aria-label, 'PDF', 'pdf'), 'pdf') or "
                    "contains(translate(@class, 'PDF', 'pdf'), 'pdf') or "
                    "contains(translate(@href, 'PDF', 'pdf'), '.pdf') or "
                    "contains(translate(@src, 'PDF', 'pdf'), 'pdf')]",
                )
            )
            lines.append(f"[{idx}] title={card_title} has_pdf={has_pdf} text={txt}")
        except Exception as exc:
            lines.append(f"[{idx}] erro={exc}")

    file_path = "/tmp/listagem_cards_summary.txt"
    try:
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        print(f"[DEBUG] Resumo dos cards salvo: {file_path}")
    except Exception as e:
        print(f"[DEBUG] Falha ao salvar resumo dos cards: {e}")


def _is_valid_pdf_trigger_element(element):
    """Valida se o elemento é um gatilho real de PDF (ícone/botão PDF), evitando clique em card."""
    try:
        tag = (element.tag_name or "").lower()
    except Exception:
        tag = ""

    class_attr = (element.get_attribute("class") or "").lower()
    title_attr = (element.get_attribute("title") or "").lower()
    aria_label = (element.get_attribute("aria-label") or "").lower()
    role_attr = (element.get_attribute("role") or "").lower()
    href_attr = (element.get_attribute("href") or "").lower()
    src_attr = (element.get_attribute("src") or "").lower()

    # Caso clássico do site: <i class="mdi-file-pdf-box ... v-icon--clickable" title="Visualizar PDF">
    if (
        tag == "i"
        and "mdi-file-pdf-box" in class_attr
        and "v-icon--clickable" in class_attr
        and "visualizar pdf" in title_attr
        and role_attr == "button"
    ):
        return True

    # Compatibilidade com variações do ícone MDI.
    if tag == "i" and "mdi-file-pdf" in class_attr:
        return True

    if tag in ("button", "a") and ("pdf" in title_attr or "pdf" in aria_label):
        return True

    if tag == "a" and ".pdf" in href_attr:
        return True

    if "visualizar pdf" in title_attr:
        return True

    if "pdf" in aria_label and role_attr in ("button", "link"):
        return True

    if "mdi-file-pdf" in class_attr and role_attr in ("button", "link"):
        return True

    if tag in ("i", "span", "button", "a") and "pdf" in class_attr:
        return True

    if tag == "img" and "pdf" in src_attr:
        return True

    # Evita card/container como alvo direto.
    if tag in ("div", "article") and ("v-card" in class_attr or "suita-block-home" in class_attr):
        return False

    # fallback: aceita wrappers clicáveis que contenham ícone PDF dentro.
    if tag in ("button", "a", "span", "div"):
        try:
            nested_pdf_icons = element.find_elements(By.XPATH, ".//i[contains(@class, 'mdi-file-pdf')]")
            if nested_pdf_icons:
                return True
        except Exception:
            pass

    return False


def _resolve_click_target_for_pdf(card, element):
    """Resolve alvo clicável apropriado para o PDF, priorizando botão/link acima do ícone."""
    try:
        tag = (element.tag_name or "").lower()
    except Exception:
        tag = ""

    class_attr = (element.get_attribute("class") or "").lower()
    title_attr = (element.get_attribute("title") or "").lower()
    role_attr = (element.get_attribute("role") or "").lower()

    # Prioriza o próprio ícone canônico de download de PDF, sem promover para ancestral.
    if (
        tag == "i"
        and "mdi-file-pdf-box" in class_attr
        and "v-icon--clickable" in class_attr
        and "visualizar pdf" in title_attr
        and role_attr == "button"
    ):
        return element

    if _is_valid_pdf_trigger_element(element):
        try:
            clickable_ancestor = element.find_element(
                By.XPATH,
                "./ancestor::*[(self::button or self::a or @role='button' or @role='link')][1]",
            )
            if clickable_ancestor and _is_valid_pdf_trigger_element(clickable_ancestor):
                return clickable_ancestor
        except Exception:
            pass
        return element

    try:
        clickable_ancestor = element.find_element(
            By.XPATH,
            "./ancestor::*[(self::button or self::a or @role='button' or @role='link')][1]",
        )
        if clickable_ancestor and _is_valid_pdf_trigger_element(clickable_ancestor):
            return clickable_ancestor
    except Exception:
        pass

    try:
        wrappers = card.find_elements(
            By.XPATH,
            ".//*[self::button or self::a or @role='button' or @role='link']["
            "contains(translate(@title,'PDF','pdf'),'pdf') or "
            "contains(translate(@aria-label,'PDF','pdf'),'pdf') or "
            "contains(translate(@class,'PDF','pdf'),'pdf') or "
            "contains(translate(@href,'PDF','pdf'),'.pdf') or "
            ".//i[contains(translate(@class,'PDF','pdf'),'pdf')] or "
            ".//img[contains(translate(@src,'PDF','pdf'),'pdf')]"
            "]",
        )
        for wrapper in wrappers:
            if _is_valid_pdf_trigger_element(wrapper):
                return wrapper
    except Exception:
        pass

    # Alguns layouts usam ícone de PDF em <img>/<span>/<i> e o clique é no ancestral.
    try:
        clickables = element.find_elements(
            By.XPATH,
            "./ancestor::*[(self::a or self::button or @role='button' or @role='link')][1]",
        )
        if clickables:
            return clickables[0]
    except Exception:
        pass

    return None


def search_edition_by_name(driver, edition_name="JORNAL"):
    """Aplica busca pelo nome da edição para reduzir ruído de resultados."""
    print(f"[PDF] Aplicando busca por nome de edição: {edition_name}")

    search_selectors = [
        "//input[contains(@placeholder, 'Pesquisar nome edição')]",
        "//input[contains(@placeholder, 'Pesquisar nome edicao')]",
        "//input[contains(@placeholder, 'nome edição')]",
        "//input[contains(@placeholder, 'nome edicao')]",
        "//input[contains(@aria-label, 'nome edição')]",
        "//input[contains(@aria-label, 'nome edicao')]",
        "//input[contains(@placeholder, 'Pesquisar texto nas edições')]",
        "//input[contains(@placeholder, 'Pesquisar texto nas edicoes')]",
    ]

    search_input = None
    for selector in search_selectors:
        try:
            search_input = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
            if search_input and search_input.is_displayed():
                break
        except Exception:
            continue

    if not search_input:
        print("[PDF] AVISO: Campo de busca por nome de edição não encontrado")
        return False

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
    time.sleep(0.5)
    search_input.clear()
    search_input.send_keys(edition_name)
    search_input.send_keys(Keys.ENTER)
    time.sleep(2)
    print("[PDF] Busca por nome aplicada")
    return True


def wait_for_listing_ready(driver, timeout=LISTING_READY_TIMEOUT):
    """Confirma que a listagem carregou antes de iniciar a busca do PDF."""
    print(f"[LISTAGEM] Aguardando listagem ficar pronta (timeout={timeout}s)...")
    _write_stage_marker("listing:waiting")

    readiness_checks = [
        ("campo_busca_edicao", "//input[contains(@placeholder, 'Pesquisar nome edição')]"),
        ("card_edicao", "//div[contains(@class,'suita-block-home') or contains(@class,'v-card') or contains(@class,'edition')]"),
        ("icone_pdf", "//i[contains(@class,'mdi-file-pdf') or contains(@title,'PDF') or contains(@aria-label,'PDF')]"),
    ]

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for label, xpath in readiness_checks:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
            except Exception:
                elements = []

            visible_elements = [element for element in elements if element.is_displayed()]
            if visible_elements:
                print(f"[LISTAGEM] Sinal de prontidão detectado: {label} ({len(visible_elements)} visíveis)")
                _write_stage_marker("listing:ready", label)
                return label
        time.sleep(0.5)

    _save_page_debug(driver, "listagem_not_ready")
    _write_stage_marker("listing:timeout")
    raise TimeoutError("Listagem não ficou pronta após o login")


def get_jornal_candidates(driver):
    """Coleta cards válidos de JORNAL com ícone PDF clicável."""
    card_xpaths = [
        "//div[contains(@class,'suita-block-home') and contains(@class,'v-card')]",
        "//div[contains(@class,'suita-block-home')]",
        "//div[contains(@class,'v-card')]",
        "//article[contains(@class,'card') or contains(@class,'edition')]",
    ]

    try:
        WebDriverWait(driver, CARD_DISCOVERY_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class,'suita-block-home') or contains(@class,'v-card') or contains(@class,'edition')]") )
        )
    except Exception:
        pass

    candidate_cards = []
    seen_ids = set()
    for card_xpath in card_xpaths:
        for card in driver.find_elements(By.XPATH, card_xpath):
            if card.id in seen_ids:
                continue
            seen_ids.add(card.id)
            candidate_cards.append(card)

    print(f"[PDF] Cards do grid encontrados: {len(candidate_cards)}")
    _write_cards_summary(driver, candidate_cards)

    jornal_candidates = []
    for idx, card in enumerate(candidate_cards):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
        except Exception:
            pass

        card_text = (card.text or "").strip()
        if not card_text:
            card_text = (card.get_attribute("innerText") or "").strip()
        card_text_lower = card_text.lower()

        if not _is_probable_jornal_card(card, card_text_lower):
            continue

        edition_number = _parse_card_edition_number(card_text)
        edition_date = _parse_card_date_ddmmyyyy(card_text)

        pdf_icon = None
        icon_selectors = [
            ".//i[contains(@class,'mdi-file-pdf-box') and contains(@class,'v-icon--clickable') and (@title='Visualizar PDF' or contains(@title,'PDF'))]",
            ".//i[contains(@class,'mdi-file-pdf') and contains(@class,'v-icon--clickable')]",
            ".//i[@title='Visualizar PDF']",
            ".//i[contains(@title,'PDF') and contains(@class,'v-icon')]",
            ".//*[self::button or self::a][contains(@title,'PDF') or contains(@aria-label,'PDF') or .//i[contains(@class,'mdi-file-pdf')]]",
            ".//*[@role='button' or @role='link'][contains(@title,'PDF') or contains(@aria-label,'PDF') or .//i[contains(@class,'mdi-file-pdf')]]",
            ".//a[contains(translate(@href,'PDF','pdf'), '.pdf')]",
            ".//*[self::button or self::a or self::span or self::i][contains(translate(@class,'PDF','pdf'),'pdf') or contains(translate(@title,'PDF','pdf'),'pdf') or contains(translate(@aria-label,'PDF','pdf'),'pdf')]",
            ".//img[contains(translate(@src,'PDF','pdf'),'pdf') or contains(translate(@alt,'PDF','pdf'),'pdf')]",
        ]
        for icon_selector in icon_selectors:
            try:
                raw_pdf_elements = card.find_elements(By.XPATH, icon_selector)
                for raw_pdf_element in raw_pdf_elements[:8]:
                    resolved = _resolve_click_target_for_pdf(card, raw_pdf_element)
                    if not resolved:
                        continue
                    if not resolved.is_displayed():
                        continue
                    pdf_icon = resolved
                    break
                if pdf_icon:
                    break
            except Exception:
                continue

        if not pdf_icon:
            continue

        jornal_candidates.append(
            {
                "card": card,
                "pdf_icon": pdf_icon,
                "edition_number": edition_number if edition_number is not None else -1,
                "edition_date": edition_date,
                "debug": card_text.replace("\n", " | ")[:260],
            }
        )
        print(
            f"[PDF] Candidato {idx}: edição={edition_number}, data={edition_date.strftime('%d/%m/%Y') if edition_date else 'N/A'}"
        )

    jornal_candidates.sort(
        key=lambda item: (
            item["edition_date"] if item["edition_date"] is not None else datetime.min,
            item["edition_number"],
        ),
        reverse=True,
    )

    return jornal_candidates


def click_latest_jornal_pdf_fast(driver):
    """Tenta caminho rápido: clicar no gatilho de PDF do JORNAL mais recente disponível."""
    print("[PDF][FAST] Tentando clique imediato no PDF do JORNAL mais recente disponível...")
    _write_stage_marker("pdf_fast:start")

    # Janela curta para a SPA renderizar os cards principais.
    deadline = time.time() + FAST_PDF_CLICK_TIMEOUT
    attempts = 0

    while time.time() < deadline:
        attempts += 1
        jornal_candidates = get_jornal_candidates(driver)
        if jornal_candidates:
            selected = jornal_candidates[0]
            pdf_icon = selected["pdf_icon"]

            if not _is_valid_pdf_trigger_element(pdf_icon):
                raise Exception("Elemento encontrado não é gatilho PDF válido no fast-path")

            _save_element_html(driver, selected["card"], "card_jornal.html")
            _save_icon_context_html(driver, pdf_icon, "pdf_icon_context.html", levels=3)
            print(
                "[PDF][FAST] Selecionado JORNAL mais recente disponível: "
                f"edicao={selected['edition_number']}, "
                f"data={selected['edition_date'].strftime('%d/%m/%Y') if selected['edition_date'] else 'N/A'}"
            )
            _human_click(driver, pdf_icon, label="icone PDF (fast-path)")
            print("[PDF][FAST] Clique no ícone PDF executado")
            _write_stage_marker("pdf_fast:clicked", selected["debug"])
            return True

        _human_pause(0.45, 0.85)

    print(f"[PDF][FAST] Nenhum candidato JORNAL+PDF após {attempts} tentativas")
    _write_stage_marker("pdf_fast:not_found", f"tentativas={attempts}")
    return False


def access_and_download_pdf(driver):
    """Acessa a URL de download, aplica filtro e clica no ícone PDF do primeiro JORNAL disponível."""
    print(f"[PDF] Navegando para {DIARIO_ACCESS_URL}...")
    _write_stage_marker("listing:open", DIARIO_ACCESS_URL)
    driver.get(DIARIO_ACCESS_URL)
    
    try:
        # Aguardar página carregar com limite objetivo
        try:
            WebDriverWait(driver, PDF_WAIT_TIMEOUT).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            print("[PDF] AVISO: document.readyState não confirmou 'complete' dentro do tempo limite")

        _human_pause(0.35, 0.7)
        print("[PDF] Página de acesso carregada")
        _save_listing_page_debug(driver)
        wait_for_listing_ready(driver)

        # Por padrão, mantém Public. Legal no estado vazio (sem seleção explícita).
        # Isso evita custo de tempo/instabilidade no dropdown em ambiente CI.
        if APPLY_PUBLIC_LEGAL_FILTER:
            set_publication_filter(driver)
            _human_pause(0.5, 1.0)
        else:
            print("[FILTRO] Mantido padrão vazio (APPLY_PUBLIC_LEGAL_FILTER=false)")

        # Regra principal: após login, a primeira tentativa é clicar direto no PDF do primeiro JORNAL disponível.
        if click_latest_jornal_pdf_fast(driver):
            print("[PDF] Fast-path concluído com sucesso")
            return
        print("[PDF] Fast-path sem sucesso; aplicando fallback estruturado")
        _write_stage_marker("pdf:fallback_start")

        search_edition_by_name(driver, "JORNAL")
        _human_pause(0.5, 1.0)

        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(translate(@class,'PDF','pdf'),'pdf') or "
                        "contains(translate(@title,'PDF','pdf'),'pdf') or "
                        "contains(translate(@aria-label,'PDF','pdf'),'pdf') or "
                        "contains(translate(@href,'PDF','pdf'),'.pdf') or "
                        "contains(translate(@src,'PDF','pdf'),'pdf')]",
                    )
                )
            )
        except Exception:
            print("[PDF] AVISO: Ícone de PDF não apareceu no tempo esperado; tentando varredura por cards")

        print("[PDF] Localizando cards de edição e selecionando JORNAL mais recente...")
        jornal_candidates = get_jornal_candidates(driver)

        if not jornal_candidates:
            try:
                driver.save_screenshot("/tmp/jornal_not_found.png")
                with open("/tmp/jornal_not_found.html", "w", encoding="utf-8") as handle:
                    handle.write(driver.page_source)
                print("[PDF] Debug salvo em /tmp/jornal_not_found.png e /tmp/jornal_not_found.html")
            except Exception:
                pass
            raise Exception("Nenhum card de JORNAL válido com ícone PDF foi encontrado")

        selected = jornal_candidates[0]
        _save_element_html(driver, selected["card"], "card_jornal.html")

        try:
            classificados_card = driver.find_element(
                By.XPATH,
                "(//div[contains(@class, 'suita-block-home')][.//h5[normalize-space()='CLASSIFICADOS']])[1]",
            )
            _save_element_html(driver, classificados_card, "card_classificados.html")
            print("[PDF] Card CLASSIFICADOS salvo para debug")
        except Exception:
            print("[PDF] Card CLASSIFICADOS não encontrado para debug")

        pdf_icon = selected["pdf_icon"]
        if not _is_valid_pdf_trigger_element(pdf_icon):
            raise Exception("Elemento selecionado não é um gatilho de PDF válido")

        _save_icon_context_html(driver, pdf_icon, "pdf_icon_context.html", levels=3)
        print(
            "[PDF] Selecionado primeiro card JORNAL disponível: "
            f"edição={selected['edition_number']}, "
            f"data={selected['edition_date'].strftime('%d/%m/%Y') if selected['edition_date'] else 'N/A'}"
        )
        print(
            "[PDF] Gatilho PDF validado: "
            f"tag={pdf_icon.tag_name}, title='{pdf_icon.get_attribute('title')}', class='{pdf_icon.get_attribute('class')}'"
        )
        print(f"[PDF] Card selecionado (debug): {selected['debug']}")
        
        # Clicar no ícone para iniciar download
        _human_click(driver, pdf_icon, label="ícone PDF")
        print("[PDF] Clique no ícone realizado. Aguardando download...")
        _write_stage_marker("pdf:clicked", selected["debug"])
        
    except Exception as e:
        print(f"[PDF] ERRO ao acessar PDF: {e}")
        _write_stage_marker("pdf:error", str(e))
        raise


# ==================== PÓS-PROCESSAMENTO ====================
def wait_for_download_completion():
    """Aguarda o download ser completado monitorando a pasta data/"""
    print("[DOWNLOAD] Aguardando conclusão do download...")
    _write_stage_marker("download:waiting")
    
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
                _write_stage_marker("download:completed", downloaded_file)
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
    
    _write_stage_marker("download:timeout")
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
    
    # Verificar Playwright
    try:
        import playwright
        version = getattr(playwright, "__version__", "instalado")
        print(f"  Playwright: ✓ {version}")
    except ImportError:
        print("  Playwright: ✗ NÃO INSTALADO")
    
    print()


def _find_first_visible_locator(page, selectors, timeout_seconds, label):
    """Retorna o primeiro locator visível para uma lista de seletores XPath."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for selector in selectors:
            locator = page.locator(f"xpath={selector}")
            try:
                if locator.count() == 0:
                    continue
                candidate = locator.first
                if candidate.is_visible():
                    print(f"[PLAYWRIGHT] {label} encontrado com seletor: {selector}")
                    return candidate
            except Exception:
                continue
        time.sleep(0.2)
    return None


def _snapshot_login_form_state_playwright(page):
    """Captura estado resumido do formulário de login para diagnosticar lock persistente."""
    snapshot = {
        "has_visible_recaptcha_widget": False,
        "disabled_inputs": 0,
        "total_inputs": 0,
        "button_disabled": False,
    }

    try:
        recaptcha_widgets = page.locator(
            "xpath=//iframe[contains(@src, 'recaptcha')] | //div[contains(@class, 'g-recaptcha')] | //textarea[@name='g-recaptcha-response']"
        )
        snapshot["has_visible_recaptcha_widget"] = recaptcha_widgets.count() > 0
    except Exception:
        pass

    try:
        form_inputs = page.locator(
            "xpath=//form[contains(@class,'v-form')]//input[contains(@class,'v-field__input') and (@type='text' or @type='password')]"
        )
        total = form_inputs.count()
        snapshot["total_inputs"] = total
        disabled = 0
        for idx in range(min(total, 4)):
            try:
                if form_inputs.nth(idx).is_disabled():
                    disabled += 1
            except Exception:
                continue
        snapshot["disabled_inputs"] = disabled
    except Exception:
        pass

    try:
        btn = page.locator("xpath=//button[normalize-space()='Entrar']")
        if btn.count() > 0:
            snapshot["button_disabled"] = btn.first.is_disabled()
    except Exception:
        pass

    return snapshot


def _wait_login_success_playwright(page, timeout_seconds):
    """Aguarda confirmação de autenticação por URL ou elementos da área logada."""
    deadline = time.monotonic() + timeout_seconds
    fatal_keywords = ["inválid", "inval", "incorret", "não confere", "nao confere", "acesso negado", "captcha", "bloque", "falhou"]
    lock_streak = 0

    while time.monotonic() < deadline:
        current_url = (page.url or "").lower()
        if "/assinante/newflip" in current_url:
            return True, None

        success_markers = [
            "xpath=//*[contains(., 'Data Edição') or contains(., 'Data Edicao')]",
            "xpath=//h5[normalize-space()='JORNAL']",
            "xpath=//*[@title='Visualizar PDF' or contains(@class,'mdi-file-pdf')]",
        ]
        for marker in success_markers:
            try:
                loc = page.locator(marker)
                if loc.count() > 0 and loc.first.is_visible():
                    return True, None
            except Exception:
                continue

        try:
            alert_nodes = page.locator("xpath=//*[contains(@class,'v-messages__message') or contains(@class,'error') or contains(@role,'alert')]")
            total = min(alert_nodes.count(), 8)
            for idx in range(total):
                txt = " ".join((alert_nodes.nth(idx).inner_text() or "").split()).lower()
                if "captcha" in txt:
                    return "recaptcha_blocked", txt
                if any(word in txt for word in fatal_keywords):
                    return False, txt
        except Exception:
            pass

        lock_snapshot = _snapshot_login_form_state_playwright(page)
        lock_detected = (
            lock_snapshot.get("button_disabled")
            and lock_snapshot.get("disabled_inputs", 0) >= 2
        )
        if lock_detected:
            lock_streak += 1
            if lock_streak >= 5:
                if lock_snapshot.get("has_visible_recaptcha_widget"):
                    return "recaptcha_blocked", (
                        "form_locked_with_visible_recaptcha_widget"
                        f" (disabled_inputs={lock_snapshot.get('disabled_inputs', 0)})"
                    )
                return "form_locked", (
                    "form_locked_after_submit"
                    f" (disabled_inputs={lock_snapshot.get('disabled_inputs', 0)})"
                )
        else:
            lock_streak = 0

        time.sleep(0.7)

    return None, None


def perform_login_playwright(page):
    """Executa login via Playwright com foco em previsibilidade e estado visível."""
    print(f"[LOGIN] Navegando para {DIARIO_LOGIN_URL}...")
    _write_stage_marker("login:start", DIARIO_LOGIN_URL)
    page.goto(DIARIO_LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    print("[LOGIN] Página de login carregada")
    _save_page_debug_playwright(page, "login_page_loaded")

    username_selectors = [
        "//label[contains(., 'Entre com seu E-mail ou CPF/CNPJ')]/ancestor::div[contains(@class, 'v-field')][1]//input[contains(@class, 'v-field__input') and not(@type='hidden')]",
        "//input[contains(@class, 'v-field__input') and @type='text' and @maxlength='100']",
        "//input[@type='text' and @maxlength='100']",
        "//input[contains(@placeholder,'E-mail') or contains(@placeholder,'CPF') or contains(@placeholder,'CNPJ')]",
    ]
    password_selectors = [
        "//input[@type='password']",
        "//input[contains(@placeholder, 'Senha')]",
        "//label[contains(., 'Senha')]/ancestor::div[contains(@class, 'v-field')][1]//input",
    ]
    button_selectors = [
        "//button[normalize-space()='Entrar']",
        "//span[normalize-space()='Entrar']/ancestor::button",
        "//button[@type='submit']",
    ]

    username = _find_first_visible_locator(page, username_selectors, LOGIN_FIELD_TIMEOUT, "campo de usuário")
    if not username:
        _save_page_debug_playwright(page, "login_username_not_found")
        raise Exception("Campo de usuário não encontrado")
    _write_stage_marker("login:username_found")
    username.click()
    username.fill("")
    username.type(DIARIO_USER, delay=40)
    print(f"[LOGIN] Usuário preenchido: {DIARIO_USER[:3]}***")

    password = _find_first_visible_locator(page, password_selectors, LOGIN_FIELD_TIMEOUT, "campo de senha")
    if not password:
        _save_page_debug_playwright(page, "login_password_not_found")
        raise Exception("Campo de senha não encontrado")
    _write_stage_marker("login:password_found")
    password.click()
    password.fill("")
    password.type(DIARIO_PASSWORD, delay=40)
    print("[LOGIN] Senha preenchida")

    login_button = _find_first_visible_locator(page, button_selectors, LOGIN_BUTTON_TIMEOUT, "botão Entrar")
    if not login_button:
        _save_page_debug_playwright(page, "login_button_not_found")
        raise Exception("Botão 'Entrar' não encontrado")
    _write_stage_marker("login:button_found")

    login_button.click(timeout=PLAYWRIGHT_DEFAULT_TIMEOUT_MS)
    _write_stage_marker("login:submitted_click", page.url)
    print("[LOGIN] Submit principal realizado (Playwright click)")

    validation_result, fatal_error = _wait_login_success_playwright(page, LOGIN_TOTAL_TIMEOUT)
    if validation_result is True:
        print(f"[LOGIN] ✓ Login realizado e validado com sucesso. URL: {page.url}")
        _write_stage_marker("login:completed", page.url)
        return

    if validation_result == "recaptcha_blocked":
        _write_stage_marker("login:recaptcha_blocked", fatal_error or "")
        _save_page_debug_playwright(page, "login_recaptcha_blocked")
        raise Exception(
            "Login bloqueado após submit: widget de captcha visível manteve o formulário travado"
            + (f" ({fatal_error})" if fatal_error else "")
        )

    if validation_result == "form_locked":
        _write_stage_marker("login:form_locked", fatal_error or "")
        _save_page_debug_playwright(page, "login_form_locked")
        raise Exception(
            "Login bloqueado após submit: formulário permaneceu desabilitado por tempo prolongado"
            + (f" ({fatal_error})" if fatal_error else "")
        )

    if validation_result is False:
        _save_page_debug_playwright(page, "login_failed_after_click")
        raise Exception(
            "Login falhou após submit no Playwright: mensagem de erro explícita detectada"
            + (f" ({fatal_error})" if fatal_error else "")
        )

    _save_page_debug_playwright(page, "login_timeout_validation")
    raise TimeoutError("Não foi possível validar login via Playwright dentro do timeout configurado")


def _wait_listing_ready_playwright(page, timeout_seconds=LISTING_READY_TIMEOUT):
    """Confirma que a listagem pós-login carregou no DOM."""
    deadline = time.monotonic() + timeout_seconds
    readiness_selectors = [
        "xpath=//input[contains(@placeholder, 'Pesquisar nome edição') or contains(@placeholder, 'Pesquisar nome edicao')]",
        "xpath=//div[contains(@class,'suita-block-home') or contains(@class,'v-card')]",
        "xpath=//*[contains(@class,'mdi-file-pdf') or contains(@title,'PDF') or contains(@aria-label,'PDF')]",
    ]

    while time.monotonic() < deadline:
        for selector in readiness_selectors:
            try:
                loc = page.locator(selector)
                if loc.count() > 0 and loc.first.is_visible():
                    print(f"[LISTAGEM] Sinal de prontidão detectado: {selector}")
                    _write_stage_marker("listing:ready", selector)
                    return
            except Exception:
                continue
        time.sleep(0.4)

    _save_page_debug_playwright(page, "listagem_not_ready")
    _write_stage_marker("listing:timeout")
    raise TimeoutError("Listagem não ficou pronta após o login (Playwright)")


def set_publication_filter_playwright(page):
    """Configura filtro Public. Legal para Exceto quando habilitado."""
    print("[FILTRO] Configurando filtro 'Public. Legal' como 'Exceto'...")
    try:
        page.screenshot(path="/tmp/filtro_debug.png", full_page=True)
        print("[FILTRO] Screenshot salvo em /tmp/filtro_debug.png")
    except Exception:
        pass

    combo = page.locator(
        "xpath=//div[contains(@class, 'v-select') and .//label[contains(., 'Public. Legal')]]//input[@role='combobox']"
    )
    if combo.count() == 0:
        combo = page.locator("xpath=//input[@role='combobox']")

    if combo.count() == 0:
        print("[FILTRO] AVISO: Dropdown não encontrado, continuando sem filtro")
        return

    control = combo.first
    try:
        current_value = (control.input_value() or "").strip().lower()
    except Exception:
        current_value = ""

    if current_value == "exceto":
        print("[FILTRO] Filtro já está em 'Exceto'")
        return

    control.click()
    page.wait_for_timeout(350)
    option = page.locator("xpath=//*[@role='option' and contains(translate(normalize-space(),'EXCETO','exceto'),'exceto')]")
    if option.count() == 0:
        option = page.locator("xpath=//div[contains(@class,'v-list-item') and contains(translate(normalize-space(),'EXCETO','exceto'),'exceto')]")

    if option.count() == 0:
        print("[FILTRO] AVISO: opção 'Exceto' não encontrada, continuando sem filtro")
        return

    option.first.click()
    page.wait_for_timeout(500)
    print("[FILTRO] Filtro 'Exceto' aplicado")


def _is_handle_visible(handle):
    """Verifica visibilidade do element handle no contexto do navegador."""
    try:
        return bool(
            handle.evaluate(
                """
                (el) => {
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }
                """
            )
        )
    except Exception:
        return False


def _get_jornal_candidates_playwright(page):
    """Coleta candidatos de cards JORNAL e seus gatilhos de PDF na listagem."""
    cards = page.locator("xpath=//div[contains(@class,'suita-block-home') or contains(@class,'v-card')]").element_handles()
    print(f"[PDF] Cards do grid encontrados: {len(cards)}")

    candidates = []
    blocked_terms = ["valvi", "folheto", "classificados", "classificado", "public. legal", "publicacao legal"]
    pdf_selectors = [
        "xpath=.//i[contains(@class,'mdi-file-pdf-box') and contains(@class,'v-icon--clickable')]",
        "xpath=.//i[contains(@class,'mdi-file-pdf') and contains(@class,'v-icon--clickable')]",
        "xpath=.//*[@title='Visualizar PDF' or contains(@title,'PDF') or contains(@aria-label,'PDF')]",
        "xpath=.//*[self::button or self::a or @role='button' or @role='link'][.//i[contains(@class,'mdi-file-pdf')] or contains(@title,'PDF') or contains(@aria-label,'PDF')]",
    ]

    for card in cards:
        try:
            text = (card.inner_text() or "").strip()
        except Exception:
            continue

        card_text_lower = text.lower()
        try:
            has_h5_jornal = bool(
                card.eval_on_selector_all(
                    "xpath=.//div[contains(@class, 'v-card-title')]//h5",
                    "nodes => nodes.some(n => (n.innerText || '').trim().toUpperCase() === 'JORNAL')",
                )
            )
        except Exception:
            has_h5_jornal = False

        if not has_h5_jornal and "jornal" not in card_text_lower:
            continue
        if any(term in card_text_lower for term in blocked_terms) and not has_h5_jornal:
            continue

        pdf_handle = None
        for selector in pdf_selectors:
            try:
                nodes = card.query_selector_all(selector)
            except Exception:
                nodes = []
            for node in nodes:
                if _is_handle_visible(node):
                    pdf_handle = node
                    break
            if pdf_handle:
                break

        if not pdf_handle:
            continue

        candidates.append(
            {
                "card": card,
                "pdf_handle": pdf_handle,
                "edition_number": _parse_card_edition_number(text) or -1,
                "edition_date": _parse_card_date_ddmmyyyy(text),
                "debug": re.sub(r"\s+", " ", text.replace("\n", " | "))[:260],
            }
        )

    candidates.sort(
        key=lambda item: (
            item["edition_date"] if item["edition_date"] is not None else datetime.min,
            item["edition_number"],
        ),
        reverse=True,
    )
    return candidates


def access_and_download_pdf_playwright(page):
    """Acessa listagem e baixa PDF do JORNAL mais recente com Playwright."""
    print(f"[PDF] Navegando para {DIARIO_ACCESS_URL}...")
    _write_stage_marker("listing:open", DIARIO_ACCESS_URL)
    page.goto(DIARIO_ACCESS_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    print("[PDF] Página de acesso carregada")
    _save_page_debug_playwright(page, "listagem_logada")

    _wait_listing_ready_playwright(page)
    if APPLY_PUBLIC_LEGAL_FILTER:
        set_publication_filter_playwright(page)
    else:
        print("[FILTRO] Mantido padrão vazio (APPLY_PUBLIC_LEGAL_FILTER=false)")

    candidates = _get_jornal_candidates_playwright(page)
    if not candidates:
        _save_page_debug_playwright(page, "jornal_not_found")
        raise Exception("Nenhum card de JORNAL válido com ícone PDF foi encontrado (Playwright)")

    selected = candidates[0]
    print(
        "[PDF] Selecionado JORNAL mais recente disponível: "
        f"edição={selected['edition_number']}, "
        f"data={selected['edition_date'].strftime('%d/%m/%Y') if selected['edition_date'] else 'N/A'}"
    )
    print(f"[PDF] Card selecionado (debug): {selected['debug']}")

    os.makedirs(DATA_FOLDER, exist_ok=True)
    target_path = os.path.join(DATA_FOLDER, PDF_FILENAME)

    try:
        with page.expect_download(timeout=DOWNLOAD_TIMEOUT * 1000) as download_info:
            selected["pdf_handle"].scroll_into_view_if_needed()
            selected["pdf_handle"].click(force=True)
        download = download_info.value
        download.save_as(target_path)
        _write_stage_marker("pdf:clicked", selected["debug"])
        _write_stage_marker("download:completed", target_path)
    except PlaywrightTimeoutError as exc:
        _save_page_debug_playwright(page, "download_timeout")
        raise TimeoutError(f"Timeout aguardando download de PDF no Playwright: {exc}")

    if not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
        raise Exception("Download finalizado sem arquivo PDF válido")

    if not validate_downloaded_file(target_path):
        raise Exception("Arquivo baixado não passou na validação")

    print(f"[DOWNLOAD] ✓ Arquivo salvo com sucesso: {target_path}")
    return target_path


def run_scraper_playwright():
    """Executa o fluxo completo de scraping usando Playwright."""
    print("[PLAYWRIGHT] Inicializando navegador Chromium...")
    launch_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
    ]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=launch_args)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
        )
        page = context.new_page()
        page.set_default_timeout(PLAYWRIGHT_DEFAULT_TIMEOUT_MS)
        _write_stage_marker("main:playwright_ready")

        try:
            perform_login_playwright(page)
            pdf_path = access_and_download_pdf_playwright(page)
            return pdf_path
        except PlaywrightTimeoutError as e:
            _write_stage_marker("playwright:error", f"timeout: {e}")
            _save_page_debug_playwright(page, "playwright_timeout")
            raise
        except Exception as e:
            _write_stage_marker("playwright:error", str(e))
            _save_page_debug_playwright(page, "playwright_error")
            raise
        finally:
            context.close()
            browser.close()


# ==================== EXECUÇÃO PRINCIPAL ====================
def main():
    """Função principal do scraper"""
    print("=" * 60)
    print("INICIANDO SCRAPER DE DIÁRIO OFICIAL")
    print("=" * 60)
    print()
    _write_stage_marker("main:start")
    
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
    _write_stage_marker("main:cleanup_done")
    
    try:
        # Etapa 2 em diante: Fluxo completo com Playwright
        final_path = run_scraper_playwright()
        _write_stage_marker("main:success", final_path)
        
        print("=" * 60)
        print(f"✓ SUCESSO! PDF salvo em: {final_path}")
        print("=" * 60)
        
    except Exception as e:
        _write_stage_marker("main:error", str(e))
        print("=" * 60)
        print(f"✗ ERRO DURANTE EXECUÇÃO: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()
