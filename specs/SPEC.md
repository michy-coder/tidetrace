# TideTrace Specification

This document describes the current TideTrace implementation. It documents existing behavior only and does not define planned features.

## Purpose

TideTrace is a small static web app for local-first pain, medication, and note logging. It helps users record observations, review recent and past records, prepare descriptive record summaries, and export or restore their data.

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
- Medication buttons. The medication subsection heading remains in the markup for assistive technologies but is visually hidden.
- Pain score and pain-state controls. The pain subsection heading remains in the markup for assistive technologies but is visually hidden. The pain score field is labeled `痛みスコア`, and the pain-state field is labeled `状態`.
- A shared optional memo field for medication, pain, or note records. Its `メモ（任意）` label remains associated with the memo textarea for assistive technologies but is visually hidden.
- Today's records.
- A collapsed past-records section.
- A collapsed 記録の集計 section.
- Management controls for backup, CSV export, settings, periods, and deleting all data.

Today's records and expanded past-record details use the same record-row display. Each row separates the time, record type, record body, and edit/delete actions. Pain, medication, and standalone note rows are visually distinguished with reusable single-color line SVG icons, and each row also includes an accessible type name (`痛みの記録`, `服薬の記録`, or `メモ`) separate from the icon. Pain rows show the body as `スコア・状態`, followed by any memo text. Medication rows show the body as `薬名 量単位`, followed by any memo text. Standalone note rows show the note text as the body. Memo text is not truncated and wraps within the body column. Edit and delete actions are shown on the right side of each record row.

## Pain recording

- Pain score is selected from integers `0` through `10`.
- Pain state is selected from active pain-state options.
- The optional memo field is trimmed and saved as the event note.
- A pain record stores the selected pain-state option ID and snapshots the current state label.
- After saving, the shared memo field is cleared.
- A toast is shown and can undo the newly saved event for a short period.

## Medication recording

- The record input card keeps the “記録” heading as an accessible heading, but it is visually hidden.
- Active medication options are rendered as medication buttons, sorted by display order, label, and ID.
- Each medication button displays a single-color line SVG icon followed by `薬名` and has the accessible name `薬名を記録`. The pain and standalone memo action buttons also keep their text labels and add matching line SVG icons. These SVG icons use `currentColor` and are hidden from assistive technologies with their meaning preserved by button text or separate accessible type text.
- Pressing a medication button creates a medication event with the option ID, a snapshot of the current label, the option default amount, and unit.
- The optional memo field is trimmed and saved as the event note.
- After saving, the shared memo field is cleared.
- A toast is shown and can undo the newly saved event for a short period.
- The “time since last medication” section is based on the most recent medication event for each active option ID.
- The last-medication section displays only one of: no record, elapsed hours/minutes under 24 hours, or `1日以上` for 1440 minutes or more.
- The last-medication section does not display the previous medication date or time.

## Note recording

- A standalone note requires non-empty trimmed text in the shared memo field.
- A note event stores the trimmed text.
- After saving, the shared memo field is cleared.
- A toast is shown and can undo the newly saved event for a short period.

## Medication settings

Medication settings support adding, editing, and hiding/showing medication options. The settings UI shows the explanation, supplemental guidance, and registered medication list before the add/edit form. The add form is hidden until the user presses `新しい薬を追加`; editing a registered item opens the same form in edit mode. After a successful save or cancel, the form closes and the registered list and add button remain available.

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

Pain-state settings support adding, editing, and hiding/showing pain-state options. The settings UI shows the explanation, supplemental guidance, and registered pain-state list before the add/edit form. The add form is hidden until the user presses `新しい状態を追加`; editing a registered item opens the same form in edit mode. After a successful save or cancel, the form closes and the registered list and add button remain available.

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

- Periods can be added, edited, and deleted. The period settings UI uses the same list-first add/edit pattern as medication and pain-state settings: the registered period list appears before the add button, the form opens only for `新しい期間を追加` or editing, and the form closes after a successful save or cancel.
- A period requires a label, start date, and end date.
- Dates must be `YYYY-MM-DD` strings and start date must be on or before end date.
- Period date ranges cannot overlap existing period ranges.
- Deleting a period does not delete records.
- Periods can be selected in the visit-summary section to fill the summary date range.

## 記録の集計 behavior

記録の集計 summarizes pain and medication records for a selected date range. By default, the end date is yesterday and the start date is 29 days before that.

The current 記録の集計 includes:

- Range and day count.
- Medication totals and daily averages by medication/unit. Medication records with the same `medicationOptionId` are treated as the same medication, while medication totals and medication-dose pain summaries remain separated by unit. Legacy medication records without an option ID are grouped by their saved `medicationLabel`.
- Pain summaries by state. Pain records with the same `stateOptionId` are treated as the same state. Legacy pain records without an option ID are grouped by their saved `stateLabel`.
- Pain summaries by time of day.
- Pain summaries by medication dose grouping.
- Recorded before-and-after pain-score changes by medication when applicable.

When a current pain-state or medication setting exists for a saved option ID, 記録の集計 displays the current setting label. When the referenced setting no longer exists, 記録の集計 displays the saved snapshot label from the record. Individual record displays keep showing the name saved at the time of recording.

Summary metric items are separated with spacing rather than slash separators. Pain summary rows show average pain before maximum pain. State-based and time-based pain summary rows display recorded days as `記録 N日`. Medication-dose pain rows show the dose heading on its own line, followed by a metric row using `N日（痛み記録 N日）`, average pain, and maximum pain. The screen display, copied text, saved text, and print view use the same metric wording and order.

Summary text uses the `TideTrace 記録の集計` output title and can be copied or downloaded as a plain text file. Summary wording is intended to be descriptive and non-diagnostic, describing recorded values without assessing treatment effectiveness, causes, or severity. Screen, copied text, saved plain text, and print output use aligned summary wording and metric order.

Result actions are shown only after a summary is successfully generated. The actions support copying, plain-text saving, and browser-standard printing without changing the generated aggregation content.

The focused print view for a generated 記録の集計 shows the `記録の集計` heading and generated aggregation result, including the current explanatory text attached to the medication, pain-by-state, pain-by-time, pain-by-dose, and pain-change sections. Printing uses the current generated result rather than recalculating the summary, and the screen returns to normal after the print UI closes.

## Past records behavior

The “過去の記録” view shows past TideTrace records by day. Daily summaries distinguish pain, medication, and memo rows with the same monochrome line SVG record-type icons used elsewhere in the app, while keeping hidden text labels for assistive technology. Daily pain summaries show average pain before maximum pain.

The currently displayed past-record daily summaries can be copied as plain text. The copied text includes the “過去の記録” heading, the visible date range, dates that have records, and available pain, medication, and memo summary lines. It is generated from summary data rather than expanded detail DOM, so opening or closing a day’s details does not change the copied text. The copied text uses written type labels such as `痛み`, `服薬`, and `メモ` instead of SVG icons.


## Past records and healthcare data behavior

The “過去の記録とヘルスケアデータ” view is shown below the visit summary. It places past TideTrace records and HeartWatch summary CSV healthcare reference values side by side by day for review. The wording is descriptive and does not assess causes, medication effects, severity, prediction, or whether care is needed.

The implementation supports temporary import of HeartWatch summary CSV files only. Imported healthcare data is kept only in memory for the current screen use and is not saved to `localStorage` or included in backups. Reloading or closing the page clears the imported healthcare data.

HeartWatch rows are joined by date using the first 10 characters of the CSV `ISO` value (`YYYY-MM-DD`). The implementation does not convert the `ISO` value to a JavaScript `Date` or UTC date before creating the join key. TideTrace records are joined by `localDate`. The daily summary table shows only dates that exist in the imported HeartWatch summary CSV, excludes today, and sorts dates oldest first.

The “表示項目” control is available before CSV import and appears before the `HeartWatch まとめCSVを読み込む` button. It edits the daily-summary column configuration as a draft until “保存” is pressed. “日付” is fixed as the first column and cannot be hidden, renamed, reordered, or stored as a selected column. Selected columns can be added with checkboxes, removed with row controls, and moved up or down without drag and drop. “初期表示に戻す” rebuilds the draft default from the currently active medication options and does not save until “保存” is pressed.

Selectable TideTrace metrics are daily pain maximum, average, minimum, and count; pain-state maximum, average, and count for every active or inactive pain-state option; one medication-event count for every active or inactive medication option; and standalone note count. Inactive medication and pain-state options remain available and are marked `（非表示中）`. Pain-state columns aggregate by `stateOptionId`. Medication columns count by `medicationOptionId`, with fallback exact matching against the recorded medication label snapshot for older medication events without an option id. Standalone note count counts only `note` events and does not count note text attached to pain or medication records. Combined medication totals, tablet totals, all-record totals, and memo contents are not daily-summary columns.

Selectable HeartWatch metrics use a stable internal catalog and exclude `index`, `ISO`, and `日付` as display metrics. Categories are `睡眠・起床`, `心拍`, `活動`, `血圧・体温・SpO2`, `血糖値`, and `体重・体組成`. Missing HeartWatch source headers and blank source cells display as blank cells, not `0`; sleep duration keeps the existing compact duration display.

Each selected metric has a short label shown in the table header and TSV header. Short labels are trimmed, must contain 1 to 8 visible Unicode characters, and must be unique after Unicode NFKC normalization and case-insensitive comparison. Invalid saves keep the draft and show a Japanese inline error. Table headers also expose the full metric name through accessible labels and titles.

The default configuration for new users and existing data without `settings.healthReviewColumns` is: `日付`, daily pain maximum, daily pain average, one medication count column for each currently active medication option, steps, sleep duration, sleep bpm, sleep HRV, and waking HRV. Defaults are built from the settings object being created, loaded, or imported. Inactive medications, pain-state metrics, daily pain minimum/count, standalone note count, and the other HeartWatch metrics are available but unchecked by default. Valid saved configurations preserve selected and unselected columns, display order, custom short labels, label modes, HeartWatch selections, TideTrace metric selections, and references to active or inactive medication and pain-state options.

The result actions are shown only after a HeartWatch summary CSV is successfully imported and at least one displayable row is generated. The actions support readable text copy, TSV copy, and browser-standard printing. Printing opens a focused result view that shows only the `日ごとのまとめ` heading and table, then returns to the normal screen after the print UI closes. The on-screen table, readable text copy, TSV copy, and print view all use the same saved selected columns, order, short labels, date rows, blank handling, and calculated TideTrace values. TSV headers exactly match the visible short labels, with fixed first header `日付`.

## Import/export behavior

### JSON backup export

- The app updates `settings.lastJsonExportedAtUtc`, saves data, and downloads a JSON file named `tide-trace-backup-YYYY-MM-DD.json`.
- The exported JSON is the full stored app data object.

### JSON backup restore/import

- Backup restore is available both during initial setup and from the management section.
- The app parses JSON, normalizes optional daily-summary display columns using the imported backup’s own medication and pain-state settings, validates the schema, replaces the current in-memory app data, and saves it to `localStorage`.
- Management-section restore asks for confirmation and warns that current browser records will be replaced.
- Invalid JSON or invalid data is rejected and does not replace current data.
- `normalizeImportedData` repairs missing or malformed optional `settings.healthReviewColumns` without dropping records, periods, option settings, export timestamps, or other unrelated settings. Valid saved column configurations are preserved, and JSON restore keeps the saved column configuration.

### CSV export

- CSV export is available for all records, pain records only, medication records only, or note records only.
- On a new page load, the CSV export target starts unselected and the CSV export button is disabled.
- The selected CSV export target is not saved; a new page load returns to the unselected state.
- The app creates and downloads a UTF-8 CSV with a BOM only when a valid CSV export target is selected, then updates `settings.lastCsvExportedAtUtc`, saves data, and updates the export status display.
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
- Opening the edit dialog moves focus inside the dialog to the dialog heading, not to an input.
- Opening the edit dialog by itself does not focus the date or time input.
- While the edit dialog is open, Tab and Shift+Tab cycle through focusable controls inside the dialog.
- Escape, the cancel button, and the dialog background close the edit dialog without saving.
- After saving or closing the edit dialog, focus returns to the edit starting point where possible, or to a stable records area if the edited row is no longer visible.
- Validation errors keep the edit dialog open, preserve entered form values, show the error in the alert area, and move focus to the problematic date or time input when the date or time is invalid.

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
