# Changelog

All notable changes to TideTrace will be documented in this file.

## Unreleased

### Added
- Added a focused print view for generated visit summaries.
- Added SVG daily-summary markers and plain-text copying for the currently displayed past-record summaries.
- Added configurable columns for the “日ごとのまとめ” table, text copy, TSV copy, and print view, including selectable TideTrace and HeartWatch metrics, custom short labels, and saved display order.
- Added a past records and healthcare data view that temporarily loads HeartWatch summary CSV files, aligns them with TideTrace daily records, and supports text, TSV, and print-friendly output.
- Added editing for record date and time on medication, pain, and note 
- Added medication pain-change summaries to visit summaries, showing recorded before-and-after pain-score changes by medication without assessing medication effectiveness.
- Added copy and plain text download actions for visit summaries.
- Added time-of-day pain summaries to visit summaries, grouping pain records by late night/early morning, morning, afternoon, and night without assessing causes or medication effects.

### Changed
- Reduced record-row edit and delete actions to their previous compact size and simplified the healthcare-data section icon to a table.
- Aligned past-record pain summaries with record summaries by showing average pain before maximum pain on screen and in copied text.
- Improved record-summary readability by removing slash separators, showing average pain before maximum pain, and clarifying dose-group rows across screen, copy, text, and print output.
- Renamed the visit-summary screen to “記録の集計” and aligned its copy, print, and saved text labels.
- Moved health-history display settings before CSV import and clarified that the importer accepts HeartWatch summary CSV files.
- Replaced record-type emojis with reusable line SVG icons and unified management button labels.
- Updated medication, pain-state, and comparison-period settings to show existing entries first and open add/edit forms only when needed.
- Updated today’s and past record details to use compact, accessible rows with type icons and wrapping memo text.
- Updated the HeartWatch daily summary to show only imported HeartWatch dates, use shorter pain headers, add active-medication count columns with short medication labels, and include sleep bpm and waking HRV reference values.
- Updated visit-summary state-pain rows to prioritize higher average pain before maximum pain.
- Updated visit-summary time-of-day pain rows to match the state-pain summary detail level and shorten the late-night label.
- Past record range labels now match the dates that actually have records.
- Added maximum-pain day counts to state and dose pain sections in visit summaries.

### Fixed
- Fixed result actions appearing before data was generated and limited summary print views to their intended result content.
- Fixed visit summaries so renamed pain states stay in one group and corrected medication names appear consistently across medication summaries.
- Saved daily-summary display columns, order, and short labels now remain after reload and JSON restore.
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