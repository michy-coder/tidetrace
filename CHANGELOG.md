# Changelog

All notable changes to TideTrace will be documented in this file.

## Unreleased

### Added
- Added configurable columns for the “日ごとのまとめ” table, text copy, TSV copy, and print view, including selectable TideTrace and HeartWatch metrics, custom short labels, and saved display order.
- Added a past records and healthcare data view that temporarily loads HeartWatch daily CSV files, aligns them with TideTrace daily records, and supports text, TSV, and print-friendly output.
- Added editing for record date and time on medication, pain, and note 
- Added medication pain-change summaries to visit summaries, showing recorded before-and-after pain-score changes by medication without assessing medication effectiveness.
- Added copy and plain text download actions for visit summaries.
- Added time-of-day pain summaries to visit summaries, grouping pain records by late night/early morning, morning, afternoon, and night without assessing causes or medication effects.

### Changed
- Updated the HeartWatch daily summary to show only imported HeartWatch dates, use shorter pain headers, add active-medication count columns with short medication labels, and include sleep bpm and waking HRV reference values.
- Updated visit-summary state-pain rows to prioritize higher average pain before maximum pain.
- Updated visit-summary time-of-day pain rows to match the state-pain summary detail level and shorten the late-night label.
- Past record range labels now match the dates that actually have records.
- Added maximum-pain day counts to state and dose pain sections in visit summaries.

### Fixed
- Past record navigation skips empty gaps and moves to the next range with records.

## v0.1.0 - 2026-06-26

### Added

- Initial public release of TideTrace.
- Added local-first pain, medication, and note logging.
- Added browser-based storage without external data transmission.
- Added JSON backup and CSV export.
- Added medical appointment summary.
- Added first-use setup flow.
- Added README, MIT License, and changelog.