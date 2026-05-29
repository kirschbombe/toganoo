<template>
  <aside class="canvas-index">

    <!-- ── Collection mode: Volumes / Pages tabs ── -->
    <template v-if="collectionVolumes">
      <div class="tab-bar">
        <button class="tab-btn" :class="{ active: activeTab === 'volumes' }" @click="activeTab = 'volumes'">
          Volumes
        </button>
        <button class="tab-btn" :class="{ active: activeTab === 'pages' }" @click="activeTab = 'pages'">
          Pages
        </button>
      </div>

      <!-- Volumes tab -->
      <div v-if="activeTab === 'volumes'" class="vol-list">
        <div
          v-for="vol in collectionVolumes"
          :key="vol.slug"
          class="vol-row"
          :class="{ active: vol.slug === currentVolumeSlug }"
          @click="onVolClick(vol)"
        >
          <span class="vol-row-num">{{ vol.volume_number }}</span>
          <span class="vol-row-label">{{ vol.volume_label || vol.title }}</span>
        </div>
      </div>

      <!-- Pages tab -->
      <div v-else class="canvas-index-list" ref="listEl">
        <div
          v-for="(canvas, i) in canvases"
          :key="canvas.id"
          class="canvas-thumb"
          :class="{ active: i === currentIndex }"
          @click="$emit('select', i)"
        >
          <div class="canvas-thumb-img-wrap" :data-index="i">
            <img
              v-if="visible.has(i) && canvas.thumbnail"
              :src="canvas.thumbnail"
              :alt="canvas.label"
              loading="lazy"
            />
            <div v-else class="canvas-thumb-placeholder">{{ i + 1 }}</div>
          </div>
          <div class="canvas-thumb-label">{{ canvas.label || i + 1 }}</div>
        </div>
      </div>
    </template>

    <!-- ── Single-volume mode: canvas list only ── -->
    <template v-else>
      <div class="canvas-index-header">
        <span class="canvas-index-label">Pages ({{ canvases.length }})</span>
      </div>
      <div class="canvas-index-list" ref="listEl">
        <div
          v-for="(canvas, i) in canvases"
          :key="canvas.id"
          class="canvas-thumb"
          :class="{ active: i === currentIndex }"
          @click="$emit('select', i)"
        >
          <div class="canvas-thumb-img-wrap" :data-index="i">
            <img
              v-if="visible.has(i) && canvas.thumbnail"
              :src="canvas.thumbnail"
              :alt="canvas.label"
              loading="lazy"
            />
            <div v-else class="canvas-thumb-placeholder">{{ i + 1 }}</div>
          </div>
          <div class="canvas-thumb-label">{{ canvas.label || i + 1 }}</div>
        </div>
      </div>
    </template>

  </aside>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  canvases:          { type: Array,  default: () => [] },
  currentIndex:      { type: Number, default: 0 },
  collectionVolumes: { type: Array,  default: null },
  currentVolumeSlug: { type: String, default: null },
})
const emit = defineEmits(['select', 'selectVolume'])

const listEl    = ref(null)
const visible   = ref(new Set())
const activeTab = ref('volumes')   // start on Volumes so user sees the set on load
let observer = null

// Switch to Volumes tab only when entering a collection (null → array).
// Re-fetching volumes for the same collection (array → new array) should not
// reset the tab — the user may have already switched to Pages.
watch(() => props.collectionVolumes, (vols, prevVols) => {
  if (vols && !prevVols) activeTab.value = 'volumes'
}, { immediate: true })

// After volume navigation completes, switch to Pages
watch(() => props.currentVolumeSlug, () => {
  if (props.collectionVolumes) activeTab.value = 'pages'
})

// Re-run observer when switching to Pages tab
watch(activeTab, (tab) => {
  if (tab === 'pages') setTimeout(setupObserver, 50)
})

function onVolClick(vol) {
  if (vol.slug === props.currentVolumeSlug) {
    // Already on this volume — just jump to Pages
    activeTab.value = 'pages'
  } else {
    // Navigate to selected volume; the currentVolumeSlug watcher will switch to Pages
    emit('selectVolume', vol.slug)
  }
}

// IntersectionObserver for lazy-loading canvas thumbnails
function setupObserver() {
  if (observer) observer.disconnect()
  visible.value = new Set()
  const root = listEl.value
  if (!root) return
  observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        visible.value = new Set([...visible.value, Number(e.target.dataset.index)])
      }
    })
  }, { root, rootMargin: '100px' })
  root.querySelectorAll('.canvas-thumb-img-wrap').forEach(el => observer.observe(el))
}

watch(() => props.canvases, () => setTimeout(setupObserver, 50))

onMounted(setupObserver)
onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
.canvas-index {
  width: 100%;
  height: 100%;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  overflow: hidden;
}

/* ── Tab bar ───────────────────────────────────────────────── */
.tab-bar {
  display: flex;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.tab-btn {
  flex: 1;
  padding: 10px 8px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 10px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;
}
.tab-btn:hover { color: var(--ink-1); }
.tab-btn.active {
  color: var(--ink-1);
  border-bottom-color: var(--vermillion);
}

/* ── Volume list (Volumes tab) ─────────────────────────────── */
.vol-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.vol-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 10px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.12s;
}
.vol-row:hover { background: rgba(255,255,255,0.04); }
.vol-row.active { background: rgba(180,40,30,0.08); }
.vol-row-num {
  font-size: 11px;
  font-weight: 700;
  color: var(--vermillion);
  flex-shrink: 0;
  min-width: 14px;
  margin-top: 1px;
}
.vol-row-label {
  font-size: 10px;
  color: var(--ink-2);
  line-height: 1.35;
  flex: 1;
  min-width: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.vol-row.active .vol-row-label { color: var(--ink-1); }

/* ── Single-vol header ─────────────────────────────────────── */
.canvas-index-header {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.canvas-index-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ── Canvas thumbnails (Pages tab + single-vol mode) ───────── */
.canvas-index-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.canvas-thumb {
  cursor: pointer;
  border-radius: 4px;
  padding: 4px 2px;
  border: 1px solid transparent;
  transition: border-color 0.15s;
}
.canvas-thumb:hover  { border-color: var(--border); }
.canvas-thumb.active { border-color: var(--vermillion); background: rgba(180,40,30,0.08); }
.canvas-thumb-img-wrap {
  width: 100%;
  aspect-ratio: 3/4;
  background: #1a1a1c;
  border-radius: 2px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.canvas-thumb-img-wrap img { width: 100%; height: 100%; object-fit: cover; }
.canvas-thumb-placeholder { font-size: 11px; color: var(--ink-3); }
.canvas-thumb-label {
  font-size: 10px;
  color: var(--ink-3);
  text-align: center;
  margin-top: 3px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
