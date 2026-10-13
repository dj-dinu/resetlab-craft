# ResetLab Craft suite roadmap

Saved October 12, 2026. **The user selected ResetLab Craft as the parent brand.** Only Spectracraft exists as a local alpha. The other tools below are future concepts; this document does not implement or promise an integration.

The goal is a family of small, well-crafted desktop tools for DJs and producers. Share a visual language and reusable infrastructure where useful, but keep each tool's purpose clear. Develop locally, validate on Windows and macOS, and qualify each release before publishing its open-source project on GitHub.

## Order of work

| Stage | Outcome | Gate before the next stage |
| --- | --- | --- |
| **1. Spectracraft** | Branded quality analyzer with reliable folder summaries, filters, duration warnings and evidence | Native desktop/clean-install qualification, macOS testing, cache/resource handling, dependency licensing and small user beta |
| **2. Keycraft** | A local musical-key and harmonic-preparation prototype | Labeled evaluation set, confidence/ambiguity reporting, tempo/key-change handling and safe export |
| **3. Stemcraft feasibility** | Measured evidence of where persistent separation would save work, and a supported reuse path | Verify target rekordbox versions; evaluate model, storage, timing and any supported interoperability |
| **4. Setcraft** | Explainable next-track suggestions tied to selected sections and transition points | A useful non-AI baseline, DJ evaluation of real transitions, confidence and optional lyric timing checks |
| **5. Cratecraft** | A separate organizer with preview, backup and tested metadata/library reconciliation | Demonstrated preservation of music, artwork, Collection entries, cues, grids, playlists and DJ notes |

Stemcraft research may run alongside Keycraft research when a small experiment can settle feasibility. Setcraft depends on dependable key/tempo/section information, so begin with an explainable candidate ranking before adding a larger model. The paid website and automatic updates stay outside this roadmap's implementation scope.

## Spectracraft: first public tool

Finish and qualify the current app before expanding it. It stays focused on spectral evidence and integrity, with the user's existing canonical engine and full-duration grading rule. Branding, themes and scrolling are presentation improvements. They must not change measurement or weaken source preservation.

Public material should distinguish a measured grade from listening preference or proof of an original lossless source. Document how the folder score treats measured tracks, errors and unmeasured tracks; do not quietly include failed analyses as LQ. Establish cache limits and make private report information predictable.

## Keycraft: harmonic preparation

**User idea:** a tool serving the kind of key and harmonic-preparation use case associated with Mixed In Key.

The first useful prototype would estimate musical key and tempo, show confidence and possible alternatives, and help compare compatible sections. Preserve existing tags by default. Optional exports come after a supported, tested workflow and a preview of what will change.

The evaluation needs pitch-annotated material and DJ listening tests across instrumental/vocal music, detuned recordings, live tempo, half/double-time ambiguity, mashups, short edits, percussion-only introductions and key changes. A single confident key for an entire changing track is often less useful than a section map. Test relative major/minor ambiguities and report “uncertain” when warranted.

Mixed In Key already documents key, BPM, energy and cue-point analysis, with additional mixing/mashup functions. The opportunity is a transparent local tool with uncertainty and useful section-level explanations; there is no evidence yet that our future model would be more accurate. See the official [Mixed In Key workflow](https://mixedinkey.com/workflows/use-energy-level-detection/) and [integration guides](https://mixedinkey.com/workflows/dj-software-integration-guides/).

Do not reproduce proprietary code, learned models, interface assets or branding. Choose any key notation deliberately and explain it. The future tool will need its own algorithm, evaluation and license review.

## Stemcraft: prepare once, reuse when supported

**User idea:** save stems for a rekordbox workflow so repeated loading does not repeatedly perform expensive separation.

Begin by reproducing the user's actual problem on the relevant rekordbox version and operating system: time the first load, subsequent loads, application restart and changed settings; inspect documented options; and check whether persistence already exists. The official rekordbox 7.2.8 manual describes three- or four-part STEMS and quality/speed settings, but the reviewed sections do not document an external persistent-cache import API. This leaves interoperability unproven rather than establishing that no caching exists. See the [rekordbox instruction manual, pages 207 and 242–243](https://cdn.rekordbox.com/files/20251202174516/rekordbox7.2.8_manual_EN.pdf).

The initial independent prototype can separate user-owned local audio into aligned PCM stem files and retain them in an app-managed cache. Identify each result by the source content hash, separation model/version, decoder and processing settings; record sample rate, duration, stem layout, timing offset and output hashes. Reuse verified results after restart, invalidate stale results, write outputs atomically, handle cancellation, and let users control storage. Preserve the original track.

That cache would serve our own preview/export workflow. It will only save work inside rekordbox if a **supported and tested** workflow accepts the outputs. Ordinary exported stem audio is not automatically equivalent to rekordbox's deck separation cache. Do not inject cache files, patch the application or modify proprietary databases to promise a seamless feature. Preserve cues, beatgrids, playlists and Collection entries; test any supported library operation on disposable fixtures first.

Useful evaluation includes separation quality, vocal/instrument bleed, transient damage, reconstruction and sample alignment, CPU/GPU memory, model-download size, processing time and disk use. Local stems are a substantially heavier tool than Spectracraft and should be optional. Check model and dependency licenses before distribution. Streaming/DRM sources require separate supported capabilities and permissions; they are not assumed to work.

## Setcraft: the next song and where to enter it

**User idea:** choose a specific starting track or point, suggest the next song, and optionally find lyric wordplay opportunities.

A candidate should be a proposed transition, not just a title:

- The current track, selected starting point and proposed outgoing cue/phrase.
- The suggested incoming track and exact incoming cue/phrase, with auditionable sections.
- The user's intended energy direction, tempo range, harmonic preference, mood, genre and mixing style.
- Plain reasons for the match, timing/tempo adjustments and uncertainty.
- A way to pin or exclude tracks, avoid accidental repeats, override a suggestion and save a planned sequence.

Start with transparent ranking using measured BPM/key/section features and user constraints. Compare that baseline with any later learned model on actual DJ tasks. Evaluate phrase alignment, tempo drift, vocal clashes, energy changes, key changes, repetitive choices and abrupt section endings. Do not claim a model predicts the crowd or guarantees a good mix.

An optional wordplay layer can look for a repeated phrase, call-and-response, thematic handoff or intentional lyrical contrast. It needs timestamped lyrics supplied with appropriate permission or locally derived by an opt-in process, alignment confidence and a human listening check. Distinguish literal wording from inferred themes; support slang, multiple languages, censored edits, remixes, missing vocals and inaccurate transcription. Show only what is necessary to locate the user's own audio. Do not bundle a copyrighted lyric corpus, publish full lyrics in reports or upload music by default.

The model should propose cue points independently before any DJ-software export. Supported exports must preserve existing manual cues unless the user explicitly chooses a tested replacement workflow. Existing rekordbox features already include suggestions and mix-point functionality; our future value needs evaluation around the user's chosen section, explanation and wordplay rather than a claim to invent next-track suggestions. The [rekordbox manual](https://cdn.rekordbox.com/files/20251202174516/rekordbox7.2.8_manual_EN.pdf) documents Track Suggestion and MIX POINT LINK.

## Cratecraft: a separate later tool

Retain the user's established shallow language/vocal-content and broad-genre folder names. Keep detailed genres and moods in metadata or playlists. An authorized rename must synchronize the cleaned embedded track title, preserving mix/version information and quality suffixes while keeping the artist in its own field.

Every organization plan needs preview, original metadata and paths in a private manifest, backups, collision handling and reversible operations. Preserve audio samples, artwork and original files. Rekordbox reconciliation requires a supported metadata workflow proven to preserve Collection entries, cues, grids, playlists and DJ notes. Nothing in this roadmap authorizes organizing or retagging the current music library.

## Shared foundation and release discipline

Reuse a small local desktop shell, theme and motion tokens, a source-hash scheme, cancellation, report conventions and cache controls when they help. Keep heavy key, stem and language models out of Spectracraft's default download. Version model results and explain when a cached measurement came from an older model.

For each tool, qualify supported file formats, Windows/macOS architectures, native installation and resource limits; review dependency/model licenses; and separate measured behavior from prototypes in release notes. Use GitHub for public source, issues and qualified releases. Final repository layout and open-source license remain decisions before publication.

After release, short Instagram demonstrations can show a real task, the result and a link to the relevant GitHub download, while promoting the user's brand. Saved commercial possibilities do not add paid requirements to today's work. **No future tool, account system, subscription, paid website or automatic-update service has been implemented by this roadmap.**
