"""
SOP Manager MCP Server
======================
Exposes SOP Manager capabilities as MCP tools so any agent (Claude Code,
other AI agents, etc.) can discover and interact with your SOP library.

Runs on Python 3.13 (requires mcp>=1.0).
Transport: SSE on http://localhost:8005/sse

Start:
  python3.13 mcp_server.py

Register in Claude Code ~/.claude/claude.json mcpServers:
  "sop-manager": { "type": "sse", "url": "http://localhost:8005/sse" }

Tools exposed:
  list_sops          — search/filter the SOP library
  get_sop            — fetch full SOP content by slug
  get_sop_version    — fetch a specific historical version
  create_sop         — create a new SOP from raw markdown
  update_sop         — update SOP content (saves new version)
  delete_sop         — delete an SOP
  ask_sop            — ask a question about an SOP via Claude
  search_sops        — full-text search across all SOP content
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE = os.getenv("SOP_MANAGER_URL", "http://localhost:8004")
MCP_PORT  = int(os.getenv("MCP_PORT", "8005"))

mcp = FastMCP("SOP Manager", port=MCP_PORT)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _api(method: str, path: str, **kwargs):
    """Synchronous HTTP call to the SOP Manager REST API."""
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=120) as client:
        resp = getattr(client, method)(url, **kwargs)
        resp.raise_for_status()
        return resp.json()


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_sops(search: str = "", tag: str = "") -> str:
    """
    List all SOPs in the library. Optionally filter by keyword search or tag.

    Args:
        search: Keyword to search in SOP titles and source filenames.
        tag:    Filter by a specific tag (e.g. 'shipping', 'onboarding').

    Returns:
        JSON array of SOP records (id, title, tags, source_type, updated_at, current_version).
    """
    params = {}
    if search: params["search"] = search
    if tag:    params["tag"]    = tag
    sops = _api("get", "/api/sops", params=params)
    # Return compact summary
    summary = [
        {
            "slug":            s["slug"],
            "title":           s["title"],
            "tags":            s.get("tags", []),
            "source_type":     s.get("source_type", ""),
            "source_filename": s.get("source_filename", ""),
            "current_version": s.get("current_version", 1),
            "updated_at":      s.get("updated_at", ""),
        }
        for s in sops
    ]
    return json.dumps(summary, indent=2)


@mcp.tool()
def get_sop(slug: str) -> str:
    """
    Retrieve the full content of an SOP including its markdown.

    Args:
        slug: The SOP slug identifier (e.g. 'freight-invoice-processing').

    Returns:
        Full SOP record including title, tags, version history, and markdown content.
    """
    sop = _api("get", f"/api/sops/{slug}")
    return json.dumps(sop, indent=2)


@mcp.tool()
def get_sop_version(slug: str, version: int) -> str:
    """
    Retrieve a specific historical version of an SOP.

    Args:
        slug:    The SOP slug identifier.
        version: Version number (e.g. 1, 2, 3).

    Returns:
        SOP record at that version including the markdown content.
    """
    sop = _api("get", f"/api/sops/{slug}/versions/{version}")
    return json.dumps(sop, indent=2)


@mcp.tool()
def create_sop(
    title: str,
    markdown: str,
    tags: str = "",
    source_filename: str = "agent-created",
    source_type: str = "Agent",
) -> str:
    """
    Create a new SOP directly from markdown content (no file upload needed).

    Args:
        title:           Title of the SOP.
        markdown:        Full SOP content in Markdown format.
        tags:            Comma-separated tags (e.g. 'shipping,onboarding').
        source_filename: Optional label for the source (defaults to 'agent-created').
        source_type:     Optional source type label (defaults to 'Agent').

    Returns:
        The created SOP record with its slug and version info.
    """
    # Use the internal store directly — import works since we share the same repo
    sys.path.insert(0, str(Path(__file__).parent))
    from app.services.sop_store import save_sop
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    record = save_sop(title, markdown, source_filename, source_type, tag_list, author="agent")
    return json.dumps(record, indent=2)


@mcp.tool()
def update_sop(
    slug: str,
    markdown: str,
    title: str = "",
    tags: str = "",
    note: str = "",
) -> str:
    """
    Update an existing SOP with new markdown content. Saves as a new version.

    Args:
        slug:     The SOP slug to update.
        markdown: New full markdown content.
        title:    New title (leave blank to keep existing).
        tags:     New comma-separated tags (leave blank to keep existing).
        note:     Change note describing what was updated.

    Returns:
        Updated SOP record with new version number.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from app.services.sop_store import get_sop as _get, update_sop as _update

    current = _get(slug)
    if not current:
        return json.dumps({"error": f"SOP '{slug}' not found."})

    final_title = title.strip() or current["title"]
    final_tags  = [t.strip() for t in tags.split(",") if t.strip()] if tags.strip() else current.get("tags", [])
    final_note  = note or "Updated by agent"

    record = _update(slug, final_title, markdown, final_tags, author="agent", note=final_note)
    return json.dumps(record, indent=2)


@mcp.tool()
def delete_sop(slug: str) -> str:
    """
    Delete an SOP and all its versions permanently.

    Args:
        slug: The SOP slug to delete.

    Returns:
        Confirmation message.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from app.services.sop_store import delete_sop as _delete
    ok = _delete(slug)
    if ok:
        return json.dumps({"success": True, "message": f"SOP '{slug}' deleted."})
    return json.dumps({"success": False, "message": f"SOP '{slug}' not found."})


@mcp.tool()
def ask_sop(slug: str, question: str) -> str:
    """
    Ask a question about a specific SOP. Claude will answer using the SOP content.
    Use this to extract information, clarify steps, or understand any part of an SOP.

    Args:
        slug:     The SOP slug to ask about.
        question: Your question about the SOP.

    Returns:
        Claude's answer based on the SOP content.
    """
    import boto3
    from botocore.config import Config

    sys.path.insert(0, str(Path(__file__).parent))
    from app.services.sop_store import get_sop as _get

    sop = _get(slug)
    if not sop:
        return json.dumps({"error": f"SOP '{slug}' not found."})

    model = (
        os.getenv("ANTHROPIC_DEFAULT_OPUS_MODEL")
        or os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL")
        or "anthropic.claude-opus-4-6"
    )
    region = os.getenv("AWS_REGION", "us-east-1")
    client = boto3.client("bedrock-runtime", region_name=region,
                          config=Config(read_timeout=60, connect_timeout=10))

    prompt = f"""You are an SOP assistant. Answer the following question based strictly on the SOP content provided.

SOP Title: {sop['title']}

SOP Content:
{sop['markdown'][:20000]}

Question: {question}

Answer concisely and accurately."""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    })
    resp = client.invoke_model(modelId=model, body=body,
                               contentType="application/json", accept="application/json")
    result = json.loads(resp["body"].read())
    answer = result["content"][0]["text"]
    return json.dumps({"slug": slug, "title": sop["title"], "question": question, "answer": answer})


@mcp.tool()
def search_sops(query: str) -> str:
    """
    Full-text search across all SOP content (not just titles).
    Returns SOPs that contain the query string in their markdown.

    Args:
        query: Text to search for within SOP content.

    Returns:
        List of matching SOPs with the matching excerpt.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from app.services.sop_store import list_sops as _list, get_sop as _get

    all_sops = _list()
    q = query.lower()
    results = []
    for s in all_sops:
        sop = _get(s["slug"])
        if not sop:
            continue
        md = sop.get("markdown", "")
        if q in md.lower():
            # Find excerpt around the match
            idx = md.lower().find(q)
            start = max(0, idx - 100)
            end   = min(len(md), idx + 200)
            excerpt = "…" + md[start:end].strip() + "…"
            results.append({
                "slug":    s["slug"],
                "title":   s["title"],
                "tags":    s.get("tags", []),
                "excerpt": excerpt,
            })
    return json.dumps(results, indent=2)


# ── Resources ─────────────────────────────────────────────────────────────────

@mcp.resource("sop://library")
def sop_library() -> str:
    """The full SOP library index — all SOPs with metadata (no content)."""
    sys.path.insert(0, str(Path(__file__).parent))
    from app.services.sop_store import list_sops as _list
    return json.dumps(_list(), indent=2)


@mcp.resource("sop://{slug}")
def sop_content(slug: str) -> str:
    """Full content of a specific SOP by slug."""
    sys.path.insert(0, str(Path(__file__).parent))
    from app.services.sop_store import get_sop as _get
    sop = _get(slug)
    if not sop:
        return json.dumps({"error": "SOP not found"})
    return sop.get("markdown", "")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Starting SOP Manager MCP Server on port {MCP_PORT}...")
    print(f"SSE endpoint: http://localhost:{MCP_PORT}/sse")
    print(f"Connecting to SOP Manager API at: {API_BASE}")
    print()
    print("Tools available:")
    print("  list_sops, get_sop, get_sop_version, create_sop,")
    print("  update_sop, delete_sop, ask_sop, search_sops")
    print()
    mcp.run(transport="sse")
