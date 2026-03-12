/**
 * md.js — shared markdown → HTML renderer
 * Produces layered sections with collapsible h2 blocks.
 */

function renderMarkdown(md) {
  if (!md) return '';

  // Split into h1 title + h2 sections
  const lines = md.split('\n');
  let titleHtml = '';
  const sections = [];
  let current = null;

  for (const line of lines) {
    if (/^# /.test(line)) {
      titleHtml = `<h1>${escInline(line.replace(/^# /, ''))}</h1>`;
    } else if (/^## /.test(line)) {
      if (current) sections.push(current);
      const heading = line.replace(/^## /, '');
      current = { heading, lines: [] };
    } else {
      if (current) current.lines.push(line);
      else if (titleHtml) {
        // Lines before first h2 go into an implicit intro section
        if (!sections.length) {
          sections.push({ heading: '', lines: [], implicit: true });
        }
        sections[0].lines.push(line);
      }
    }
  }
  if (current) sections.push(current);

  let html = titleHtml;

  for (const section of sections) {
    if (section.implicit) {
      html += renderBody(section.lines.join('\n'));
      continue;
    }
    const id = 'sec-' + section.heading.toLowerCase().replace(/[^\w]+/g, '-');
    const bodyHtml = renderBody(section.lines.join('\n'));
    html += `
<div class="sop-section" id="${id}">
  <div class="sop-section-header" onclick="toggleSection('${id}')">
    <span class="sop-section-toggle">&#9660;</span>
    <h2>${escInline(section.heading)}</h2>
  </div>
  <div class="sop-section-body" style="max-height: 9999px">${bodyHtml}</div>
</div>`;
  }

  return html;
}

function renderBody(text) {
  if (!text.trim()) return '';
  let html = text;

  // Code blocks (preserve raw)
  const codeBlocks = [];
  html = html.replace(/```[\s\S]*?```/g, m => {
    const inner = m.replace(/^```\w*\n?/, '').replace(/\n?```$/, '');
    codeBlocks.push(`<pre><code>${escHtml(inner)}</code></pre>`);
    return `\x00CODE${codeBlocks.length - 1}\x00`;
  });

  // Escape HTML (after code block extraction)
  html = escHtml(html);

  // Restore code blocks
  html = html.replace(/\x00CODE(\d+)\x00/g, (_, i) => codeBlocks[parseInt(i)]);

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headings (h3/h4 — h1/h2 handled above)
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');

  // Bold / italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Note / Warning callouts
  html = html.replace(/\*\*Note:\*\*([^\n]*)/g,
    '<div class="callout callout-note"><span class="callout-icon">&#8505;</span><span><strong>Note:</strong>$1</span></div>');
  html = html.replace(/\*\*Warning:\*\*([^\n]*)/g,
    '<div class="callout callout-warning"><span class="callout-icon">&#9888;</span><span><strong>Warning:</strong>$1</span></div>');

  // HR
  html = html.replace(/^---+$/gm, '<hr/>');

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Tables
  html = html.replace(/((?:\|.+\|\n?)+)/g, (match) => {
    const rows = match.trim().split('\n');
    if (rows.length < 2) return match;
    const sep = rows[1];
    if (!sep || !/^\|[\s\-:|]+\|$/.test(sep.trim())) return match;
    const thCells = rows[0].split('|').slice(1,-1).map(c => `<th>${c.trim()}</th>`).join('');
    const trRows = rows.slice(2).map(r => {
      const cells = r.split('|').slice(1,-1).map(c => `<td>${c.trim()}</td>`).join('');
      return `<tr>${cells}</tr>`;
    }).join('');
    return `<table><thead><tr>${thCells}</tr></thead><tbody>${trRows}</tbody></table>`;
  });

  // Ordered lists
  html = html.replace(/((?:^\d+\. .+\n?)+)/gm, (match) => {
    const items = match.trim().split('\n').map(l =>
      `<li><span>${l.replace(/^\d+\. /, '')}</span></li>`
    ).join('');
    return `<ol>${items}</ol>`;
  });

  // Unordered lists
  html = html.replace(/((?:^[-*] .+\n?)+)/gm, (match) => {
    const items = match.trim().split('\n').map(l =>
      `<li>${l.replace(/^[-*] /, '')}</li>`
    ).join('');
    return `<ul>${items}</ul>`;
  });

  // Paragraphs
  html = html.replace(/\n\n+/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p>(<(?:h3|h4|ul|ol|table|pre|hr|blockquote|div)[^>]*>)/g, '$1');
  html = html.replace(/(<\/(?:h3|h4|ul|ol|table|pre|hr|blockquote|div)>)<\/p>/g, '$1');
  html = html.replace(/<p>\s*<\/p>/g, '');
  html = html.replace(/<p>\n/g, '<p>');

  return html;
}

function toggleSection(id) {
  const sec = document.getElementById(id);
  if (!sec) return;
  const body = sec.querySelector('.sop-section-body');
  if (sec.classList.contains('collapsed')) {
    sec.classList.remove('collapsed');
    body.style.maxHeight = body.scrollHeight + 'px';
    // Allow auto-height after expand
    setTimeout(() => { body.style.maxHeight = '9999px'; }, 260);
  } else {
    body.style.maxHeight = body.scrollHeight + 'px';
    requestAnimationFrame(() => {
      sec.classList.add('collapsed');
      body.style.maxHeight = '0';
    });
  }
}

function buildTOC(contentEl, tocEl) {
  tocEl.innerHTML = '';
  const headings = contentEl.querySelectorAll('h1, h2, h3, h4');
  headings.forEach(h => {
    const level = parseInt(h.tagName[1]);
    const link = document.createElement('span');
    link.className = `toc-link level-${level}`;
    link.textContent = h.textContent;
    link.addEventListener('click', () => {
      h.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    tocEl.appendChild(link);
  });

  // Highlight active section on scroll
  const sop = document.querySelector('.sop-main');
  if (!sop) return;
  sop.addEventListener('scroll', () => {
    const allLinks = tocEl.querySelectorAll('.toc-link');
    const allHeadings = Array.from(contentEl.querySelectorAll('h1,h2,h3'));
    let active = 0;
    allHeadings.forEach((h, i) => {
      if (h.getBoundingClientRect().top < 100) active = i;
    });
    allLinks.forEach((l, i) => l.classList.toggle('active', i === active));
  }, { passive: true });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escInline(str) {
  // For heading text that's already safe
  return String(str).replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
