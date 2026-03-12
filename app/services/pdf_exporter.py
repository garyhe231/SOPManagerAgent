"""
Export an SOP to a styled PDF using Playwright (Chromium headless).
Converts markdown → styled HTML → PDF bytes.
"""
import re


def _md_to_html(md: str) -> str:
    """Markdown → HTML for PDF rendering."""
    lines = md.split("\n")
    html_parts = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(_esc(lines[i]))
                i += 1
            html_parts.append('<pre><code>' + "<br>".join(code_lines) + '</code></pre>')
            i += 1
            continue

        # Table
        if "|" in line and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|", lines[i + 1]):
            headers = [c.strip() for c in line.split("|")[1:-1]]
            th = "".join("<th>" + _inline(_esc(h)) + "</th>" for h in headers)
            table_rows = ["<thead><tr>" + th + "</tr></thead><tbody>"]
            i += 2
            while i < len(lines) and "|" in lines[i]:
                cells = [c.strip() for c in lines[i].split("|")[1:-1]]
                td = "".join("<td>" + _inline(_esc(c)) + "</td>" for c in cells)
                table_rows.append("<tr>" + td + "</tr>")
                i += 1
            table_rows.append("</tbody>")
            html_parts.append("<table>" + "".join(table_rows) + "</table>")
            continue

        # Ordered list block
        if re.match(r"^\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                text = re.sub(r"^\d+\. ", "", lines[i])
                items.append("<li><span>" + _inline(_esc(text)) + "</span></li>")
                i += 1
            html_parts.append("<ol>" + "".join(items) + "</ol>")
            continue

        # Unordered list block
        if re.match(r"^[-*] ", line):
            items = []
            while i < len(lines) and re.match(r"^[-*] ", lines[i]):
                text = re.sub(r"^[-*] ", "", lines[i])
                items.append("<li>" + _inline(_esc(text)) + "</li>")
                i += 1
            html_parts.append("<ul>" + "".join(items) + "</ul>")
            continue

        # Headings
        if line.startswith("#### "):
            html_parts.append("<h4>" + _inline(_esc(line[5:])) + "</h4>")
        elif line.startswith("### "):
            html_parts.append("<h3>" + _inline(_esc(line[4:])) + "</h3>")
        elif line.startswith("## "):
            html_parts.append("<h2>" + _inline(_esc(line[3:])) + "</h2>")
        elif line.startswith("# "):
            html_parts.append("<h1>" + _inline(_esc(line[2:])) + "</h1>")
        elif line.startswith("---"):
            html_parts.append("<hr/>")
        elif line.strip() == "":
            pass  # skip blank lines
        else:
            html_parts.append("<p>" + _inline(_esc(line)) + "</p>")

        i += 1

    return "\n".join(html_parts)


def _esc(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


PDF_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.65;
    color: #1a1a2e;
    padding: 40px 48px;
    max-width: 800px;
    margin: 0 auto;
}

.pdf-meta {
    font-size: 9pt;
    color: #666;
    margin-bottom: 18pt;
    padding-bottom: 10pt;
    border-bottom: 1px solid #dde0f0;
    display: flex;
    flex-wrap: wrap;
    gap: 10pt;
    align-items: center;
}
.tag {
    background: #eef1ff;
    color: #4f6ef7;
    border-radius: 20pt;
    padding: 1pt 8pt;
    font-size: 8.5pt;
    font-weight: 600;
}
.version-badge {
    background: #4f6ef7;
    color: white;
    border-radius: 20pt;
    padding: 1pt 8pt;
    font-size: 8.5pt;
    font-weight: 700;
}

h1 {
    font-size: 22pt;
    font-weight: 800;
    color: #1a1a2e;
    margin-bottom: 8pt;
    padding-bottom: 10pt;
    border-bottom: 3px solid #4f6ef7;
    page-break-after: avoid;
}

h2 {
    font-size: 13pt;
    font-weight: 700;
    color: #1a1a2e;
    margin-top: 22pt;
    margin-bottom: 8pt;
    padding: 5pt 12pt;
    background: #f0f3ff;
    border-left: 4px solid #4f6ef7;
    page-break-after: avoid;
}

h3 {
    font-size: 11.5pt;
    font-weight: 700;
    color: #2d3561;
    margin-top: 14pt;
    margin-bottom: 5pt;
    page-break-after: avoid;
}

h4 {
    font-size: 10pt;
    font-weight: 700;
    color: #4a5068;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 10pt;
    margin-bottom: 4pt;
    page-break-after: avoid;
}

p { margin-bottom: 7pt; }

ul, ol { margin: 4pt 0 10pt 20pt; }
li { margin-bottom: 4pt; }

ol {
    list-style: none;
    counter-reset: steps;
    margin-left: 0;
}
ol li {
    counter-increment: steps;
    display: flex;
    gap: 10pt;
    align-items: flex-start;
    padding: 4pt 0;
}
ol li::before {
    content: counter(steps);
    background: #4f6ef7;
    color: white;
    font-size: 8pt;
    font-weight: 700;
    min-width: 20pt;
    height: 20pt;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
th {
    background: #f0f3ff;
    padding: 6pt 9pt;
    text-align: left;
    font-weight: 700;
    border: 1px solid #c8d0f0;
}
td {
    padding: 6pt 9pt;
    border: 1px solid #c8d0f0;
}
tr:nth-child(even) td { background: #f8f9ff; }

code {
    background: #f4f4f8;
    border-radius: 3pt;
    padding: 1pt 4pt;
    font-family: "Courier New", monospace;
    font-size: 9pt;
    color: #2d3561;
}
pre {
    background: #f4f4f8;
    border-radius: 4pt;
    padding: 10pt;
    margin: 8pt 0;
    page-break-inside: avoid;
    overflow: hidden;
}
pre code { background: none; padding: 0; font-size: 8.5pt; }

strong { font-weight: 700; }
em     { font-style: italic; }

hr {
    border: none;
    border-top: 1px solid #d0d5e8;
    margin: 14pt 0;
}
"""


async def markdown_to_pdf(
    markdown: str,
    title: str,
    source_filename: str,
    source_type: str,
    tags: list,
    version: int,
    updated_at: str,
) -> bytes:
    from playwright.sync_api import sync_playwright

    try:
        from datetime import datetime
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        date_str = dt.strftime("%b %d, %Y")
    except Exception:
        date_str = updated_at[:10]

    tag_chips = "".join('<span class="tag">' + t + '</span>' for t in tags)

    meta_html = (
        '<div class="pdf-meta">'
        '<span class="version-badge">v' + str(version) + '</span>'
        '<span>' + _esc(source_type) + '</span>'
        '<span>' + _esc(source_filename) + '</span>'
        '<span>Updated: ' + date_str + '</span>'
        + tag_chips +
        '</div>'
    )

    body_html = _md_to_html(markdown)

    full_html = (
        '<!DOCTYPE html><html><head>'
        '<meta charset="UTF-8"/>'
        '<title>' + _esc(title) + '</title>'
        '<style>' + PDF_CSS + '</style>'
        '</head><body>'
        + meta_html
        + body_html
        + '</body></html>'
    )

    # Run Playwright in a thread to avoid event loop conflicts with FastAPI
    import asyncio
    import concurrent.futures
    from playwright.sync_api import sync_playwright

    def _render_sync():
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(full_html, wait_until="domcontentloaded")
            pdf = page.pdf(
                format="A4",
                margin={"top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm"},
                print_background=True,
            )
            browser.close()
            return pdf

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _render_sync)
