"""Keep Streamlit app alive with headless Selenium."""

from __future__ import annotations

import os
import time
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


TARGET_URL = os.getenv("KEEP_ALIVE_URL", "https://clipagem-secom.streamlit.app/")
WAIT_SECONDS = int(os.getenv("KEEP_ALIVE_WAIT_SECONDS", "10"))
SCREENSHOT_PATH = os.getenv("KEEP_ALIVE_SCREENSHOT", "keep_alive_screenshot.png")
REQUEST_TIMEOUT = int(os.getenv("KEEP_ALIVE_HTTP_TIMEOUT", "20"))
USE_SELENIUM_FALLBACK = os.getenv("KEEP_ALIVE_USE_SELENIUM", "true").lower() == "true"


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def ping_http() -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    }
    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        print(f"HTTP keep-alive failed: {exc}")
        return False

    ok = 200 <= response.status_code < 400
    print(f"HTTP keep-alive status: {response.status_code}")
    return ok


def run() -> None:
    if ping_http():
        return

    if not USE_SELENIUM_FALLBACK:
        print("Selenium fallback disabled. Exiting.")
        return

    driver: webdriver.Chrome | None = None
    try:
        driver = build_driver()
        driver.set_page_load_timeout(60)
        driver.get(TARGET_URL)
        time.sleep(WAIT_SECONDS)

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        screenshot_file = SCREENSHOT_PATH.replace(".png", f"-{timestamp}.png")
        driver.save_screenshot(screenshot_file)
        print(f"Screenshot saved: {screenshot_file}")
    except Exception as exc:
        print(f"Keep-alive failed: {exc}")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    run()
