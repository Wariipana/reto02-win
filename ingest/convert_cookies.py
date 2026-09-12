"""Convierte un export de cookies estilo Cookie-Editor/EditThisCookie (lista de
objetos {domain, name, value, expirationDate, ...}) al formato storage_state
que espera Playwright ({cookies: [...], origins: [...]}).

Uso:
    python3 convert_cookies.py <archivo_export.json> <sitio>

<sitio> es "tiktok" o "twitter" — determina el nombre del archivo de salida en
.sessions/. El archivo de entrada NO se toca ni se commitea; el de salida
tampoco (ambos deben quedar fuera de git, ver .gitignore).
"""
import json
import sys
from pathlib import Path

SESSIONS_DIR = Path(__file__).resolve().parent.parent / ".sessions"


def _same_site_playwright(value):
    """Cookie-Editor usa null/'no_restriction'/'lax'/'strict'; Playwright espera
    'Strict' | 'Lax' | 'None'."""
    mapping = {
        None: "None",
        "no_restriction": "None",
        "lax": "Lax",
        "strict": "Strict",
        "unspecified": "None",
    }
    return mapping.get(value, "None")


def convert(export_path: str, sitio: str):
    data = json.loads(Path(export_path).read_text())

    cookies = []
    for c in data:
        cookie = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
            "sameSite": _same_site_playwright(c.get("sameSite")),
        }
        if not c.get("session", False) and c.get("expirationDate"):
            cookie["expires"] = c["expirationDate"]
        else:
            cookie["expires"] = -1
        cookies.append(cookie)

    storage_state = {"cookies": cookies, "origins": []}

    SESSIONS_DIR.mkdir(exist_ok=True, mode=0o700)
    out_path = SESSIONS_DIR / f"{sitio}_state.json"
    out_path.write_text(json.dumps(storage_state, indent=2))
    out_path.chmod(0o600)

    print(f"Convertidas {len(cookies)} cookies -> {out_path}")
    print("Recuerda borrar el archivo de export original si ya no lo necesitas.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python3 convert_cookies.py <archivo_export.json> <tiktok|twitter>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
