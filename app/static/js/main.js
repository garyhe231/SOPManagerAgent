/* SOP Manager Agent — index page */

const fileInput = document.getElementById('fileInput');
const fileDrop = document.getElementById('fileDrop');
const dropLabel = document.getElementById('dropLabel');
const fileSelected = document.getElementById('fileSelected');
const browseBtn = document.getElementById('browseBtn');
const uploadForm = document.getElementById('uploadForm');
const uploadBtn = document.getElementById('uploadBtn');
const uploadBtnText = document.getElementById('uploadBtnText');
const uploadSpinner = document.getElementById('uploadSpinner');
const uploadResult = document.getElementById('uploadResult');
const progressWrap = document.getElementById('progressWrap');
const progressBar  = document.getElementById('progressBar');
const progressPct  = document.getElementById('progressPct');
const progressStage= document.getElementById('progressStage');
const searchInput = document.getElementById('searchInput');
const tagFilter = document.getElementById('tagFilter');
const refreshBtn = document.getElementById('refreshBtn');
const sopList = document.getElementById('sopList');

// --- File Drop ---
browseBtn.addEventListener('click', () => fileInput.click());
fileDrop.addEventListener('click', (e) => { if (e.target === fileDrop || e.target === dropLabel) fileInput.click(); });

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) showFile(fileInput.files[0].name);
});

fileDrop.addEventListener('dragover', (e) => { e.preventDefault(); fileDrop.classList.add('dragover'); });
fileDrop.addEventListener('dragleave', () => fileDrop.classList.remove('dragover'));
fileDrop.addEventListener('drop', (e) => {
  e.preventDefault();
  fileDrop.classList.remove('dragover');
  const dt = e.dataTransfer;
  if (dt.files.length) {
    fileInput.files = dt.files;
    showFile(dt.files[0].name);
  }
});

function showFile(name) {
  dropLabel.classList.add('hidden');
  fileSelected.classList.remove('hidden');
  fileSelected.textContent = '✓ ' + name;
}

// --- Progress simulation ---
// Stages: [label, target %, min ms to hold before advancing]
const STAGES = [
  { label: 'Uploading file…',           pct: 10,  hold: 400  },
  { label: 'Extracting content…',       pct: 30,  hold: 800  },
  { label: 'Analysing with Claude…',    pct: 55,  hold: 2000 },
  { label: 'Generating SOP structure…', pct: 75,  hold: 2000 },
  { label: 'Writing markdown…',         pct: 90,  hold: 1000 },
];

let _progressTimer = null;

function startProgress() {
  progressWrap.classList.remove('hidden');
  uploadResult.classList.add('hidden');
  progressBar.classList.remove('done');
  setProgress(0, '');
  let i = 0;

  function advance() {
    if (i >= STAGES.length) return;
    const s = STAGES[i++];
    setProgress(s.pct, s.label);
    _progressTimer = setTimeout(advance, s.hold);
  }
  advance();
}

function setProgress(pct, label) {
  progressBar.style.width = pct + '%';
  progressPct.textContent = pct + '%';
  if (label) progressStage.textContent = label;
}

function finishProgress(success) {
  clearTimeout(_progressTimer);
  if (success) {
    progressBar.classList.add('done');
    setProgress(100, 'Done!');
  }
  setTimeout(() => progressWrap.classList.add('hidden'), 1200);
}

// --- Upload ---
uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!fileInput.files.length) return;

  uploadBtn.disabled = true;
  uploadBtnText.textContent = 'Processing…';
  uploadSpinner.classList.remove('hidden');
  uploadResult.classList.add('hidden');
  startProgress();

  const fd = new FormData(uploadForm);
  try {
    const res = await fetch('/api/sops/upload', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');
    finishProgress(true);
    showResult('success', `SOP "${data.sop.title}" generated successfully! <a href="/sop/${data.sop.slug}" style="color:inherit;text-decoration:underline">View it &rarr;</a>`);
    uploadForm.reset();
    dropLabel.classList.remove('hidden');
    fileSelected.classList.add('hidden');
    loadSOPs();
  } catch (err) {
    finishProgress(false);
    showResult('error', '✗ ' + err.message);
  } finally {
    uploadBtn.disabled = false;
    uploadBtnText.textContent = 'Process & Generate SOP';
    uploadSpinner.classList.add('hidden');
  }
});

function showResult(type, html) {
  uploadResult.className = 'upload-result ' + type;
  uploadResult.innerHTML = html;
  uploadResult.classList.remove('hidden');
}

// --- Library ---
let debounceTimer;
searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(loadSOPs, 300);
});
tagFilter.addEventListener('change', loadSOPs);
refreshBtn.addEventListener('click', loadSOPs);

async function loadSOPs() {
  const search = searchInput.value.trim();
  const tag = tagFilter.value;
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (tag) params.set('tag', tag);

  try {
    const [sopRes, tagRes] = await Promise.all([
      fetch('/api/sops?' + params),
      fetch('/api/sops/tags')
    ]);
    const sops = await sopRes.json();
    const tags = await tagRes.json();
    renderTags(tags);
    renderSOPs(sops);
  } catch (err) {
    sopList.innerHTML = '<div class="empty-state">Error loading SOPs.</div>';
  }
}

function renderTags(tags) {
  const current = tagFilter.value;
  tagFilter.innerHTML = '<option value="">All Tags</option>';
  tags.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t; opt.textContent = t;
    if (t === current) opt.selected = true;
    tagFilter.appendChild(opt);
  });
}

function renderSOPs(sops) {
  if (!sops.length) {
    sopList.innerHTML = '<div class="empty-state">No SOPs found. Upload a document to get started.</div>';
    return;
  }
  sopList.innerHTML = sops.map(s => `
    <a class="sop-item" href="/sop/${s.slug}">
      <div class="sop-item-left">
        <div class="sop-item-title">${escHtml(s.title)}</div>
        <div class="sop-item-meta">
          ${escHtml(s.source_filename)} &middot; ${formatDate(s.updated_at)}
        </div>
      </div>
      <div class="sop-item-right">
        ${(s.tags || []).map(t => `<span class="tag-chip">${escHtml(t)}</span>`).join('')}
        <span class="source-badge">${escHtml(s.source_type)}</span>
      </div>
    </a>
  `).join('');
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// Init
loadSOPs();
