<template>
  <main class="admin-page">
    <div class="admin-content">

      <!-- Tab selector -->
      <div class="admin-tabs">
        <button class="admin-tab" :class="{ active: tab === 'manifest' }" @click="tab = 'manifest'">
          Add Manifest
        </button>
        <button class="admin-tab" :class="{ active: tab === 'collection' }" @click="tab = 'collection'">
          Add Collection
        </button>
        <button class="admin-tab" :class="{ active: tab === 'users' }" @click="tab = 'users'; loadUsers()">
          User Access
        </button>
      </div>

      <!-- ── Add single manifest ── -->
      <template v-if="tab === 'manifest'">
        <h2 class="admin-heading">Add IIIF Manifest</h2>
        <p class="admin-desc">
          Paste a IIIF manifest URL to add a new volume to the collection.
          Metadata will be extracted automatically from the manifest.
        </p>

        <form class="admin-form" @submit.prevent="handleIngest">
          <div class="form-group">
            <label class="form-label">IIIF Manifest URL <span class="required">*</span></label>
            <input v-model="mForm.manifest_url" type="url" class="form-input" required
              placeholder="https://example.edu/iiif/manifest" />
          </div>
          <div class="form-group">
            <label class="form-label">Institution <span class="required">*</span></label>
            <input v-model="mForm.institution" type="text" class="form-input" required
              placeholder="e.g. Harvard Library" />
          </div>
          <div class="form-group">
            <label class="form-label">Slug prefix <span class="required">*</span></label>
            <input v-model="mForm.slug_prefix" type="text" class="form-input" required
              placeholder="e.g. harvard" pattern="[a-z0-9-]+" />
            <span class="form-hint">Lowercase, numbers, hyphens. Final slug: {{ mForm.slug_prefix }}-{local-id}</span>
          </div>
          <div class="form-group">
            <label class="form-label">Slug suffix <span class="form-hint-inline">(optional)</span></label>
            <input v-model="mForm.slug_suffix" type="text" class="form-input"
              placeholder="e.g. ms-12345" pattern="[a-z0-9-]*" />
          </div>

          <div v-if="mError" class="admin-error">{{ mError }}</div>
          <div v-if="mResult" class="admin-success">
            ✓ Added: <strong>{{ mResult.slug }}</strong> — {{ mResult.title }}
            <br>
            <RouterLink :to="`/viewer/${mResult.slug}`">Open in viewer →</RouterLink>
          </div>

          <button type="submit" class="admin-btn" :disabled="mLoading">
            {{ mLoading ? 'Fetching manifest…' : 'Add to collection' }}
          </button>
        </form>
      </template>

      <!-- ── Add IIIF Collection ── -->
      <!-- ── User Access ── -->
      <template v-else-if="tab === 'users'">
        <h2 class="admin-heading">User Access</h2>
        <p class="admin-desc">
          Anyone can log in with ORCID, but only users granted <strong>Editor</strong> access can
          create and edit annotations. Admins can also manage volumes and grant access to others.
        </p>

        <div v-if="usersLoading" class="admin-desc">Loading…</div>
        <div v-else-if="usersError" class="admin-error">{{ usersError }}</div>
        <table v-else class="user-table">
          <thead>
            <tr>
              <th>Name / ORCID</th>
              <th>Editor</th>
              <th>Admin</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in usersList" :key="u.id">
              <td class="user-cell">
                <span class="user-name">{{ u.name }}</span>
                <a class="user-orcid" :href="u.id" target="_blank">{{ u.id.replace('https://orcid.org/', '') }}</a>
              </td>
              <td class="role-cell">
                <button
                  class="role-btn"
                  :class="{ active: u.is_editor }"
                  @click="toggleRole(u, 'is_editor')"
                >{{ u.is_editor ? '✓' : '–' }}</button>
              </td>
              <td class="role-cell">
                <button
                  class="role-btn"
                  :class="{ active: u.is_admin }"
                  @click="toggleRole(u, 'is_admin')"
                >{{ u.is_admin ? '✓' : '–' }}</button>
              </td>
            </tr>
            <tr v-if="!usersList.length">
              <td colspan="3" class="admin-desc" style="padding: 16px 0">
                No users have logged in yet.
              </td>
            </tr>
          </tbody>
        </table>
      </template>

      <template v-else>
        <h2 class="admin-heading">Add IIIF Collection</h2>
        <p class="admin-desc">
          Paste a IIIF Collection URL to ingest all member manifests as a multi-volume set.
          Each manifest will be added as a volume linked to the collection.
        </p>

        <form class="admin-form" @submit.prevent="handleCollectionIngest">
          <div class="form-group">
            <label class="form-label">IIIF Collection URL <span class="required">*</span></label>
            <input v-model="cForm.collection_url" type="url" class="form-input" required
              placeholder="https://example.edu/iiif/collection" />
          </div>
          <div class="form-group">
            <label class="form-label">Institution <span class="required">*</span></label>
            <input v-model="cForm.institution" type="text" class="form-input" required
              placeholder="e.g. Harvard Library" />
          </div>
          <div class="form-group">
            <label class="form-label">Slug prefix <span class="required">*</span></label>
            <input v-model="cForm.slug_prefix" type="text" class="form-input" required
              placeholder="e.g. harvard" pattern="[a-z0-9-]+" />
            <span class="form-hint">Used as prefix for both the collection and all member volumes.</span>
          </div>

          <div v-if="cError" class="admin-error">{{ cError }}</div>
          <div v-if="cResult" class="admin-success">
            ✓ Ingested: <strong>{{ cResult.title }}</strong>
            <br>{{ cResult.volumes_ingested }} volumes added.
            <br v-if="cResult.volumes?.length">
            <RouterLink v-if="cResult.volumes?.length" :to="`/viewer/${cResult.volumes[0].slug}`">
              Open first volume →
            </RouterLink>
          </div>

          <button type="submit" class="admin-btn" :disabled="cLoading">
            {{ cLoading ? 'Fetching collection…' : 'Ingest collection' }}
          </button>
        </form>
      </template>

    </div>
  </main>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ingestManifest, ingestCollection } from '../api/index.js'

// ── Users ──
const usersList   = ref([])
const usersLoading = ref(false)
const usersError  = ref('')

async function loadUsers() {
  if (usersLoading.value) return
  usersLoading.value = true
  usersError.value   = ''
  try {
    const res = await fetch('/api/users/')
    if (!res.ok) throw new Error(await res.text())
    usersList.value = await res.json()
  } catch (e) {
    usersError.value = e.message
  } finally {
    usersLoading.value = false
  }
}

async function toggleRole(user, field) {
  const newVal = !user[field]
  try {
    const res = await fetch(`/api/users/${encodeURIComponent(user.id)}`, {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ [field]: newVal }),
    })
    if (!res.ok) throw new Error(await res.text())
    const updated = await res.json()
    Object.assign(user, updated)
  } catch (e) {
    alert(`Failed to update role: ${e.message}`)
  }
}

const tab = ref('manifest')

// ── Single manifest ──
const mForm    = reactive({ manifest_url: '', institution: '', slug_prefix: '', slug_suffix: '' })
const mLoading = ref(false)
const mError   = ref('')
const mResult  = ref(null)

async function handleIngest() {
  mLoading.value = true
  mError.value   = ''
  mResult.value  = null
  try {
    mResult.value = await ingestManifest({
      manifest_url: mForm.manifest_url,
      institution:  mForm.institution,
      slug_prefix:  mForm.slug_prefix,
      slug_suffix:  mForm.slug_suffix || undefined,
    })
    Object.assign(mForm, { manifest_url: '', slug_suffix: '' })
  } catch (e) {
    mError.value = e.message
  } finally {
    mLoading.value = false
  }
}

// ── IIIF Collection ──
const cForm    = reactive({ collection_url: '', institution: '', slug_prefix: '' })
const cLoading = ref(false)
const cError   = ref('')
const cResult  = ref(null)

async function handleCollectionIngest() {
  cLoading.value = true
  cError.value   = ''
  cResult.value  = null
  try {
    cResult.value = await ingestCollection({
      collection_url: cForm.collection_url,
      institution:    cForm.institution,
      slug_prefix:    cForm.slug_prefix,
    })
    Object.assign(cForm, { collection_url: '' })
  } catch (e) {
    cError.value = e.message
  } finally {
    cLoading.value = false
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

/* Tabs */
.admin-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 28px;
  border-bottom: 1px solid var(--border);
}
.admin-tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-3);
  cursor: pointer;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}
.admin-tab:hover { color: var(--ink-1); }
.admin-tab.active {
  color: var(--ink-1);
  border-bottom-color: var(--vermillion);
}

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

/* User table */
.user-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.user-table th {
  text-align: left;
  padding: 6px 8px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-3);
  border-bottom: 1px solid var(--border);
}
.user-table td { padding: 8px 8px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.user-cell { display: flex; flex-direction: column; gap: 2px; }
.user-name { color: var(--ink-1); font-weight: 500; }
.user-orcid { color: var(--ink-3); font-size: 10px; font-family: monospace; text-decoration: none; }
.user-orcid:hover { color: var(--gold); }
.role-cell { text-align: center; width: 64px; }
.role-btn {
  width: 32px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: none;
  color: var(--ink-3);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}
.role-btn.active {
  background: rgba(180,40,30,0.12);
  border-color: var(--vermillion);
  color: var(--vermillion);
}
.role-btn:hover { border-color: var(--ink-1); color: var(--ink-1); }
.role-btn.active:hover { background: rgba(180,40,30,0.2); }
</style>
