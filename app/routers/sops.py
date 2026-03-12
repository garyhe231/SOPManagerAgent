"""
FastAPI routes for SOP CRUD, file upload/processing, and version history.
"""
import os
import tempfile
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.services.extractor import extract_text
from app.services.ai_translator import translate_to_sop
from app.services.sop_store import (
    save_sop, update_sop, delete_sop, get_sop,
    get_version_markdown, list_sops, all_tags
)

router = APIRouter(prefix="/api/sops", tags=["sops"])

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v",
    ".mp3", ".wav", ".m4a", ".txt"
}


@router.post("/upload")
async def upload_and_process(
    file: UploadFile = File(...),
    title: str = Form(""),
    tags: str = Form(""),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not supported.")

    if ext == ".pdf":
        source_type = "PDF"
    elif ext in (".docx", ".doc"):
        source_type = "Word Document"
    elif ext in (".xlsx", ".xls"):
        source_type = "Excel Spreadsheet"
    elif ext in (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mp3", ".wav", ".m4a"):
        source_type = "Video/Audio Recording"
    else:
        source_type = "Text File"

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        raw_text = extract_text(tmp_path, file.filename)
        if not raw_text.strip():
            raise HTTPException(422, "Could not extract any text from the file.")

        sop_title = title.strip() or os.path.splitext(file.filename)[0].replace("_", " ").replace("-", " ").title()
        markdown = translate_to_sop(raw_text, file.filename, title_hint=sop_title)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        record = save_sop(sop_title, markdown, file.filename, source_type, tag_list)
        return {"success": True, "sop": record}
    finally:
        os.unlink(tmp_path)


@router.get("")
async def list_all(search: str = "", tag: str = ""):
    return list_sops(search=search, tag=tag)


@router.get("/tags")
async def get_tags():
    return all_tags()


@router.get("/{slug}/versions/{version}/download")
async def download_version(slug: str, version: int):
    md = get_version_markdown(slug, version)
    if md is None:
        raise HTTPException(404, "Version not found.")
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{slug}-v{version}.md"'},
    )


@router.get("/{slug}/versions/{version}")
async def get_version(slug: str, version: int):
    sop = get_sop(slug, version=version)
    if not sop:
        raise HTTPException(404, "SOP not found.")
    return sop


@router.get("/{slug}")
async def get_one(slug: str):
    sop = get_sop(slug)
    if not sop:
        raise HTTPException(404, "SOP not found.")
    return sop


@router.get("/{slug}/download")
async def download_markdown(slug: str):
    sop = get_sop(slug)
    if not sop:
        raise HTTPException(404, "SOP not found.")
    return PlainTextResponse(
        content=sop["markdown"],
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{sop["slug"]}-v{sop.get("current_version",1)}.md"'},
    )


@router.put("/{slug}")
async def update_one(
    slug: str,
    title: str = Form(""),
    markdown: str = Form(""),
    tags: str = Form(""),
    author: str = Form("user"),
    note: str = Form(""),
):
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    record = update_sop(slug, title, markdown, tag_list, author=author, note=note)
    if not record:
        raise HTTPException(404, "SOP not found.")
    return {"success": True, "sop": record}


@router.delete("/{slug}")
async def delete_one(slug: str):
    if not delete_sop(slug):
        raise HTTPException(404, "SOP not found.")
    return {"success": True}
