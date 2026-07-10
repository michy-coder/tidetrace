import json
import subprocess
import tempfile
import textwrap
from pathlib import Path


APP_JS = Path(__file__).parents[1] / "docs" / "app.js"


def run_app_js(assertions: str) -> None:
    source = APP_JS.read_text()
    source = source[: source.rfind("wireEvents();")]
    script = source + "\n" + textwrap.dedent(assertions)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(script)
        script_path = handle.name
    try:
        subprocess.run(["node", script_path], check=True, text=True)
    finally:
        Path(script_path).unlink(missing_ok=True)


def test_backup_validation_rejects_legacy_option_completion() -> None:
    data = {
        "schemaVersion": 1,
        "appName": "Tide Trace",
        "settings": {
            "painStateOptions": [{"id": "pain", "label": "Pain", "active": True, "sortOrder": 1}],
            "medicationOptions": [
                {"label": "B", "isActive": False},
                {"id": "med_a", "label": "A", "active": True, "sortOrder": 1},
            ],
            "lastJsonExportedAtUtc": None,
            "lastCsvExportedAtUtc": None,
        },
        "periods": [],
        "events": [],
    }
    run_app_js(
        f"""
        const assert = require('node:assert/strict');
        const data = normalizeImportedData({json.dumps(data)});
        assert.deepEqual(data.settings.medicationOptions[0], {{ label: 'B', isActive: false }});
        assert.equal(validateData(data), false);
        """
    )


def test_backup_validation_rejects_missing_current_format_fields() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const valid = {
          schemaVersion: 1,
          appName: 'Tide Trace',
          settings: {
            painStateOptions: [{ id: 'pain', label: 'Pain', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med', label: 'Medication', defaultAmount: 1, unit: 'unit', active: true, sortOrder: 1 }],
            lastJsonExportedAtUtc: null,
            lastCsvExportedAtUtc: '2026-06-19T00:00:00.000Z'
          },
          periods: [{ id: 'period', label: 'Compare', startDate: '2026-06-01', endDate: '2026-06-07', note: '' }],
          events: [{
            id: 'event', type: 'pain', recordedAtUtc: '2026-06-19T00:00:00.000Z', localDate: '2026-06-19',
            localTime: '09:00', timezone: 'Asia/Tokyo', createdAtUtc: '2026-06-19T00:00:00.000Z',
            updatedAtUtc: '2026-06-19T00:00:00.000Z', painScore: 3, stateOptionId: 'pain', note: ''
          }]
        };
        assert.equal(validateData(valid), true);

        for (const key of ['lastJsonExportedAtUtc', 'lastCsvExportedAtUtc']) {
          const copy = structuredClone(valid);
          delete copy.settings[key];
          assert.equal(validateData(copy), false);
        }
        const noPeriods = structuredClone(valid);
        delete noPeriods.periods;
        assert.equal(validateData(noPeriods), false);
        const noPeriodNote = structuredClone(valid);
        delete noPeriodNote.periods[0].note;
        assert.equal(validateData(noPeriodNote), false);
        const noUpdated = structuredClone(valid);
        delete noUpdated.events[0].updatedAtUtc;
        assert.equal(validateData(noUpdated), false);
        const stringSort = structuredClone(valid);
        stringSort.settings.painStateOptions[0].sortOrder = '1';
        assert.equal(validateData(stringSort), false);
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
            "painStateOptions": [{"id": "pain", "label": "Pain", "active": True, "sortOrder": 1}],
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




def test_visit_summary_fills_blank_medication_units_from_current_settings() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            medicationOptions: [
              { id: 'med_001', label: 'Medication A', defaultAmount: 1, unit: 'tablet', active: true, sortOrder: 1 }
            ]
          },
          events: [
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: 'Medication A', amount: 1, unit: '', localDate: '2026-06-20' },
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: 'Medication A', amount: 1, unit: 'tablet', localDate: '2026-06-20' }
          ]
        };

        const rows = buildMedicationSummary('2026-06-20', '2026-06-20').filter((row) => row.total > 0);

        assert.equal(rows.length, 1);
        assert.equal(rows[0].label, 'Medication A');
        assert.equal(rows[0].unit, 'tablet');
        assert.equal(rows[0].total, 2);
        assert.equal(rows[0].dates.size, 1);
        """
    )


def test_visit_summary_keeps_multiple_non_empty_medication_units_separate() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            medicationOptions: [
              { id: 'med_001', label: 'Medication A', defaultAmount: 1, unit: 'tablet', active: true, sortOrder: 1 }
            ]
          },
          events: [
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: 'Medication A', amount: 1, unit: 'tablet', localDate: '2026-06-20' },
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: 'Medication A', amount: 1, unit: 'packet', localDate: '2026-06-20' }
          ]
        };

        const rows = buildMedicationSummary('2026-06-20', '2026-06-20').filter((row) => row.total > 0);

        assert.deepEqual(rows.map((row) => [row.unit, row.total]), [['packet', 1], ['tablet', 1]]);
        """
    )


def test_visit_summary_medication_display_omits_medication_days_but_keeps_average() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const elements = {
          'visit-summary-result': {
            innerHTML: '',
            children: [],
            appendChild(item) { this.children.push(item); }
          }
        };
        global.document = {
          getElementById(id) { return elements[id]; },
          createElement(tag) {
            return {
              tag,
              className: '',
              innerHTML: '',
              textContent: '',
              children: [],
              appendChild(item) { this.children.push(item); },
              append(...items) { this.children.push(...items); }
            };
          }
        };

        renderVisitSummaryResult('2026-06-01', '2026-06-07', 7, [
          { label: 'Medication A', total: 14, unit: 'tablet', dates: new Set(['2026-06-01', '2026-06-02']) }
        ], [], []);

        const block = elements['visit-summary-result'].children[0];
        const medicationItem = block.children.find((child) => child.className === 'visit-summary-medication-item');
        assert.match(medicationItem.innerHTML, /合計 14tablet \\/ 1日平均 2\\.00tablet/);
        assert.doesNotMatch(medicationItem.innerHTML, /服薬日数/);
        """
    )


def test_visit_summary_state_pain_groups_daily_by_resolved_state_label() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            painStateOptions: [
              { id: 'standing', label: 'Standing current', active: true },
              { id: 'sitting', label: 'Sitting current', active: false },
              { id: 'unused', label: 'Unused active', active: true }
            ]
          },
          events: [
            { type: 'pain', localDate: '2026-07-01', painScore: 4, stateOptionId: 'standing', stateLabel: '立位' },
            { type: 'pain', localDate: '2026-07-01', painScore: 8, stateOptionId: 'standing', stateLabel: '立位' },
            { type: 'pain', localDate: '2026-07-02', painScore: 6, stateOptionId: 'standing', stateLabel: '立位' },
            { type: 'pain', localDate: '2026-07-02', painScore: 8, stateOptionId: 'standing', stateLabel: '立位' },
            { type: 'pain', localDate: '2026-07-02', painScore: 3, stateOptionId: 'sitting' },
            { type: 'pain', localDate: '2026-07-03', painScore: 9, stateOptionId: 'missing' },
            { type: 'pain', localDate: '2026-07-04', painScore: 10, stateOptionId: 'standing', stateLabel: '範囲外' }
          ]
        };

        const rows = buildStatePainSummary('2026-07-01', '2026-07-03');

        assert.deepEqual(rows.map((row) => [row.label, row.recordDays, row.maxPain, row.maxPainDays, row.averagePain.toFixed(1)]), [
          ['不明な状態', 1, 9, 1, '9.0'],
          ['立位', 2, 8, 2, '6.5'],
          ['Sitting current', 1, 3, 1, '3.0']
        ]);
        assert.equal(rows.some((row) => row.label === 'Unused active'), false);
        assert.equal(rows.some((row) => row.label === '範囲外'), false);
        """
    )


def test_visit_summary_state_pain_display_uses_compact_labels_and_notice() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const block = { children: [], appendChild(item) { this.children.push(item); } };
        global.document = {
          createElement(tag) {
            return {
              tag,
              className: '',
              innerHTML: '',
              textContent: '',
              children: [],
              appendChild(item) { this.children.push(item); },
              append(...items) { this.children.push(...items); }
            };
          }
        };

        renderStatePainSummary(block, [
          { label: '排便後', recordDays: 6, maxPain: 9, maxPainDays: 3, averagePain: 7.6 }
        ]);

        const stateItem = block.children.find((child) => child.className === 'visit-summary-state-pain-item');
        const notice = block.children.at(-1);
        assert.match(stateItem.innerHTML, /排便後<\\/strong>：記録日数 6日 \\/ 最大 9\\(3日\\) \\/ 平均 7\\.6/);
        assert.doesNotMatch(stateItem.innerHTML, /最大痛み|平均痛み/);
        assert.equal(notice.className.includes('visit-summary-notice'), true);
        assert.equal(notice.textContent, '同じ日・同じ状態の痛みを日単位で集計しています。服薬前後や他の薬との併用条件は分けていません。');
        """
    )


def test_visit_summary_dose_pain_counts_max_pain_days_after_daily_grouping() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            medicationOptions: [
              { id: 'med_001', label: '薬A', defaultAmount: 1, unit: '錠', active: true, sortOrder: 1 }
            ]
          },
          events: [
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: '薬A', amount: 1, unit: '錠', localDate: '2026-07-01' },
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: '薬A', amount: 1, unit: '錠', localDate: '2026-07-02' },
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: '薬A', amount: 1, unit: '錠', localDate: '2026-07-03' },
            { type: 'pain', localDate: '2026-07-01', painScore: 7 },
            { type: 'pain', localDate: '2026-07-01', painScore: 7 },
            { type: 'pain', localDate: '2026-07-02', painScore: 5 },
            { type: 'pain', localDate: '2026-07-03', painScore: 7 }
          ]
        };

        const rows = buildDosePainSummary('2026-07-01', '2026-07-03');
        const oneTabletGroup = rows[0].doseGroups.find((group) => group.amount === 1);

        assert.equal(oneTabletGroup.maxPain, 7);
        assert.equal(oneTabletGroup.maxPainDays, 2);
        assert.equal(oneTabletGroup.painDays, 3);
        """
    )


def test_visit_summary_dose_pain_display_uses_compact_pain_labels_and_notice() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const block = { children: [], appendChild(item) { this.children.push(item); } };
        global.document = {
          createElement(tag) {
            return {
              tag,
              className: '',
              innerHTML: '',
              textContent: '',
              open: false,
              children: [],
              appendChild(item) { this.children.push(item); },
              append(...items) { this.children.push(...items); }
            };
          }
        };

        renderDosePainSummary(block, [
          {
            label: '薬A',
            unit: '錠',
            doseGroups: [
              { amount: 2, targetDays: 7, painDays: 5, maxPain: 7, maxPainDays: 2, averagePainTotal: 27 }
            ]
          }
        ]);

        const doseItem = block.children.find((child) => child.className === 'visit-summary-dose-pain-item');
        const doseRow = doseItem.children[1].children[0];
        const notice = block.children.at(-1);
        assert.match(doseRow.innerHTML, /対象 7日 \\/ 痛み記録あり 5日<br>最大 7\\(2日\\) \\/ 平均 5\\.4/);
        assert.doesNotMatch(doseRow.innerHTML, /最大痛み|平均痛み/);
        assert.equal(notice.className.includes('visit-summary-notice'), true);
        assert.equal(notice.textContent, '薬ごとに日単位で集計しています。他の薬との併用条件は分けていません。');
        """
    )



def test_visit_summary_time_pain_groups_by_local_time_and_restored_utc() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: { medicationOptions: [], painStateOptions: [] },
          events: [
            { type: 'pain', localDate: '2026-07-01', localTime: '00:00', painScore: 4 },
            { type: 'pain', localDate: '2026-07-01', localTime: '05:59', painScore: 9 },
            { type: 'pain', localDate: '2026-07-01', localTime: '06:00', painScore: 5 },
            { type: 'pain', localDate: '2026-07-02', localTime: '11:59', painScore: 7 },
            { type: 'pain', localDate: '2026-07-02', localTime: '12:00', painScore: 6 },
            { type: 'pain', localDate: '2026-07-03', localTime: '17:59', painScore: 8 },
            { type: 'pain', localDate: '2026-07-03', localTime: '18:00', painScore: 3 },
            { type: 'pain', localDate: '2026-07-04', localTime: '23:59', painScore: 5 },
            { type: 'pain', localDate: '2026-07-04', recordedAtUtc: '2026-07-03T15:30:00.000Z', painScore: 7 },
            { type: 'pain', localDate: '2026-07-04', painScore: 10 },
            { type: 'pain', localDate: '2026-07-04', localTime: '09:00', painScore: '8' }
          ]
        };

        const rows = buildTimePainSummary('2026-07-01', '2026-07-04');
        assert.deepEqual(rows.map((row) => row.label), ['深夜', '午前', '午後', '夜']);
        assert.deepEqual(rows.map((row) => [row.recordDays, row.count, row.maxPain, row.maxPainDays, row.averagePain.toFixed(1)]), [
          [2, 3, 9, 1, '6.7'],
          [2, 2, 7, 1, '6.0'],
          [2, 2, 8, 1, '7.0'],
          [2, 2, 5, 1, '4.0']
        ]);
        assert.equal(formatTimePainSummaryRow(rows[0]), '深夜：記録日数 2日 / 最大 9(1日) / 平均 6.7');
        """
    )


def test_visit_summary_time_pain_display_and_empty_notice() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const block = { children: [], appendChild(item) { this.children.push(item); } };
        global.document = {
          createElement(tag) {
            return { tag, className: '', innerHTML: '', textContent: '', children: [], appendChild(item) { this.children.push(item); } };
          }
        };

        renderTimePainSummary(block, [{ label: '午前', recordDays: 1, count: 2, maxPain: 8, maxPainDays: 1, averagePain: 6.5 }]);
        assert.equal(block.children[0].textContent, '時間帯別の痛み');
        assert.equal(block.children[1].textContent, '午前：記録日数 1日 / 最大 8(1日) / 平均 6.5');
        assert.equal(block.children[2].className, 'visit-summary-notice supplemental-text');
        assert.equal(block.children[2].textContent, '同じ日・同じ時間帯の痛みを日単位で集計しています。姿勢・状態・服薬前後・他の薬との併用条件は分けていません。');

        const emptyBlock = { children: [], appendChild(item) { this.children.push(item); } };
        renderTimePainSummary(emptyBlock, []);
        assert.equal(emptyBlock.children[1].className, 'empty');
        assert.equal(emptyBlock.children[1].textContent, '条件に合う痛み記録はありません。');
        """
    )


def test_visit_summary_pain_change_uses_required_windows_and_medication_groups() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            medicationOptions: [
              { id: 'med_a', label: '薬A', active: true, sortOrder: 1 },
              { id: 'med_b', label: '薬B', active: true, sortOrder: 2 }
            ]
          },
          events: [
            { type: 'pain', localDate: '2026-07-01', localTime: '08:00', painScore: 9 },
            { type: 'pain', localDate: '2026-07-01', localTime: '09:30', painScore: 8 },
            { type: 'medication', medicationOptionId: 'med_a', medicationLabel: '薬A', localDate: '2026-07-01', localTime: '10:00' },
            { type: 'pain', localDate: '2026-07-01', localTime: '11:00', painScore: 5 },
            { type: 'pain', localDate: '2026-07-01', localTime: '12:00', painScore: 4 },
            { type: 'pain', localDate: '2026-07-01', localTime: '12:30', painScore: 4 },
            { type: 'pain', localDate: '2026-07-02', localTime: '08:10', painScore: 6 },
            { type: 'medication', medicationOptionId: 'med_a', medicationLabel: '薬A', localDate: '2026-07-02', localTime: '09:00' },
            { type: 'pain', localDate: '2026-07-02', localTime: '10:30', painScore: 3 },
            { type: 'pain', localDate: '2026-07-03', localTime: '08:00', painScore: 7 },
            { type: 'medication', medicationOptionId: 'med_b', medicationLabel: '薬B', localDate: '2026-07-03', localTime: '09:00' },
            { type: 'pain', localDate: '2026-07-04', localTime: '10:00', painScore: 4 },
            { type: 'medication', medicationOptionId: 'med_b', medicationLabel: '薬B', localDate: '2026-07-04', localTime: '11:00' },
            { type: 'pain', localDate: '2026-07-04', localTime: '14:30', painScore: 2 },
            { type: 'pain', localDate: '2026-07-05', localTime: '08:00', painScore: 0 },
            { type: 'medication', medicationOptionId: 'med_b', medicationLabel: '薬B', localDate: '2026-07-05', localTime: '09:00' },
            { type: 'pain', localDate: '2026-07-05', localTime: '10:30', painScore: 0 }
          ]
        };

        const rows = buildMedicationPainChangeSummary('2026-07-01', '2026-07-05');

        assert.equal(rows.length, 1);
        assert.equal(rows[0].label, '薬A');
        assert.equal(rows[0].count, 2);
        assert.equal(rows[0].averageBefore.toFixed(1), '7.0');
        assert.equal(rows[0].averageAfter.toFixed(1), '3.5');
        assert.equal(Math.round(rows[0].averageChange), 50);
        assert.equal(Math.round(rows[0].medianChange), 50);
        """
    )


def test_visit_summary_pain_change_display_and_empty_notice() -> None:
    run_app_js(
        r"""
        const assert = require('node:assert/strict');
        const block = { children: [], appendChild(item) { this.children.push(item); } };
        global.document = {
          createElement(tag) {
            return {
              tag,
              className: '',
              innerHTML: '',
              textContent: '',
              children: [],
              appendChild(item) { this.children.push(item); },
              append(...items) { this.children.push(...items); }
            };
          }
        };

        renderMedicationPainChangeSummary(block, [
          { label: '薬A', count: 2, averageChange: 42.4, medianChange: 40, averageBefore: 7.75, averageAfter: 4.5 },
          { label: '薬B', count: 1, averageChange: -15.2, medianChange: -15.2, averageBefore: 5, averageAfter: 5.76 }
        ]);

        const items = block.children.filter((child) => child.className === 'visit-summary-pain-change-item');
        const notice = block.children.at(-1);
        assert.match(items[0].innerHTML, /薬A<\/strong>：対象 2回 \/ 平均 42%低下 \/ 中央 40%低下 \/ 前後 7\.8→4\.5/);
        assert.match(items[1].innerHTML, /薬B<\/strong>：対象 1回 \/ 15%上昇 \/ 前後 5→5\.8/);
        assert.equal(notice.textContent, '服薬前2時間以内と服薬後1〜3時間以内の痛み記録がそろう服薬だけを集計しています。姿勢・状態・他の薬との併用条件は分けていません。');

        const emptyBlock = { children: [], appendChild(item) { this.children.push(item); } };
        renderMedicationPainChangeSummary(emptyBlock, []);
        assert.equal(emptyBlock.children.find((child) => child.className === 'empty').textContent, '条件に合う服薬前後の痛み記録はありません。');
        """
    )

def test_last_medication_list_uses_active_sorted_options_and_compact_elapsed_text() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const RealDate = Date;
        const fixedNow = new RealDate('2026-06-20T12:00:00.000Z').getTime();
        global.Date = class extends RealDate {
          constructor(...args) { super(...args); }
          static now() { return fixedNow; }
        };
        const list = {
          children: [],
          innerHTML: '',
          appendChild(item) { this.children.push(item); }
        };
        global.document = {
          getElementById(id) { return id === 'last-medication-list' ? list : null; },
          createElement() { return { className: '', textContent: '' }; }
        };
        appData = {
          settings: {
            medicationOptions: [
              { id: 'hidden', label: 'Hidden', active: false, sortOrder: 1 },
              { id: 'active-b', label: 'B', active: true, sortOrder: 2 },
              { id: 'active-a', label: 'A', active: true, sortOrder: 1 },
              { id: 'active-none', label: 'No record', active: true, sortOrder: 3 }
            ]
          },
          events: [
            { type: 'medication', medicationOptionId: 'hidden', recordedAtUtc: '2026-06-20T11:55:00.000Z', localDate: '2026-06-20', localTime: '20:55' },
            { type: 'medication', medicationOptionId: 'active-b', recordedAtUtc: '2026-06-20T06:35:00.000Z', localDate: '2026-06-20', localTime: '15:35' },
            { type: 'medication', medicationOptionId: 'active-a', recordedAtUtc: '2026-06-18T22:00:00.000Z', localDate: '2026-06-19', localTime: '07:00' }
          ]
        };

        renderLastMedicationList();

        assert.deepEqual(list.children.map((item) => item.textContent), [
          'A：前回 6/19 / 1日以上',
          'B：前回 15:35 / 経過 5時間25分',
          'No record：記録なし'
        ]);
        global.Date = RealDate;
        """
    )

def test_management_disclosure_summaries_show_counts() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const elements = {
          'medication-settings-summary': { textContent: '' },
          'comparison-period-summary': { textContent: '' }
        };
        global.document = { getElementById(id) { return elements[id]; } };
        appData = {
          settings: {
            medicationOptions: [
              { id: 'visible-a', active: true },
              { id: 'hidden', active: false },
              { id: 'visible-b', active: true }
            ]
          },
          periods: [
            { id: 'period-a' },
            { id: 'period-b' }
          ],
          events: []
        };

        renderMedicationSettingsSummary();
        renderComparisonPeriodSummary();

        assert.equal(elements['medication-settings-summary'].textContent, '薬設定　表示中2件 / 非表示1件');
        assert.equal(elements['comparison-period-summary'].textContent, '体調比較用期間の設定　登録済み2件');
        """
    )

def test_visit_summary_default_range_is_recent_30_days_ending_yesterday_with_yesterday_end_mode() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-21T00:00:00.000Z', localDate: '2026-06-21', localTime: '09:00' });
        const elements = {
          'summary-start-date': { value: '' },
          'summary-end-date': { value: '', disabled: false, hidden: false },
          'summary-end-yesterday': { checked: false },
          'summary-end-custom': { checked: false },
          'summary-end-yesterday-label': { textContent: '' },
          'summary-period-picker': { innerHTML: '', append() {} }
        };
        global.document = { getElementById(id) { return elements[id]; } };
        appData = { periods: [] };

        ensureSummaryDefaults();

        assert.equal(elements['summary-start-date'].value, '2026-05-22');
        assert.equal(elements['summary-end-date'].value, '2026-06-20');
        assert.equal(elements['summary-end-yesterday'].checked, true);
        assert.equal(elements['summary-end-custom'].checked, false);
        assert.equal(elements['summary-end-date'].disabled, true);
        assert.equal(elements['summary-end-date'].hidden, true);
        assert.equal(elements['summary-end-yesterday-label'].textContent, '昨日（2026/06/20）');
        """
    )


def test_visit_summary_yesterday_end_mode_sets_end_date_to_yesterday() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-21T00:00:00.000Z', localDate: '2026-06-21', localTime: '09:00' });
        const elements = {
          'summary-end-date': { value: '2026-06-20', disabled: false, hidden: false },
          'summary-end-yesterday': { checked: true },
          'summary-end-yesterday-label': { textContent: '' }
        };
        global.document = { getElementById(id) { return elements[id]; } };

        updateSummaryEndDateMode();

        assert.equal(elements['summary-end-date'].value, '2026-06-20');
        assert.equal(elements['summary-end-date'].disabled, true);
        assert.equal(elements['summary-end-date'].hidden, true);
        assert.equal(elements['summary-end-yesterday-label'].textContent, '昨日（2026/06/20）');
        """
    )


def test_visit_summary_period_picker_copies_range_as_custom_end_date() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-21T00:00:00.000Z', localDate: '2026-06-21', localTime: '09:00' });
        const elements = {
          'summary-period-picker': { innerHTML: '', children: [], append(...items) { this.children.push(...items); } },
          'summary-start-date': { value: '' },
          'summary-end-date': { value: '', disabled: true, hidden: true },
          'summary-end-custom': { checked: false },
          'summary-end-yesterday': { checked: true },
          'summary-end-yesterday-label': { textContent: '' }
        };
        global.document = {
          getElementById(id) { return elements[id]; },
          createElement(tag) {
            return {
              tag,
              id: '',
              className: '',
              textContent: '',
              innerHTML: '',
              value: '',
              listeners: {},
              setAttribute(name, value) { this[name] = value; },
              addEventListener(type, listener) { this.listeners[type] = listener; }
            };
          }
        };
        appData = {
          periods: [
            { id: 'period-1', label: 'Compare', startDate: '2026-06-01', endDate: '2026-06-07' }
          ]
        };

        renderSummaryPeriodPicker();
        const select = elements['summary-period-picker'].children[1];
        select.value = 'period-1';
        select.listeners.change();

        assert.equal(elements['summary-start-date'].value, '2026-06-01');
        assert.equal(elements['summary-end-date'].value, '2026-06-07');
        assert.equal(elements['summary-end-custom'].checked, true);
        assert.equal(elements['summary-end-date'].disabled, false);
        assert.equal(elements['summary-end-date'].hidden, false);
        """
    )

def test_initial_setup_settings_filters_defaults_and_orders() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const result = buildInitialSetupSettings(
          [
            { label: '  Custom A  ', amount: '2.5', unit: ' 包 ' },
            { label: '   ', amount: 'bad', unit: '回' },
            { label: 'Custom B', amount: '', unit: '' }
          ],
          [' 安静 ', ' ', '歩行']
        );

        assert.equal(result.error, '');
        assert.deepEqual(result.medicationOptions, [
          { id: 'med_001', label: 'Custom A', active: true, defaultAmount: 2.5, unit: '包', sortOrder: 1 },
          { id: 'med_002', label: 'Custom B', active: true, defaultAmount: 1, unit: '錠', sortOrder: 2 }
        ]);
        assert.deepEqual(result.painStateOptions, [
          { id: 'ps_001', label: '安静', active: true, sortOrder: 1 },
          { id: 'ps_002', label: '歩行', active: true, sortOrder: 2 }
        ]);
        """
    )


def test_initial_setup_settings_validation_messages() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        assert.equal(
          buildInitialSetupSettings([{ label: '', amount: '1', unit: '錠' }], ['安静時']).error,
          '薬ボタンを1つ以上入力してください。'
        );
        assert.equal(
          buildInitialSetupSettings([{ label: '薬', amount: 'abc', unit: '錠' }], ['安静時']).error,
          '薬の量は0より大きい数値を入力してください。'
        );
        assert.equal(
          buildInitialSetupSettings([{ label: '薬', amount: '0', unit: '錠' }], ['安静時']).error,
          '薬の量は0より大きい数値を入力してください。'
        );
        assert.equal(
          buildInitialSetupSettings([{ label: '薬', amount: '1', unit: '錠' }], [' ']).error,
          '痛み状態を1つ以上入力してください。'
        );
        """
    )


def test_open_edit_event_panel_shows_fields_without_focus() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let focused = false;
        const fields = {
          innerHTML: '',
          querySelectorAll(selector) { return []; },
          querySelector(selector) { focused = true; return { focus() { focused = true; } }; }
        };
        const panel = { hidden: true };
        global.document = { getElementById(id) { return id === 'edit-event-fields' ? fields : panel; } };
        appData = {
          settings: { medicationOptions: [{ id: 'med', label: 'Medication', defaultAmount: 1, unit: 'tablet', active: true, sortOrder: 1 }], painStateOptions: [] },
          periods: [],
          events: [{
            id: 'event-med', type: 'medication', medicationOptionId: 'med', medicationLabel: 'Medication', amount: 1, unit: 'tablet',
            localDate: '2026-06-27', localTime: '23:45', recordedAtUtc: '2026-06-27T23:45:00.000Z',
            createdAtUtc: '2026-06-27T23:45:00.000Z', updatedAtUtc: '2026-06-27T23:45:00.000Z', note: ''
          }]
        };

        openEditEventPanel('event-med');

        assert.equal(panel.hidden, false);
        assert.equal(focused, false);
        assert.match(fields.innerHTML, /type="date" value="2026-06-27"/);
        assert.match(fields.innerHTML, /type="time" value="23:45"/);
        assert.equal(fields.innerHTML.includes('<label for="edit-medication-option">薬</label>'), true);
        assert.equal(fields.innerHTML.includes('<select id="edit-medication-option">'), true);
        assert.equal(fields.innerHTML.includes('<textarea id="edit-note" rows="4" placeholder="メモを入力"></textarea>'), true);
        assert.equal(fields.innerHTML.includes('日時を変更'), false);
        assert.equal(fields.innerHTML.includes('内容を変更'), false);
        assert.equal(fields.innerHTML.includes('メモを追加'), false);
        """
    )


def test_save_edited_event_without_visible_datetime_preserves_datetime_values() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const elements = {
          'edit-note': { value: ' changed ' },
          'edit-event-error': { textContent: '' },
          'edit-event-panel': { hidden: false },
          'edit-event-fields': { innerHTML: '' }
        };
        global.document = { getElementById(id) { return elements[id]; } };
        global.localStorage = { setItem() {} };
        render = () => {};
        showToast = () => {};
        appData = { settings: { medicationOptions: [], painStateOptions: [] }, periods: [], events: [{
          id: 'event-note', type: 'note', localDate: '2026-06-28', localTime: '00:10', recordedAtUtc: '2026-06-28T00:10:00.000Z',
          createdAtUtc: '2026-06-28T00:10:00.000Z', updatedAtUtc: '2026-06-28T00:10:00.000Z', note: 'original'
        }] };
        editingEventId = 'event-note';

        saveEditedEvent();

        const event = appData.events[0];
        assert.equal(event.localDate, '2026-06-28');
        assert.equal(event.localTime, '00:10');
        assert.equal(event.recordedAtUtc, '2026-06-28T00:10:00.000Z');
        assert.equal(event.createdAtUtc, '2026-06-28T00:10:00.000Z');
        assert.equal(event.note, 'changed');
        assert.notEqual(event.updatedAtUtc, '2026-06-28T00:10:00.000Z');
        """
    )

def test_validate_edited_date_time_rejects_empty_malformed_and_overflow_values() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');

        assert.equal(validateEditedDateTime('', '23:45').error, '日付を入力してください。');
        assert.equal(validateEditedDateTime('2026-06-27', '').error, '時刻を入力してください。');
        assert.equal(validateEditedDateTime('2026-6-27', '23:45').error, '日付はYYYY-MM-DD形式で入力してください。');
        assert.equal(validateEditedDateTime('2026-06-27', '3:45').error, '時刻はHH:mm形式で入力してください。');
        assert.equal(validateEditedDateTime('2026-02-30', '23:45').error, '有効な日付と時刻を入力してください。');
        assert.equal(validateEditedDateTime('2026-06-27', '24:00').error, '有効な日付と時刻を入力してください。');
        assert.equal(validateEditedDateTime('2026-06-27', '23:45').error, '');
        """
    )


def test_save_edited_event_updates_local_and_utc_times_without_changing_created_at() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const elements = {
          'edit-local-date': { value: '2026-06-27' },
          'edit-local-time': { value: '23:45' },
          'edit-medication-option': { value: 'med' },
          'edit-note': { value: ' corrected ' },
          'edit-event-error': { textContent: '' },
          'edit-event-panel': { hidden: false },
          'edit-event-fields': { innerHTML: '' }
        };
        global.document = { getElementById(id) { return elements[id]; } };
        global.localStorage = { setItem() {} };
        render = () => {};
        showToast = () => {};
        appData = {
          settings: { medicationOptions: [{ id: 'med', label: 'Medication', defaultAmount: 1, unit: 'tablet' }], painStateOptions: [] },
          periods: [],
          events: [{
            id: 'event-med', type: 'medication', medicationOptionId: 'med', medicationLabel: 'Medication', amount: 1, unit: 'tablet',
            localDate: '2026-06-28', localTime: '00:10', recordedAtUtc: '2026-06-28T00:10:00.000Z',
            createdAtUtc: '2026-06-28T00:10:00.000Z', updatedAtUtc: '2026-06-28T00:10:00.000Z', note: ''
          }]
        };
        editingEventId = 'event-med';

        saveEditedEvent();

        const event = appData.events[0];
        assert.equal(event.localDate, '2026-06-27');
        assert.equal(event.localTime, '23:45');
        assert.equal(event.recordedAtUtc, new Date('2026-06-27T23:45:00').toISOString());
        assert.equal(event.createdAtUtc, '2026-06-28T00:10:00.000Z');
        assert.notEqual(event.updatedAtUtc, '2026-06-28T00:10:00.000Z');
        assert.equal(event.note, 'corrected');
        """
    )


def test_save_edited_event_shows_error_and_does_not_save_invalid_date_time() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const elements = {
          'edit-local-date': { value: '2026-02-30' },
          'edit-local-time': { value: '23:45' },
          'edit-note': { value: 'changed' },
          'edit-event-error': { textContent: '' }
        };
        let saved = false;
        global.document = { getElementById(id) { return elements[id]; } };
        global.localStorage = { setItem() { saved = true; } };
        appData = { settings: { medicationOptions: [], painStateOptions: [] }, periods: [], events: [{
          id: 'event-note', type: 'note', localDate: '2026-06-28', localTime: '00:10', recordedAtUtc: '2026-06-28T00:10:00.000Z',
          createdAtUtc: '2026-06-28T00:10:00.000Z', updatedAtUtc: '2026-06-28T00:10:00.000Z', note: 'original'
        }] };
        editingEventId = 'event-note';

        saveEditedEvent();

        assert.equal(saved, false);
        assert.equal(elements['edit-event-error'].textContent, '有効な日付と時刻を入力してください。');
        assert.equal(appData.events[0].localDate, '2026-06-28');
        assert.equal(appData.events[0].note, 'original');
        """
    )

def test_edit_note_section_uses_single_memo_label_and_empty_textarea() -> None:
    run_app_js(
        r"""
        const assert = require('node:assert/strict');
        const html = editEventSectionHtml(editTextareaHtml(''));

        assert.equal((html.match(/<label for="edit-note">メモ<\/label>/g) || []).length, 1);
        assert.match(html, /<textarea id="edit-note" rows="4" placeholder="メモを入力"><\/textarea>/);
        assert.doesNotMatch(html, /<h3>メモ<\/h3>/);
        assert.doesNotMatch(html, /なし/);
        """
    )


def test_edit_panel_omits_redundant_section_headings() -> None:
    source = APP_JS.read_text()
    assert "editEventSectionHtml('日時'" not in source
    assert "editEventSectionHtml('内容'" not in source
    assert "editEventSectionHtml('メモ'" not in source
    assert "<h3>${escapeHtml(title)}</h3>" not in source


def test_edit_panel_does_not_call_date_or_time_picker_apis() -> None:
    source = APP_JS.read_text()
    assert ".showPicker(" not in source
    assert "$('edit-local-date').focus" not in source
    assert "$('edit-local-time').focus" not in source


def test_history_range_labels_use_actual_record_dates_and_skip_empty_ranges() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: { medicationOptions: [] },
          periods: [],
          events: [
            { id: 'recent-start', type: 'note', localDate: '2026-06-15', localTime: '09:00', note: 'start' },
            { id: 'recent-end', type: 'note', localDate: '2026-06-20', localTime: '09:00', note: 'end' },
            { id: 'older', type: 'note', localDate: '2026-03-12', localTime: '09:00', note: 'older' }
          ]
        };

        const current = { start: '2026-05-22', end: '2026-06-20', mode: 'older' };
        assert.equal(formatHistoryRangeLabel(current), '2026/06/15〜2026/06/20');

        const target = olderHistoryRange(current);
        assert.deepEqual(target, { start: '2026-02-11', end: '2026-03-12', mode: 'older' });
        assert.equal(formatHistoryRangeLabel(target), '2026/03/12');
        assert.equal(hasOlderHistory(target), false);
        """
    )


def test_history_navigation_renders_before_and_after_records() -> None:
    source = APP_JS.read_text()
    assert source.count("renderHistoryNavigation(today, list);") == 2
    assert "scrollHistoryToStart();" in source
    assert "formatFullDate(dateText)" in source


def test_visit_summary_text_uses_shared_summary_data_without_ui_labels() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          schemaVersion: 1,
          settings: {
            painStateOptions: [{ id: 'state', label: '安静時', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med', label: '薬A', defaultAmount: 1, unit: '錠', active: true, sortOrder: 1 }]
          },
          periods: [],
          events: [
            { id: 'm1', type: 'medication', localDate: '2026-02-16', localTime: '09:00', medicationOptionId: 'med', medicationLabel: '薬A', amount: 1, unit: '錠' },
            { id: 'p1', type: 'pain', localDate: '2026-02-16', localTime: '08:30', painScore: 6, stateOptionId: 'state', stateLabel: '安静時' },
            { id: 'p2', type: 'pain', localDate: '2026-02-16', localTime: '11:00', painScore: 3, stateOptionId: 'state', stateLabel: '安静時' }
          ]
        };
        const summary = buildVisitSummaryData('2026-02-16', '2026-02-16');
        const text = buildVisitSummaryText(summary);
        assert.match(text, /^Tide Trace 診察用サマリー/);
        assert.equal(text.includes('範囲：2026/02/16〜2026/02/16'), true);
        assert.equal(text.includes('服薬\\n薬A：合計 1錠 / 1日平均 1.00錠'), true);
        assert.equal(text.includes('状態別の痛み\\n安静時：記録日数 1日 / 最大 6(1日) / 平均 4.5'), true);
        assert.equal(text.includes('時間帯別の痛み\\n午前：記録日数 1日 / 最大 6(1日) / 平均 4.5'), true);
        assert.equal(text.includes('服薬前後の痛み変化\\n薬A：対象 1回 / 50%低下 / 前後 6→3'), true);
        assert.equal(text.includes('コピー'), false);
        assert.equal(text.includes('テキスト保存'), false);
        assert.equal(visitSummaryTextFilename(summary), 'tide-trace-summary-2026-02-16_2026-02-16.txt');
        """
    )

def test_visit_summary_actions_are_hidden_until_run_and_cleared_on_condition_change() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-21T00:00:00.000Z', localDate: '2026-06-21', localTime: '09:00' });
        appData = { schemaVersion: 1, settings: { medicationOptions: [], painStateOptions: [] }, periods: [], events: [] };
        const elements = {
          'summary-start-date': { value: '2026-06-01' },
          'summary-end-date': { value: '2026-06-07', disabled: false, hidden: false },
          'summary-end-yesterday': { checked: false },
          'summary-end-custom': { checked: true },
          'summary-end-yesterday-label': { textContent: '' },
          'visit-summary-actions': { hidden: true },
          'visit-summary-result': { innerHTML: '' },
          'visit-summary-message': { textContent: '', classList: { values: new Set(), toggle(name, on) { on ? this.values.add(name) : this.values.delete(name); }, remove(name) { this.values.delete(name); } } }
        };
        global.document = { getElementById(id) { return elements[id]; } };
        renderVisitSummaryResult = (startDate, endDate) => { elements['visit-summary-result'].innerHTML = `${startDate}_${endDate}`; };

        assert.equal(elements['visit-summary-actions'].hidden, true);
        runVisitSummary();
        assert.equal(elements['visit-summary-actions'].hidden, false);
        assert.equal(elements['visit-summary-result'].innerHTML, '2026-06-01_2026-06-07');
        assert.equal(currentVisitSummaryDataForAction().startDate, '2026-06-01');
        assert.equal(currentVisitSummaryTextForAction().includes('範囲：2026/06/01〜2026/06/07'), true);

        elements['summary-start-date'].value = '2026-06-02';
        handleVisitSummaryConditionChange();
        assert.equal(elements['visit-summary-actions'].hidden, true);
        assert.equal(elements['visit-summary-result'].innerHTML, '');
        assert.equal(currentVisitSummaryDataForAction(), null);
        assert.equal(currentVisitSummaryTextForAction(), '');
        """
    )


def test_visit_summary_copy_and_save_use_current_generated_text_without_rebuilding() -> None:
    run_app_js(
        """
        (async () => {
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-21T00:00:00.000Z', localDate: '2026-06-21', localTime: '09:00' });
        appData = { schemaVersion: 1, settings: { medicationOptions: [], painStateOptions: [] }, periods: [], events: [] };
        const elements = {
          'summary-start-date': { value: '2026-06-01' },
          'summary-end-date': { value: '2026-06-07', disabled: false, hidden: false },
          'summary-end-yesterday': { checked: false },
          'summary-end-custom': { checked: true },
          'summary-end-yesterday-label': { textContent: '' },
          'visit-summary-actions': { hidden: true },
          'visit-summary-result': { innerHTML: '' },
          'visit-summary-message': { textContent: '', classList: { toggle() {} } }
        };
        global.document = {
          getElementById(id) { return elements[id]; },
          createElement(tag) { return { tag, click() {}, set href(value) { this._href = value; }, set download(value) { this._download = value; } }; }
        };
        renderVisitSummaryResult = () => { elements['visit-summary-result'].innerHTML = 'rendered'; };
        let clipboardText = '';
        Object.defineProperty(globalThis, 'navigator', { value: { clipboard: { writeText(text) { clipboardText = text; return Promise.resolve(); } } }, configurable: true });
        let blobText = '';
        global.Blob = function(parts) { blobText = parts.join(''); };
        global.URL = { createObjectURL() { return 'blob:test'; }, revokeObjectURL() {} };
        global.showToast = () => {};

        runVisitSummary();
        const generatedText = currentVisitSummaryTextForAction();
        buildVisitSummaryData = () => { throw new Error('copy/save must not rebuild'); };
        await copyVisitSummary();
        saveVisitSummaryText();

        assert.equal(clipboardText, generatedText);
        assert.equal(blobText, generatedText);
        })();
        """
    )


def test_visit_summary_actions_are_below_run_button_and_initially_hidden() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    run_index = html.index('id="run-visit-summary"')
    actions_index = html.index('id="visit-summary-actions"')
    result_index = html.index('id="visit-summary-result"')
    assert run_index < actions_index < result_index
    assert 'id="visit-summary-actions" class="visit-summary-actions" aria-label="診察用サマリーの操作" hidden' in html



def test_static_asset_versions_are_current_for_column_editor_fix() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    assert 'href="styles.css?v=14"' in html
    assert 'src="app.js?v=14"' in html
    assert 'styles.css?v=13' not in html
    assert 'app.js?v=13' not in html


def test_heartwatch_csv_uses_iso_prefix_and_keeps_import_temporary() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let storageWrites = 0;
        global.localStorage = { getItem() { return null; }, setItem() { storageWrites += 1; } };
        const csv = '\uFEFFISO,日付,歩数,睡眠時間,睡眠-bpm,睡眠-心拍変動-ms,起床-心拍変動-ms\\n2026-06-15T23:00:00+09:00,6/15,5757,09:51:22,61,34,45\\n2026-06-16T04:00:00+09:00,6/16,2384,,58,29,';
        const parsed = parseHeartWatchCsv(csv);
        assert.equal(parsed.error, false);
        assert.equal(parsed.data.has('2026-06-15'), true);
        assert.equal(parsed.data.has('2026-06-16'), true);
        assert.equal(parsed.data.has('2026-06-14'), false);
        assert.equal(parsed.data.get('2026-06-15').sleep, '9:51');
        assert.equal(parsed.data.get('2026-06-16').sleep, '');
        assert.equal(storageWrites, 0);
        """
    )


def test_health_history_daily_summary_uses_heartwatch_dates_dynamic_medications_and_outputs() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-17T00:00:00.000Z', localDate: '2026-06-16', localTime: '09:00' });
        appData = {
          settings: { medicationOptions: [
            { id: 'inactive', label: '非表示', active: false, sortOrder: 0 },
            { id: 'med_b', label: 'カロナール', active: true, sortOrder: 2 },
            { id: 'med_a', label: 'ロキソニン', active: true, sortOrder: 1 }
          ] },
          events: [
            { type: 'pain', localDate: '2026-06-15', painScore: 8 },
            { type: 'pain', localDate: '2026-06-15', painScore: 5 },
            { type: 'pain', localDate: '2026-06-16', painScore: 9 },
            { type: 'medication', localDate: '2026-06-15', medicationOptionId: 'med_a', medicationLabel: 'ロキソニン' },
            { type: 'medication', localDate: '2026-06-15', medicationOptionId: 'med_a', medicationLabel: 'ロキソニン' },
            { type: 'medication', localDate: '2026-06-15', medicationLabel: 'カロナール' },
            { type: 'medication', localDate: '2026-06-15', medicationOptionId: 'inactive', medicationLabel: '非表示' },
            { type: 'pain', localDate: '2026-06-14', painScore: 10 },
            { type: 'medication', localDate: '2026-06-14', medicationOptionId: 'med_a', medicationLabel: 'ロキソニン' }
          ]
        };
        const parsed = parseHeartWatchCsv('ISO,歩数,睡眠時間,睡眠-bpm,睡眠-心拍変動-ms,起床-心拍変動-ms\\n2026-06-15T23:00:00+09:00,5757,09:51:00,61,34,45\\n2026-06-16T04:00:00+09:00,,08:04:00,,29,');
        const rows = buildHealthHistoryRows(parsed.data);
        assert.deepEqual(rows.map((row) => row.date), ['2026-06-15']);
        assert.equal(rows[0].painMax, 8);
        assert.equal(rows[0].painAverage, '6.5');
        assert.deepEqual(rows[0].medicationCounts, { med_a: '2', med_b: '1' });
        assert.equal(rows[0].steps, '5757');
        assert.equal(rows[0].sleepBpm, '61');
        assert.deepEqual(healthHistoryColumns().map((column) => column.label), ['日付', '最大', '平均', 'ロキ', 'カロ', '歩数', '睡眠', '睡bpm', '睡HRV', '起HRV']);
        assert.match(buildHealthHistoryTsv(rows), /^日付\t最大\t平均\tロキ\tカロ\t歩数\t睡眠\t睡bpm\t睡HRV\t起HRV\\n2026-06-15\t8\t6.5\t2\t1\t5757\t9:51\t61\t34\t45$/);
        assert.match(buildHealthHistoryText(rows), /日ごとのまとめ（2026-06-15〜2026-06-15）/);
        assert.equal(hasMissingHeartWatchDates(rows, parsed.data), false);
        """
    )


def test_health_history_medication_short_label_duplicates_and_blank_heartwatch_values() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-17T00:00:00.000Z', localDate: '2026-06-17', localTime: '09:00' });
        appData = {
          settings: { medicationOptions: [
            { id: 'med_a', label: 'ロキA', active: true, sortOrder: 1 },
            { id: 'med_b', label: 'ロキB', active: true, sortOrder: 2 },
            { id: 'med_c', label: '同', active: true, sortOrder: 3 },
            { id: 'med_d', label: '同', active: true, sortOrder: 4 }
          ] },
          events: [
            { type: 'medication', localDate: '2026-06-15', medicationOptionId: 'med_a', medicationLabel: '古い名前' },
            { type: 'medication', localDate: '2026-06-15', medicationLabel: 'ロキB' }
          ]
        };
        const parsed = parseHeartWatchCsv('ISO,歩数,睡眠時間,睡眠-bpm,睡眠-心拍変動-ms,起床-心拍変動-ms\\n2026-06-15T23:00:00+09:00,,,,,');
        const rows = buildHealthHistoryRows(parsed.data);
        assert.deepEqual(healthHistoryColumns().map((column) => column.label), ['日付', '最大', '平均', 'ロキA', 'ロキ', '同', '同2', '歩数', '睡眠', '睡bpm', '睡HRV', '起HRV']);
        assert.deepEqual(rows[0].medicationCounts, { med_a: '1', med_b: '1', med_c: '0', med_d: '0' });
        assert.deepEqual([rows[0].steps, rows[0].sleep, rows[0].sleepBpm, rows[0].sleepHrv, rows[0].wakeHrv], ['', '', '', '', '']);
        assert.equal(buildHealthHistoryTsv(rows).split('\\n')[0], healthHistoryColumns().map((column) => column.label).join('\t'));
        """
    )

def test_health_history_configurable_columns_validation_and_calculations() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        nowParts = () => ({ iso: '2026-06-17T00:00:00.000Z', localDate: '2026-06-17', localTime: '09:00' });
        appData = {
          schemaVersion: 1,
          appName: 'Tide Trace',
          settings: {
            painStateOptions: [
              { id: 'rest', label: '安静時', active: true, sortOrder: 1 },
              { id: 'hidden', label: '歩行時', active: false, sortOrder: 2 }
            ],
            medicationOptions: [
              { id: 'med_a', label: '鎮痛薬A', active: true, sortOrder: 1 },
              { id: 'med_b', label: '鎮痛薬B', active: false, sortOrder: 2 }
            ],
            lastJsonExportedAtUtc: null,
            lastCsvExportedAtUtc: null,
            healthReviewColumns: [
              { columnId: 'date', shortLabel: '日付', shortLabelMode: 'custom' },
              { columnId: 'tidetrace:pain:min', shortLabel: ' 最小 ', shortLabelMode: 'custom' },
              { columnId: 'tidetrace:pain:count', shortLabel: '痛回', shortLabelMode: 'auto' },
              { columnId: 'tidetrace:pain-state:rest:average', shortLabel: '安静平', shortLabelMode: 'auto' },
              { columnId: 'tidetrace:medication:med_b:count', shortLabel: '非薬', shortLabelMode: 'custom' },
              { columnId: 'tidetrace:note:count', shortLabel: 'メモ', shortLabelMode: 'auto' },
              { columnId: 'heartwatch:bp-am-systolic', shortLabel: '朝収縮', shortLabelMode: 'auto' }
            ]
          },
          periods: [],
          events: [
            { id: 'p1', type: 'pain', localDate: '2026-06-15', painScore: 8, stateOptionId: 'rest' },
            { id: 'p2', type: 'pain', localDate: '2026-06-15', painScore: 4, stateOptionId: 'rest', note: 'attached' },
            { id: 'm1', type: 'medication', localDate: '2026-06-15', medicationOptionId: 'med_b', medicationLabel: '鎮痛薬B', note: 'attached' },
            { id: 'm2', type: 'medication', localDate: '2026-06-15', medicationLabel: '鎮痛薬B' },
            { id: 'n1', type: 'note', localDate: '2026-06-15', note: 'standalone' }
          ]
        };
        ensureHealthReviewColumns();
        const columns = selectedHealthHistoryColumns();
        assert.equal(columns[0].shortLabel, '日付');
        assert.equal(appData.settings.healthReviewColumns.some((column) => column.columnId === 'date'), false);
        assert.deepEqual(columns.map((column) => column.shortLabel), ['日付', '最小', '痛回', '安静平', '非薬', 'メモ', '朝収縮']);
        assert.equal(validateHealthHistoryColumns([{ shortLabel: 'HRV' }, { shortLabel: 'ｈｒｖ' }]).message, '短縮名が重複しています。');
        assert.equal(validateHealthHistoryColumns([{ shortLabel: '123456789' }]).message, '短縮名は8文字以内で入力してください。');
        assert.equal(validateHealthHistoryColumns([{ shortLabel: '   ' }]).message, '短縮名を入力してください。');
        const parsed = parseHeartWatchCsv('ISO,血圧 (am)-収縮\\n2026-06-15T23:00:00+09:00,120');
        const rows = buildHealthHistoryRows(parsed.data);
        assert.deepEqual(healthHistoryValues(rows[0], columns), ['2026-06-15', '4', '2', '6.0', '2', '1', '120']);
        assert.equal(buildHealthHistoryTsv(rows).split('\\n')[0], '日付\t最小\t痛回\t安静平\t非薬\tメモ\t朝収縮');
        """
    )
