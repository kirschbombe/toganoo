<template>
  <div class="vol-card" role="button" tabindex="0" @keydown.enter="$emit('click')">
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
        <span v-if="volume.institution !== 'UCLA Library'" class="vol-card-inst">{{ volume.institution }}</span>
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
  background: var(--sidebar-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.15s;
}
.vol-card:hover {
  border-color: var(--vermillion);
  transform: translateY(-2px);
}
.vol-card-thumb {
  width: 100%;
  aspect-ratio: 3/4;
  background: #1a1a1c;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
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
  padding: 8px 10px;
}
.vol-card-title {
  font-size: 11px;
  font-weight: 500;
  color: var(--ink-1);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.vol-card-ja {
  font-size: 11px;
  color: var(--ink-3);
  margin-top: 2px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.vol-card-sub {
  font-size: 10px;
  color: var(--ink-3);
  margin-top: 4px;
  display: flex;
  gap: 6px;
}
.vol-card-inst {
  background: var(--gold);
  color: #222;
  border-radius: 2px;
  padding: 0 4px;
  font-size: 9px;
}
</style>
