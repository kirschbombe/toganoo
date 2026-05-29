<template>
  <aside class="canvas-index">

    <!-- ── Collection mode: volume list + sliding page drawer ── -->
    <template v-if="collectionVolumes">
      <div class="canvas-index-header">
        <span class="canvas-index-label">Volumes</span>
      </div>

      <div class="vol-list">
        <div
          v-for="vol in collectionVolumes"
          :key="vol.slug"
          class="vol-row"
          :class="{ active: vol.slug === currentVolumeSlug }"
          @click="onVolRowClick(vol)"
        >
          <span class="vol-row-num">{{ vol.volume_number }}</span>
          <span class="vol-row-label">{{ vol.volume_label || vol.title }}</span>
          <!-- pages indicator on the active volume -->
          <span v-if="vol.slug === currentVolumeSlug" class="vol-row-pages-icon" :class="{ open: drawerOpen }">⊞</span>
        </div>
      </div>

      <!-- Sliding page drawer -->
      <Transition name="drawer">
        <div v-if="drawerOpen" class="canvas-drawer" @click.self="drawerOpen = false">
          <div class="canvas-drawer-header">
            <span class="canvas-drawer-label">Pages ({{ canvases.length }})</span>
            <button class="canvas-drawer-close" @click="drawerOpen = false">✕</button>
          </div>
          <div class="canvas-drawer-list" ref="listEl">
            <div
              v-for="(canvas, i) in canvases"
              :key="canvas.id"
              class="canvas-thumb"
              :class="{ active: i === currentIndex }"
              @click="selectPage(i)"
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
        </div>
      </Transition>
    </template>

    <!-- ── Single-volume mode: canvas list ── -->
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
const drawerOpen = ref(false)
let observer = null

// Open drawer automatically when collection data loads
watch(() => props.collectionVolumes, (vols) => {
  if (vols) drawerOpen.value = true
}, { immediate: true })

// Re-open and scroll to active page when navigating between volumes
watch(() => props.currentVolumeSlug, () => {
  drawerOpen.value = true
})

function onVolRowClick(vol) {
  if (vol.slug === props.currentVolumeSlug) {
    drawerOpen.value = !drawerOpen.value
  } else {
    emit('selectVolume', vol.slug)
  }
}

function selectPage(i) {
  emit('select', i)
  // Keep drawer open — user may want to navigate multiple pages
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
        const i = Number(e.target.dataset.index)
        visible.value = new Set([...visible.value, i])
      }
    })
  }, { root, rootMargin: '100px' })

  root.querySelectorAll('.canvas-thumb-img-wrap').forEach(el => observer.observe(el))
}

watch([() => props.canvases, drawerOpen], () => {
  if (drawerOpen.value) setTimeout(setupObserver, 50)
}, { immediate: false })

onMounted(setupObserver)
onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
.canvas-index {
  position: relative;
  width: 100%;
  height: 100%;
  background: var(--sidebar-bg);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  overflow: visible;   /* allow drawer to extend beyond sidebar bounds */
}
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

/* ── Volume list (collection mode) ────────────────────────── */
.vol-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.vol-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 10px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.12s;
  min-height: 0;
}
.vol-row:hover:not(.active) { background: rgba(255,255,255,0.04); }
.vol-row.active {
  background: rgba(180,40,30,0.08);
  cursor: pointer;  /* still clickable to toggle drawer */
}
.vol-row-num {
  font-size: 11px;
  font-weight: 700;
  color: var(--vermillion);
  flex-shrink: 0;
  min-width: 14px;
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
.vol-row-pages-icon {
  font-size: 12px;
  color: var(--ink-3);
  flex-shrink: 0;
  transition: color 0.15s;
}
.vol-row-pages-icon.open { color: var(--vermillion); }

/* ── Sliding page drawer ───────────────────────────────────── */
.canvas-drawer {
  position: absolute;
  left: 100%;
  top: 0;
  bottom: 0;
  width: 112px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  box-shadow: 4px 0 16px rgba(0,0,0,0.35);
  display: flex;
  flex-direction: column;
  z-index: 20;
  overflow: hidden;
}
.canvas-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.canvas-drawer-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--ink-3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.canvas-drawer-close {
  background: none;
  border: none;
  color: var(--ink-3);
  cursor: pointer;
  font-size: 12px;
  padding: 0 2px;
  line-height: 1;
}
.canvas-drawer-close:hover { color: var(--ink-1); }
.canvas-drawer-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Slide transition */
.drawer-enter-active,
.drawer-leave-active { transition: transform 0.2s ease; }
.drawer-enter-from,
.drawer-leave-to    { transform: translateX(-100%); }

/* ── Canvas thumbnails (shared) ────────────────────────────── */
.canvas-index-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
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
