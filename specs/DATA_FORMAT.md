# TideTrace Data Format

This document describes the current TideTrace storage and export format. It documents existing behavior only and does not define planned features.

## Storage location

TideTrace stores the full app data object in browser `localStorage`.

| Key | Value |
| --- | --- |
| `tideTrace.data.v1` | JSON string containing the app data object |

There are no other app data `localStorage` keys in the current implementation.

## Top-level app data object

```json
{
  "schemaVersion": 1,
  "appName": "Tide Trace",
  "settings": {},
  "periods": [],
  "events": []
}
```

Required top-level fields:

| Field | Type | Notes |
| --- | --- | --- |
| `schemaVersion` | number | Must be exactly `1` to validate. |
| `appName` | string | Initial data uses `Tide Trace`. Validation only checks that it is a string. |
| `settings` | object | See settings structure below. |
| `periods` | array | See periods structure below. |
| `events` | array | See events structure below. |

## `schemaVersion`

Current schema version is `1`. Stored and imported data must have `schemaVersion: 1`; otherwise validation fails and the data is not loaded.

Unknown from current implementation: any migration behavior for schema versions other than `1`.

## Settings structure

Initial settings are created with this shape:

```json
{
  "medicationOptions": [],
  "painStateOptions": [],
  "setupCompletedAtUtc": "2026-07-04T00:00:00.000Z",
  "lastJsonExportedAtUtc": null,
  "lastCsvExportedAtUtc": null
}
```

Validated settings fields:

| Field | Type | Notes |
| --- | --- | --- |
| `medicationOptions` | array | Required. Each item must match the medication option format. |
| `painStateOptions` | array | Required. Each item must match the pain-state option format. |
| `lastJsonExportedAtUtc` | string or null | Required by validation. Updated before JSON backup download. |
| `lastCsvExportedAtUtc` | string or null | Required by validation. Updated before CSV download. |

Other settings fields used by current initial data:

| Field | Type | Notes |
| --- | --- | --- |
| `setupCompletedAtUtc` | string | Set when initial app data is created or setup is completed. Current validation does not require this field. |

## `medicationOptions`

Medication options are stored in `settings.medicationOptions`.

```json
{
  "id": "med_001",
  "label": "鎮痛薬A",
  "active": true,
  "defaultAmount": 1,
  "unit": "錠",
  "sortOrder": 1
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Initial IDs use `med_###`; later IDs use a timestamp/random pattern. |
| `label` | string | Display label. New medication events snapshot this into `medicationLabel`. |
| `active` | boolean | Controls whether the option appears as a medication button. |
| `defaultAmount` | number | Must be finite. Saved into new medication events as `amount`. |
| `unit` | string | Saved into new medication events as `unit`. |
| `sortOrder` | number | Must be finite. Used for display ordering. |

## `stateOptions` / `painStateOptions`

The current data field is `settings.painStateOptions`. Some UI text calls these “pain states”; there is no separate `stateOptions` key in the current implementation.

Pain-state options are stored in `settings.painStateOptions`.

```json
{
  "id": "ps_001",
  "label": "安静時",
  "active": true,
  "sortOrder": 1
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Initial IDs use `ps_###`; later IDs use a timestamp/random pattern. |
| `label` | string | Display label. New pain events snapshot this into `stateLabel`. |
| `active` | boolean | Controls whether the option appears in the pain-state selector. |
| `sortOrder` | number | Must be finite. Used for display ordering. |

## Events structure

Events are stored in the top-level `events` array. Event IDs are generated with `crypto.randomUUID()` when available, otherwise with a timestamp/random fallback.

All event types share these fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | Yes | Event identifier. |
| `type` | string | Yes | One of `pain`, `medication`, or `note`. |
| `recordedAtUtc` | string | Yes | ISO timestamp for the recorded date/time. |
| `localDate` | string | Yes | `YYYY-MM-DD`. New records use the Asia/Tokyo date. Edited records use the browser-created date/time value converted to ISO for `recordedAtUtc`. |
| `localTime` | string | Yes | `HH:mm`. New records use the Asia/Tokyo time. |
| `timezone` | string | Yes | New records use `Asia/Tokyo`. |
| `createdAtUtc` | string | Yes | Creation timestamp. |
| `updatedAtUtc` | string | Yes | Creation timestamp initially; updated on edit. |
| `note` | string | Conditional | Optional for pain and medication events; required for note events. |

### Pain event fields

```json
{
  "id": "...",
  "recordedAtUtc": "2026-07-04T00:00:00.000Z",
  "localDate": "2026-07-04",
  "localTime": "09:00",
  "timezone": "Asia/Tokyo",
  "createdAtUtc": "2026-07-04T00:00:00.000Z",
  "updatedAtUtc": "2026-07-04T00:00:00.000Z",
  "type": "pain",
  "painScore": 5,
  "stateOptionId": "ps_001",
  "stateLabel": "安静時",
  "note": ""
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `painScore` | number | Must validate between `0` and `10`. UI creates integer values. |
| `stateOptionId` | string | Required. |
| `stateLabel` | string | Optional by validation; current new records set it. |
| `note` | string | Optional by validation; current new records set trimmed text, possibly empty. |

### Medication event fields

```json
{
  "id": "...",
  "recordedAtUtc": "2026-07-04T00:00:00.000Z",
  "localDate": "2026-07-04",
  "localTime": "09:00",
  "timezone": "Asia/Tokyo",
  "createdAtUtc": "2026-07-04T00:00:00.000Z",
  "updatedAtUtc": "2026-07-04T00:00:00.000Z",
  "type": "medication",
  "medicationOptionId": "med_001",
  "medicationLabel": "鎮痛薬A",
  "amount": 1,
  "unit": "錠",
  "note": ""
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `medicationOptionId` | string | Optional by validation; current new records set it. |
| `medicationLabel` | string | Optional by validation; current new records set it. |
| `amount` | number | Optional by validation; current new records set it from option `defaultAmount`. |
| `unit` | string | Optional by validation; current new records set it from option `unit`. |
| `note` | string | Optional by validation; current new records set trimmed text, possibly empty. |

### Note event fields

```json
{
  "id": "...",
  "recordedAtUtc": "2026-07-04T00:00:00.000Z",
  "localDate": "2026-07-04",
  "localTime": "09:00",
  "timezone": "Asia/Tokyo",
  "createdAtUtc": "2026-07-04T00:00:00.000Z",
  "updatedAtUtc": "2026-07-04T00:00:00.000Z",
  "type": "note",
  "note": "User-entered note text"
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `note` | string | Required for note events. UI requires non-empty trimmed text for standalone notes. |

## Periods structure

Periods are stored in the top-level `periods` array.

```json
{
  "id": "...",
  "label": "Period label",
  "startDate": "2026-07-01",
  "endDate": "2026-07-31",
  "note": ""
}
```

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Generated with `crypto.randomUUID()` when available, otherwise timestamp/random fallback. |
| `label` | string | Required by validation and by the period form. |
| `startDate` | string | Must be `YYYY-MM-DD`. |
| `endDate` | string | Must be `YYYY-MM-DD` and on or after `startDate`. |
| `note` | string | Required by validation; form stores trimmed text, possibly empty. |

The current validator rejects overlapping period date ranges.

## JSON backup format

JSON backup export downloads the full app data object as pretty-printed JSON. The filename is:

```text
tide-trace-backup-YYYY-MM-DD.json
```

Before download, the app sets `settings.lastJsonExportedAtUtc` to the current ISO timestamp and saves the updated app data.

JSON restore/import accepts only data that passes current validation. Import replaces the whole stored app data object with the imported object.

## CSV export format

CSV export writes UTF-8 CSV with a byte order mark. Filenames use:

```text
tide-trace-{type}-YYYYMMDD-HHMM.csv
```

Rows are sorted ascending by `localDate + localTime + createdAtUtc`. Values containing commas, quotes, or line breaks are CSV-escaped with doubled quotes.

### All records CSV

Type selector value: `all`  
Filename part: `all`

Headers:

```text
id,local_date,local_time,recorded_at_utc,timezone,type,pain_score,state_option_label,medication_option_label,note,created_at_utc,updated_at_utc,schema_version
```

### Pain CSV

Type selector value: `pain`  
Filename part: `pain`

Headers:

```text
id,local_date,local_time,recorded_at_utc,timezone,pain_score,state_option_label,note,created_at_utc,updated_at_utc,schema_version
```

### Medication CSV

Type selector value: `medication`  
Filename part: `medication`

Headers:

```text
id,local_date,local_time,recorded_at_utc,timezone,medication_option_label,note,created_at_utc,updated_at_utc,schema_version
```

Medication CSV does not currently include `amount`, `unit`, or `medicationOptionId` columns.

### Notes CSV

Type selector value: `note`  
Filename part: `notes`

Headers:

```text
id,local_date,local_time,recorded_at_utc,timezone,note,created_at_utc,updated_at_utc,schema_version
```

## Compatibility and migration policy

Current implementation behavior:

- `loadStoredData()` ignores invalid stored data and shows setup instead.
- JSON import rejects invalid data and leaves current data unchanged.
- `normalizeImportedData()` currently returns data unchanged; no migrations are implemented.
- Validation requires schema version `1`.
- Validation requires known required fields but does not explicitly strip unknown extra fields.
- Event display falls back to current option labels when snapshot labels are absent, and to “unknown” Japanese labels when an option cannot be found.
- CSV export is not a complete backup format. JSON backup is the format that preserves settings, periods, event IDs, option IDs, amounts, units, and export timestamps.

Unknown from current implementation: compatibility guarantees for future schemas or future storage keys.
