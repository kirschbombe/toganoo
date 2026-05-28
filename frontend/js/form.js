// Vocabulary constants and form rendering

export const MARK_TYPES = [
  { v: 'collectors-seal',          l: "Collector's seal 蔵書印" },
  { v: 'institutional-stamp',      l: 'Institutional stamp' },
  { v: 'sticker-label',            l: 'Sticker / label' },
  { v: 'handwritten-inscription',  l: 'Handwritten inscription' },
  { v: 'signature',                l: 'Signature / 花押' },
  { v: 'catalogue-entry',          l: 'Catalogue entry' },
  { v: 'trace-remnant',            l: 'Trace / remnant' },
  { v: 'other',                    l: 'Other' },
];

export const SHAPES       = ['circular','oval','rectangular','square','gourd-shaped','irregular','other'];
export const INK_COLORS   = ['vermillion','black','blue','green','brown','gold','other'];
export const LABEL_COLORS = ['yellow-green','white','pink','red','blue','other'];
export const SCRIPT_TYPES = [
  { v: 'tensho',  l: 'Tensho 篆書 (seal script)' },
  { v: 'reisho',  l: 'Reisho 隷書 (clerical)' },
  { v: 'kaisho',  l: 'Kaisho 楷書 (block)' },
  { v: 'gyosho',  l: 'Gyōsho 行書 (semi-cursive)' },
  { v: 'sosho',   l: 'Sōsho 草書 (cursive)' },
  { v: 'kana',    l: 'Kana' },
  { v: 'mixed',   l: 'Mixed' },
  { v: 'other',   l: 'Other' },
];
export const CONDITIONS = ['clear','faded','partially-visible','trace-only','obscured'];
export const LOCATIONS = [
  { v: 'front-cover',       l: 'Front cover' },
  { v: 'back-cover',        l: 'Back cover' },
  { v: 'title-slip',        l: 'Title slip' },
  { v: 'spine',             l: 'Spine' },
  { v: 'first-leaf-recto',  l: 'First leaf (1r)' },
  { v: 'first-leaf-verso',  l: 'First leaf (1v)' },
  { v: 'last-leaf-recto',   l: 'Last leaf recto' },
  { v: 'last-leaf-verso',   l: 'Last leaf verso' },
  { v: 'throughout',        l: 'Throughout' },
  { v: 'endpaper-front',    l: 'Front endpaper' },
  { v: 'endpaper-back',     l: 'Back endpaper' },
  { v: 'other',             l: 'Other' },
];
export const OWNER_TYPES = [
  { v: 'person',            l: 'Person' },
  { v: 'temple',            l: 'Temple' },
  { v: 'school',            l: 'School / academy' },
  { v: 'library',           l: 'Library' },
  { v: 'other-institution', l: 'Other institution' },
];

export function defaultForm() {
  return {
    markType:          'collectors-seal',
    shape:             'rectangular',
    inkColor:          'vermillion',
    scriptType:        'kaisho',
    condition:         'clear',
    transcription:     '',
    transcriptionRom:  '',
    ownerName:         '',
    ownerType:         'temple',
    ownerAuthorityUri: '',
    placeName:         '',
    placeAuthorityUri: '',
    locationOnObject:  'front-cover',
    notes:             '',
  };
}

function sel(items, selected) {
  return items.map(item => {
    const v = typeof item === 'string' ? item : item.v;
    const l = typeof item === 'string' ? item : item.l;
    return `<option value="${v}"${v === selected ? ' selected' : ''}>${l}</option>`;
  }).join('');
}

export function renderForm(form, isNew) {
  const showPhysical = ['collectors-seal','institutional-stamp'].includes(form.markType);
  const showLabel    = form.markType === 'sticker-label';
  const showScript   = form.markType !== 'trace-remnant';

  return `
<div class="anno-form" id="anno-form">
  <div class="field-group">
    <label class="field-label" for="f-type">Mark type <span class="req">*</span></label>
    <select id="f-type" name="markType">${sel(MARK_TYPES, form.markType)}</select>
  </div>

  ${showPhysical ? `
  <div class="field-group">
    <label class="field-label" for="f-shape">Shape</label>
    <select id="f-shape" name="shape">${sel(SHAPES, form.shape)}</select>
  </div>
  <div class="field-group">
    <label class="field-label" for="f-color">Ink / color</label>
    <select id="f-color" name="inkColor">${sel(INK_COLORS, form.inkColor)}</select>
  </div>` : ''}

  ${showLabel ? `
  <div class="field-group">
    <label class="field-label" for="f-color">Label color</label>
    <select id="f-color" name="inkColor">${sel(LABEL_COLORS, form.inkColor)}</select>
  </div>` : ''}

  ${showScript ? `
  <div class="field-group">
    <label class="field-label" for="f-script">Script type</label>
    <select id="f-script" name="scriptType">${sel(SCRIPT_TYPES, form.scriptType)}</select>
  </div>` : ''}

  <div class="field-group">
    <label class="field-label" for="f-condition">Condition <span class="req">*</span></label>
    <select id="f-condition" name="condition">${sel(CONDITIONS, form.condition)}</select>
  </div>

  <div class="form-divider"></div>

  <div class="field-group">
    <label class="field-label" for="f-transcription">Transcription</label>
    <textarea id="f-transcription" name="transcription" rows="2"
      placeholder="Text of the mark in original script…"
      style="font-size:14px">${form.transcription}</textarea>
  </div>
  <div class="field-group">
    <label class="field-label" for="f-transrom">Romanization</label>
    <input type="text" id="f-transrom" name="transcriptionRom"
      value="${form.transcriptionRom}"
      placeholder="Hepburn romanization…">
  </div>

  <div class="form-divider"></div>

  <div class="field-group">
    <label class="field-label" for="f-owner">Owner name</label>
    <div class="viaf-row">
      <input type="text" id="f-owner" name="ownerName"
        value="${form.ownerName}"
        placeholder="Name in original script…">
      <button class="viaf-lookup-btn" id="viaf-owner-btn" title="Look up in VIAF">VIAF ↗</button>
    </div>
    <span class="field-hint">Search VIAF for authority record; paste URI below if found</span>
  </div>
  <div class="field-group">
    <label class="field-label" for="f-owner-uri">Owner authority URI</label>
    <input type="text" id="f-owner-uri" name="ownerAuthorityUri"
      value="${form.ownerAuthorityUri}"
      placeholder="https://viaf.org/viaf/…">
  </div>
  <div class="field-group">
    <label class="field-label" for="f-owner-type">Owner type</label>
    <select id="f-owner-type" name="ownerType">${sel(OWNER_TYPES, form.ownerType)}</select>
  </div>

  <div class="field-group">
    <label class="field-label" for="f-place">Associated place</label>
    <div class="viaf-row">
      <input type="text" id="f-place" name="placeName"
        value="${form.placeName}"
        placeholder="Place in original script…">
      <button class="viaf-lookup-btn" id="viaf-place-btn" title="Look up in VIAF">VIAF ↗</button>
    </div>
  </div>
  <div class="field-group">
    <label class="field-label" for="f-place-uri">Place authority URI</label>
    <input type="text" id="f-place-uri" name="placeAuthorityUri"
      value="${form.placeAuthorityUri}"
      placeholder="https://viaf.org/viaf/… or TGN…">
  </div>

  <div class="form-divider"></div>

  <div class="field-group">
    <label class="field-label" for="f-location">Location on object <span class="req">*</span></label>
    <select id="f-location" name="locationOnObject">${sel(LOCATIONS, form.locationOnObject)}</select>
  </div>

  <div class="field-group">
    <label class="field-label" for="f-notes">Notes</label>
    <textarea id="f-notes" name="notes" rows="2"
      placeholder="Interpretation, uncertainty, context…">${form.notes}</textarea>
  </div>

  <div class="form-actions">
    <button class="cancel-btn" id="form-cancel-btn">Cancel</button>
    <button class="save-btn" id="form-save-btn">${isNew ? 'Save annotation' : 'Update annotation'}</button>
  </div>
</div>`;
}

export function readForm(container) {
  const get = id => container.querySelector(`#${id}`)?.value ?? '';
  return {
    markType:          get('f-type'),
    shape:             get('f-shape'),
    inkColor:          get('f-color'),
    scriptType:        get('f-script'),
    condition:         get('f-condition'),
    transcription:     get('f-transcription'),
    transcriptionRom:  get('f-transrom'),
    ownerName:         get('f-owner'),
    ownerAuthorityUri: get('f-owner-uri'),
    ownerType:         get('f-owner-type'),
    placeName:         get('f-place'),
    placeAuthorityUri: get('f-place-uri'),
    locationOnObject:  get('f-location'),
    notes:             get('f-notes'),
  };
}

export function markTypeLabel(v) {
  return MARK_TYPES.find(m => m.v === v)?.l ?? v;
}
export function locationLabel(v) {
  return LOCATIONS.find(l => l.v === v)?.l ?? v;
}

export function openViaf(query) {
  if (!query.trim()) return;
  const url = `https://viaf.org/search#query=cql.any+all+%22${encodeURIComponent(query.trim())}%22&maximumRecords=10`;
  window.open(url, '_blank', 'noopener');
}
