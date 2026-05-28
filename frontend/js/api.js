// Thin wrapper around backend API endpoints

export async function getUser() {
  const res = await fetch('/auth/me');
  const data = await res.json();
  return data.user;
}

export async function getVolumeAnnotations(manifestUrl) {
  const res = await fetch(`/api/annotations/volume/${encodeURIComponent(manifestUrl)}`);
  if (!res.ok) return [];
  return res.json();
}

export async function createAnnotation(payload) {
  const res = await fetch('/api/annotations/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateAnnotation(id, payload) {
  const res = await fetch(`/api/annotations/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteAnnotation(id) {
  const res = await fetch(`/api/annotations/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchManifest(url) {
  const res = await fetch(`/api/manifest/proxy?url=${encodeURIComponent(url)}`);
  if (!res.ok) throw new Error(`Failed to load manifest: ${res.status}`);
  return res.json();
}

export function exportUrl(type, manifestUrl) {
  return `/api/export/${type}/${encodeURIComponent(manifestUrl)}`;
}
