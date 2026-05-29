<template>
  <div class="osd-wrap">
    <div ref="osdEl" class="osd-container"></div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  canvas:              Object,
  readonly:            Boolean,
  annotations:         Array,
  activeAnnotationId:  { type: [Number, String], default: null },
})

const emit = defineEmits(['regionDrawn', 'annotationClicked'])

const osdEl  = ref(null)
let osd  = null
let anno = null

watch(() => props.canvas, (canvas) => {
  if (!canvas) return
  initViewer(canvas)
}, { immediate: true })

watch(() => props.annotations, () => {
  renderSavedAnnotations()
}, { deep: true })

watch(() => props.activeAnnotationId, (id) => {
  if (anno && id != null) anno.selectAnnotation(`#anno-${id}`)
})

function initViewer(canvas) {
  if (osd) {
    osd.destroy()
    osd  = null
    anno = null
  }
  if (!osdEl.value) return

  osd = window.OpenSeadragon({
    element:              osdEl.value,
    prefixUrl:            'https://cdn.jsdelivr.net/npm/openseadragon@4.1.0/build/openseadragon/images/',
    animationTime:        0.3,
    blendTime:            0.1,
    constrainDuringPan:   true,
    maxZoomPixelRatio:    4,
    minZoomLevel:         0.5,
    visibilityRatio:      1,
    zoomPerScroll:        1.3,
    showNavigationControl: true,
    navigationControlAnchor: window.OpenSeadragon.ControlAnchor.TOP_RIGHT,
    showNavigator: false,
  })

  anno = window.OpenSeadragon.Annotorious(osd, {
    readOnly: props.readonly,
    widgets:  [],
  })

  anno.on('createSelection', selection => {
    anno.setDrawingEnabled(false)
    const xywh = selectionToXywh(selection)
    emit('regionDrawn', { canvasId: canvas.id, canvasLabel: canvas.label, xywh })
    anno.cancelSelected()
  })

  // clickAnnotation fires when the user clicks an existing annotation shape.
  // The id in the event is '#anno-{db-id}' — strip the prefix to get the db id.
  anno.on('clickAnnotation', (a) => {
    const dbId = (a?.id ?? '').replace(/^#anno-/, '')
    if (!dbId) return
    emit('annotationClicked', dbId)
    // Dismiss Annotorious editor popup — editing lives in the sidebar
    setTimeout(() => anno?.cancelSelected(), 0)
  })

  osd.addHandler('open', () => {
    osd.viewport.goHome(true)   // reset zoom/pan to fit-page on every new tile source
    renderSavedAnnotations()
  })

  const ts = canvas.tileSource
  if (ts) osd.open(ts)
}

function selectionToXywh(selection) {
  const frag = selection?.target?.selector?.value ?? ''
  const m = frag.match(/xywh=pixel:([\d.]+),([\d.]+),([\d.]+),([\d.]+)/)
  if (m) return `pixel:${m[1]},${m[2]},${m[3]},${m[4]}`
  return frag.replace('xywh=', '')
}

function renderSavedAnnotations() {
  if (!anno || !props.canvas) return
  anno.clearAnnotations()
  const forPage = (props.annotations ?? []).filter(a => a.canvas_id === props.canvas.id)
  forPage.forEach((a, i) => {
    anno.addAnnotation({
      '@context': 'http://www.w3.org/ns/anno.jsonld',
      id:         `#anno-${a.id}`,
      type:       'Annotation',
      motivation: 'supplementing',
      body:       [{ type: 'TextualBody', value: `${i + 1}. ${a.mark_type}` }],
      target: {
        source:   props.canvas.id,
        selector: {
          type: 'FragmentSelector',
          conformsTo: 'http://www.w3.org/TR/media-frags/',
          value: `xywh=${a.region_xywh}`,
        },
      },
    })
  })
}

function setDrawing(enabled) {
  if (anno) anno.setDrawingEnabled(enabled)
}

function selectAnnotation(id) {
  if (anno) anno.selectAnnotation(`#anno-${id}`)
}

defineExpose({ setDrawing, selectAnnotation })

onUnmounted(() => {
  if (osd) { osd.destroy(); osd = null; anno = null }
})
</script>

<style scoped>
.osd-wrap {
  width: 100%;
  height: 100%;
  background: #111;
}
.osd-container {
  width: 100%;
  height: 100%;
}
:deep(.openseadragon-canvas) {
  outline: none;
}
</style>
