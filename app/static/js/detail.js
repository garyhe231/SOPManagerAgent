/* SOP Manager Agent v2 — detail page */

const slug = document.getElementById('slugScript').dataset.slug;

// DOM refs
const sopMeta     = document.getElementById('sopMeta');
const sopContent  = document.getElementById('sopContent');
const tocNav      = document.getElementById('tocNav');
const viewMode    = document.getElementById('viewMode');
const editMode    = document.getElementById('editMode');
const editBtn     = document.getElementById('editBtn');
const downloadBtn = document.getElementById('downloadBtn');
const deleteBtn   = document.getElementById('deleteBtn');
const versionsBtn  = document.getElementById('versionsBtn');
const exportPdfBtn = document.getElementById('exportPdfBtn');
const editTitle   = document.getElementById('editTitle');
const editTags    = document.getElementById('editTags');
const editNote    = document.getElementById('editNote');
const editMarkdown= document.getElementById('editMarkdown');
const editPreview = document.getElementById('editPreview');
const saveBtn     = document.getElementById('saveBtn');
const cancelBtn   = document.getElementById('cancelBtn');
const versionsModal = document.getElementById('versionsModal');
const versionsClose = document.getElementById('versionsClose');
const versionsList  = document.getElementById('versionsList');
const chatMessages  = document.getElementById('chatMessages');
const chatInput     = document.getElementById('chatInput');
const chatSendBtn   = document.getElementById('chatSendBtn');
const patchPreview  = document.getElementById('patchPreview');
const applyPatchBtn = document.getElementById('applyPatchBtn');
const rejectPatchBtn= document.getElementById('rejectPatchBtn');
const toast         = document.getElementById('toast');

let currentSOP = null;
let chatHistory = [];
let pendingPatch = null;   // { markdown, summary }

// ─── Load ─────────────────────────────────────────────────
async function loadSOP() {
  try {
    const res = await fetch('/api/sops/' + slug);
    if (!res.ok) throw new Error('SOP not found');
    currentSOP = await res.json();
    renderSOP(currentSOP);
  } catch (err) {
    sopContent.innerHTML = '<div class="empty-state" style="padding:40px">SOP not found.</div>';
  }
}

function renderSOP(sop) {
  document.title = sop.title + ' — SOP Manager Agent';

  const tags = (sop.tags || []).map(t =>
    `<span class="tag-chip">${escHtml(t)}</span>`
  ).join('');
  const ver = sop.current_version || 1;

  sopMeta.innerHTML = `
    <span class="version-badge">v${ver}</span>
    <span class="source-badge">${escHtml(sop.source_type)}</span>
    <span>Source: ${escHtml(sop.source_filename)}</span>
    <span>Updated: ${formatDate(sop.updated_at)}</span>
    ${tags}
  `;

  sopContent.innerHTML = renderMarkdown(sop.markdown || '');
  buildTOC(sopContent, tocNav);
}

// ─── Edit ─────────────────────────────────────────────────
editBtn.addEventListener('click', () => {
  if (!currentSOP) return;
  editTitle.value = currentSOP.title;
  editTags.value = (currentSOP.tags || []).join(', ');
  editNote.value = '';
  editMarkdown.value = currentSOP.markdown || '';
  editPreview.innerHTML = renderMarkdown(editMarkdown.value);
  viewMode.classList.add('hidden');
  editMode.classList.remove('hidden');
});

editMarkdown.addEventListener('input', () => {
  editPreview.innerHTML = renderMarkdown(editMarkdown.value);
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
  fd.append('author', 'user');
  fd.append('note', editNote.value || 'Manual edit');
  try {
    const res = await fetch('/api/sops/' + slug, { method: 'PUT', body: fd });
    if (!res.ok) throw new Error('Save failed');
    const data = await res.json();
    currentSOP = { ...currentSOP, ...data.sop, markdown: editMarkdown.value };
    renderSOP(currentSOP);
    viewMode.classList.remove('hidden');
    editMode.classList.add('hidden');
    showToast('Saved as new version', 'success');
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save as New Version';
  }
});

// ─── Download ─────────────────────────────────────────────
downloadBtn.addEventListener('click', () => {
  window.location.href = '/api/sops/' + slug + '/download';
});

// ─── Export PDF ───────────────────────────────────────────
exportPdfBtn.addEventListener('click', async () => {
  exportPdfBtn.disabled = true;
  exportPdfBtn.textContent = '⏳ Generating PDF…';
  try {
    window.location.href = '/api/sops/' + slug + '/export/pdf';
    await new Promise(r => setTimeout(r, 3000));
  } finally {
    exportPdfBtn.disabled = false;
    exportPdfBtn.innerHTML = '&#128196; Export PDF';
  }
});

// ─── Delete ───────────────────────────────────────────────
deleteBtn.addEventListener('click', async () => {
  if (!confirm('Delete this SOP permanently?')) return;
  const res = await fetch('/api/sops/' + slug, { method: 'DELETE' });
  if (res.ok) window.location.href = '/';
  else showToast('Delete failed', 'error');
});

// ─── Versions modal ───────────────────────────────────────
versionsBtn.addEventListener('click', () => {
  if (!currentSOP) return;
  renderVersions(currentSOP);
  versionsModal.classList.remove('hidden');
});
versionsClose.addEventListener('click', () => versionsModal.classList.add('hidden'));
versionsModal.addEventListener('click', e => {
  if (e.target === versionsModal) versionsModal.classList.add('hidden');
});

function renderVersions(sop) {
  const versions = [...(sop.versions || [])].reverse();
  if (!versions.length) {
    versionsList.innerHTML = '<div style="padding:20px;color:var(--text-muted);font-size:13px">No version history yet.</div>';
    return;
  }
  versionsList.innerHTML = versions.map(v => {
    const isCurrent = v.version === sop.current_version;
    return `<div class="version-row ${isCurrent ? 'version-current' : ''}">
      <span class="version-num">v${v.version}</span>
      <div class="version-info">
        <div class="version-note">${escHtml(v.note || 'No note')}</div>
        <div class="version-meta">${formatDate(v.created_at)} · ${escHtml(v.author || 'system')}</div>
      </div>
      <div class="version-actions">
        ${!isCurrent ? `<button class="btn-ghost btn-sm" onclick="viewVersion(${v.version})">View</button>` : '<span class="tag-chip" style="font-size:11px">Current</span>'}
        <a class="btn-ghost btn-sm" href="/api/sops/${sop.slug}/versions/${v.version}/download">&#8659;</a>
      </div>
    </div>`;
  }).join('');
}

async function viewVersion(version) {
  versionsModal.classList.add('hidden');
  try {
    const res = await fetch(`/api/sops/${slug}/versions/${version}`);
    if (!res.ok) throw new Error('Version not found');
    const sop = await res.json();
    // Show version in a read-only way by updating content + meta temporarily
    const ver = sop.viewed_version || version;
    sopMeta.innerHTML = `
      <span class="version-badge" style="background:var(--yellow);color:#000">v${ver} (historical)</span>
      <span class="source-badge">${escHtml(sop.source_type)}</span>
      <button class="btn-ghost btn-sm" onclick="renderSOP(currentSOP)" style="margin-left:8px">&#8617; Back to current</button>
    `;
    sopContent.innerHTML = renderMarkdown(sop.markdown || '');
    buildTOC(sopContent, tocNav);
  } catch (err) {
    showToast('Could not load version', 'error');
  }
}

// ─── Chat ─────────────────────────────────────────────────
chatSendBtn.addEventListener('click', sendChat);
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

async function sendChat() {
  const text = chatInput.value.trim();
  if (!text || !currentSOP) return;
  chatInput.value = '';
  chatSendBtn.disabled = true;

  appendMsg('user', text);
  chatHistory.push({ role: 'user', content: text });

  const botEl = appendMsg('bot', '', true);

  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slug,
        message: text,
        history: chatHistory.slice(-10),
      }),
    });

    if (!res.ok) throw new Error('Chat error');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = JSON.parse(line.slice(6));

        if (payload.delta) {
          fullText += payload.delta;
          // Strip PATCH:/ANSWER: prefix from display
          const display = fullText.replace(/^(PATCH|ANSWER):\s*/, '').replace(/```markdown[\s\S]*?```/g, '').trim();
          botEl.querySelector('.chat-bubble').textContent = display;
          chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        if (payload.done) {
          botEl.querySelector('.chat-bubble').classList.remove('streaming');
          if (payload.type === 'patch' && payload.markdown) {
            pendingPatch = { markdown: payload.markdown, summary: payload.summary };
            showPatchPreview(payload.summary);
            const display = payload.summary || 'I\'ve drafted changes to the SOP. Review and apply above.';
            botEl.querySelector('.chat-bubble').textContent = display;
            chatHistory.push({ role: 'assistant', content: display });
          } else {
            const answer = payload.text || fullText.replace(/^ANSWER:\s*/, '').trim();
            chatHistory.push({ role: 'assistant', content: answer });
          }
        }
      }
    }
  } catch (err) {
    botEl.querySelector('.chat-bubble').textContent = 'Error: ' + err.message;
    botEl.querySelector('.chat-bubble').classList.remove('streaming');
  } finally {
    chatSendBtn.disabled = false;
  }
}

function appendMsg(role, text, streaming = false) {
  const wrap = document.createElement('div');
  wrap.className = 'chat-msg ' + role;
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble' + (streaming ? ' streaming' : '');
  bubble.textContent = text;
  wrap.appendChild(bubble);
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}

function showPatchPreview(summary) {
  patchPreview.classList.remove('hidden');
  patchPreview.querySelector('.patch-label').textContent =
    'Proposed: ' + (summary || 'AI suggested changes — review before applying');
}

applyPatchBtn.addEventListener('click', async () => {
  if (!pendingPatch || !currentSOP) return;
  applyPatchBtn.disabled = true;
  applyPatchBtn.textContent = 'Applying…';

  const fd = new FormData();
  fd.append('title', currentSOP.title);
  fd.append('tags', (currentSOP.tags || []).join(','));
  fd.append('markdown', pendingPatch.markdown);
  fd.append('author', 'AI Assistant');
  fd.append('note', pendingPatch.summary || 'AI-suggested edit');

  try {
    const res = await fetch('/api/sops/' + slug, { method: 'PUT', body: fd });
    if (!res.ok) throw new Error('Apply failed');
    const data = await res.json();
    currentSOP = { ...currentSOP, ...data.sop, markdown: pendingPatch.markdown };
    renderSOP(currentSOP);
    patchPreview.classList.add('hidden');
    pendingPatch = null;
    showToast('Changes applied as new version', 'success');
    appendMsg('bot', 'Changes applied! The SOP has been updated to a new version.');
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
  } finally {
    applyPatchBtn.disabled = false;
    applyPatchBtn.textContent = 'Apply Changes';
  }
});

rejectPatchBtn.addEventListener('click', () => {
  pendingPatch = null;
  patchPreview.classList.add('hidden');
  appendMsg('bot', 'Changes discarded. Let me know if you\'d like something different.');
});

// ─── Helpers ──────────────────────────────────────────────
function showToast(msg, type) {
  toast.textContent = msg;
  toast.className = 'toast ' + (type || '');
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 3500);
}

// Init
loadSOP();
