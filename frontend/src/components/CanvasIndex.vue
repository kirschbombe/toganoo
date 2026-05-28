<template>
  <aside class="canvas-index">
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
  </aside>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  canvases:     { type: Array, default: () => [] },
  currentIndex: { type: Number, default: 0 },
})
defineEmits(['select'])

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
  // Re-observe after canvases load
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
