import { getUser, getVolumeAnnotations, createAnnotation, updateAnnotation, deleteAnnotation, fetchManifest, exportUrl } from './api.js';
import { parseManifest, canvasToTileSource } from './manifest.js';
import { defaultForm, renderForm, readForm, markTypeLabel, locationLabel, openViaf } from './form.js';

// ── State ────────────────────────────────────────────────────────────────────

const state = {
  user:        null,
  volumes:     [],
  selectedVol: null,
  canvases:    [],
  pageIndex:   0,
  annotations: [],   // for current volume
  pendingRegion: null,   // { canvasId, canvasLabel, xywh } — drawn but not yet saved
  editingId:    null,    // annotation id being edited, or 'new'
  form:         defaultForm(),
  osd:          null,
  anno:         null,    // Annotorious instance
};

// ── Boot ─────────────────────────────────────────────────────────────────────

async function boot() {
  state.volumes = await loadVolumes();
  state.user    = await getUser();

  renderSidebar();
  renderAuth();
  renderPanel();

  // Re-check auth on focus (handles return from ORCID OAuth)
  window.addEventListener('focus', async () => {
    const user = await getUser();
    if (JSON.stringify(user) !== JSON.stringify(state.user)) {
      state.user = user;
      renderAuth();
      renderPanel();
      updateAnnotationMode();
    }
  });
}

async function loadVolumes() {
  try {
    const res = await fetch('/data/volumes.json');
    return res.json();
  } catch {
    return [];
  }
}

// ── Auth ─────────────────────────────────────────────────────────────────────

function renderAuth() {
  const el = document.getElementById('auth-status');
  if (state.user) {
    el.innerHTML = `
      <span class="user-name">${state.user.name}</span>
      <a href="/auth/logout" class="auth-btn">Sign out</a>`;
  } else {
    el.innerHTML = `
      <a href="/auth/login" class="auth-btn">
        <span class="orcid-dot">iD</span>Sign in with ORCID
      </a>`;
  }
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function renderSidebar() {
  const search = document.getElementById('vol-search');
  search.addEventListener('input', () => renderVolList(search.value));
  renderVolList('');
}

function renderVolList(query) {
  const q    = query.toLowerCase();
  const vols = q
    ? state.volumes.filter(v =>
        v.title.toLowerCase().includes(q) ||
        v.titleJa.includes(q) ||
        v.callNumber.toLowerCase().includes(q))
    : state.volumes;

  document.getElementById('vol-count').textContent = `(${vols.length})`;

  const list = document.getElementById('vol-list');
  list.innerHTML = vols.map(v => `
    <div class="vol-item${state.selectedVol?.ark === v.ark ? ' active' : ''}"
         data-ark="${v.ark}">
      <img class="vol-thumb" src="${v.thumbnail}" alt=""
           loading="lazy" onerror="this.style.opacity=0">
      <div class="vol-meta">
        <div class="vol-title">${v.title}</div>
        <div class="vol-ja">${v.titleJa}</div>
        <div class="vol-sub">${v.dateNormalized || v.dateCreation} · ${v.genre || 'text'}</div>
      </div>
    </div>`).join('');

  list.querySelectorAll('.vol-item').forEach(el => {
    el.addEventListener('click', () => selectVolume(
      state.volumes.find(v => v.ark === el.dataset.ark)
    ));
  });
}

// ── Volume selection ──────────────────────────────────────────────────────────

async function selectVolume(vol) {
  if (state.selectedVol?.ark === vol.ark) return;
  state.selectedVol = vol;
  state.pageIndex   = 0;
  state.pendingRegion = null;
  state.editingId     = null;
  state.form          = defaultForm();

  renderVolList(document.getElementById('vol-search').value);
  renderVolInfo();
  renderViewerFooter();
  renderPanel();

  // Load manifest and boot viewer
  try {
    const manifest = await fetchManifest(vol.manifestUrl);
    state.canvases  = parseManifest(manifest);
  } catch (err) {
    console.error('Manifest load failed:', err);
    state.canvases = [];
  }

  state.annotations = await getVolumeAnnotations(vol.ark);
  loadPage(0);
  renderPanel();
  renderExportButtons();
}

function renderVolInfo() {
  const bar = document.getElementById('vol-info-bar');
  if (!state.selectedVol) { bar.style.display = 'none'; return; }
  const v = state.selectedVol;
  bar.style.display = 'block';
  document.getElementById('vol-info-title').innerHTML =
    `${v.title} <span style="font-weight:400;color:#888">${v.titleJa}</span>`;
  document.getElementById('vol-info-meta').textContent =
    [v.callNumber, v.dateCreation || v.dateNormalized, v.genre]
      .filter(Boolean).join(' · ') +
    (v.toganooContainer ? ` · ${v.toganooContainer}` : '');
  const noteEl = document.getElementById('vol-info-note');
  noteEl.textContent = v.adminNote || '';
  noteEl.style.display = v.adminNote ? 'block' : 'none';
}

// ── OSD Viewer ────────────────────────────────────────────────────────────────

function initViewer() {
  if (state.osd) { state.osd.destroy(); state.osd = null; state.anno = null; }

  const placeholder = document.getElementById('viewer-placeholder');
  placeholder.style.display = 'none';

  state.osd = OpenSeadragon({
    id:                  'osd-viewer',
    prefixUrl:           'https://cdn.jsdelivr.net/npm/openseadragon@4.1.0/build/openseadragon/images/',
    animationTime:       0.3,
    blendTime:           0.1,
    constrainDuringPan:  true,
    maxZoomPixelRatio:   4,
    minZoomLevel:        0.5,
    visibilityRatio:     1,
    zoomPerScroll:       1.3,
    showNavigationControl: true,
    navigationControlAnchor: OpenSeadragon.ControlAnchor.TOP_RIGHT,
    showNavigator:       false,
  });

  // Annotorious — disable default widget/popup; we drive the panel
  state.anno = OpenSeadragon.Annotorious(state.osd, {
    readOnly:   false,
    widgets:    [],   // no default popup
    formatter:  null,
  });

  // When a region is drawn (selection complete)
  state.anno.on('createSelection', selection => {
    if (!state.user) { state.anno.cancelSelected(); return; }
    const drawBtn = document.getElementById("draw-btn");
    if (drawBtn) { drawBtn.classList.remove("active"); }
    state.anno.setDrawingEnabled(false);
    const canvas = state.canvases[state.pageIndex];
    state.pendingRegion = {
      canvasId:    canvas.id,
      canvasLabel: canvas.label,
      xywh:        selectionToXywh(selection, canvas),
    };
    state.editingId = 'new';
    state.form      = defaultForm();
    renderPanelForm(true);
    // Remove the Annotorious selection shape — our panel drives the UX
    state.anno.cancelSelected();
  });

  // Re-render saved annotations on each page load
  state.osd.addHandler('open', () => {
    renderSavedAnnotations();
    updateAnnotationMode();
  });
}

function selectionToXywh(selection, canvas) {
  // Annotorious v2 uses image-coordinate fragments
  const frag = selection?.target?.selector?.value ?? '';
  // e.g. "xywh=pixel:100,200,50,80"
  const m = frag.match(/xywh=pixel:([\d.]+),([\d.]+),([\d.]+),([\d.]+)/);
  if (m) return `pixel:${m[1]},${m[2]},${m[3]},${m[4]}`;
  return frag.replace('xywh=', '');
}

function renderSavedAnnotations() {
  if (!state.anno) return;
  state.anno.clearAnnotations();
  const canvas = state.canvases[state.pageIndex];
  if (!canvas) return;
  const forPage = state.annotations.filter(a => a.canvas_id === canvas.id);
  forPage.forEach((a, i) => {
    state.anno.addAnnotation({
      '@context': 'http://www.w3.org/ns/anno.jsonld',
      id:         `#anno-${a.id}`,
      type:       'Annotation',
      motivation: 'supplementing',
      body:       [{ type: 'TextualBody', value: `${i + 1}. ${markTypeLabel(a.mark_type)}` }],
      target: {
        source:   canvas.id,
        selector: { type: 'FragmentSelector', conformsTo: 'http://www.w3.org/TR/media-frags/', value: `xywh=${a.region_xywh}` },
      },
    });
  });
}

function updateAnnotationMode() {
  if (!state.anno) return;
  const btn = document.getElementById("draw-btn");
  if (btn) btn.style.display = state.user ? "block" : "none";
  document.getElementById('viewer-hint').textContent = state.user
    ? 'Click "+ Add annotation" then draw a region on the image'
    : 'Sign in with ORCID to annotate';
}

// ── Page navigation ───────────────────────────────────────────────────────────

function loadPage(index) {
  if (!state.canvases.length) { initViewer(); return; }
  index = Math.max(0, Math.min(index, state.canvases.length - 1));
  state.pageIndex = index;

  if (!state.osd) initViewer();

  const canvas = state.canvases[index];
  const ts     = canvasToTileSource(canvas);
  if (ts) state.osd.open(ts);
  renderPageControls();
}

function renderPageControls() {
  const total = state.canvases.length;
  const cur   = state.pageIndex;
  const canvas = state.canvases[cur];
  document.getElementById('page-indicator').textContent =
    total ? `${cur + 1} / ${total}${canvas ? ' — ' + canvas.label : ''}` : '';
  document.getElementById('prev-page').disabled = cur === 0;
  document.getElementById('next-page').disabled = cur >= total - 1;
}

function renderViewerFooter() {
  const footer = document.getElementById('viewer-footer');
  footer.style.display = state.selectedVol ? 'flex' : 'none';
  document.getElementById('prev-page').addEventListener('click', () => loadPage(state.pageIndex - 1));
  document.getElementById('next-page').addEventListener('click', () => loadPage(state.pageIndex + 1));
  const drawBtn = document.getElementById('draw-btn');
  if (drawBtn) {
    drawBtn.addEventListener('click', () => {
      const active = drawBtn.classList.toggle('active');
      state.anno.setDrawingEnabled(active);
    });
  }
  updateAnnotationMode();
}

function renderExportButtons() {
  const btns = document.getElementById('export-btns');
  if (!state.selectedVol || !state.annotations.length) { btns.style.display = 'none'; return; }
  btns.style.display = 'flex';
  document.getElementById('export-tei-btn').onclick = () =>
    window.open(exportUrl('tei', state.selectedVol.ark), '_blank');
  document.getElementById('export-la-btn').onclick = () =>
    window.open(exportUrl('linked-art', state.selectedVol.ark), '_blank');
  document.getElementById('export-anno-btn').onclick = () =>
    window.open(exportUrl('annotations', state.selectedVol.ark), '_blank');
}

// ── Panel ─────────────────────────────────────────────────────────────────────

function renderPanel() {
  const body      = document.getElementById('panel-body');
  const titleEl   = document.getElementById('panel-title');
  const closeBtn  = document.getElementById('panel-close-btn');

  if (!state.user) {
    titleEl.textContent = 'Annotations';
    closeBtn.style.display = 'none';
    body.innerHTML = `
      <div class="panel-login">
        <div style="font-size:32px;opacity:0.25">🔒</div>
        <p>Sign in with ORCID to create and view annotations for this volume.</p>
      </div>`;
    return;
  }

  if (state.editingId) {
    renderPanelForm(state.editingId === 'new');
    return;
  }

  titleEl.textContent = 'Annotations';
  closeBtn.style.display = 'none';

  if (!state.selectedVol) {
    body.innerHTML = `
      <div class="panel-empty">
        <div class="panel-empty-icon">📖</div>
        <p>Select a volume from the list to begin annotating.</p>
      </div>`;
    return;
  }

  if (!state.annotations.length) {
    body.innerHTML = `
      <div class="panel-empty">
        <div class="panel-empty-icon">✏️</div>
        <p>No annotations yet for this volume.<br>
           Click and drag on the image to mark a provenance feature.</p>
      </div>`;
    return;
  }

  titleEl.textContent = `Annotations (${state.annotations.length})`;
  body.innerHTML = `
    <div style="padding:8px 8px 0">
      <div style="display:flex;gap:5px;flex-wrap:wrap">
        <a class="export-panel-btn" href="${exportUrl('tei', state.selectedVol.ark)}" target="_blank">
          ↓ TEI XML
        </a>
        <a class="export-panel-btn" href="${exportUrl('linked-art', state.selectedVol.ark)}" target="_blank">
          ↓ Linked Art
        </a>
        <a class="export-panel-btn" href="${exportUrl('annotations', state.selectedVol.ark)}" target="_blank">
          ↓ W3C Annotations
        </a>
      </div>
    </div>
    <div class="anno-list">${state.annotations.map((a, i) => `
    <div class="anno-card${state.editingId === a.id ? ' selected' : ''}" data-id="${a.id}">
      <div class="anno-card-head">
        <span class="anno-seq">#${i + 1}</span>
        <span class="mark-badge">${markTypeLabel(a.mark_type)}</span>
      </div>
      <div class="anno-detail">
        ${a.transcription ? `<div class="ja">${a.transcription}</div>` : ''}
        ${a.owner_name    ? `<div>👤 ${a.owner_name}</div>` : ''}
        ${a.place_name    ? `<div>📍 ${a.place_name}</div>` : ''}
        <div>📄 ${locationLabel(a.location_on_object)}</div>
        <div style="color:#aaa;font-size:10px">by ${a.annotator_name || a.annotator_orcid}</div>
      </div>
      <div class="anno-actions">
        <button class="anno-action-btn edit-btn" data-id="${a.id}">Edit</button>
        ${a.annotator_orcid === state.user?.orcid
          ? `<button class="anno-action-btn danger delete-btn" data-id="${a.id}">Delete</button>`
          : ''}
      </div>
    </div>`).join('')}</div></div>`;

  body.querySelectorAll('.edit-btn').forEach(btn => btn.addEventListener('click', e => {
    e.stopPropagation();
    const a = state.annotations.find(x => x.id === btn.dataset.id);
    if (!a) return;
    state.editingId = a.id;
    state.form = {
      markType:          a.mark_type,
      shape:             a.shape || '',
      inkColor:          a.ink_color || '',
      scriptType:        a.script_type || '',
      condition:         a.condition || '',
      transcription:     a.transcription || '',
      transcriptionRom:  a.transcription_rom || '',
      ownerName:         a.owner_name || '',
      ownerType:         a.owner_type || 'temple',
      ownerAuthorityUri: a.owner_authority_uri || '',
      placeName:         a.place_name || '',
      placeAuthorityUri: a.place_authority_uri || '',
      locationOnObject:  a.location_on_object || '',
      notes:             a.notes || '',
    };
    renderPanelForm(false);
  }));

  body.querySelectorAll('.delete-btn').forEach(btn => btn.addEventListener('click', async e => {
    e.stopPropagation();
    if (!confirm('Delete this annotation?')) return;
    await deleteAnnotation(btn.dataset.id);
    state.annotations = await getVolumeAnnotations(state.selectedVol.ark);
    renderSavedAnnotations();
    renderPanel();
    renderExportButtons();
  }));
}

function renderPanelForm(isNew) {
  const titleEl  = document.getElementById('panel-title');
  const closeBtn = document.getElementById('panel-close-btn');
  const body     = document.getElementById('panel-body');

  titleEl.textContent   = isNew ? 'New annotation' : 'Edit annotation';
  closeBtn.style.display = 'block';
  closeBtn.onclick = cancelEdit;

  body.innerHTML = renderForm(state.form, isNew);

  // Live update form state on type changes (re-render for conditional fields)
  body.querySelector('#f-type')?.addEventListener('change', e => {
    state.form.markType = e.target.value;
    renderPanelForm(isNew);
  });

  // VIAF lookup buttons
  body.querySelector('#viaf-owner-btn')?.addEventListener('click', () =>
    openViaf(body.querySelector('#f-owner')?.value ?? ''));
  body.querySelector('#viaf-place-btn')?.addEventListener('click', () =>
    openViaf(body.querySelector('#f-place')?.value ?? ''));

  body.querySelector('#form-save-btn')?.addEventListener('click', async () => {
    const formData = readForm(body);
    if (!formData.markType) { alert('Mark type is required.'); return; }

    if (isNew) {
      if (!state.pendingRegion) { alert('No region drawn — please draw a region on the image first.'); return; }
      await createAnnotation({
        volume_ark:          state.selectedVol.ark,
        canvas_id:           state.pendingRegion.canvasId,
        canvas_label:        state.pendingRegion.canvasLabel,
        region_xywh:         state.pendingRegion.xywh,
        mark_type:           formData.markType,
        shape:               formData.shape || null,
        ink_color:           formData.inkColor || null,
        script_type:         formData.scriptType || null,
        condition:           formData.condition || null,
        transcription:       formData.transcription || null,
        transcription_rom:   formData.transcriptionRom || null,
        owner_name:          formData.ownerName || null,
        owner_type:          formData.ownerType || null,
        owner_authority_uri: formData.ownerAuthorityUri || null,
        place_name:          formData.placeName || null,
        place_authority_uri: formData.placeAuthorityUri || null,
        location_on_object:  formData.locationOnObject || null,
        notes:               formData.notes || null,
      });
    } else {
      await updateAnnotation(state.editingId, {
        volume_ark:          state.selectedVol.ark,
        canvas_id:           state.annotations.find(a => a.id === state.editingId)?.canvas_id ?? '',
        region_xywh:         state.annotations.find(a => a.id === state.editingId)?.region_xywh ?? '',
        mark_type:           formData.markType,
        shape:               formData.shape || null,
        ink_color:           formData.inkColor || null,
        script_type:         formData.scriptType || null,
        condition:           formData.condition || null,
        transcription:       formData.transcription || null,
        transcription_rom:   formData.transcriptionRom || null,
        owner_name:          formData.ownerName || null,
        owner_type:          formData.ownerType || null,
        owner_authority_uri: formData.ownerAuthorityUri || null,
        place_name:          formData.placeName || null,
        place_authority_uri: formData.placeAuthorityUri || null,
        location_on_object:  formData.locationOnObject || null,
        notes:               formData.notes || null,
      });
    }

    state.annotations   = await getVolumeAnnotations(state.selectedVol.ark);
    state.pendingRegion = null;
    state.editingId     = null;
    state.form          = defaultForm();
    renderSavedAnnotations();
    renderPanel();
    renderExportButtons();
  });

  body.querySelector('#form-cancel-btn')?.addEventListener('click', cancelEdit);
}

function cancelEdit() {
  state.pendingRegion = null;
  state.editingId     = null;
  state.form          = defaultForm();
  renderPanel();
}

// ── Start ─────────────────────────────────────────────────────────────────────

boot();
