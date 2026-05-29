<template>
  <aside class="canvas-index">
    <!-- Collection volume list header -->
    <template v-if="collectionVolumes">
      <div class="canvas-index-header">
        <span class="canvas-index-label">Volumes ({{ collectionVolumes.length }})</span>
      </div>
      <div class="canvas-index-list" ref="listEl">
        <template v-for="vol in collectionVolumes" :key="vol.slug">
          <!-- Volume header row -->
          <div
            class="vol-header"
            :class="{ active: vol.slug === currentVolumeSlug }"
            @click="vol.slug !== currentVolumeSlug && $emit('selectVolume', vol.slug)"
          >
            <span class="vol-header-caret">{{ vol.slug === currentVolumeSlug ? '▼' : '▶' }}</span>
            <span class="vol-header-label">
              <span class="vol-num">Vol. {{ vol.volume_number }}</span>
              <span class="vol-title">{{ vol.volume_label || vol.title }}</span>
            </span>
          </div>

          <!-- Canvas thumbnails — only for the active volume -->
          <div v-if="vol.slug === currentVolumeSlug" class="vol-canvases">
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
      </div>
    </template>

    <!-- Single-volume mode (no collection) -->
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
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  canvases:          { type: Array,  default: () => [] },
  currentIndex:      { type: Number, default: 0 },
  collectionVolumes: { type: Array,  default: null },
  currentVolumeSlug: { type: String, default: null },
})
defineEmits(['select', 'selectVolume'])

const listEl  = ref(null)
const visible = ref(new Set())
let observer  = null

function setupObserver() {
  if (observer) observer.disconnect()
  visible.value = new Set()

  observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const i = Number(e.target.dataset.index)
        visible.value = new Set([...visible.value, i])
      }
    })
  }, { root: listEl.value, rootMargin: '100px' })

  listEl.value?.querySelectorAll('.canvas-thumb-img-wrap').forEach(el => observer.observe(el))
}

watch(() => props.canvases, () => {
  setTimeout(setupObserver, 50)
}, { immediate: false })

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
.canvas-index-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* ── Volume headers (collection mode) ─────────────────────── */
.vol-header {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.12s;
  flex-shrink: 0;
}
.vol-header:hover:not(.active) { background: rgba(255,255,255,0.04); }
.vol-header.active {
  background: rgba(180,40,30,0.07);
  cursor: default;
}
.vol-header-caret {
  font-size: 9px;
  color: var(--ink-3);
  margin-top: 2px;
  flex-shrink: 0;
}
.vol-header-label {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.vol-num {
  font-size: 10px;
  color: var(--ink-3);
  font-weight: 600;
}
.vol-title {
  font-size: 11px;
  color: var(--ink-2);
  line-height: 1.3;
  word-break: break-word;
}
.vol-header.active .vol-title { color: var(--ink-1); }

/* ── Canvas thumbnails ─────────────────────────────────────── */
.vol-canvases {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
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
.canvas-thumb-img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.canvas-thumb-placeholder {
  font-size: 11px;
  color: var(--ink-3);
}
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
