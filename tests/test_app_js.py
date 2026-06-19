import json
import subprocess
import textwrap
from pathlib import Path


APP_JS = Path(__file__).parents[1] / "docs" / "app.js"


def run_app_js(assertions: str) -> None:
    source = APP_JS.read_text()
    source = source[: source.rfind("wireEvents();")]
    script = source + "\n" + textwrap.dedent(assertions)
    subprocess.run(["node", "-e", script], check=True, text=True)


def test_medication_normalization_sorting_and_validation() -> None:
    data = {
        "schemaVersion": 1,
        "appName": "Tide Trace",
        "settings": {
            "painStateOptions": [{"id": "pain", "label": "Pain", "active": True}],
            "medicationOptions": [
                {"label": "B", "isActive": False},
                {"id": "med_a", "label": "A", "active": True, "sortOrder": 1},
                {"id": "med_c", "label": "C", "active": True, "sortOrder": 1},
            ],
        },
        "periods": [],
        "events": [],
    }
    run_app_js(
        f"""
        const assert = require('node:assert/strict');
        const data = normalizeImportedData({json.dumps(data)});
        assert.deepEqual(data.settings.medicationOptions[0], {{
          id: 'med_imported_1',
          label: 'B',
          defaultAmount: 1,
          unit: '',
          active: false,
          sortOrder: 1
        }});
        assert.equal(validateData(data), true);
        appData = data;
        assert.deepEqual(activeMedicationOptions().map((option) => option.id), ['med_a', 'med_c']);
        """
    )


def test_medication_snapshot_display_csv_and_edit_options() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          schemaVersion: 1,
          settings: {
            painStateOptions: [],
            medicationOptions: [
              { id: 'active', label: 'Current', defaultAmount: 2, unit: 'units', active: true, sortOrder: 1 },
              { id: 'inactive', label: 'Hidden', defaultAmount: 1, unit: '', active: false, sortOrder: 2 }
            ]
          },
          periods: [],
          events: []
        };
        const snapshot = {
          type: 'medication',
          medicationOptionId: 'active',
          medicationLabel: 'Recorded',
          amount: 1,
          unit: 'unit',
          localTime: '10:00',
          note: ''
        };
        assert.equal(medicationEventLabel(snapshot), 'Recorded');
        assert.match(eventText(snapshot), /Recorded \\/ 1unit/);
        assert.equal(csvValueForHeader(snapshot, 'medication_option_label'), 'Recorded');
        assert.equal(medicationEventLabel({ medicationOptionId: 'inactive' }), 'Hidden');
        assert.equal(medicationEditOptions({ medicationOptionId: 'inactive' }).at(-1).displayLabel, 'Hidden（非表示）');
        assert.equal(
          medicationEditOptions({ medicationOptionId: 'missing', medicationLabel: 'Archived' }).at(-1).displayLabel,
          'Archived（設定なし）'
        );
        """
    )



def test_unedited_exported_backup_import_replaces_storage_and_preserves_data() -> None:
    data = {
        "schemaVersion": 1,
        "appName": "Tide Trace",
        "settings": {
            "painStateOptions": [{"id": "pain", "label": "Pain", "active": True}],
            "medicationOptions": [
                {"id": "med", "label": "Medication", "defaultAmount": 1, "unit": "unit", "active": True, "sortOrder": 1}
            ],
            "lastJsonExportedAtUtc": "2026-06-19T00:00:00.000Z",
            "lastCsvExportedAtUtc": None,
        },
        "periods": [{"id": "period", "label": "Compare", "startDate": "2026-06-01", "endDate": "2026-06-07", "note": ""}],
        "events": [
            {
                "id": "event-med",
                "type": "medication",
                "recordedAtUtc": "2026-06-19T00:00:00.000Z",
                "localDate": "2026-06-19",
                "localTime": "09:00",
                "timezone": "Asia/Tokyo",
                "createdAtUtc": "2026-06-19T00:00:00.000Z",
                "updatedAtUtc": "2026-06-19T00:00:00.000Z",
                "medicationOptionId": "med",
                "medicationLabel": "Medication",
                "amount": 1,
                "unit": "unit",
                "note": "",
            },
            {
                "id": "event-pain",
                "type": "pain",
                "recordedAtUtc": "2026-06-19T01:00:00.000Z",
                "localDate": "2026-06-19",
                "localTime": "10:00",
                "timezone": "Asia/Tokyo",
                "createdAtUtc": "2026-06-19T01:00:00.000Z",
                "updatedAtUtc": "2026-06-19T01:00:00.000Z",
                "painScore": 3,
                "stateOptionId": "pain",
                "note": "",
            },
        ],
    }
    run_app_js(
        f"""
        const assert = require('node:assert/strict');
        const backupText = JSON.stringify({json.dumps(data)});
        let savedText = null;
        let rendered = false;
        global.localStorage = {{ setItem(key, value) {{ savedText = value; }} }};
        global.document = {{
          getElementById(id) {{
            return {{
              textContent: '',
              classList: {{ add() {{}}, remove() {{}} }},
            }};
          }}
        }};
        startElapsedRefresh = () => {{}};
        render = () => {{ rendered = true; }};

        const errorElement = {{ textContent: '' }};
        const result = initializeFromText(backupText, errorElement);

        assert.equal(result, true);
        assert.equal(errorElement.textContent, '');
        assert.equal(rendered, true);
        assert.deepEqual(JSON.parse(savedText), appData);
        assert.equal(appData.events[0].medicationLabel, 'Medication');
        assert.equal(appData.events[0].amount, 1);
        assert.equal(appData.events[0].unit, 'unit');
        assert.equal(appData.events[1].painScore, 3);
        assert.equal(appData.periods[0].label, 'Compare');
        assert.equal(appData.settings.lastJsonExportedAtUtc, '2026-06-19T00:00:00.000Z');
        """
    )

def test_backup_import_request_cancel_does_not_open_picker() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let clicked = false;
        const input = {
          files: [],
          value: 'existing',
          click() { clicked = true; }
        };
        global.document = { getElementById(id) { return id === 'import-file' ? input : null; } };
        global.confirm = () => false;

        requestBackupImport();

        assert.equal(clicked, false);
        assert.equal(input.value, 'existing');
        """
    )

def test_backup_import_request_ok_opens_picker_without_selected_file() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let clicked = false;
        const input = {
          files: [],
          value: 'stale',
          click() { clicked = true; }
        };
        global.document = { getElementById(id) { return id === 'import-file' ? input : null; } };
        global.confirm = () => true;

        requestBackupImport();

        assert.equal(input.value, '');
        assert.equal(clicked, true);
        """
    )

def test_backup_import_request_ok_reads_already_selected_file() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let clicked = false;
        let selectedFile = null;
        const input = {
          files: [{ name: 'backup.json' }],
          value: 'backup.json',
          click() { clicked = true; }
        };
        global.document = { getElementById(id) { return id === 'import-file' ? input : null; } };
        global.confirm = () => true;
        global.FileReader = function FileReader() {
          this.readAsText = (file) => { selectedFile = file; };
        };

        requestBackupImport();

        assert.equal(clicked, false);
        assert.equal(selectedFile, input.files[0]);
        """
    )
