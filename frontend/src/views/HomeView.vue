<template>
  <main class="home">
    <div class="home-content">
      <h1 class="home-title">Toganoo Collection<br>Provenance Annotation Tool</h1>
      <p class="home-subtitle">
        UCLA Library · Toganoo Collection of Esoteric Buddhism
      </p>
      <p class="home-desc">
        A collaborative workspace for annotating provenance marks — collector's seals,
        stamps, inscriptions, and labels — in digitized Japanese Buddhist manuscripts.
        Annotations are exportable as TEI XML and Linked Art JSON-LD.
      </p>
      <div class="home-actions">
        <RouterLink to="/collection" class="home-btn primary">Browse the Collection</RouterLink>
        <button v-if="!auth.user" class="home-btn secondary" @click="auth.login()">
          <span class="orcid-dot">iD</span>Sign in with ORCID to annotate
        </button>
        <span v-else class="home-signed-in">Signed in as {{ auth.user.name }}</span>
      </div>
    </div>
  </main>
</template>

<script setup>
import { useAuthStore } from '../stores/auth.js'
const auth = useAuthStore()
</script>

<style scoped>
.home {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--topbar-h));
  padding: 48px 24px;
  background: var(--bg);
}
.home-content {
  max-width: 600px;
  text-align: center;
}
.home-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--ink-1);
  line-height: 1.2;
  margin-bottom: 12px;
}
.home-subtitle {
  font-size: 14px;
  color: var(--ink-3);
  margin-bottom: 24px;
  letter-spacing: 0.02em;
}
.home-desc {
  font-size: 15px;
  color: var(--ink-2);
  line-height: 1.7;
  margin-bottom: 36px;
}
.home-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  align-items: center;
}
.home-btn {
  padding: 10px 22px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: opacity 0.15s;
}
.home-btn:hover { opacity: 0.85; }
.home-btn.primary  { background: var(--vermillion); color: #fff; }
.home-btn.secondary { background: var(--sidebar-bg); color: var(--ink-2); border: 1px solid var(--border); }
.home-signed-in { font-size: 13px; color: var(--ink-3); }
</style>
