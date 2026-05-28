<template>
  <main class="collection-page">
    <div class="collection-toolbar">
      <div class="collection-toolbar-left">
        <h2 class="collection-heading">Collection</h2>
        <span class="collection-count">{{ filtered.length }} volumes</span>
      </div>
      <div class="collection-toolbar-right">
        <select v-model="filterInstitution" class="filter-select">
          <option value="">All institutions</option>
          <option v-for="inst in institutions" :key="inst" :value="inst">{{ inst }}</option>
        </select>
        <input
          v-model="query"
          type="search"
          class="collection-search"
          placeholder="Search titles…"
          autocomplete="off"
        />
      </div>
    </div>

    <div v-if="store.loading" class="collection-loading">Loading…</div>
    <div v-else-if="!filtered.length" class="collection-empty">No volumes match your search.</div>
    <div v-else class="collection-grid">
      <VolumeCard
        v-for="vol in filtered"
        :key="vol.slug"
        :volume="vol"
        @click="openViewer(vol.slug)"
      />
    </div>
  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useVolumesStore } from '../stores/volumes.js'
import VolumeCard from '../components/VolumeCard.vue'

const store  = useVolumesStore()
const router = useRouter()
const query             = ref('')
const filterInstitution = ref('')

onMounted(() => store.fetchVolumes())

const institutions = computed(() =>
  [...new Set(store.volumes.map(v => v.institution))].sort()
)

const filtered = computed(() => {
  const q    = query.value.toLowerCase()
  const inst = filterInstitution.value
  return store.volumes.filter(v => {
    const matchQ = !q || v.title.toLowerCase().includes(q) ||
                   (v.title_local ?? '').includes(q) ||
                   v.slug.includes(q)
    const matchI = !inst || v.institution === inst
    return matchQ && matchI
  })
})

function openViewer(slug) {
  router.push(`/viewer/${slug}`)
}
</script>

<style scoped>
.collection-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - var(--topbar-h));
  background: var(--bg);
  padding: 24px 32px;
}
.collection-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.collection-toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.collection-heading {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ink-1);
  margin: 0;
}
.collection-count {
  font-size: 12px;
  color: var(--ink-3);
}
.collection-toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.collection-search {
  background: var(--sidebar-bg);
  border: 1px solid var(--border);
  color: var(--ink-1);
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
  width: 220px;
}
.collection-search:focus { outline: 1px solid var(--vermillion); }
.filter-select {
  background: var(--sidebar-bg);
  border: 1px solid var(--border);
  color: var(--ink-2);
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 13px;
}
.collection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}
.collection-loading,
.collection-empty {
  color: var(--ink-3);
  font-size: 14px;
  padding: 48px;
  text-align: center;
}
</style>
