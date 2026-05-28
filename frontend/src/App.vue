<template>
  <AppHeader />
  <RouterView />
</template>

<script setup>
import { onMounted } from 'vue'
import AppHeader from './components/AppHeader.vue'
import { useAuthStore } from './stores/auth.js'

const auth = useAuthStore()
onMounted(() => auth.fetchUser())
</script>
