<template>
  <main class="collection-page">
    <div class="collection-toolbar">
      <div class="collection-toolbar-left">
        <h2 class="collection-heading">Collection</h2>
        <span class="collection-count">{{ filtered.length }} items</span>
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

    <div v-if="loading" class="collection-loading">Loading…</div>
    <div v-else-if="!filtered.length" class="collection-empty">No items match your search.</div>
    <div v-else class="collection-grid">
      <VolumeCard
        v-for="item in filtered"
        :key="item._key"
        :volume="item"
        @click="openItem(item)"
      />
    </div>
  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCollections } from '../api/index.js'
import VolumeCard from '../components/VolumeCard.vue'
import { useVolumesStore } from '../stores/volumes.js'

const store  = useVolumesStore()
const router = useRouter()
const query             = ref('')
const filterInstitution = ref('')
const loading           = ref(true)
const collections       = ref([])

onMounted(async () => {
  loading.value = true
  // Fetch all volumes + collections in parallel
  await Promise.all([
    store.fetchVolumes(),
    fetchCollections().then(c => { collections.value = c }),
  ])
  loading.value = false
})

// Normalize collections into card-compatible objects
const collectionItems = computed(() =>
  collections.value.map(c => ({
    _key:            `coll-${c.slug}`,
    slug:            c.slug,
    title:           c.title,
    title_local:     c.title_local ?? null,
    institution:     c.institution,
    thumbnail:       c.thumbnail ?? null,
    date_label:      null,
    isCollection:    true,
    volumeCount:     c.volume_count,
    annotationCount: c.annotation_count ?? 0,
    firstVolumeSlug: c.first_volume_slug,
  }))
)

// Normalize standalone volumes (exclude those belonging to a collection)
const volumeItems = computed(() =>
  store.volumes
    .filter(v => !v.collection_id)
    .map(v => ({
      ...v,
      _key: `vol-${v.slug}`,
      isCollection: false,
      annotationCount: v.annotation_count ?? 0,
    }))
)

// Merge and sort by institution then title
const allItems = computed(() => {
  const combined = [...collectionItems.value, ...volumeItems.value]
  return combined.sort((a, b) =>
    a.institution.localeCompare(b.institution) || a.title.localeCompare(b.title)
  )
})

const institutions = computed(() =>
  [...new Set(allItems.value.map(v => v.institution))].sort()
)

const filtered = computed(() => {
  const q    = query.value.toLowerCase()
  const inst = filterInstitution.value
  return allItems.value.filter(v => {
    const matchQ = !q || v.title.toLowerCase().includes(q) ||
                   (v.title_local ?? '').includes(q) ||
                   v.slug.includes(q)
    const matchI = !inst || v.institution === inst
    return matchQ && matchI
  })
})

function openItem(item) {
  if (item.isCollection) {
    router.push(`/viewer/${item.firstVolumeSlug}`)
  } else {
    router.push(`/viewer/${item.slug}`)
  }
}
</script>

<style scoped>
.collection-page {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - var(--topbar-h));
  background: var(--bg);
  padding: 40px 48px;
}
.collection-toolbar {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}
.collection-toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}
.collection-heading {
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 600;
  color: var(--text-1);
  margin: 0;
}
.collection-count {
  font-size: 15px;
  color: var(--text-3);
}
.collection-toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
}
.collection-search {
  background: var(--bg-elev);
  border: 1px solid oklch(38% 0.014 264 / 60%);
  color: oklch(90% 0.006 264);
  padding: 11px 16px;
  border-radius: 8px;
  font-size: 15px;
  width: 260px;
}
.collection-search::placeholder { color: var(--text-3); }
.collection-search:focus { outline: none; border-color: var(--vermillion); }
.filter-select {
  background: var(--bg-elev);
  border: 1px solid oklch(38% 0.014 264 / 60%);
  color: oklch(80% 0.008 264);
  padding: 11px 14px;
  border-radius: 8px;
  font-size: 15px;
  width: auto;
}
.filter-select:focus { outline: none; border-color: var(--vermillion); }
.collection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 24px;
}
.collection-loading,
.collection-empty {
  color: var(--text-3);
  font-size: 16px;
  padding: 64px;
  text-align: center;
}

@media (max-width: 720px) {
  .collection-page { padding: 28px 20px; }
  .collection-toolbar-right { width: 100%; }
  .collection-search { flex: 1; width: auto; }
}
</style>
