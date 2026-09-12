"""Guarda el storage_state (cookies + localStorage) de una sesión de login manual,
para reusarla luego sin volver a pedir credenciales. El usuario hace login dentro
de una ventana de Chromium real y visible (headed) en su propio escritorio/VNC;
este script nunca lee cookies individuales, sólo le pide a Playwright que
serialice el estado completo a un archivo una vez el usuario confirma que ya
inició sesión.

Uso:
    /lsiopy/bin/python3 save_session.py tiktok
    /lsiopy/bin/python3 save_session.py twitter

El archivo resultante (p.ej. .sessions/tiktok_state.json) NO debe subirse a git
(ver .gitignore) — contiene cookies de sesión reales.
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SITES = {
    "tiktok": {
        "login_url": "https://www.tiktok.com/login",
        # con sesión iniciada, TikTok redirige lejos de /login hacia el feed
        "logged_in_check": lambda url: "/login" not in url and "tiktok.com" in url,
    },
    "twitter": {
        "login_url": "https://x.com/login",
        "logged_in_check": lambda url: "/login" not in url and ("x.com/home" in url or url.rstrip("/") == "https://x.com"),
    },
}

SESSIONS_DIR = Path(__file__).resolve().parent.parent / ".sessions"


def save_session(site: str, timeout_seconds: int = 300, poll_seconds: int = 3):
    if site not in SITES:
        print(f"Sitio no soportado: {site}. Opciones: {list(SITES)}")
        sys.exit(1)

    cfg = SITES[site]
    SESSIONS_DIR.mkdir(exist_ok=True)
    out_path = SESSIONS_DIR / f"{site}_state.json"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(cfg["login_url"])

        print(f"\nSe abrió una ventana de Chromium en tu escritorio (conéctate por VNC si aún no lo estás).")
        print(f"Inicia sesión normalmente en {site} dentro de esa ventana.")
        print(f"Esperando hasta {timeout_seconds}s a que el login se complete...")

        elapsed = 0
        logged_in = False
        while elapsed < timeout_seconds:
            page.wait_for_timeout(poll_seconds * 1000)
            elapsed += poll_seconds
            if cfg["logged_in_check"](page.url):
                logged_in = True
                break

        if not logged_in:
            print("Tiempo de espera agotado sin detectar login. No se guardó ninguna sesión.")
            browser.close()
            sys.exit(1)

        # margen para que terminen de asentarse las cookies post-redirect
        page.wait_for_timeout(2000)
        ctx.storage_state(path=str(out_path))
        browser.close()

    print(f"\nSesión guardada en: {out_path}")
    print("Este archivo contiene cookies reales — no se sube a git (ver .gitignore).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("site", choices=list(SITES))
    parser.add_argument("--timeout", type=int, default=300, help="segundos a esperar el login")
    args = parser.parse_args()
    save_session(args.site, timeout_seconds=args.timeout)


if __name__ == "__main__":
    main()
