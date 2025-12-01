from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse

app = FastAPI()

CURRENT_DIR = Path(__file__).resolve().parent
WEBUI_DIR = CURRENT_DIR.parent


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve index.html op /"""
    return FileResponse(WEBUI_DIR / "index.html")


@app.get("/results.html", include_in_schema=False)
async def serve_result():
    """Serve result.html op /result.html"""
    return FileResponse(WEBUI_DIR / "result.html")


@app.post("/start-scan")
async def start_scan():
    """
    Hier later OpenVAS aanroepen.
    Voor nu: alleen 'scan gestart' teruggeven zodat de frontend kan redirecten.
    """
    return {"status": "scan started"}


@app.get("/summary", response_class=PlainTextResponse)
async def get_summary():
    """
    Dummy samenvatting; later vervang je dit door echte OpenVAS resultaten + AI-samenvatting.
    """
    dummy_summary = (
        "Scan complete.\n\n"
        "- 3 medium vulnerabilities gevonden (bijv. verouderde SSH server).\n"
        "- 1 low severity issue (HTTP header misconfig).\n\n"
        "Aanbevolen stappen:\n"
        "1. Update OpenSSH naar een recente versie.\n"
        "2. Schakel zwakke ciphers/protocollen uit.\n"
        "3. Voeg strikte security headers toe (HSTS, X-Frame-Options, CSP).\n"
    )
    return dummy_summary
