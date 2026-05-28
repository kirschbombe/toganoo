import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useVolumesStore = defineStore('volumes', () => {
  const volumes = ref([])
  const loading = ref(false)

  async function fetchVolumes() {
    if (volumes.value.length) return  // already loaded
    loading.value = true
    try {
      const res = await fetch('/api/volumes/')
      volumes.value = await res.json()
    } finally {
      loading.value = false
    }
  }

  function bySlug(slug) {
    return volumes.value.find(v => v.slug === slug) ?? null
  }

  return { volumes, loading, fetchVolumes, bySlug }
})
