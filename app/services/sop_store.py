"""
Persist SOP records as JSON index + markdown files on disk.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SOP_DIR = Path(__file__).parent.parent / "sops"
INDEX_FILE = SOP_DIR / "index.json"


def _slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80]


def _load_index() -> List[Dict]:
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            return json.load(f)
    return []


def _save_index(records: List[Dict]) -> None:
    SOP_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(records, f, indent=2)


def save_sop(
    title: str,
    markdown: str,
    source_filename: str,
    source_type: str,
    tags: Optional[List[str]] = None,
) -> Dict:
    records = _load_index()
    slug = _slug(title)
    # Avoid collisions
    existing_slugs = {r["slug"] for r in records}
    base_slug = slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    now = datetime.utcnow().isoformat() + "Z"
    record = {
        "id": slug,
        "slug": slug,
        "title": title,
        "source_filename": source_filename,
        "source_type": source_type,
        "tags": tags or [],
        "created_at": now,
        "updated_at": now,
        "markdown_file": f"{slug}.md",
    }

    md_path = SOP_DIR / f"{slug}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    records.append(record)
    _save_index(records)
    return record


def update_sop(slug: str, title: str, markdown: str, tags: Optional[List[str]] = None) -> Optional[Dict]:
    records = _load_index()
    for r in records:
        if r["slug"] == slug:
            r["title"] = title
            r["updated_at"] = datetime.utcnow().isoformat() + "Z"
            if tags is not None:
                r["tags"] = tags
            md_path = SOP_DIR / r["markdown_file"]
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            _save_index(records)
            return r
    return None


def delete_sop(slug: str) -> bool:
    records = _load_index()
    new_records = [r for r in records if r["slug"] != slug]
    if len(new_records) == len(records):
        return False
    removed = next(r for r in records if r["slug"] == slug)
    md_path = SOP_DIR / removed["markdown_file"]
    if md_path.exists():
        md_path.unlink()
    _save_index(new_records)
    return True


def get_sop(slug: str) -> Optional[Dict]:
    records = _load_index()
    for r in records:
        if r["slug"] == slug:
            md_path = SOP_DIR / r["markdown_file"]
            content = ""
            if md_path.exists():
                with open(md_path, encoding="utf-8") as f:
                    content = f.read()
            return {**r, "markdown": content}
    return None


def list_sops(search: str = "", tag: str = "") -> List[Dict]:
    records = _load_index()
    result = records
    if search:
        q = search.lower()
        result = [r for r in result if q in r["title"].lower() or q in r["source_filename"].lower()]
    if tag:
        result = [r for r in result if tag in r.get("tags", [])]
    return sorted(result, key=lambda r: r["updated_at"], reverse=True)


def all_tags() -> List[str]:
    records = _load_index()
    tags = set()
    for r in records:
        tags.update(r.get("tags", []))
    return sorted(tags)
