<template>
  <div class="viewer-page">

    <!-- Left: canvas index -->
    <CanvasIndex
      :canvases="canvases"
      :current-index="pageIndex"
      @select="goToPage"
    />

    <!-- Center: viewer + controls -->
    <div class="viewer-center">
      <div class="vol-info-bar" v-if="volume">
        <div class="vol-info-title">
          {{ volume.title }}
          <span class="vol-info-ja">{{ volume.title_local }}</span>
        </div>
        <div class="vol-info-meta">
          {{ [volume.institution, volume.date_label, volume.genre].filter(Boolean).join(' · ') }}
        </div>
      </div>

      <div class="viewer-wrap">
        <div v-if="!volume" class="viewer-placeholder">
          <div class="placeholder-icon">📖</div>
          <p>Volume not found</p>
        </div>
        <OsdViewer
          v-else
          ref="osdViewer"
          :canvas="currentCanvas"
          :annotations="annotations"
          @regionDrawn="onRegionDrawn"
        />
      </div>

      <div class="viewer-footer" v-if="volume">
        <div class="page-nav">
          <button class="nav-btn" :disabled="pageIndex === 0" @click="goToPage(pageIndex - 1)">←</button>
          <span class="page-indicator">
            {{ pageIndex + 1 }} / {{ canvases.length }}
            <span v-if="currentCanvas"> — {{ currentCanvas.label }}</span>
          </span>
          <button class="nav-btn" :disabled="pageIndex >= canvases.length - 1" @click="goToPage(pageIndex + 1)">→</button>
        </div>
        <div class="viewer-hint">
          {{ auth.user ? 'Click "+ Add annotation" then draw a region on the image' : 'Sign in with ORCID to annotate' }}
        </div>
        <button
          v-if="auth.user"
          class="draw-btn"
          :class="{ active: drawing }"
          @click="toggleDrawing"
        >+ Add annotation</button>
      </div>
    </div>

    <!-- Right: annotation panel -->
    <AnnotationPanel
      :user="auth.user"
      :volume="volume"
      :annotations="annotations"
      :pending-region="pendingRegion"
      @annotationsChanged="reloadAnnotations"
      @clearPendingRegion="pendingRegion = null"
    />

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore }    from '../stores/auth.js'
import { useVolumesStore } from '../stores/volumes.js'
import { getVolumeAnnotations, fetchManifest } from '../api/index.js'
import OsdViewer      from '../components/OsdViewer.vue'
import CanvasIndex    from '../components/CanvasIndex.vue'
import AnnotationPanel from '../components/AnnotationPanel.vue'

const route   = useRoute()
const auth    = useAuthStore()
const volStore = useVolumesStore()

const canvases      = ref([])
const pageIndex     = ref(0)
const annotations   = ref([])
const pendingRegion = ref(null)
const drawing       = ref(false)
const osdViewer     = ref(null)

const volume = computed(() => volStore.bySlug(route.params.slug))
const currentCanvas = computed(() => canvases.value[pageIndex.value] ?? null)

onMounted(async () => {
  await volStore.fetchVolumes()
  if (volume.value) await loadManifest()
})

watch(volume, async (v) => { if (v) await loadManifest() })

async function loadManifest() {
  try {
    const manifest  = await fetchManifest(volume.value.manifest_url)
    canvases.value  = parseCanvases(manifest)
    annotations.value = await getVolumeAnnotations(volume.value.manifest_url)
  } catch (e) {
    console.error('Manifest load failed:', e)
  }
}

async function reloadAnnotations() {
  if (volume.value) {
    annotations.value = await getVolumeAnnotations(volume.value.manifest_url)
  }
}

function goToPage(index) {
  pageIndex.value = Math.max(0, Math.min(index, canvases.value.length - 1))
  drawing.value = false
  if (osdViewer.value) osdViewer.value.setDrawing(false)
}

function toggleDrawing() {
  drawing.value = !drawing.value
  if (osdViewer.value) osdViewer.value.setDrawing(drawing.value)
}

function onRegionDrawn(region) {
  drawing.value   = false
  pendingRegion.value = region
}

// ── Manifest parsing ──────────────────────────────────────────────────────────

function labelValue(label) {
  if (!label) return ''
  if (typeof label === 'string') return label
  if (Array.isArray(label)) return label[0] ?? ''
  for (const lang of ['none', 'en', 'ja']) {
    if (label[lang]) { const v = label[lang]; return Array.isArray(v) ? v[0] : v }
  }
  const first = Object.values(label)[0]
  return Array.isArray(first) ? first[0] : (first ?? '')
}

function serviceId(service) {
  if (!service) return null
  if (Array.isArray(service)) service = service[0]
  return service?.id ?? service?.['@id'] ?? null
}

function thumbnailUrl(svcId) {
  return svcId ? `${svcId.replace(/\/$/, '')}/full/80,/0/default.jpg` : null
}

function tileSource(svcId) {
  return svcId ? { type: 'image', url: `${svcId.replace(/\/$/, '')}/info.json` } : null
}

function parseCanvases(manifest) {
  const ctx  = manifest['@context'] ?? ''
  const isV3 = ctx.includes('presentation/3') || manifest.type === 'Manifest'

  const raw = isV3
    ? (manifest.items ?? [])
    : (manifest.sequences?.[0]?.canvases ?? [])

  return raw.map(c => {
    const id    = c.id ?? c['@id'] ?? ''
    const label = labelValue(c.label)

    let svcId = null
    if (isV3) {
      const body = c.items?.[0]?.items?.[0]?.body
      const b    = Array.isArray(body) ? body[0] : body
      svcId = serviceId(b?.service)
    } else {
      const img  = c.images?.[0]
      svcId = serviceId(img?.resource?.service) ?? serviceId(img?.resource?.['@id'])
    }

    return { id, label, thumbnail: thumbnailUrl(svcId), tileSource: tileSource(svcId) }
  })
}
</script>

<style scoped>
.viewer-page {
  display: grid;
  grid-template-columns: 120px 1fr var(--panel-w, 320px);
  height: calc(100vh - var(--topbar-h));
  overflow: hidden;
}
.viewer-center {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}
.vol-info-bar {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.vol-info-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-1);
}
.vol-info-ja {
  font-weight: 400;
  color: var(--ink-3);
  margin-left: 8px;
}
.vol-info-meta {
  font-size: 11px;
  color: var(--ink-3);
  margin-top: 2px;
}
.viewer-wrap {
  flex: 1;
  overflow: hidden;
  position: relative;
}
.viewer-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ink-3);
}
.placeholder-icon { font-size: 3rem; opacity: 0.2; margin-bottom: 12px; }
.viewer-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  flex-wrap: wrap;
}
.page-nav { display: flex; align-items: center; gap: 8px; }
.nav-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--ink-2);
  border-radius: 3px;
  padding: 3px 10px;
  cursor: pointer;
  font-size: 14px;
}
.nav-btn:disabled { opacity: 0.3; cursor: default; }
.page-indicator { font-size: 12px; color: var(--ink-3); white-space: nowrap; }
.viewer-hint { font-size: 11px; color: var(--ink-3); flex: 1; }
.draw-btn {
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--border);
  background: var(--sidebar-bg);
  color: var(--ink-2);
  cursor: pointer;
  transition: background 0.15s;
}
.draw-btn.active {
  background: var(--vermillion);
  color: #fff;
  border-color: var(--vermillion);
}
</style>
