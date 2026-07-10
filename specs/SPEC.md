# TideTrace Specification

This document describes the current TideTrace implementation. It documents existing behavior only and does not define planned features.

## Purpose

TideTrace is a small static web app for local-first pain, medication, and note logging. It helps users record observations, review recent and past records, prepare descriptive visit summaries, and export or restore their data.

## Non-goals

TideTrace does not provide:

- Medical advice, diagnosis, treatment recommendations, medication timing advice, emergency triage, or severity judgment.
- Server-side storage or external sync for user-entered records.
- External APIs for app features or record processing.
- Third-party application libraries.

Cloudflare Web Analytics may be present in the published page for public page-usage analytics. User-entered TideTrace records are stored locally and are not sent to a TideTrace application server.

## Local-first privacy model

- The app runs as a static GitHub Pages app from `docs/`.
- The current implementation stores TideTrace app data in browser `localStorage` under `tideTrace.data.v1`.
- Pain records, medication records, notes, periods, and settings are not sent to a TideTrace application server.
- Users are warned that browser or device conditions can remove local records and that private browsing may not retain records.
- Users can manually export a JSON backup or CSV files.

## Main user flows

### First use

If no valid stored data exists, the setup screen is shown. The user can:

- Confirm or edit initial medication buttons.
- Confirm or edit initial pain-state labels.
- Start with those settings.
- Restore from a TideTrace JSON backup.

Setup requires at least one medication option and at least one pain-state option.

### Daily recording and review

After setup, the app shows:

- Time since the last record for each active medication option.
- Medication buttons.
- Pain score and pain-state controls.
- A shared optional memo field for medication, pain, or note records.
- Today's records.
- A collapsed past-records section.
- A collapsed visit-summary section.
- Management controls for backup, CSV export, settings, periods, and deleting all data.

## Pain recording

- Pain score is selected from integers `0` through `10`.
- Pain state is selected from active pain-state options.
- The optional memo field is trimmed and saved as the event note.
- A pain record stores the selected pain-state option ID and snapshots the current state label.
- After saving, the shared memo field is cleared.
- A toast is shown and can undo the newly saved event for a short period.

## Medication recording

- Active medication options are rendered as medication buttons, sorted by display order, label, and ID.
- Pressing a medication button creates a medication event with the option ID, a snapshot of the current label, the option default amount, and unit.
- The optional memo field is trimmed and saved as the event note.
- After saving, the shared memo field is cleared.
- A toast is shown and can undo the newly saved event for a short period.
- The “time since last medication” section is based on the most recent medication event for each active option ID.

## Note recording

- A standalone note requires non-empty trimmed text in the shared memo field.
- A note event stores the trimmed text.
- After saving, the shared memo field is cleared.
- A toast is shown and can undo the newly saved event for a short period.

## Medication settings

Medication settings support adding, editing, and hiding/showing medication options.

Each option has:

- ID.
- Label.
- Active flag.
- Default amount.
- Unit.
- Sort order.

Validation requires a non-empty label, numeric default amount, and numeric sort order. The current implementation accepts any finite numeric default amount and sort order in the management form.

Hidden medication options do not appear as new-record buttons. Existing records remain in stored events and can still be displayed, exported, and summarized.

The UI advises users to hide an old medication option and add a new one instead of overwriting names when switching to a different medication.

## Pain state settings

Pain-state settings support adding, editing, and hiding/showing pain-state options.

Each option has:

- ID.
- Label.
- Active flag.
- Sort order.

Validation requires a non-empty label and numeric sort order.

Hidden pain-state options do not appear in the new pain-record selector. Existing records remain in stored events and can still be displayed, exported, and summarized.

The UI advises users to hide an old state and add a new one instead of overwriting names when switching to a different state meaning.

## Period comparison

The app stores “condition comparison periods” with a label, start date, end date, and note.

- Periods can be added, edited, and deleted.
- A period requires a label, start date, and end date.
- Dates must be `YYYY-MM-DD` strings and start date must be on or before end date.
- Period date ranges cannot overlap existing period ranges.
- Deleting a period does not delete records.
- Periods can be selected in the visit-summary section to fill the summary date range.

## Visit summary behavior

The visit summary is generated for a selected date range. By default, the end date is yesterday and the start date is 29 days before that.

The current summary includes:

- Range and day count.
- Medication totals and daily averages by medication/unit.
- Pain summaries by state.
- Pain summaries by time of day.
- Pain summaries by medication dose grouping.
- Recorded before-and-after pain-score changes by medication when applicable.

Summary text can be copied or downloaded as a plain text file. Summary wording is intended to be descriptive and non-diagnostic, describing recorded values without assessing treatment effectiveness, causes, or severity.


## Past records and healthcare data behavior

The “過去の記録とヘルスケアデータ” view is shown below the visit summary. It is intended to place past TideTrace records and HeartWatch-style healthcare reference values side by side by day for review. The wording is descriptive and does not assess causes, medication effects, severity, prediction, or whether care is needed.

The current implementation supports temporary import of HeartWatch daily CSV files only. Detailed HeartWatch CSV files, Apple Healthcare exports, graph display, and heart-rate display around pain or medication events are not implemented. Imported healthcare data is kept only in memory for the current screen use and is not saved to `localStorage` or included in backups. Reloading or closing the page clears the imported healthcare data.

The view excludes today’s date because the day is not complete. Today is determined with the same Asia/Tokyo date helper used for TideTrace records.

HeartWatch rows are joined by date using the first 10 characters of the CSV `ISO` value (`YYYY-MM-DD`). The implementation does not convert the `ISO` value to a JavaScript `Date` or UTC date before creating the join key. TideTrace records are joined by the event `localDate` field.

The daily summary table shows only dates that exist in the imported HeartWatch CSV, excluding today, sorted oldest first. TideTrace-only dates are not added as rows. Columns are: date (`日付`), maximum TideTrace pain score (`最大`), average TideTrace pain score rounded to one decimal place (`平均`), one medication-event count column for each active medication option, steps (`歩数`), sleep duration (`睡眠`), sleep bpm (`睡bpm`), sleep HRV (`睡HRV`), and waking HRV (`起HRV`). Pain cells remain blank when there are no pain records for a HeartWatch date. Missing HeartWatch values remain blank and are not converted to zero. Note contents are not shown.

Medication count columns use active medication options sorted by the medication-button order: `sortOrder`, then `label`, then `id`. Column headers use short labels derived from the trimmed medication label, normally the first two visible characters. If short labels duplicate, the implementation extends labels where possible and then appends numeric suffixes if needed. Medication events are counted by `medicationOptionId` when available, with fallback exact matching against the recorded medication label snapshot for older events without an option id. The counts describe recorded medication events only and do not assess effects, timing, or treatment.

Available actions are:

- Copy readable plain text for the daily summary using the same HeartWatch-date filtering, columns, medication short labels, and blank-value handling as the table.
- Copy TSV for spreadsheet paste. TSV headers match the displayed table headers.
- Show a print-friendly display with the same rows and columns; users can save PDF files through the browser’s share or print feature.

## Import/export behavior

### JSON backup export

- The app updates `settings.lastJsonExportedAtUtc`, saves data, and downloads a JSON file named `tide-trace-backup-YYYY-MM-DD.json`.
- The exported JSON is the full stored app data object.

### JSON backup restore/import

- Backup restore is available both during initial setup and from the management section.
- The app parses JSON, validates the schema, replaces the current in-memory app data, and saves it to `localStorage`.
- Management-section restore asks for confirmation and warns that current browser records will be replaced.
- Invalid JSON or invalid data is rejected and does not replace current data.
- `normalizeImportedData` currently returns imported data unchanged.

### CSV export

- CSV export is available for all records, pain records only, medication records only, or note records only.
- The app downloads a UTF-8 CSV with a BOM, then updates `settings.lastCsvExportedAtUtc`, saves data, and updates the export status display.
- CSV rows are sorted ascending by local date, local time, and creation timestamp.
- CSV export is an output format only; CSV import is not implemented.

## Editing and deletion behavior

### Event editing

Medication, pain, and note events can be edited from today’s records and past-record details.

- All event types can edit date, time, and memo text.
- Pain events can edit pain score and pain state.
- Medication events can edit medication option.
- Changing a medication option also updates the event label, amount, and unit from the selected option.
- Changing a pain state also updates the event state label from the selected option.
- Saving an edit updates `updatedAtUtc`.

### Event deletion

- Individual events can be deleted after a confirmation dialog.
- Deleting an event removes it from `events` and saves the updated data.

### Period deletion

- Deleting a period requires confirmation and does not delete records.

### Delete all data

- The management section has an all-data delete action.
- After confirmation, the app removes `tideTrace.data.v1` from `localStorage`, clears in-memory app data, and returns to setup.

## UI wording principles

- The app UI is currently Japanese, with English repository documentation.
- Health-context wording should stay limited to recording, organizing, and reviewing user-entered observations.
- Wording should avoid diagnosis, treatment recommendations, medication timing advice, emergency guidance, and effectiveness claims.
- Summaries may calculate and group recorded data but should not interpret it as medical conclusions.

## Compatibility notes

- Current schema version is `1`.
- The app validates stored or imported data before loading it.
- Unknown top-level or nested fields are not explicitly removed by validation and may remain if the required structure is valid.
- Existing option labels are snapshotted into new events so past records can retain readable labels if settings change.
- Current import normalization performs no migration. Unknown from current implementation: behavior for future schema versions.
