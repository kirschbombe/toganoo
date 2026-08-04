<template>
  <aside class="anno-panel">

    <!-- Header -->
    <div class="panel-header">
      <span class="panel-label">{{ panelTitle }}</span>
      <div class="panel-header-actions">
        <button
          v-if="!editing && user && volume && (user.is_editor || user.is_admin)"
          class="add-anno-btn"
          :class="{ drawing: drawing }"
          @click="$emit('startDrawing')"
        >
          <span v-if="drawing">✕ Cancel drawing</span>
          <span v-else>+ Add annotation</span>
        </button>
        <button v-if="editing" class="panel-close-btn" @click="cancelEdit">✕</button>
      </div>
    </div>

    <!-- Drawing mode instruction strip -->
    <div v-if="drawing && !editing" class="drawing-strip">
      Click and drag on the image to draw a region
    </div>

    <!-- Form: new or edit -->
    <div v-if="editing" class="panel-body">
      <AnnotationForm
        :initial="editingAnnotation"
        @save="handleSave"
        @cancel="cancelEdit"
      />
    </div>

    <!-- No volume selected -->
    <div v-else-if="!volume" class="panel-body panel-empty">
      <div class="panel-empty-icon">📖</div>
      <p>Select a volume from the collection to begin annotating.</p>
    </div>

    <!-- Annotation list: collection mode (grouped by volume) -->
    <div v-else-if="collectionAnnotations" class="panel-body">
      <div v-for="group in collectionAnnotations" :key="group.volume_slug" class="vol-group">
        <div
          class="vol-group-header"
          :class="{ expanded: expandedVolumeSlug === group.volume_slug }"
          @click="toggleVolumeGroup(group.volume_slug)"
        >
          <span class="vol-group-caret">{{ expandedVolumeSlug === group.volume_slug ? '▼' : '▶' }}</span>
          <span class="vol-group-title">
            Vol. {{ group.volume_number }} — {{ group.volume_label || group.volume_title }}
          </span>
          <span class="vol-group-count">({{ group.annotations.length }})</span>
        </div>
        <div v-if="expandedVolumeSlug === group.volume_slug" class="anno-list">
          <div v-if="!group.annotations.length" class="panel-empty-sm">No annotations in this volume.</div>
          <div
            v-for="(a, i) in group.annotations"
            :key="a.id"
            class="anno-card"
            :class="{ selected: selectedId === a.id }"
            :data-anno-id="a.id"
            @click="toggleSelected(a.id, group.volume_slug)"
          >
            <div class="anno-card-head">
              <span class="anno-seq">#{{ i + 1 }}</span>
              <span class="mark-badge">{{ markTypeLabel(a.mark_type) }}</span>
              <span class="anno-expand-icon">{{ selectedId === a.id ? '▲' : '▼' }}</span>
            </div>
            <div class="anno-detail">
              <div v-if="a.transcription" class="ja">{{ a.transcription }}</div>
              <div v-if="a.owner_name">👤 {{ a.owner_name }}</div>
              <div v-if="a.place_name">📍 {{ a.place_name }}</div>
              <div>📄 {{ locationLabel(a.location_on_object) }}</div>
              <div class="anno-by">by {{ a.annotator_name || a.annotator_orcid }}</div>
            </div>
            <div v-if="selectedId === a.id" class="anno-expanded">
              <dl class="anno-fields">
                <template v-if="a.shape"><dt>Shape</dt><dd>{{ a.shape }}</dd></template>
                <template v-if="a.ink_color"><dt>Color</dt><dd>{{ a.ink_color }}</dd></template>
                <template v-if="a.script_type"><dt>Script</dt><dd>{{ a.script_type }}</dd></template>
                <template v-if="a.condition"><dt>Condition</dt><dd>{{ a.condition }}</dd></template>
                <template v-if="a.transcription_rom"><dt>Romanization</dt><dd>{{ a.transcription_rom }}</dd></template>
                <template v-if="a.owner_type"><dt>Owner type</dt><dd>{{ a.owner_type }}</dd></template>
                <template v-if="a.owner_authority_uri">
                  <dt>Owner URI</dt>
                  <dd><a :href="a.owner_authority_uri" target="_blank" rel="noopener" class="anno-uri">{{ a.owner_authority_uri }}</a></dd>
                </template>
                <template v-if="a.place_authority_uri">
                  <dt>Place URI</dt>
                  <dd><a :href="a.place_authority_uri" target="_blank" rel="noopener" class="anno-uri">{{ a.place_authority_uri }}</a></dd>
                </template>
                <template v-if="a.notes"><dt>Notes</dt><dd>{{ a.notes }}</dd></template>
                <template v-if="a.canvas_label"><dt>Canvas</dt><dd>{{ a.canvas_label }}</dd></template>
              </dl>
            </div>
            <div class="anno-actions" @click.stop>
              <button
                v-if="user && (user.is_editor || user.is_admin)"
                class="anno-action-btn" @click="startEdit(a)">Edit</button>
              <button
                v-if="user && (a.annotator_orcid === user.orcid || user.is_admin)"
                class="anno-action-btn danger"
                @click="handleDelete(a.id)"
              >Delete</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Annotation list: single-volume mode -->
    <div v-else class="panel-body">

      <!-- Export links -->
      <div v-if="annotations.length" class="panel-exports">
        <a :href="exportUrl('tei', volume.manifest_url)" target="_blank" class="export-panel-btn">↓ TEI XML</a>
        <a :href="exportUrl('linked-art', volume.manifest_url)" target="_blank" class="export-panel-btn">↓ Linked Art</a>
        <a :href="exportUrl('annotations', volume.manifest_url)" target="_blank" class="export-panel-btn">↓ IIIF Annotations</a>
      </div>

      <!-- Empty state -->
      <div v-if="!annotations.length" class="panel-empty">
        <div class="panel-empty-icon">✏️</div>
        <p>No annotations yet for this volume.<br>
           Click "+ Add annotation" then draw a region on the image.</p>
      </div>

      <!-- Annotation cards -->
      <div class="anno-list">
        <div
          v-for="(a, i) in annotations"
          :key="a.id"
          class="anno-card"
          :class="{ selected: selectedId === a.id }"
          :data-anno-id="a.id"
          @click="toggleSelected(a.id)"
        >
          <div class="anno-card-head">
            <span class="anno-seq">#{{ i + 1 }}</span>
            <span class="mark-badge">{{ markTypeLabel(a.mark_type) }}</span>
            <span class="anno-expand-icon">{{ selectedId === a.id ? '▲' : '▼' }}</span>
          </div>

          <!-- Compact summary (always visible) -->
          <div class="anno-detail">
            <div v-if="a.transcription" class="ja">{{ a.transcription }}</div>
            <div v-if="a.owner_name">👤 {{ a.owner_name }}</div>
            <div v-if="a.place_name">📍 {{ a.place_name }}</div>
            <div>📄 {{ locationLabel(a.location_on_object) }}</div>
            <div class="anno-by">by {{ a.annotator_name || a.annotator_orcid }}</div>
          </div>

          <!-- Expanded details -->
          <div v-if="selectedId === a.id" class="anno-expanded">
            <dl class="anno-fields">
              <template v-if="a.shape">
                <dt>Shape</dt><dd>{{ a.shape }}</dd>
              </template>
              <template v-if="a.ink_color">
                <dt>Color</dt><dd>{{ a.ink_color }}</dd>
              </template>
              <template v-if="a.script_type">
                <dt>Script</dt><dd>{{ a.script_type }}</dd>
              </template>
              <template v-if="a.condition">
                <dt>Condition</dt><dd>{{ a.condition }}</dd>
              </template>
              <template v-if="a.transcription_rom">
                <dt>Romanization</dt><dd>{{ a.transcription_rom }}</dd>
              </template>
              <template v-if="a.owner_type">
                <dt>Owner type</dt><dd>{{ a.owner_type }}</dd>
              </template>
              <template v-if="a.owner_authority_uri">
                <dt>Owner URI</dt>
                <dd><a :href="a.owner_authority_uri" target="_blank" rel="noopener" class="anno-uri">{{ a.owner_authority_uri }}</a></dd>
              </template>
              <template v-if="a.place_authority_uri">
                <dt>Place URI</dt>
                <dd><a :href="a.place_authority_uri" target="_blank" rel="noopener" class="anno-uri">{{ a.place_authority_uri }}</a></dd>
              </template>
              <template v-if="a.notes">
                <dt>Notes</dt><dd>{{ a.notes }}</dd>
              </template>
              <template v-if="a.canvas_label">
                <dt>Canvas</dt><dd>{{ a.canvas_label }}</dd>
              </template>
            </dl>
          </div>

          <!-- Actions stop propagation so clicks don't toggle expand -->
          <div class="anno-actions" @click.stop>
            <button
              v-if="user && (user.is_editor || user.is_admin)"
              class="anno-action-btn" @click="startEdit(a)">Edit</button>
            <button
              v-if="user && (a.annotator_orcid === user.orcid || user.is_admin)"
              class="anno-action-btn danger"
              @click="handleDelete(a.id)"
            >Delete</button>
          </div>
        </div>
      </div>
    </div>

  </aside>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import AnnotationForm from './AnnotationForm.vue'
import { exportUrl } from '../api/index.js'
import { createAnnotation, updateAnnotation, deleteAnnotation } from '../api/index.js'

const props = defineProps({
  user:                 Object,
  volume:               Object,
  drawing:              { type: Boolean, default: false },
  annotations:          Array,
  pendingRegion:        Object,
  activeAnnotationId:   { type: [Number, String], default: null },
  collectionAnnotations: { type: Array,  default: null },
  currentVolumeSlug:    { type: String, default: null },
})

const emit = defineEmits(['annotationsChanged', 'clearPendingRegion', 'startDrawing', 'annotationSelected'])

const editingId           = ref(null)
const editingAnnotation   = ref({})
const selectedId          = ref(null)
const expandedVolumeSlug  = ref(props.currentVolumeSlug)

const editing    = computed(() => editingId.value !== null)
const panelTitle = computed(() => {
  if (editingId.value === 'new') return 'New annotation'
  if (editing.value)             return 'Edit annotation'
  if (props.annotations?.length) return `Annotations (${props.annotations.length})`
  return 'Annotations'
})

watch(() => props.pendingRegion, (region) => {
  if (region) { editingId.value = 'new'; editingAnnotation.value = {} }
})

watch(() => props.currentVolumeSlug, (slug) => {
  if (slug) expandedVolumeSlug.value = slug
})

watch(() => props.activeAnnotationId, async (id) => {
  if (id == null) return
  selectedId.value = id
  // In collection mode, expand the group that contains this annotation
  if (props.collectionAnnotations) {
    for (const group of props.collectionAnnotations) {
      if (group.annotations.some(a => a.id === id)) {
        expandedVolumeSlug.value = group.volume_slug
        break
      }
    }
  }
  await nextTick()
  const el = document.querySelector(`[data-anno-id="${id}"]`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
})

function toggleVolumeGroup(slug) {
  expandedVolumeSlug.value = expandedVolumeSlug.value === slug ? null : slug
}

function toggleSelected(id, volumeSlug) {
  selectedId.value = selectedId.value === id ? null : id
  if (selectedId.value != null) {
    // Look in single-volume annotations or across collection groups
    let annotation = props.annotations?.find(a => a.id === id)
    if (!annotation && props.collectionAnnotations) {
      for (const group of props.collectionAnnotations) {
        annotation = group.annotations.find(a => a.id === id)
        if (annotation) { annotation = { ...annotation, volume_slug: group.volume_slug }; break }
      }
    }
    if (annotation) emit('annotationSelected', annotation)
  }
}

function startEdit(a) {
  editingId.value         = a.id
  editingAnnotation.value = a
  selectedId.value        = null
}

function cancelEdit() {
  editingId.value = null
  editingAnnotation.value = {}
  emit('clearPendingRegion')
}

async function handleSave(formData) {
  if (!formData.markType) return alert('Mark type is required.')

  const payload = {
    mark_type:           formData.markType,
    shape:               formData.shape               || null,
    ink_color:           formData.inkColor            || null,
    script_type:         formData.scriptType          || null,
    condition:           formData.condition           || null,
    transcription:       formData.transcription       || null,
    transcription_rom:   formData.transcriptionRom    || null,
    owner_name:          formData.ownerName           || null,
    owner_type:          formData.ownerType           || null,
    owner_authority_uri: formData.ownerAuthorityUri   || null,
    place_name:          formData.placeName           || null,
    place_authority_uri: formData.placeAuthorityUri   || null,
    location_on_object:  formData.locationOnObject    || null,
    notes:               formData.notes               || null,
  }

  if (editingId.value === 'new') {
    if (!props.pendingRegion) return alert('No region drawn — please draw a region first.')
    await createAnnotation({
      ...payload,
      volume_id:    props.volume.manifest_url,
      canvas_id:    props.pendingRegion.canvasId,
      canvas_label: props.pendingRegion.canvasLabel,
      region_xywh:  props.pendingRegion.xywh,
    })
  } else {
    const existing = props.annotations.find(a => a.id === editingId.value)
    await updateAnnotation(editingId.value, {
      ...payload,
      volume_id:   props.volume.manifest_url,
      canvas_id:   existing?.canvas_id    ?? '',
      region_xywh: existing?.region_xywh  ?? '',
    })
  }

  editingId.value = null
  editingAnnotation.value = {}
  emit('clearPendingRegion')
  emit('annotationsChanged')
}

async function handleDelete(id) {
  if (!confirm('Delete this annotation?')) return
  await deleteAnnotation(id)
  emit('annotationsChanged')
}

const MARK_TYPE_LABELS = {
  'collectors-seal': "Collector's seal", 'institutional-stamp': 'Institutional stamp',
  'sticker-label': 'Sticker / label', 'handwritten-inscription': 'Handwritten inscription',
  'signature': 'Signature', 'catalogue-entry': 'Catalogue entry',
  'trace-remnant': 'Trace / remnant', 'other': 'Other',
}
const LOCATION_LABELS = {
  'front-cover': 'Front cover', 'back-cover': 'Back cover', 'title-slip': 'Title slip',
  'spine': 'Spine', 'first-leaf-recto': 'First leaf recto', 'first-leaf-verso': 'First leaf verso',
  'last-leaf-recto': 'Last leaf recto', 'last-leaf-verso': 'Last leaf verso',
  'throughout': 'Throughout', 'endpaper-front': 'Front endpaper',
  'endpaper-back': 'Back endpaper', 'other': 'Other',
}

function markTypeLabel(v) { return MARK_TYPE_LABELS[v] ?? v }
function locationLabel(v)  { return LOCATION_LABELS[v]  ?? v  }
</script>

<style scoped>
.anno-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--paper);
  border-left: 1px solid var(--paper-border);
  color: var(--paper-ink-1);
  overflow: hidden;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--paper-mid);
  border-bottom: 1px solid var(--paper-border);
  flex-shrink: 0;
  gap: 10px;
}
.panel-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--paper-ink-2);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.panel-header-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.add-anno-btn {
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 7px;
  border: 1px solid var(--vermillion);
  background: var(--vermillion);
  color: #fff;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.add-anno-btn:hover { background: var(--vermillion-hover); border-color: var(--vermillion-hover); }
.add-anno-btn.drawing {
  background: transparent;
  border-color: var(--paper-border);
  color: var(--paper-ink-2);
}
.add-anno-btn.drawing:hover {
  background: transparent;
  border-color: var(--paper-ink-3);
  color: var(--paper-ink-1);
}
.drawing-strip {
  font-size: 13px;
  color: var(--paper-ink-2);
  background: oklch(90% 0.03 27 / 40%);
  border-bottom: 1px solid oklch(53% 0.19 27 / 25%);
  padding: 11px 18px;
  text-align: center;
  flex-shrink: 0;
}
.panel-close-btn {
  background: none;
  border: none;
  color: var(--paper-ink-3);
  cursor: pointer;
  font-size: 18px;
  padding: 4px 6px;
}
.panel-close-btn:hover { color: var(--paper-ink-1); }
.panel-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.panel-empty {
  padding: 56px 28px;
  text-align: center;
  color: var(--paper-ink-3);
  font-size: 15px;
  line-height: 1.7;
}
.panel-empty-icon { font-size: 2rem; margin-bottom: 12px; opacity: 0.4; }
.panel-exports {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 14px 18px;
  border-bottom: 1px solid oklch(60% 0.02 75 / 25%);
}
.export-panel-btn {
  font-size: 12px;
  color: var(--paper-ink-2);
  text-decoration: none;
  padding: 6px 12px;
  border: 1px solid oklch(60% 0.02 75 / 40%);
  border-radius: 6px;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.export-panel-btn:hover {
  color: var(--vermillion);
  border-color: var(--vermillion);
  background: oklch(90% 0.03 27 / 35%);
}
/* ── Collection volume groups ────────────────────────────── */
.vol-group { border-bottom: 1px solid oklch(60% 0.02 75 / 25%); }
.vol-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 13px 18px;
  cursor: pointer;
  user-select: none;
  transition: background 0.1s;
}
.vol-group-header:hover { background: oklch(60% 0.02 75 / 12%); }
.vol-group-header.expanded { background: oklch(90% 0.03 27 / 30%); }
.vol-group-caret { font-size: 11px; color: var(--paper-ink-3); flex-shrink: 0; }
.vol-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--paper-ink-2);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.vol-group-count { font-size: 12px; color: var(--paper-ink-3); flex-shrink: 0; }
.panel-empty-sm { font-size: 13px; color: var(--paper-ink-3); padding: 16px 20px; }

.anno-list { display: flex; flex-direction: column; }
.anno-card {
  padding: 16px 20px;
  border-left: 3px solid transparent;
  border-bottom: 1px solid oklch(60% 0.02 75 / 25%);
  cursor: pointer;
  transition: background 0.1s;
}
.anno-card:hover    { background: oklch(60% 0.02 75 / 10%); }
.anno-card.selected {
  background: oklch(90% 0.03 27 / 40%);
  border-left-color: var(--vermillion);
}
.anno-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.anno-seq { font-size: 13px; color: var(--paper-ink-3); }
.mark-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--vermillion);
  color: #fff;
}
.anno-expand-icon { font-size: 11px; color: var(--paper-ink-3); margin-left: auto; }
.anno-detail { font-size: 14px; color: oklch(30% 0.02 75); line-height: 1.6; }
.anno-detail .ja {
  font-family: var(--font-serif);
  font-size: 17px;
  color: oklch(22% 0.02 75);
  margin-bottom: 4px;
}
.anno-by { font-size: 12px; color: var(--paper-ink-3); margin-top: 4px; }
.anno-expanded {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid oklch(60% 0.02 75 / 25%);
}
.anno-fields {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 14px;
}
.anno-fields dt {
  color: var(--paper-ink-3);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.04em;
  white-space: nowrap;
  padding-top: 2px;
}
.anno-fields dd { color: oklch(32% 0.02 75); font-size: 13px; word-break: break-word; }
.anno-uri { color: var(--paper-ink-3); word-break: break-all; font-size: 12px; }
.anno-uri:hover { color: var(--vermillion); }
.anno-actions { display: flex; gap: 8px; margin-top: 12px; }
.anno-action-btn {
  font-family: inherit;
  font-size: 12px;
  padding: 5px 12px;
  border-radius: 5px;
  border: 1px solid oklch(60% 0.02 75 / 40%);
  background: none;
  color: var(--paper-ink-2);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.anno-action-btn:hover { color: var(--paper-ink-1); border-color: var(--paper-ink-3); }
.anno-action-btn.danger { color: var(--vermillion); border-color: oklch(53% 0.19 27 / 50%); }
.anno-action-btn.danger:hover { color: var(--vermillion); border-color: var(--vermillion); }
</style>
