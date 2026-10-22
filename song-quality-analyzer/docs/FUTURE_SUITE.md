# ResetLab Craft suite: saved direction

Updated October 12, 2026 from the user's instructions. This document preserves product decisions when work resumes. **The user selected ResetLab Craft as the parent brand and Bandprism as its first tool.** Release/name-availability checks remain outstanding.

The suite identity should be visible in the open-source project itself, starting with **Bandprism**. A consistent app name, mark, colors, typography and README should make it feel like a crafted family of tools from the first GitHub release. The suite does not depend on a future commercial website.

## Decisions to preserve

- Build useful, carefully designed tools for DJs, music producers and music collectors. Keep each tool understandable and lightweight.
- Work locally first. Publish open-source source code and qualified platform releases on GitHub after the release checks pass. No public repository or release has been created yet.
- The first app is Bandprism, the existing Song Quality Analyzer. Its measurements retain the canonical full-spectrum HQ/MQ/LQ rules. Branding does not change grading or add a second quality engine.
- A common visual language includes light and dark themes, readable evidence, a consistent suite signature, and accessible scrolling and motion. Reduced-motion preferences and ordinary keyboard navigation remain supported.
- Keep analyzer v1 focused on correct measurement, duration integrity, folder summaries, reliable batch work, report export and platform qualification. Future tools must not complicate its main workflow.
- Preserve the future idea of a paid website and convenient automatic updates. **Do not design or implement the paid version now.** No pricing, subscriptions, accounts, checkout, paid gates or updater work belongs to the current scope.
- After release, use short Instagram videos to promote the released app and the user's brand, and attract relevant leads. Demonstrate actual behavior; label previews and future ideas accurately.
- Save files continuously and checkpoint unfinished work at meaningful milestones or approaching usage limits. Keep private paths, tokens and music out of publishable project memory.

## Product family

The following names are working concepts, not shipped features.

| App | Purpose | Current status |
| --- | --- | --- |
| **Bandprism** | Inspect spectral coverage and track integrity, with folder summaries and evidence | Local alpha; release qualification continues |
| **Keycraft** | Musical-key and harmonic-mixing preparation, inspired by the use case of Mixed In Key | Future research and prototype |
| **Stemcraft** | Prepare reusable separated audio and investigate supported rekordbox workflows | Future feasibility work; rekordbox cache injection is not promised |
| **Setcraft** | Suggest the next song and actual transition points from a chosen starting track/section, with optional lyric wordplay | Future research and prototype |
| **Cratecraft** | Organize files and metadata while preserving originals and DJ library data | Deferred; follows the user's established folder/title preferences |

Use **ResetLab Craft** for the suite and **Bandprism** for the first app in user-facing material. Keep stable technical paths until a deliberate migration; a display-name update does not require moving canonical analysis code or existing files. See [Brand](BRAND.md) for naming and visual rules and [Suite roadmap](SUITE_ROADMAP.md) for ordered milestones, research questions and release gates.

## Boundaries for future work

Mixed In Key is a reference for a musical workflow, not permission to reuse proprietary code, models, interface assets or claims. A future key tool needs its own evaluated implementation and confidence estimates.

The stems idea is to avoid repeating expensive separation. The safe starting concept is a private cache of independently generated stems, identified by source audio and model/settings versions. Do not assume a supported route exists for loading this cache directly into rekordbox. Confirm the user's rekordbox version, existing behavior and supported import/export routes before making an integration promise. Preserve Collection entries, cues, grids, playlists and DJ notes.

The song-suggestion idea needs more than a track-level key/BPM match: respect the selected starting point, compare outgoing and incoming sections, explain why a candidate fits, and let the DJ audition and override it. Optional wordplay must identify the actual phrase and timing with confidence; unverified lyrics are not evidence.

## Naming still to resolve

The selected parent brand is **ResetLab Craft**. Product names can share `-craft`, but the user relaxed that requirement; Bandprism is the analyzer. Check relevant software names, domain and social handles before publication; display-name approval does not establish availability.

Earlier searches found existing products called Signaloom, ToneHarbor, Cratewell, Sonaloom and Wavewright, so those are poor first choices. Examples: [Signaloom](https://play.google.com/store/apps/details?id=com.maromav.realenginesound), [ToneHarbor](https://github.com/LyricTracers/ToneHarbor), [Cratewell](https://play.google.com/store/apps/details?id=com.cratewell.g82ec6227f0b48a32d374), [Sonaloom](https://sonaloom.com/), [Wavewright](https://store.steampowered.com/app/4149720/Wavewright/). These are preliminary conflict findings, not legal clearance.

The future paid website and automatic-update idea remains **saved planning only**. Native Windows, clean-install and macOS qualification are still release work; a local bundle does not qualify all platforms.
