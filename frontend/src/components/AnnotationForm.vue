<template>
  <form class="anno-form" @submit.prevent="$emit('save', form)">

    <div class="form-group">
      <label class="form-label">Mark type <span class="required">*</span></label>
      <select v-model="form.markType" class="form-input" required>
        <option value="">— select —</option>
        <option v-for="t in MARK_TYPES" :key="t.v" :value="t.v">{{ t.l }}</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">Location on object</label>
      <select v-model="form.locationOnObject" class="form-input">
        <option value="">— select —</option>
        <option v-for="l in LOCATIONS" :key="l.v" :value="l.v">{{ l.l }}</option>
      </select>
    </div>

    <!-- Physical properties -->
    <details class="form-section" open>
      <summary class="form-section-title">Physical</summary>
      <div class="form-section-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Shape</label>
            <select v-model="form.shape" class="form-input">
              <option value=""></option>
              <option v-for="s in SHAPES" :key="s.v" :value="s.v">{{ s.l }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Ink color</label>
            <select v-model="form.inkColor" class="form-input">
              <option value=""></option>
              <option v-for="c in INK_COLORS" :key="c.v" :value="c.v">{{ c.l }}</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group" v-if="showScript">
            <label class="form-label">Script type</label>
            <select v-model="form.scriptType" class="form-input">
              <option value=""></option>
              <option v-for="s in SCRIPT_TYPES" :key="s.v" :value="s.v">{{ s.l }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Condition</label>
            <select v-model="form.condition" class="form-input">
              <option value=""></option>
              <option v-for="c in CONDITIONS" :key="c.v" :value="c.v">{{ c.l }}</option>
            </select>
          </div>
        </div>
      </div>
    </details>

    <!-- Content -->
    <details class="form-section" :open="hasTranscription">
      <summary class="form-section-title">Content</summary>
      <div class="form-section-body">
        <div class="form-group">
          <label class="form-label">Transcription</label>
          <textarea v-model="form.transcription" class="form-input form-textarea"
            placeholder="Text in original script…" rows="2"></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Romanization</label>
          <input v-model="form.transcriptionRom" type="text" class="form-input"
            placeholder="Romanized reading…" />
        </div>
      </div>
    </details>

    <!-- Provenance -->
    <details class="form-section" :open="hasOwner">
      <summary class="form-section-title">Provenance</summary>
      <div class="form-section-body">
        <div class="form-group">
          <label class="form-label">Owner name</label>
          <div class="form-input-with-btn">
            <input v-model="form.ownerName" type="text" class="form-input"
              placeholder="Name in original script…" />
            <button type="button" class="viaf-btn" @click="openViaf(form.ownerName)">VIAF ↗</button>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Owner type</label>
          <select v-model="form.ownerType" class="form-input">
            <option v-for="t in OWNER_TYPES" :key="t.v" :value="t.v">{{ t.l }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Owner authority URI</label>
          <input v-model="form.ownerAuthorityUri" type="url" class="form-input"
            placeholder="https://viaf.org/viaf/…" />
        </div>
        <div class="form-group">
          <label class="form-label">Place name</label>
          <div class="form-input-with-btn">
            <input v-model="form.placeName" type="text" class="form-input"
              placeholder="Place name…" />
            <button type="button" class="viaf-btn" @click="openViaf(form.placeName)">VIAF ↗</button>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Place authority URI</label>
          <input v-model="form.placeAuthorityUri" type="url" class="form-input"
            placeholder="https://viaf.org/viaf/…" />
        </div>
      </div>
    </details>

    <div class="form-group">
      <label class="form-label">Notes</label>
      <textarea v-model="form.notes" class="form-input form-textarea" rows="2"
        placeholder="Additional observations…"></textarea>
    </div>

    <div class="form-actions">
      <button type="submit" class="form-btn primary" :disabled="!form.markType">Save</button>
      <button type="button" class="form-btn" @click="$emit('cancel')">Cancel</button>
    </div>

  </form>
</template>

<script setup>
import { reactive, computed } from 'vue'

const props = defineProps({ initial: { type: Object, default: () => ({}) } })
const emit  = defineEmits(['save', 'cancel'])

const MARK_TYPES  = [
  { v: 'collectors-seal',         l: "Collector's seal" },
  { v: 'institutional-stamp',     l: 'Institutional stamp' },
  { v: 'sticker-label',           l: 'Sticker / label' },
  { v: 'handwritten-inscription', l: 'Handwritten inscription' },
  { v: 'signature',               l: 'Signature' },
  { v: 'catalogue-entry',         l: 'Catalogue entry' },
  { v: 'trace-remnant',           l: 'Trace / remnant' },
  { v: 'other',                   l: 'Other' },
]
const SHAPES      = [
  { v: 'circular', l: 'Circular' }, { v: 'oval', l: 'Oval' },
  { v: 'rectangular', l: 'Rectangular' }, { v: 'square', l: 'Square' },
  { v: 'gourd-shaped', l: 'Gourd-shaped' }, { v: 'irregular', l: 'Irregular' },
  { v: 'other', l: 'Other' },
]
const INK_COLORS  = [
  { v: 'vermillion', l: 'Vermillion' }, { v: 'black', l: 'Black' },
  { v: 'blue', l: 'Blue' }, { v: 'green', l: 'Green' },
  { v: 'brown', l: 'Brown' }, { v: 'gold', l: 'Gold' }, { v: 'other', l: 'Other' },
]
const SCRIPT_TYPES = [
  { v: 'tensho', l: 'Tensho (篆書)' }, { v: 'reisho', l: 'Reisho (隷書)' },
  { v: 'kaisho', l: 'Kaisho (楷書)' }, { v: 'gyosho', l: 'Gyosho (行書)' },
  { v: 'sosho', l: 'Sosho (草書)' }, { v: 'kana', l: 'Kana' },
  { v: 'mixed', l: 'Mixed' }, { v: 'other', l: 'Other' },
]
const CONDITIONS   = [
  { v: 'clear', l: 'Clear' }, { v: 'faded', l: 'Faded' },
  { v: 'partially-visible', l: 'Partially visible' },
  { v: 'trace-only', l: 'Trace only' }, { v: 'obscured', l: 'Obscured' },
]
const LOCATIONS    = [
  { v: 'front-cover', l: 'Front cover' }, { v: 'back-cover', l: 'Back cover' },
  { v: 'title-slip', l: 'Title slip' }, { v: 'spine', l: 'Spine' },
  { v: 'first-leaf-recto', l: 'First leaf recto' }, { v: 'first-leaf-verso', l: 'First leaf verso' },
  { v: 'last-leaf-recto', l: 'Last leaf recto' }, { v: 'last-leaf-verso', l: 'Last leaf verso' },
  { v: 'throughout', l: 'Throughout' }, { v: 'endpaper-front', l: 'Front endpaper' },
  { v: 'endpaper-back', l: 'Back endpaper' }, { v: 'other', l: 'Other' },
]
const OWNER_TYPES  = [
  { v: 'temple',            l: 'Temple / monastery' },
  { v: 'school',            l: 'School / lineage' },
  { v: 'library',           l: 'Library / archive' },
  { v: 'other-institution', l: 'Other institution' },
  { v: 'individual',        l: 'Individual' },
]

const INSCRIPTION_TYPES = new Set([
  'handwritten-inscription', 'signature', 'catalogue-entry',
])

const form = reactive({
  markType:          props.initial.mark_type          ?? '',
  shape:             props.initial.shape              ?? '',
  inkColor:          props.initial.ink_color          ?? '',
  scriptType:        props.initial.script_type        ?? '',
  condition:         props.initial.condition          ?? '',
  transcription:     props.initial.transcription      ?? '',
  transcriptionRom:  props.initial.transcription_rom  ?? '',
  ownerName:         props.initial.owner_name         ?? '',
  ownerType:         props.initial.owner_type         ?? 'temple',
  ownerAuthorityUri: props.initial.owner_authority_uri ?? '',
  placeName:         props.initial.place_name         ?? '',
  placeAuthorityUri: props.initial.place_authority_uri ?? '',
  locationOnObject:  props.initial.location_on_object ?? '',
  notes:             props.initial.notes              ?? '',
})

const showScript      = computed(() => INSCRIPTION_TYPES.has(form.markType))
const hasTranscription = computed(() => !!form.transcription)
const hasOwner         = computed(() => !!form.ownerName)

function openViaf(query) {
  const term = encodeURIComponent(query || '')
  window.open(`https://viaf.org/search#query=cql.any+all+%22${term}%22`, '_blank', 'noopener')
}
</script>

<style scoped>
.anno-form { display: flex; flex-direction: column; gap: 8px; padding: 12px; }
.form-group { display: flex; flex-direction: column; gap: 3px; }
.form-label { font-size: 11px; font-weight: 600; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.04em; }
.required { color: var(--vermillion); }
.form-input {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--ink-1);
  padding: 5px 8px;
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
  width: 100%;
}
.form-input:focus { outline: 1px solid var(--vermillion); }
.form-textarea { resize: vertical; min-height: 52px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.form-input-with-btn { display: flex; gap: 4px; }
.form-input-with-btn .form-input { flex: 1; }
.viaf-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--ink-3);
  border-radius: 4px;
  padding: 4px 7px;
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}
.viaf-btn:hover { color: var(--ink-1); }
.form-section { border: 1px solid var(--border); border-radius: 4px; overflow: hidden; }
.form-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 6px 10px;
  cursor: pointer;
  background: rgba(255,255,255,0.03);
  list-style: none;
}
.form-section-title::-webkit-details-marker { display: none; }
.form-section-body { padding: 8px 10px; display: flex; flex-direction: column; gap: 8px; }
.form-actions { display: flex; gap: 6px; padding-top: 4px; }
.form-btn {
  padding: 7px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border);
  background: var(--sidebar-bg);
  color: var(--ink-2);
  transition: opacity 0.15s;
}
.form-btn:hover { opacity: 0.85; }
.form-btn.primary { background: var(--vermillion); color: #fff; border-color: var(--vermillion); }
.form-btn:disabled { opacity: 0.4; cursor: default; }
</style>
