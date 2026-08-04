// Helpers for presenting volumes that belong to a multi-volume set.
//
// `volume_label` carries the designation from the source manifest and is
// authoritative; `volume_number` is only the ingest sequence, and the two
// diverge for incomplete sets — surviving volumes 1, 4, 5 and 7 are numbered
// 1 through 4.

const VOL_IN_LABEL = /vol\.?\s*(\d+)/i

/** "Vol. 4" for a set member, from its label where one states a number. */
export function volumeDesignation(volume) {
  if (!volume) return ''
  const match = (volume.volume_label || '').match(VOL_IN_LABEL)
  if (match) return `Vol. ${match[1]}`
  return (volume.volume_label || '').trim() ||
         (volume.volume_number ? `Vol. ${volume.volume_number}` : '')
}
