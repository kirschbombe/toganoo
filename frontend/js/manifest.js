/**
 * Parse a IIIF Presentation API manifest (v2 or v3)
 * Returns a normalised array of canvas objects.
 */

export function parseManifest(manifest) {
  const version = detectVersion(manifest);
  if (version === 3) return parseV3(manifest);
  return parseV2(manifest);
}

function detectVersion(manifest) {
  const ctx = manifest['@context'];
  if (typeof ctx === 'string') {
    return ctx.includes('/3/') ? 3 : 2;
  }
  if (Array.isArray(ctx)) {
    return ctx.some(c => typeof c === 'string' && c.includes('/3/')) ? 3 : 2;
  }
  return manifest.type === 'Manifest' ? 3 : 2;
}

function parseV2(manifest) {
  const canvases = manifest?.sequences?.[0]?.canvases ?? [];
  return canvases.map((c, i) => {
    const image = c.images?.[0];
    const resource = image?.resource ?? {};
    const service = resource.service ?? {};
    const serviceId = service['@id'] ?? service.id ?? resource['@id'] ?? '';

    return {
      id:           c['@id'] ?? '',
      label:        labelToString(c.label) || `Page ${i + 1}`,
      width:        c.width ?? 0,
      height:       c.height ?? 0,
      imageServiceId: serviceId,
      imageUrl:     serviceId ? `${serviceId}/full/max/0/default.jpg` : (resource['@id'] ?? ''),
      thumbnailUrl: serviceId ? `${serviceId}/full/200,/0/default.jpg` : '',
    };
  });
}

function parseV3(manifest) {
  const items = manifest?.items ?? [];
  return items.map((canvas, i) => {
    const annoPage = canvas.items?.[0];
    const anno     = annoPage?.items?.[0];
    const body     = anno?.body ?? {};

    // body can be an object or array
    const bodyObj  = Array.isArray(body) ? body[0] : body;
    const services = bodyObj.service ?? [];
    const serviceArr = Array.isArray(services) ? services : [services];
    const service  = serviceArr.find(s => s?.type === 'ImageService3' || s?.type === 'ImageService2') ?? serviceArr[0] ?? {};
    const serviceId = service?.id ?? service?.['@id'] ?? '';

    return {
      id:             canvas.id ?? canvas['@id'] ?? '',
      label:          labelToString(canvas.label) || `Page ${i + 1}`,
      width:          canvas.width ?? 0,
      height:         canvas.height ?? 0,
      imageServiceId: serviceId,
      imageUrl:       serviceId ? `${serviceId}/full/max/0/default.jpg` : (bodyObj.id ?? ''),
      thumbnailUrl:   serviceId ? `${serviceId}/full/200,/0/default.jpg` : '',
    };
  });
}

function labelToString(label) {
  if (!label) return '';
  if (typeof label === 'string') return label;
  // IIIF v3 label: { "en": ["value"] } or { "none": ["value"] }
  if (typeof label === 'object' && !Array.isArray(label)) {
    const values = label.none ?? label.en ?? label.ja ?? Object.values(label)[0];
    if (Array.isArray(values)) return values[0] ?? '';
    return String(values ?? '');
  }
  if (Array.isArray(label)) return label[0] ?? '';
  return String(label);
}

/**
 * Build an OpenSeadragon tile source from a parsed canvas.
 *
 * Passing an info.json URL as a plain string lets OSD auto-detect the
 * IIIF Image API and load tiles properly. Wrapping it in { type:'image' }
 * tells OSD to treat it as a flat image — which silently fails for info.json.
 */
export function canvasToTileSource(canvas) {
  if (canvas.imageServiceId) {
    // Plain string → OSD auto-detects IIIF Image API via info.json
    return `${canvas.imageServiceId}/info.json`;
  }
  // Fallback: plain image URL (no tiling)
  if (canvas.imageUrl) {
    return {
      type:         'image',
      url:          canvas.imageUrl,
      buildPyramid: false,
    };
  }
  return null;
}
