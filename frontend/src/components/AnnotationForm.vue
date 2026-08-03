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
        <div class="form-row" v-if="showPhysical">
          <div class="form-group">
            <label class="form-label">Shape</label>
            <select v-model="form.shape" class="form-input">
              <option value=""></option>
              <option v-for="s in SHAPES" :key="s.v" :value="s.v">{{ s.l }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Ink / color</label>
            <select v-model="form.inkColor" class="form-input">
              <option value=""></option>
              <option v-for="c in INK_COLORS" :key="c.v" :value="c.v">{{ c.l }}</option>
            </select>
          </div>
        </div>
        <div class="form-group" v-if="showLabel">
          <label class="form-label">Label color</label>
          <select v-model="form.inkColor" class="form-input">
            <option value=""></option>
            <option v-for="c in LABEL_COLORS" :key="c" :value="c">{{ c }}</option>
          </select>
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
const LABEL_COLORS = ['yellow-green', 'white', 'pink', 'red', 'blue', 'other']
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

const PHYSICAL_TYPES = new Set(['collectors-seal', 'institutional-stamp'])

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

const showPhysical    = computed(() => PHYSICAL_TYPES.has(form.markType))
const showLabel       = computed(() => form.markType === 'sticker-label')
const showScript      = computed(() => form.markType !== 'trace-remnant' && form.markType !== '')
const hasTranscription = computed(() => !!form.transcription)
const hasOwner         = computed(() => !!form.ownerName)

function openViaf(query) {
  const term = encodeURIComponent(query || '')
  window.open(`https://viaf.org/search#query=cql.any+all+%22${term}%22`, '_blank', 'noopener')
}
</script>

<style scoped>
.anno-form { display: flex; flex-direction: column; gap: 16px; padding: 20px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--paper-ink-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.required { color: var(--vermillion); }
.form-input {
  background: #fff;
  border: 1px solid oklch(60% 0.02 75 / 45%);
  color: var(--paper-ink-1);
  padding: 10px 12px;
  border-radius: 7px;
  font-size: 14px;
  font-family: inherit;
  width: 100%;
}
.form-input::placeholder { color: var(--paper-ink-3); }
.form-input:focus { outline: none; border-color: var(--vermillion); }
.form-textarea { resize: vertical; min-height: 64px; line-height: 1.5; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-input-with-btn { display: flex; gap: 6px; }
.form-input-with-btn .form-input { flex: 1; }
.viaf-btn {
  background: var(--paper-mid);
  border: 1px solid oklch(60% 0.02 75 / 45%);
  color: var(--paper-ink-2);
  border-radius: 7px;
  padding: 8px 12px;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.viaf-btn:hover { color: var(--paper-ink-1); border-color: var(--paper-ink-3); }
.form-section {
  border: 1px solid oklch(60% 0.02 75 / 40%);
  border-radius: 8px;
  overflow: hidden;
}
.form-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--paper-ink-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 14px;
  cursor: pointer;
  background: var(--paper-mid);
  list-style: none;
}
.form-section-title::-webkit-details-marker { display: none; }
.form-section-body { padding: 14px; display: flex; flex-direction: column; gap: 14px; }
.form-actions { display: flex; gap: 10px; padding-top: 4px; }
.form-btn {
  padding: 12px 20px;
  border-radius: 8px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid oklch(60% 0.02 75 / 45%);
  background: none;
  color: var(--paper-ink-2);
  transition: background 0.15s, color 0.15s;
}
.form-btn:hover { background: var(--paper-mid); color: var(--paper-ink-1); }
.form-btn.primary {
  flex: 1;
  padding: 12px;
  font-weight: 600;
  background: var(--vermillion);
  color: #fff;
  border-color: var(--vermillion);
}
.form-btn.primary:hover { background: var(--vermillion-hover); border-color: var(--vermillion-hover); }
.form-btn:disabled { opacity: 0.4; cursor: default; }
.form-btn.primary:disabled:hover { background: var(--vermillion); }
</style>
