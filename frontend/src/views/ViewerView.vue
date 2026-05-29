<template>
  <div class="viewer-page">

    <!-- Left: canvas index -->
    <CanvasIndex
      :canvases="canvases"
      :current-index="pageIndex"
      :collection-volumes="collectionVolumes"
      :current-volume-slug="route.params.slug"
      @select="goToPage"
      @selectVolume="goToVolume"
    />

    <!-- Center: viewer + controls -->
    <div class="viewer-center">
      <div class="vol-info-bar" v-if="volume">
        <div class="vol-info-text">
          <div class="vol-info-title">
            {{ volume.title }}
            <span class="vol-info-ja">{{ volume.title_local }}</span>
          </div>
          <div class="vol-info-meta">
            {{ [volume.institution, volume.date_label, volume.genre].filter(Boolean).join(' · ') }}
          </div>
        </div>
        <button class="gallery-btn" @click="galleryOpen = true" title="Browse all pages">⊞ Gallery</button>
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
          :activeAnnotationId="activeAnnotationId"
          @regionDrawn="onRegionDrawn"
          @annotationClicked="onAnnotationClicked"
        />
        <template v-if="volume && canvases.length > 1">
          <button class="viewer-nav-btn viewer-nav-left"
            :disabled="isRtl ? pageIndex >= canvases.length - 1 : pageIndex === 0"
            @click="goToPage(isRtl ? pageIndex + 1 : pageIndex - 1)"
            aria-label="Previous page">&#8592;</button>
          <button class="viewer-nav-btn viewer-nav-right"
            :disabled="isRtl ? pageIndex === 0 : pageIndex >= canvases.length - 1"
            @click="goToPage(isRtl ? pageIndex - 1 : pageIndex + 1)"
            aria-label="Next page">&#8594;</button>
        </template>
      </div>

      <div class="viewer-footer" v-if="volume">
        <div class="page-nav">
          <button class="nav-btn"
            :disabled="isRtl ? pageIndex >= canvases.length - 1 : pageIndex === 0"
            @click="goToPage(isRtl ? pageIndex + 1 : pageIndex - 1)">←</button>
          <span class="page-indicator">
            {{ pageIndex + 1 }} / {{ canvases.length }}
            <span v-if="currentCanvas"> — {{ currentCanvas.label }}</span>
          </span>
          <button class="nav-btn"
            :disabled="isRtl ? pageIndex === 0 : pageIndex >= canvases.length - 1"
            @click="goToPage(isRtl ? pageIndex - 1 : pageIndex + 1)">→</button>
        </div>
      </div>
    </div>

    <!-- Right: annotation panel -->
    <AnnotationPanel
      :user="auth.user"
      :volume="volume"
      :annotations="annotations"
      :pending-region="pendingRegion"
      :activeAnnotationId="activeAnnotationId"
      :collectionAnnotations="collectionAnnotations"
      :currentVolumeSlug="route.params.slug"
      @annotationsChanged="reloadAnnotations"
      @clearPendingRegion="pendingRegion = null"
      @startDrawing="toggleDrawing"
      @annotationSelected="onAnnotationSelected"
    />

    <!-- Gallery overlay -->
    <Teleport to="body">
      <div v-if="galleryOpen" class="gallery-overlay" @click.self="galleryOpen = false">
        <div class="gallery-modal">
          <div class="gallery-modal-header">
            <span class="gallery-modal-title">{{ volume?.title }} — All pages</span>
            <button class="gallery-modal-close" @click="galleryOpen = false">✕</button>
          </div>
          <div class="gallery-grid">
            <div
              v-for="(canvas, i) in canvases"
              :key="canvas.id"
              class="gallery-item"
              :class="{ active: i === pageIndex }"
              @click="goToPage(i); galleryOpen = false"
            >
              <div class="gallery-item-img">
                <img v-if="canvas.thumbnail" :src="canvas.thumbnail" :alt="canvas.label" loading="lazy" />
                <span v-else class="gallery-item-num">{{ i + 1 }}</span>
              </div>
              <div class="gallery-item-label">{{ canvas.label || i + 1 }}</div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore }    from '../stores/auth.js'
import { useVolumesStore } from '../stores/volumes.js'
import { getVolumeAnnotations, fetchManifest, fetchCollection, fetchCollectionAnnotations } from '../api/index.js'
import OsdViewer      from '../components/OsdViewer.vue'
import CanvasIndex    from '../components/CanvasIndex.vue'
import AnnotationPanel from '../components/AnnotationPanel.vue'

const route   = useRoute()
const router  = useRouter()
const auth    = useAuthStore()
const volStore = useVolumesStore()

const canvases              = ref([])
const pageIndex             = ref(0)
const annotations           = ref([])
const pendingRegion         = ref(null)
const drawing               = ref(false)
const osdViewer             = ref(null)
const galleryOpen           = ref(false)
const activeAnnotationId    = ref(null)
const viewingDirection      = ref('left-to-right')
const collectionVolumes     = ref(null)   // null = standalone volume
const collectionAnnotations = ref(null)   // null = standalone volume

const isRtl = computed(() => viewingDirection.value === 'right-to-left')

const volume = computed(() => volStore.bySlug(route.params.slug))
const currentCanvas = computed(() => canvases.value[pageIndex.value] ?? null)

onMounted(async () => {
  await volStore.fetchVolumes()
  if (volume.value) await loadManifest()
})

watch(volume, async (v) => { if (v) await loadManifest() })

async function loadManifest() {
  // Reset page position but do NOT clear collectionVolumes — keeping the volume
  // list populated prevents CanvasIndex from toggling in/out of collection mode,
  // which would cause OSD's container to resize and miscalculate its initial zoom.
  pageIndex.value = 0

  try {
    const manifest         = await fetchManifest(volume.value.manifest_url)
    canvases.value         = parseCanvases(manifest)
    viewingDirection.value = manifest.viewingDirection
      ?? manifest.sequences?.[0]?.viewingDirection
      ?? 'left-to-right'
    annotations.value = await getVolumeAnnotations(volume.value.manifest_url)
  } catch (e) {
    console.error('Manifest load failed:', e)
  }

  // If this volume belongs to a collection, refresh collection context.
  // If it's standalone, clear any leftover collection state from a previous volume.
  if (volume.value.collection_id) {
    const coll = volume.value.collection
    if (coll?.slug) await loadCollection(coll.slug)
  } else {
    collectionVolumes.value     = null
    collectionAnnotations.value = null
  }
}

async function loadCollection(collSlug) {
  try {
    const [collData, collAnnos] = await Promise.all([
      fetchCollection(collSlug),
      fetchCollectionAnnotations(collSlug),
    ])
    collectionVolumes.value     = collData.volumes   // [{slug, title, volume_number, volume_label, ...}]
    collectionAnnotations.value = collAnnos          // [{volume_slug, volume_title, volume_number, volume_label, annotations[]}]
  } catch (e) {
    console.error('Collection load failed:', e)
  }
}

async function goToVolume(slug) {
  await router.push(`/viewer/${slug}`)
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
  drawing.value       = false
  pendingRegion.value = region
}

function onAnnotationClicked(id) {
  activeAnnotationId.value = id
}

async function onAnnotationSelected(annotation) {
  // Cross-volume navigation (collection mode)
  if (annotation.volume_slug && annotation.volume_slug !== route.params.slug) {
    await goToVolume(annotation.volume_slug)
    await new Promise(r => setTimeout(r, 800))
    activeAnnotationId.value = annotation.id
    if (osdViewer.value) osdViewer.value.selectAnnotation(annotation.id)
    return
  }

  activeAnnotationId.value = annotation.id
  const targetCanvasIndex = canvases.value.findIndex(c => c.id === annotation.canvas_id)
  if (targetCanvasIndex === -1) return

  if (targetCanvasIndex !== pageIndex.value) {
    goToPage(targetCanvasIndex)
    // Wait for canvas to load and annotations to render before selecting
    await new Promise(r => setTimeout(r, 600))
  }

  if (osdViewer.value) osdViewer.value.selectAnnotation(annotation.id)
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
  return svcId ? `${svcId.replace(/\/$/, '')}/info.json` : null
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
  /* No overflow:hidden here — the canvas drawer slides out of the sidebar
     column as position:absolute and needs to be visible over the viewer.
     Each panel manages its own overflow internally. */
}
.viewer-center {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg);
}
.vol-info-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.vol-info-text { min-width: 0; }
.vol-info-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
.viewer-nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  background: rgba(0,0,0,0.45);
  color: #fff;
  border: none;
  border-radius: 4px;
  width: 36px;
  height: 64px;
  font-size: 20px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.viewer-wrap:hover .viewer-nav-btn:not(:disabled) { opacity: 1; }
.viewer-nav-btn:disabled { cursor: default; }
.viewer-nav-left  { left:  8px; }
.viewer-nav-right { right: 8px; }
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
  justify-content: center;
  padding: 8px 14px;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
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

.gallery-btn {
  padding: 5px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--border);
  background: var(--sidebar-bg);
  color: var(--ink-2);
  cursor: pointer;
  flex-shrink: 0;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.gallery-btn:hover { background: var(--border); color: var(--ink-1); }

/* Gallery overlay */
.gallery-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.gallery-modal {
  background: var(--sidebar-bg);
  border-radius: 8px;
  border: 1px solid var(--border);
  width: min(90vw, 960px);
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.gallery-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.gallery-modal-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-1);
}
.gallery-modal-close {
  background: none;
  border: none;
  color: var(--ink-3);
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
}
.gallery-modal-close:hover { color: var(--ink-1); }
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  grid-auto-rows: 200px;
  gap: 10px;
  padding: 16px;
  overflow-y: auto;
}
.gallery-item {
  cursor: pointer;
  border-radius: 4px;
  border: 2px solid transparent;
  transition: border-color 0.15s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.gallery-item:hover    { border-color: rgba(255,255,255,0.2); }
.gallery-item.active   { border-color: var(--vermillion); }
.gallery-item-img {
  flex: 1;
  min-height: 0;
  background: #111;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gallery-item-img img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.gallery-item-num { font-size: 12px; color: var(--ink-3); }
.gallery-item-label {
  font-size: 10px;
  color: var(--ink-3);
  text-align: center;
  padding: 4px 4px 6px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
