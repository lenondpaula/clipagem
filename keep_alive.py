"""Keep Streamlit app alive with headless Selenium."""

from __future__ import annotations

import os
import stat
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


TARGET_URL = os.getenv("KEEP_ALIVE_URL", "https://clipagem-secom.streamlit.app/")
WAIT_SECONDS = int(os.getenv("KEEP_ALIVE_WAIT_SECONDS", "10"))
SCREENSHOT_PATH = os.getenv("KEEP_ALIVE_SCREENSHOT", "keep_alive_screenshot.png")


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    # Adicionar user-agent para simular navegador real
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # Desabilitar notificações e popups
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    
    # Corrigir bug do webdriver-manager (THIRD_PARTY_NOTICES)
    driver_path = Path(ChromeDriverManager().install())
    if driver_path.name.startswith("THIRD_PARTY_NOTICES"):
        candidate = driver_path.with_name("chromedriver")
        if candidate.exists():
            driver_path = candidate
    
    # Garantir permissões de execução (fix para GitHub Actions)
    os.chmod(driver_path, os.stat(driver_path).st_mode | stat.S_IEXEC)
    
    service = Service(str(driver_path))
    return webdriver.Chrome(service=service, options=options)


def run() -> None:
    """Mantém a app Streamlit ativa via Selenium Chrome headless."""
    driver: webdriver.Chrome | None = None
    try:
        print(f"[KEEP_ALIVE] Iniciando acesso a {TARGET_URL}...")
        driver = build_driver()
        driver.set_page_load_timeout(60)
        
        # Tentar carregar a página
        driver.get(TARGET_URL)
        
        # Aguardar um pouco para a página carregar completamente
        time.sleep(5)
        
        # Verificar se a página carregou (procurar por elementos Streamlit)
        try:
            # Tentar encontrar elementos típicos do Streamlit
            streamlit_elements = driver.find_elements_by_css_selector("[data-testid], .stApp, .main")
            if streamlit_elements:
                print("[KEEP_ALIVE] ✓ Página Streamlit detectada com sucesso")
            else:
                print("[KEEP_ALIVE] ⚠️ Página carregada, mas elementos Streamlit não detectados")
        except:
            print("[KEEP_ALIVE] Página carregada (verificação de elementos falhou)")
        
        # Aguardar o tempo configurado
        print(f"[KEEP_ALIVE] Aguardando {WAIT_SECONDS} segundos...")
        time.sleep(WAIT_SECONDS)
        
        # Fazer screenshot com timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        screenshot_file = SCREENSHOT_PATH.replace(".png", f"-{timestamp}.png")
        driver.save_screenshot(screenshot_file)
        print(f"[KEEP_ALIVE] Screenshot salvo: {screenshot_file}")
        
        print(f"[KEEP_ALIVE] Keep-alive completado com sucesso")
        
    except Exception as exc:
        print(f"[KEEP_ALIVE] ✗ Erro ao manter app ativa: {exc}")
        raise
    finally:
        if driver is not None:
            try:
                driver.quit()
                print(f"[KEEP_ALIVE] Driver finalizado")
            except Exception:
                pass


if __name__ == "__main__":
    run()
