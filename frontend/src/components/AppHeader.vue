<template>
  <header id="topbar">
    <div id="topbar-left">
      <RouterLink to="/" class="app-title-link">
        <span id="app-title">Toganoo Provenance</span>
      </RouterLink>
      <span id="app-subtitle">UCLA Library · Toganoo Collection of Esoteric Buddhism</span>
    </div>
    <nav id="topbar-right">
      <RouterLink to="/collection" class="nav-link">← Collection</RouterLink>
      <RouterLink v-if="auth.user?.is_admin" to="/admin" class="nav-link">Admin</RouterLink>
      <div id="auth-status">
        <template v-if="auth.user">
          <span class="user-name">{{ auth.user.name }}</span>
          <button class="auth-btn" @click="auth.logout()">Sign out</button>
        </template>
        <template v-else>
          <button class="auth-btn" @click="auth.login()">
            <span class="orcid-dot">iD</span>Sign in with ORCID
          </button>
        </template>
      </div>
    </nav>
  </header>
</template>

<script setup>
import { useAuthStore } from '../stores/auth.js'
const auth = useAuthStore()
</script>

<style scoped>
.app-title-link {
  text-decoration: none;
  color: inherit;
}
.nav-link {
  color: var(--ink-3);
  text-decoration: none;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 4px;
  transition: background 0.15s;
}
.nav-link:hover,
.nav-link.router-link-active {
  background: rgba(255,255,255,0.08);
  color: var(--ink-1);
}
</style>
