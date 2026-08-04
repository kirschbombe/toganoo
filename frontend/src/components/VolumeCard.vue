<template>
  <div class="vol-card" role="button" tabindex="0" @click="$emit('click')" @keydown.enter="$emit('click')">
    <div class="vol-card-thumb">
      <img
        v-if="volume.thumbnail"
        :src="volume.thumbnail"
        :alt="volume.title"
        loading="lazy"
        @error="imgError = true"
        :class="{ hidden: imgError }"
      />
      <div v-if="!volume.thumbnail || imgError" class="vol-card-thumb-placeholder">📖</div>
    </div>
    <div class="vol-card-meta">
      <div class="vol-card-title">{{ volume.title }}</div>
      <div v-if="volume.title_local" class="vol-card-ja">{{ volume.title_local }}</div>
      <div class="vol-card-sub">
        <span v-if="volume.date_label">{{ volume.date_label }}</span>
        <span v-if="volume.isCollection" class="vol-card-set-badge">{{ volume.volumeCount }} vols.</span>
        <span v-if="volume.institution !== 'UCLA Library'" class="vol-card-inst">{{ volume.institution }}</span>
        <span
          v-if="volume.annotationCount"
          class="vol-card-anno-count"
          :title="`${volume.annotationCount} annotation(s)`"
        >{{ volume.annotationCount }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
defineProps({ volume: Object })
defineEmits(['click'])
const imgError = ref(false)
</script>

<style scoped>
.vol-card {
  background: var(--bg-elev);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.15s;
}
.vol-card:hover {
  border-color: var(--vermillion);
  transform: translateY(-2px);
}
.vol-card-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  background: var(--bg-sunken);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
/* Sits at the end of the meta row rather than over the thumbnail, where it
   competed with the manuscript image. Circular for one or two digits, easing
   into a pill beyond that. */
.vol-card-anno-count {
  margin-left: auto;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--vermillion);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.vol-card-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.vol-card-thumb img.hidden { display: none; }
.vol-card-thumb-placeholder {
  font-size: 2rem;
  opacity: 0.2;
}
.vol-card-meta {
  padding: 16px;
}
.vol-card-title {
  font-size: 15px;
  font-weight: 600;
  color: oklch(92% 0.006 264);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.vol-card-ja {
  font-family: var(--font-serif);
  font-size: 15px;
  color: oklch(65% 0.008 264);
  margin-top: 4px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.vol-card-sub {
  font-size: 12px;
  color: var(--text-3);
  margin-top: 10px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.vol-card-inst {
  background: var(--gold);
  color: oklch(22% 0.03 83);
  border-radius: 5px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
}
/* Gold rather than vermillion so the volume count and the annotation count
   don't read as the same kind of signal */
.vol-card-set-badge {
  background: var(--gold);
  color: oklch(22% 0.03 83);
  border-radius: 5px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
}
</style>
