import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loaded = ref(false)

  async function fetchUser() {
    const res = await fetch('/auth/me')
    const data = await res.json()
    user.value = data.user
    loaded.value = true
  }

  function login()  { window.location.href = '/auth/login' }
  function logout() { window.location.href = '/auth/logout' }

  return { user, loaded, fetchUser, login, logout }
})
