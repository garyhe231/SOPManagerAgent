"""
SOP Manager Agent — main FastAPI application.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers.sops import router as sops_router
from app.routers.chat import router as chat_router

app = FastAPI(title="SOP Manager Agent", version="2.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(sops_router)
app.include_router(chat_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/sop/{slug}", response_class=HTMLResponse)
async def sop_detail(request: Request, slug: str):
    return templates.TemplateResponse("detail.html", {"request": request, "slug": slug})


@app.get("/health")
async def health():
    return {"status": "ok"}
