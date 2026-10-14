"use strict";
const assert = require("node:assert/strict");
const { orderedTracks, analysisOrder, analysisBatches } = require("../music_library_lab/static/library-view.js");
const tracks = [
  { id: "z", title: "Zebra", artist: "A", source_path: "z.wav", enabled: false },
  { id: "10", title: "Álpha 10", artist: "B", source_path: "10.wav", enabled: true },
  { id: "2", title: "alpha 2", artist: "A", source_path: "2.wav", enabled: true },
  { id: "a", title: "Alpha", artist: "C", source_path: "a.wav", enabled: false }
];
const before = JSON.stringify(tracks);
assert.deepEqual(orderedTracks(tracks, "title-asc").map(x => x.track.id), ["a", "2", "10", "z"]);
assert.deepEqual(orderedTracks(tracks, "title-desc").map(x => x.track.id), ["z", "10", "2", "a"]);
assert.deepEqual(orderedTracks(tracks, "artist-asc").map(x => x.track.id), ["2", "z", "10", "a"]);
for (const sort of ["title-asc", "title-desc", "artist-asc"]) {
  for (const row of orderedTracks(tracks, sort)) assert.equal(tracks[row.index], row.track);
}
assert.equal(JSON.stringify(tracks), before);
assert.deepEqual(orderedTracks([], "title-asc"), []);
console.log("Sorting invariants passed: numeric/accent-aware order, stable identity, original selection/order preserved.");
const large = Array.from({length:103}, (_, i) => ({id:String(103-i),title:"Track " + (103-i),source_path:"filename " + i + ".wav",enabled:true,scan_valid:true}));
const largeBefore = JSON.stringify(large);
const batches = analysisBatches(large,50);
assert.deepEqual(batches.map(batch=>batch.length),[50,50,3]);
assert.deepEqual(batches.flat().map(track=>track.id),Array.from({length:103},(_,i)=>String(i+1)));
assert.equal(new Set(batches.flat().map(track=>track.id)).size,103);
assert.equal(JSON.stringify(large),largeBefore);
large[0].enabled=false;
large[1].scan_valid=false;
assert.equal(analysisBatches(large,50).flat().length,101);
assert.equal(analysisOrder(large)[0].id,"1");
console.log("Automatic batching passed: 50/50/3 in title order, no duplicates/omissions, invalid and unchecked tracks excluded.");
