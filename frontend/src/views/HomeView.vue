<template>
  <main class="home">
    <img class="home-hero-img" :src="HERO_IMAGE" alt="" aria-hidden="true" />
    <div class="home-hero-scrim" aria-hidden="true"></div>
    <div class="home-content">
      <h1 class="home-title">Buddhist Temple Books<br>Provenance Project</h1>
      <p class="home-subtitle">
        UCLA Library · Toganoo Collection of Esoteric Buddhism
      </p>
      <p class="home-desc">
        A collaborative workspace for annotating provenance marks — collector's seals,
        stamps, inscriptions, and labels — in books and manuscripts from the UCLA
        Toganoo Collection of Japanese Buddhist texts.
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

// Hero backdrop: an existing UCLA IIIF image requested at display size.
// The pct: region trims the black photographic background from the edges, so
// the hero can anchor near the top without the object's edge coming into frame.
const HERO_IMAGE =
  'https://iiif.library.ucla.edu/iiif/2/ark%3A%2F21198%2Fn1s91b%2Fsw43zc5x/pct:4,3,92,92/1400,/0/default.jpg'
</script>

<style scoped>
.home {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--topbar-h));
  padding: 64px 24px;
  background: var(--bg);
  overflow: hidden;
}
.home-hero-img {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 70%;
  height: 100%;
  object-fit: cover;
  /* Anchored to the top of the cropped image, with a little headroom */
  object-position: 50% 4%;
  opacity: 0.55;
  filter: saturate(0.85);
  /* Feather the left edge so the image has no hard seam against the page */
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 30%);
  mask-image: linear-gradient(90deg, transparent 0%, #000 30%);
}
.home-hero-scrim {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    100deg,
    var(--bg) 30%,
    oklch(20% 0.014 264 / 65%) 55%,
    oklch(20% 0.014 264 / 25%) 100%
  );
}
.home-content {
  position: relative;
  max-width: 680px;
  text-align: center;
}
.home-title {
  font-family: var(--font-serif);
  font-size: 56px;
  font-weight: 600;
  color: oklch(96% 0.006 264);
  line-height: 1.12;
  letter-spacing: -0.01em;
  margin-bottom: 20px;
}
.home-subtitle {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-3);
  margin-bottom: 24px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.home-desc {
  font-size: 19px;
  color: oklch(78% 0.008 264);
  line-height: 1.6;
  max-width: 560px;
  margin: 0 auto 40px;
}
.home-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  align-items: center;
}
.home-btn {
  padding: 15px 32px;
  border-radius: 9px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  transition: background 0.15s, border-color 0.15s;
}
.home-btn.primary  { background: var(--vermillion); color: #fff; }
.home-btn.primary:hover { background: var(--vermillion-hover); }
.home-btn.secondary {
  padding: 15px 28px;
  font-weight: 500;
  background: transparent;
  color: oklch(85% 0.006 264);
  border: 1px solid var(--border-strong);
}
.home-btn.secondary:hover { background: rgba(255,255,255,0.06); }
.home-btn.secondary .orcid-dot { width: 20px; height: 20px; font-size: 10px; }
.home-signed-in { font-size: 15px; color: var(--text-2); }

@media (max-width: 720px) {
  .home-title { font-size: 38px; }
  .home-desc  { font-size: 17px; }
  /* Too narrow to keep the image beside the text — sit it behind, dimmed */
  .home-hero-img {
    width: 100%;
    opacity: 0.3;
    -webkit-mask-image: none;
    mask-image: none;
  }
  .home-hero-scrim {
    background: linear-gradient(
      180deg,
      oklch(20% 0.014 264 / 85%),
      oklch(20% 0.014 264 / 70%)
    );
  }
}
</style>
