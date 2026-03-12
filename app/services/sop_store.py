"""
Persist SOP records as JSON index + versioned markdown files on disk.

Layout:
  app/sops/
    index.json                  — list of all SOP records
    <slug>/
      current.md                — latest version
      v1.md, v2.md, …           — version history snapshots
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


def _sop_dir(slug: str) -> Path:
    d = SOP_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_version(slug: str, markdown: str, version: int) -> None:
    d = _sop_dir(slug)
    with open(d / f"v{version}.md", "w", encoding="utf-8") as f:
        f.write(markdown)
    with open(d / "current.md", "w", encoding="utf-8") as f:
        f.write(markdown)


def save_sop(
    title: str,
    markdown: str,
    source_filename: str,
    source_type: str,
    tags: Optional[List[str]] = None,
    author: str = "system",
) -> Dict:
    records = _load_index()
    slug = _slug(title)
    existing_slugs = {r["slug"] for r in records}
    base_slug = slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    now = datetime.utcnow().isoformat() + "Z"
    version_entry = {"version": 1, "created_at": now, "author": author, "note": "Initial version"}
    record = {
        "id": slug,
        "slug": slug,
        "title": title,
        "source_filename": source_filename,
        "source_type": source_type,
        "tags": tags or [],
        "created_at": now,
        "updated_at": now,
        "current_version": 1,
        "versions": [version_entry],
    }

    _write_version(slug, markdown, 1)
    records.append(record)
    _save_index(records)
    return record


def update_sop(
    slug: str,
    title: str,
    markdown: str,
    tags: Optional[List[str]] = None,
    author: str = "user",
    note: str = "",
) -> Optional[Dict]:
    records = _load_index()
    for r in records:
        if r["slug"] == slug:
            r["title"] = title
            r["updated_at"] = datetime.utcnow().isoformat() + "Z"
            if tags is not None:
                r["tags"] = tags
            new_version = r.get("current_version", 1) + 1
            r["current_version"] = new_version
            version_entry = {
                "version": new_version,
                "created_at": r["updated_at"],
                "author": author,
                "note": note or f"Updated to v{new_version}",
            }
            r.setdefault("versions", []).append(version_entry)
            _write_version(slug, markdown, new_version)
            _save_index(records)
            return r
    return None


def delete_sop(slug: str) -> bool:
    records = _load_index()
    new_records = [r for r in records if r["slug"] != slug]
    if len(new_records) == len(records):
        return False
    import shutil
    sop_path = SOP_DIR / slug
    if sop_path.exists():
        shutil.rmtree(sop_path)
    _save_index(new_records)
    return True


def get_sop(slug: str, version: Optional[int] = None) -> Optional[Dict]:
    records = _load_index()
    for r in records:
        if r["slug"] == slug:
            d = _sop_dir(slug)
            if version:
                md_path = d / f"v{version}.md"
            else:
                md_path = d / "current.md"
                # Backward compat: old flat file layout
                if not md_path.exists():
                    old = SOP_DIR / r.get("markdown_file", f"{slug}.md")
                    if old.exists():
                        md_path = old
            content = ""
            if md_path.exists():
                with open(md_path, encoding="utf-8") as f:
                    content = f.read()
            return {**r, "markdown": content, "viewed_version": version or r.get("current_version", 1)}
    return None


def get_version_markdown(slug: str, version: int) -> Optional[str]:
    d = SOP_DIR / slug
    md_path = d / f"v{version}.md"
    if md_path.exists():
        with open(md_path, encoding="utf-8") as f:
            return f.read()
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
