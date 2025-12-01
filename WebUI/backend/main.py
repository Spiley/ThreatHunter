from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse

# BASE_DIR = .../WebUI
BASE_DIR = Path(__file__).resolve().parent.parent
WEBUI_DIR = BASE_DIR  # index.html and result.html are in the WebUI folder

app = FastAPI()


# Serve index.html at "/"
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(WEBUI_DIR / "index.html")


# Serve result.html at "/result.html"
@app.get("/result.html", include_in_schema=False)
async def serve_result():
    return FileResponse(WEBUI_DIR / "result.html")


# Endpoint called by your "Start Scan" button
@app.post("/start-scan")
async def start_scan():
    """
    TODO: Trigger OpenVAS scan here.
    For now we just pretend and immediately redirect to result page.
    """
    # you might later:
    # - read target from body
    # - call OpenVAS / gvmd / openvasd API
    # - store a task ID
    return {"status": "scan started"}


# Endpoint used by result.html to get the summary text
@app.get("/summary", response_class=PlainTextResponse)
async def get_summary():
    """
    TODO: Fetch OpenVAS scan results and summarize.
    Right now we just return a dummy summary string.
    """
    dummy_summary = (
        "Scan complete.\n\n"
        "- 3 medium vulnerabilities found (e.g. outdated SSH server).\n"
        "- 1 low severity issue (HTTP header misconfiguration).\n\n"
        "Recommended next steps:\n"
        "1. Update OpenSSH to the latest stable version.\n"
        "2. Disable weak ciphers and protocols.\n"
        "3. Add strict security headers (HSTS, X-Frame-Options, CSP).\n"
    )
    return dummy_summary
