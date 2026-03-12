/* SOP Manager Agent — detail page */

const slug = document.getElementById('slugScript').dataset.slug;
const sopMeta = document.getElementById('sopMeta');
const sopContent = document.getElementById('sopContent');
const viewMode = document.getElementById('viewMode');
const editMode = document.getElementById('editMode');
const editBtn = document.getElementById('editBtn');
const downloadBtn = document.getElementById('downloadBtn');
const deleteBtn = document.getElementById('deleteBtn');
const editTitle = document.getElementById('editTitle');
const editTags = document.getElementById('editTags');
const editMarkdown = document.getElementById('editMarkdown');
const saveBtn = document.getElementById('saveBtn');
const cancelBtn = document.getElementById('cancelBtn');
const toast = document.getElementById('toast');

let currentSOP = null;

// --- Load ---
async function loadSOP() {
  try {
    const res = await fetch('/api/sops/' + slug);
    if (!res.ok) throw new Error('SOP not found');
    currentSOP = await res.json();
    renderSOP(currentSOP);
  } catch (err) {
    sopContent.innerHTML = '<div class="empty-state">SOP not found.</div>';
  }
}

function renderSOP(sop) {
  document.title = sop.title + ' — SOP Manager Agent';

  const tags = (sop.tags || []).map(t =>
    `<span class="tag-chip">${escHtml(t)}</span>`
  ).join(' ');

  sopMeta.innerHTML = `
    <span class="source-badge">${escHtml(sop.source_type)}</span>
    <span>Source: ${escHtml(sop.source_filename)}</span>
    <span>Updated: ${formatDate(sop.updated_at)}</span>
    ${tags}
  `;

  sopContent.innerHTML = renderMarkdown(sop.markdown || '');
}

// Simple markdown renderer (no external dep)
function renderMarkdown(md) {
  let html = escHtml(md);

  // Tables
  html = html.replace(/((?:\|.+\|\n)+)/g, (match) => {
    const rows = match.trim().split('\n');
    const header = rows[0];
    const separator = rows[1];
    const body = rows.slice(2);
    if (!separator || !separator.match(/^\|[\s\-|]+\|$/)) return match;
    const thCells = header.split('|').slice(1,-1).map(c => `<th>${c.trim()}</th>`).join('');
    const trRows = body.map(r => {
      const cells = r.split('|').slice(1,-1).map(c => `<td>${c.trim()}</td>`).join('');
      return `<tr>${cells}</tr>`;
    }).join('');
    return `<table><thead><tr>${thCells}</tr></thead><tbody>${trRows}</tbody></table>`;
  });

  // Code blocks
  html = html.replace(/```[\s\S]*?```/g, m => {
    const inner = m.replace(/^```\w*\n?/, '').replace(/```$/, '');
    return `<pre><code>${inner}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headings
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold / italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // HR
  html = html.replace(/^---+$/gm, '<hr/>');

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Ordered list items
  html = html.replace(/((?:^\d+\. .+\n?)+)/gm, (match) => {
    const items = match.trim().split('\n').map(l => {
      return '<li>' + l.replace(/^\d+\. /, '') + '</li>';
    }).join('');
    return `<ol>${items}</ol>`;
  });

  // Unordered list items
  html = html.replace(/((?:^[-*] .+\n?)+)/gm, (match) => {
    const items = match.trim().split('\n').map(l => {
      return '<li>' + l.replace(/^[-*] /, '') + '</li>';
    }).join('');
    return `<ul>${items}</ul>`;
  });

  // Paragraphs (double newline)
  html = html.replace(/\n\n+/g, '</p><p>');
  html = '<p>' + html + '</p>';

  // Cleanup empty paragraphs / wrap around block elements
  html = html.replace(/<p>(<(?:h[123]|ul|ol|table|pre|hr|blockquote)[^>]*>)/g, '$1');
  html = html.replace(/(<\/(?:h[123]|ul|ol|table|pre|hr|blockquote)>)<\/p>/g, '$1');
  html = html.replace(/<p><\/p>/g, '');

  return html;
}

// --- Actions ---
editBtn.addEventListener('click', () => {
  if (!currentSOP) return;
  editTitle.value = currentSOP.title;
  editTags.value = (currentSOP.tags || []).join(', ');
  editMarkdown.value = currentSOP.markdown || '';
  viewMode.classList.add('hidden');
  editMode.classList.remove('hidden');
});

cancelBtn.addEventListener('click', () => {
  viewMode.classList.remove('hidden');
  editMode.classList.add('hidden');
});

saveBtn.addEventListener('click', async () => {
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';
  const fd = new FormData();
  fd.append('title', editTitle.value);
  fd.append('tags', editTags.value);
  fd.append('markdown', editMarkdown.value);
  try {
    const res = await fetch('/api/sops/' + slug, { method: 'PUT', body: fd });
    if (!res.ok) throw new Error('Save failed');
    const data = await res.json();
    currentSOP = { ...currentSOP, ...data.sop, markdown: editMarkdown.value };
    renderSOP(currentSOP);
    viewMode.classList.remove('hidden');
    editMode.classList.add('hidden');
    showToast('Saved successfully', 'success');
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Changes';
  }
});

downloadBtn.addEventListener('click', () => {
  window.location.href = '/api/sops/' + slug + '/download';
});

deleteBtn.addEventListener('click', async () => {
  if (!confirm('Delete this SOP? This cannot be undone.')) return;
  const res = await fetch('/api/sops/' + slug, { method: 'DELETE' });
  if (res.ok) {
    window.location.href = '/';
  } else {
    showToast('Delete failed', 'error');
  }
});

// --- Helpers ---
function showToast(msg, type) {
  toast.textContent = msg;
  toast.className = 'toast ' + (type || '');
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 3000);
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Init
loadSOP();
