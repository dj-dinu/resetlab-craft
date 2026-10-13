# Folder summaries and incomplete audio

Implemented locally October 12, 2026. The analyzer remains read-only.

The folder score is the equally weighted average of measured grade values: HQ100, MQ50, LQ0. It is a summary of the user's spectral rule, not a percentage of audible quality or original source authenticity. All-HQ gives100. The test folder with36HQ,30MQ,34LQ gives51. Errors and unmeasured tracks are excluded, counted visibly, and prevent a complete-folder claim. A capped inventory is explicitly partial.

Keep the50-track run limit. Select the next unmeasured batch to continue. Compact per-track grade/coverage records accumulate in the current inventory while detailed time bins and graphs belong only to the latest completed batch. Filters affect visible rows, not score or selection. Rescanning resets the inventory's measurements. JSON report export is the latest batch, and cancellation retains the prior completed report.

Duration-integrity checks live only in the canonical scanner. Structural WAV/RF64 data lengths, AIFF COMM sample counts, FLAC STREAMINFO totals, MP3 Xing/Info/VBRI frame counts and MP4 audio stream timelines can declare an expected length. Compare this with fully decoded PCM duration. An absolute difference exceeding max(0.25 seconds,2% of the declaration) is an ungraded integrity error. Keep both durations and their provenance, and request local review of an incomplete file or incorrect header.

The user's example is covered: a header declares240seconds but only60seconds decode. Even though the decoded audio meets HQ, the scanner returns integrity_error with no quality grade. The app excludes it from score and displays the two durations. A valid60-second HQ edit still receives HQ. Missing seconds are not fabricated or added as synthetic silence.

An absent declaration cannot establish intended original length. Raw AAC or MPEG without a trustworthy frame-count header may end cleanly after a shorter edit or truncation; this remains duration_not_verifiable. ID3 TLEN, filenames and estimated bitrate/file-size durations do not prove missing content. Header agreement also does not prove an intended original version. Abrupt-ending heuristics are deferred because intentional DJ edits/stems can end sharply.

The spectral math and HQ30% rule are unchanged. Real HQ/MQ/LQ metrics, every time bin, powers and source hashes remain identical. Canonical format checks58 and integrity checks16 passed. Public launch still requires native Windows/macOS, clean-machine, licensing and cache/resource qualification.
