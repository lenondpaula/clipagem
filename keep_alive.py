"""Keep Streamlit app alive with headless Playwright."""

from __future__ import annotations

import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright


TARGET_URL = os.getenv("KEEP_ALIVE_URL", "https://clipagem-secom.streamlit.app/")
WAIT_SECONDS = int(os.getenv("KEEP_ALIVE_WAIT_SECONDS", "10"))
SCREENSHOT_PATH = os.getenv("KEEP_ALIVE_SCREENSHOT", "keep_alive_screenshot.png")


def run() -> None:
    """Mantém a app Streamlit ativa via Playwright Chromium headless."""
    try:
        print(f"[KEEP_ALIVE] Iniciando acesso a {TARGET_URL}...")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/146.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            streamlit_nodes = page.locator("[data-testid], .stApp, .main")
            if streamlit_nodes.count() > 0:
                print("[KEEP_ALIVE] ✓ Página Streamlit detectada com sucesso")
            else:
                print("[KEEP_ALIVE] ⚠ Página carregada, mas elementos Streamlit não detectados")

            print(f"[KEEP_ALIVE] Aguardando {WAIT_SECONDS} segundos...")
            time.sleep(WAIT_SECONDS)

            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            screenshot_file = SCREENSHOT_PATH.replace(".png", f"-{timestamp}.png")
            page.screenshot(path=screenshot_file, full_page=True)
            print(f"[KEEP_ALIVE] Screenshot salvo: {screenshot_file}")

            context.close()
            browser.close()

        print("[KEEP_ALIVE] Keep-alive completado com sucesso")
    except Exception as exc:
        print(f"[KEEP_ALIVE] ✗ Erro ao manter app ativa: {exc}")
        raise


if __name__ == "__main__":
    run()
