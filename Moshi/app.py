"""
Moshi Full-Duplex Voice AI Server
Based on: "Moshi: a speech-text foundation model for real-time dialogue"
arXiv: 2410.00037 | Kyutai Labs

FastAPI + WebSocket server implementing:
- Full-duplex simultaneous audio streaming
- Inner monologue text token streaming
- Real-time interruption detection
- Simulation mode (CPU-compatible)
"""

import os
import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load environment variables locally (won't affect cloud environments)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from fastapi.responses import FileResponse, JSONResponse
from moshi_engine import DuplexEngine
from menu_data import MENU_ITEMS, MENU_CATEGORIES

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("moshi.server")

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Moshi Full-Duplex Voice AI",
    description="Real-time full-duplex spoken dialogue with inner monologue (arXiv 2410.00037)",
    version="1.0.0"
)

# ── CORS (allow Next.js frontend on port 3000) ───────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Routes ────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok",
        "mode": "simulation",
        "paper": "arXiv:2410.00037",
        "features": ["full-duplex", "inner-monologue", "interruption-detection", "vad"]
    })


@app.get("/api/menu")
async def get_menu():
    return JSONResponse({
        "categories": MENU_CATEGORIES,
        "items": MENU_ITEMS
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = websocket.client.host if websocket.client else "unknown"
    logger.info(f"🔌 Client connected: {client}")

    engine = DuplexEngine(websocket)
    try:
        await engine.run()
    except WebSocketDisconnect:
        logger.info(f"✅ Client disconnected normally: {client}")
    except Exception as e:
        logger.error(f"❌ WebSocket error [{client}]: {e}", exc_info=True)
    finally:
        engine.stop()
        logger.info(f"🔒 Session ended: {client}")


# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    banner = (
        "\n"
        "  +===================================================+\n"
        "  |   MOSHI -- Full-Duplex Voice AI                   |\n"
        "  |   arXiv: 2410.00037 | Kyutai Labs                 |\n"
        "  |   Mode: Simulation (CPU-compatible)               |\n"
        "  +===================================================+\n"
        "  |   Features:                                       |\n"
        "  |   * Full-Duplex (listen + speak simultaneously)   |\n"
        "  |   * Inner Monologue (text tokens before audio)    |\n"
        "  |   * Interruption Detection (VAD-based)            |\n"
        "  |   * Real-time waveform visualization              |\n"
        "  +===================================================+\n"
        "  |   Open: http://localhost:8998                     |\n"
        "  +===================================================+\n"
    )
    print(banner)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8998)),
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )
