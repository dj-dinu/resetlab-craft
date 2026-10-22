"use strict";

// Presentation order only: selections, grades and evidence stay keyed by ID.
function orderedTracks(tracks, sort) {
  const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });
  const text = value => value == null ? "" : String(value);
  const name = track => text(track.source_path).split(/[\\/]/).pop();
  return tracks.map((track, index) => ({ track, index })).sort((a, b) => {
    const field = sort === "artist-asc" ? "artist" : "title";
    const compare = collator.compare(text(a.track[field] || name(a.track)), text(b.track[field] || name(b.track)));
    return (sort === "title-desc" ? -compare : compare) || collator.compare(text(a.track.source_path), text(b.track.source_path)) || a.index - b.index;
  });
}

function analysisOrder(tracks) {
  return orderedTracks(tracks, "title-asc").map(row => row.track);
}
function analysisBatches(tracks, limit) {
  const selected = analysisOrder(tracks).filter(track => track.scan_valid !== false && track.enabled !== false);
  const size = Number.isInteger(limit) && limit > 0 ? limit : 50;
  const batches = [];
  for (let index = 0; index < selected.length; index += size) batches.push(selected.slice(index, index + size));
  return batches;
}
if (typeof module !== "undefined" && module.exports) module.exports = { orderedTracks, analysisOrder, analysisBatches };
else window.BandprismLibraryView = { orderedTracks, analysisOrder, analysisBatches };
