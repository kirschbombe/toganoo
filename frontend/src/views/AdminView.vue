<template>
  <main class="admin-page">
    <div class="admin-content">
      <h2 class="admin-heading">Add IIIF Manifest</h2>
      <p class="admin-desc">
        Paste a IIIF manifest URL to add a new volume to the collection.
        Metadata will be extracted automatically from the manifest.
      </p>

      <form class="admin-form" @submit.prevent="handleIngest">
        <div class="form-group">
          <label class="form-label">IIIF Manifest URL <span class="required">*</span></label>
          <input v-model="form.manifest_url" type="url" class="form-input" required
            placeholder="https://example.edu/iiif/manifest" />
        </div>
        <div class="form-group">
          <label class="form-label">Institution <span class="required">*</span></label>
          <input v-model="form.institution" type="text" class="form-input" required
            placeholder="e.g. Harvard Library" />
        </div>
        <div class="form-group">
          <label class="form-label">Slug prefix <span class="required">*</span></label>
          <input v-model="form.slug_prefix" type="text" class="form-input" required
            placeholder="e.g. harvard" pattern="[a-z0-9-]+" />
          <span class="form-hint">Lowercase letters, numbers, hyphens only. Final slug: {{ form.slug_prefix }}-{local-id}</span>
        </div>
        <div class="form-group">
          <label class="form-label">Slug suffix <span class="form-hint-inline">(optional — auto-generated if blank)</span></label>
          <input v-model="form.slug_suffix" type="text" class="form-input"
            placeholder="e.g. ms-12345" pattern="[a-z0-9-]*" />
        </div>

        <div v-if="error" class="admin-error">{{ error }}</div>
        <div v-if="result" class="admin-success">
          ✓ Added: <strong>{{ result.slug }}</strong> — {{ result.title }}
          <br>
          <RouterLink :to="`/viewer/${result.slug}`">Open in viewer →</RouterLink>
        </div>

        <button type="submit" class="admin-btn" :disabled="loading">
          {{ loading ? 'Fetching manifest…' : 'Add to collection' }}
        </button>
      </form>
    </div>
  </main>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ingestManifest } from '../api/index.js'

const form = reactive({ manifest_url: '', institution: '', slug_prefix: '', slug_suffix: '' })
const loading = ref(false)
const error   = ref('')
const result  = ref(null)

async function handleIngest() {
  loading.value = true
  error.value   = ''
  result.value  = null
  try {
    result.value = await ingestManifest({
      manifest_url: form.manifest_url,
      institution:  form.institution,
      slug_prefix:  form.slug_prefix,
      slug_suffix:  form.slug_suffix || undefined,
    })
    Object.assign(form, { manifest_url: '', slug_suffix: '' })
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-page {
  display: flex;
  justify-content: center;
  padding: 48px 24px;
  min-height: calc(100vh - var(--topbar-h));
  background: var(--bg);
}
.admin-content { width: 100%; max-width: 520px; }
.admin-heading { font-size: 1.1rem; font-weight: 600; color: var(--ink-1); margin-bottom: 8px; }
.admin-desc { font-size: 13px; color: var(--ink-3); margin-bottom: 24px; line-height: 1.6; }
.admin-form { display: flex; flex-direction: column; gap: 14px; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-label { font-size: 11px; font-weight: 600; color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.04em; }
.form-hint { font-size: 11px; color: var(--ink-3); margin-top: 2px; }
.form-hint-inline { font-weight: 400; text-transform: none; color: var(--ink-3); }
.required { color: var(--vermillion); }
.form-input {
  background: var(--sidebar-bg);
  border: 1px solid var(--border);
  color: var(--ink-1);
  padding: 7px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
}
.form-input:focus { outline: 1px solid var(--vermillion); }
.admin-btn {
  padding: 9px 20px;
  background: var(--vermillion);
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  align-self: flex-start;
}
.admin-btn:disabled { opacity: 0.5; cursor: default; }
.admin-error {
  padding: 10px 12px;
  background: rgba(180,40,30,0.15);
  border: 1px solid var(--vermillion);
  border-radius: 4px;
  font-size: 13px;
  color: var(--vermillion);
}
.admin-success {
  padding: 10px 12px;
  background: rgba(80,160,80,0.12);
  border: 1px solid #4a4;
  border-radius: 4px;
  font-size: 13px;
  color: #8d8;
  line-height: 1.6;
}
.admin-success a { color: var(--gold); }
</style>
