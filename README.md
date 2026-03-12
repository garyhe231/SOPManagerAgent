# SOP Manager Agent

Convert operational documents (PDFs, Word docs, Excel sheets, video recordings) into structured, searchable SOPs using Claude AI. Includes version control, an AI chatbot, and an MCP server so other agents can interact with your SOP library.

## Features
- Upload PDF, DOCX, XLSX, MP4/MOV/audio files
- AI-powered translation to structured Markdown SOPs via Claude Opus 4.6
- Central SOP library with search and tag filtering
- Layered 3-column viewer: TOC rail, collapsible sections, AI chat panel
- Version control — every save creates an immutable snapshot
- AI chatbot — ask questions or request edits, applied as new versions
- **MCP server** — expose all SOP operations to any MCP-compatible agent

## Setup

```bash
pip3 install -r requirements.txt

# MCP server also needs mcp on Python 3.13
/opt/homebrew/bin/python3.13 -m pip install mcp httpx --break-system-packages
```

## Run

```bash
# Main web app (port 8004)
python3 run.py

# MCP server (port 8005) — for agent integrations
/opt/homebrew/bin/python3.13 mcp_server.py
```

Open [http://localhost:8004](http://localhost:8004)

## MCP Integration

The MCP server runs on `http://localhost:8005/sse` and exposes these tools:

| Tool | Description |
|------|-------------|
| `list_sops` | List/search the SOP library |
| `get_sop` | Fetch full SOP content by slug |
| `get_sop_version` | Fetch a specific historical version |
| `create_sop` | Create a new SOP from markdown |
| `update_sop` | Update SOP content (saves new version) |
| `delete_sop` | Delete an SOP permanently |
| `ask_sop` | Ask Claude a question about an SOP |
| `search_sops` | Full-text search across all SOP content |

### Register in Claude Code

Add to `~/.claude/claude.json` under `mcpServers`:

```json
"sop-manager": {
  "type": "sse",
  "url": "http://localhost:8005/sse"
}
```

### Use from another agent

```python
# Any agent can call the REST API directly too
import httpx
sops = httpx.get("http://localhost:8004/api/sops").json()
sop  = httpx.get("http://localhost:8004/api/sops/freight-invoice-processing").json()
```

## Stack
- FastAPI + Jinja2 + Vanilla JS (Python 3.9)
- Claude Opus 4.6 via AWS Bedrock (boto3)
- pdfplumber, python-docx, openpyxl, openai-whisper
- MCP server via `mcp` + `fastmcp` (Python 3.13)
- SOPs stored as versioned Markdown files in `app/sops/`
