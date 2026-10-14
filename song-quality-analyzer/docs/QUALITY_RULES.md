# Current spectral grading rule

The user authorized this rule change: **HQ requires qualifying signal at or
above 20 kHz for at least 40% of the complete decoded duration.** If HQ fails,
MQ requires qualifying signal at or above 18 kHz for at least 40%. Otherwise LQ.
Encoded bitrate and the filename's existing label remain informational.

The sole maintained scanner implements the rule. A half-second window qualifies
when mean power across its available FFT bins from the target frequency to
Nyquist meets both -110 dBFS and -65 dB relative to the 1–10 kHz reference region,
with summed power above 3e-6 to exclude silence. No FFT bin below the target is
included. The frequency ceiling is half the native sample rate. Channel powers
are averaged; full-track duration, including quiet sections, remains the divisor.
The finite FFT resolution and these sensitive signal thresholds still limit
what can be inferred about musical content or source authenticity.

Rule version: `2026-10-13-40-percent-at-or-above`. Reports carry this version
and `coverage_threshold: 0.4`. This supersedes the old 30% rule and its +/-200 Hz
target band. Reanalyze tracks to obtain the new result; old reports, tags and
filenames are preserved. Raising the threshold does not guarantee that a
previous HQ track becomes MQ. Source files remain unchanged by the analyzer.
