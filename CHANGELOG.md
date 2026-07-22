# Changelog

All notable changes to TideTrace will be documented in this file.

## Unreleased

### Added
- Added browser-standard printing and PDF saving for generated record summaries and the daily summary table.
- Added plain-text copying for the currently displayed past-record summaries.
- Added configurable columns for the daily summary table, text copy, TSV copy, and print view, including selectable TideTrace and HeartWatch metrics, custom short labels, and saved display order.
- Added a past records and healthcare data view that temporarily loads HeartWatch summary CSV files, aligns them with TideTrace daily records, and supports text, TSV, and print output.
- Added date and time editing for medication, pain, and note records.
- Added medication pain-change summaries to record summaries, showing recorded before-and-after pain-score changes by medication without assessing medication effectiveness.
- Added copy and plain-text download actions for record summaries.
- Added time-of-day pain summaries to record summaries, grouping pain records into overnight, morning, afternoon, and evening periods without assessing causes or medication effects.
- Added maximum-pain day counts to state-based and medication-dose pain summaries.
- Added a shared app icon, favicon, Apple touch icon, and web app manifest metadata.

### Changed
- Updated today’s and past record details to use compact, accessible rows with line SVG type icons and wrapping memo text.
- Updated past-record daily summaries to use SVG type markers and show average pain before maximum pain on screen and in copied text.
- Improved record-summary readability by removing slash separators, showing average pain before maximum pain, shortening day-count labels, and clarifying medication-dose rows across screen, copy, text, and print output.
- Renamed the summary screen from a medical-appointment label to a neutral record-summary label and aligned its screen, copy, print, saved-text, and filename wording.
- Sorted state-based pain summaries by average pain, then maximum pain.
- Updated time-of-day pain summaries to match the state-based summary detail level and shortened the late-night label.
- Improved past-record navigation with controls above and below the record list, year-inclusive range labels, and automatic scrolling after navigation.
- Moved health-history display settings before CSV import and clarified that the importer accepts HeartWatch summary CSV files.
- Updated the HeartWatch daily summary to show only imported HeartWatch dates, use shorter pain headers, include medication-count columns, and support sleep heart-rate and waking HRV values.
- Updated medication, pain-state, and comparison-period settings to show registered entries first and open add or edit forms only when needed.
- Updated section, settings, record-type, and action icons to use reusable monochrome line SVGs.

### Fixed
- Fixed edit-dialog keyboard behavior with Escape close, focus trapping, validation focus, and focus return after save or close.
- Fixed result actions appearing before data was generated and restricted print output to the intended result content.
- Fixed record summaries so renamed pain states remain in one group and current medication names appear consistently across medication summaries.
- Fixed saved daily-summary display columns, order, and short labels being lost after reload or JSON restore.
- Fixed past-record navigation to skip empty date gaps and show range labels based on dates that contain records.
- Fixed SVG icon class handling in Safari, preventing oversized medication buttons and missing record-type icons.

## v0.1.0 - 2026-06-26

### Added

- Initial public release of TideTrace.
- Added local-first pain, medication, and note logging.
- Added browser-based storage without external data transmission.
- Added JSON backup and CSV export.
- Added medical appointment summary.
- Added first-use setup flow.
- Added README, MIT License, and changelog.