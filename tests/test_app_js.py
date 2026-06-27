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
            { type: 'pain', localDate: '2026-07-02', painScore: 3, stateOptionId: 'sitting' },
            { type: 'pain', localDate: '2026-07-03', painScore: 9, stateOptionId: 'missing' },
            { type: 'pain', localDate: '2026-07-04', painScore: 10, stateOptionId: 'standing', stateLabel: '範囲外' }
          ]
        };

        const rows = buildStatePainSummary('2026-07-01', '2026-07-03');

        assert.deepEqual(rows.map((row) => [row.label, row.recordDays, row.maxPain, row.averagePain.toFixed(1)]), [
          ['不明な状態', 1, 9, '9.0'],
          ['立位', 2, 8, '6.0'],
          ['Sitting current', 1, 3, '3.0']
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
          { label: '排便後', recordDays: 6, maxPain: 9, averagePain: 7.6 }
        ]);

        const stateItem = block.children.find((child) => child.className === 'visit-summary-state-pain-item');
        const notice = block.children.at(-1);
        assert.match(stateItem.innerHTML, /排便後<\\/strong>：記録日数 6日 \\/ 最大 9 \\/ 平均 7\\.6/);
        assert.doesNotMatch(stateItem.innerHTML, /最大痛み|平均痛み/);
        assert.equal(notice.className.includes('visit-summary-notice'), true);
        assert.equal(notice.textContent, '同じ日・同じ状態の痛みを日単位で集計しています。服薬前後や他の薬との併用条件は分けていません。');
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
              { amount: 2, targetDays: 7, painDays: 5, maxPain: 9, averagePainTotal: 27 }
            ]
          }
        ]);

        const doseItem = block.children.find((child) => child.className === 'visit-summary-dose-pain-item');
        const doseRow = doseItem.children[1].children[0];
        const notice = block.children.at(-1);
        assert.match(doseRow.innerHTML, /対象 7日 \\/ 痛み記録あり 5日<br>最大 9 \\/ 平均 5\\.4/);
        assert.doesNotMatch(doseRow.innerHTML, /最大痛み|平均痛み/);
        assert.equal(notice.className.includes('visit-summary-notice'), true);
        assert.equal(notice.textContent, '薬ごとに日単位で集計しています。他の薬との併用条件は分けていません。');
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
          '薬の量は1以上の数値で入力してください。'
        );
        assert.equal(
          buildInitialSetupSettings([{ label: '薬', amount: '0', unit: '錠' }], ['安静時']).error,
          '薬の量は1以上の数値で入力してください。'
        );
        assert.equal(
          buildInitialSetupSettings([{ label: '薬', amount: '1', unit: '錠' }], [' ']).error,
          '痛み状態を1つ以上入力してください。'
        );
        """
    )
