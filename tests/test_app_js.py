import json
import subprocess
import tempfile
import textwrap
from pathlib import Path
import re


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
        assert.deepEqual(eventDisplayInfo(snapshot), { typeLabel: '服薬の記録', summary: 'Recorded 1unit', note: '' });
        assert.equal(csvValueForHeader(snapshot, 'medication_option_label'), 'Recorded');
        assert.equal(medicationEventLabel({ medicationOptionId: 'inactive' }), 'Hidden');
        assert.equal(medicationEditOptions({ medicationOptionId: 'inactive' }).at(-1).displayLabel, 'Hidden（非表示）');
        assert.equal(
          medicationEditOptions({ medicationOptionId: 'missing', medicationLabel: 'Archived' }).at(-1).displayLabel,
          'Archived（設定なし）'
        );
        """
    )



def test_render_event_list_uses_compact_accessible_rows_and_keeps_actions() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        function makeElement(tag) {
          return {
            tag, attributes: {}, children: [], listeners: {}, textContent: '', innerHTML: '', className: '', type: '',
            setAttribute(name, value) { this.attributes[name] = value; },
            getAttribute(name) { return this.attributes[name]; },
            addEventListener(name, handler) { this.listeners[name] = handler; },
            append(...items) { this.children.push(...items); },
            appendChild(item) { this.children.push(item); },
            click() { this.listeners.click(); },
            queryByClass(name) {
              const attrClass = this.getAttribute('class') || '';
              if (`${attrClass} ${this.className}`.split(/\\s+/).includes(name)) return this;
              for (const child of this.children) {
                if (child && child.queryByClass) {
                  const result = child.queryByClass(name);
                  if (result) return result;
                }
              }
              return null;
            },
            allText() {
              return this.textContent + this.children.map((child) => typeof child === 'string' ? child : child.allText()).join('');
            }
          };
        }
        global.document = {
          createElement: makeElement,
          createTextNode(text) { return text; }
        };
        appData = {
          settings: {
            painStateOptions: [{ id: 'standing', label: '立位', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med-a', label: 'Medication A', defaultAmount: 1, unit: '錠', active: true, sortOrder: 1 }]
          },
          events: [], periods: []
        };
        const container = makeElement('div');
        const opened = [];
        const deleted = [];
        openEditEventPanel = (id) => opened.push(id);
        deleteEvent = (id) => deleted.push(id);
        const events = [
          { id: 'pain-id', type: 'pain', localDate: '2026-07-10', localTime: '15:32', createdAtUtc: '3', painScore: 4, stateOptionId: 'standing', note: '腰が重い' },
          { id: 'med-id', type: 'medication', localDate: '2026-07-10', localTime: '15:10', createdAtUtc: '2', medicationOptionId: 'med-a', amount: 1, unit: '錠', note: '外出前' },
          { id: 'note-id', type: 'note', localDate: '2026-07-10', localTime: '14:45', createdAtUtc: '1', note: '午後から雨。少しだるい' }
        ];

        renderEventList(container, events, sortedEventsDescending, { showDate: false });

        assert.equal(container.children.length, 3);
        const pain = container.children[0];
        assert.deepEqual(pain.children.map((child) => child.className), ['event-time', 'event-type', 'event-body', 'event-actions']);
        assert.equal(pain.queryByClass('event-time').textContent, '15:32');
        assert.equal(pain.queryByClass('event-type-icon').tag, 'svg');
        assert.equal(pain.queryByClass('event-type-icon').getAttribute('aria-hidden'), 'true');
        assert.equal(pain.queryByClass('event-type-icon').getAttribute('stroke'), 'currentColor');
        assert.equal(pain.queryByClass('visually-hidden').textContent, '痛みの記録');
        assert.equal(pain.queryByClass('event-summary').textContent, '4・立位');
        assert.equal(pain.queryByClass('event-note').textContent, '腰が重い');
        assert.equal(pain.allText().includes('pain'), false);
        assert.equal(pain.allText().includes('score'), false);
        assert.equal(pain.allText().includes('/'), false);

        const med = container.children[1];
        assert.equal(med.queryByClass('event-time').textContent, '15:10');
        assert.equal(med.queryByClass('event-type-icon').tag, 'svg');
        assert.equal(med.queryByClass('event-type-icon').getAttribute('aria-hidden'), 'true');
        assert.equal(med.queryByClass('visually-hidden').textContent, '服薬の記録');
        assert.equal(med.queryByClass('event-summary').textContent, 'Medication A 1錠');
        assert.equal(med.queryByClass('event-note').textContent, '外出前');
        assert.equal(med.allText().includes('medication'), false);
        assert.equal(med.allText().includes('/'), false);

        const note = container.children[2];
        assert.equal(note.queryByClass('event-time').textContent, '14:45');
        assert.equal(note.queryByClass('event-type-icon').tag, 'svg');
        assert.equal(note.queryByClass('event-type-icon').getAttribute('aria-hidden'), 'true');
        assert.equal(note.queryByClass('visually-hidden').textContent, 'メモ');
        assert.equal(note.queryByClass('event-summary').textContent, '午後から雨。少しだるい');
        assert.equal(note.allText().includes('note'), false);
        assert.equal(note.allText().includes('/'), false);

        const editButton = pain.queryByClass('edit-event-button');
        const deleteButton = pain.queryByClass('delete-event-button');
        assert.equal(editButton.getAttribute('aria-label'), '編集');
        assert.equal(deleteButton.getAttribute('aria-label'), '記録を削除');
        editButton.click();
        deleteButton.click();
        assert.deepEqual(opened, ['pain-id']);
        assert.deepEqual(deleted, ['pain-id']);
        """
    )


def test_event_display_info_handles_missing_legacy_values() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: { medicationOptions: [], painStateOptions: [] },
          events: [], periods: []
        };
        assert.deepEqual(eventDisplayInfo({ type: 'pain', painScore: 4, stateLabel: '保存済み状態', note: '' }), {
          typeLabel: '痛みの記録', summary: '4・保存済み状態', note: ''
        });
        assert.deepEqual(eventDisplayInfo({ type: 'pain', painScore: 4, stateOptionId: 'missing', note: '' }).summary, '4・不明な状態');
        assert.deepEqual(eventDisplayInfo({ type: 'medication', medicationOptionId: 'missing', note: '' }).summary, '不明な薬');
        assert.deepEqual(eventDisplayInfo({ type: 'medication', medicationLabel: 'Medication A', unit: '錠', note: '' }).summary, 'Medication A 錠');
        assert.deepEqual(eventDisplayInfo({ type: 'medication', medicationLabel: 'Medication A', amount: 1, note: '' }).summary, 'Medication A 1');
        assert.equal(eventDisplayInfo({ type: 'medication', medicationLabel: 'Medication A', note: '' }).summary.includes('undefined'), false);
        """
    )


def test_svg_icons_use_namespaced_elements_and_class_attributes() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const createdWithNs = [];
        function makeElement(tag, isSvg = false) {
          const element = {
            tag,
            isSvg,
            attributes: {}, children: [], listeners: {}, textContent: '', innerHTML: '', type: '',
            className: isSvg ? { baseVal: '', animVal: '' } : '',
            setAttribute(name, value) { this.attributes[name] = String(value); },
            getAttribute(name) { return this.attributes[name]; },
            addEventListener(name, handler) { this.listeners[name] = handler; },
            append(...items) { this.children.push(...items); },
            appendChild(item) { this.children.push(item); },
            click() { if (this.listeners.click) this.listeners.click(); },
            queryByClass(name) {
              const attrClass = this.getAttribute('class') || '';
              const propClass = typeof this.className === 'string' ? this.className : '';
              if (`${attrClass} ${propClass}`.split(/\\s+/).includes(name)) return this;
              for (const child of this.children) {
                if (child && child.queryByClass) {
                  const result = child.queryByClass(name);
                  if (result) return result;
                }
              }
              return null;
            },
            allText() {
              return this.textContent + this.children.map((child) => typeof child === 'string' ? child : child.allText()).join('');
            }
          };
          return element;
        }
        const elementsById = {
          'save-pain': makeElement('button'),
          'save-note': makeElement('button')
        };
        elementsById['save-pain'].textContent = '痛みを記録';
        elementsById['save-note'].textContent = 'メモだけ保存';
        global.document = {
          createElement: (tag) => makeElement(tag),
          createElementNS(ns, tag) {
            createdWithNs.push({ ns, tag });
            return makeElement(tag, true);
          },
          createTextNode(text) { return text; },
          getElementById(id) { return elementsById[id]; }
        };
        appData = {
          settings: {
            painStateOptions: [{ id: 'standing', label: '立位', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med-a', label: 'Medication A', defaultAmount: 1, unit: '錠', active: true, sortOrder: 1 }]
          },
          events: [], periods: []
        };

        const buttonIcon = createTypeIcon('medication', 'button-type-icon');
        assert.equal(buttonIcon.tag, 'svg');
        assert.equal(buttonIcon.isSvg, true);
        assert.notEqual(typeof buttonIcon.className, 'string');
        assert.equal(buttonIcon.getAttribute('class'), 'button-type-icon');
        assert.equal(buttonIcon.getAttribute('viewBox'), '0 0 24 24');
        assert.equal(buttonIcon.getAttribute('stroke'), 'currentColor');
        assert.equal(buttonIcon.getAttribute('aria-hidden'), 'true');

        const eventIcon = createTypeIcon('pain');
        assert.equal(eventIcon.getAttribute('class'), 'event-type-icon');
        assert.equal(eventIcon.getAttribute('viewBox'), '0 0 24 24');
        assert.equal(eventIcon.getAttribute('stroke'), 'currentColor');
        assert.equal(eventIcon.getAttribute('aria-hidden'), 'true');
        assert.ok(createdWithNs.some((item) => item.ns === 'http://www.w3.org/2000/svg' && item.tag === 'svg'));

        decorateRecordActionButtons();
        assert.equal(elementsById['save-pain'].queryByClass('button-type-icon').getAttribute('class'), 'button-type-icon');
        assert.equal(elementsById['save-note'].queryByClass('button-type-icon').getAttribute('class'), 'button-type-icon');

        const container = makeElement('div');
        renderEventList(container, [
          { id: 'med-id', type: 'medication', localDate: '2026-07-10', localTime: '15:10', createdAtUtc: '2', medicationOptionId: 'med-a', amount: 1, unit: '錠', note: '' },
          { id: 'pain-id', type: 'pain', localDate: '2026-07-10', localTime: '15:32', createdAtUtc: '3', painScore: 4, stateOptionId: 'standing', note: '' },
          { id: 'note-id', type: 'note', localDate: '2026-07-10', localTime: '14:45', createdAtUtc: '1', note: 'メモ' }
        ], sortedEventsDescending, { showDate: false });
        for (const row of container.children) {
          const rowIcon = row.queryByClass('event-type-icon');
          assert.equal(rowIcon.tag, 'svg');
          assert.equal(rowIcon.getAttribute('class'), 'event-type-icon');
          assert.equal(rowIcon.getAttribute('viewBox'), '0 0 24 24');
          assert.equal(rowIcon.getAttribute('stroke'), 'currentColor');
          assert.equal(rowIcon.getAttribute('aria-hidden'), 'true');
        }
        """
    )


def test_event_row_css_wraps_body_without_truncation() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()
    event_block = re.search(r"\.event \{(?P<body>[^}]+)\}", css).group('body')
    body_block = re.search(r"\.event-body \{(?P<body>[^}]+)\}", css).group('body')
    time_block = re.search(r"\.event-time \{(?P<body>[^}]+)\}", css).group('body')
    type_block = re.search(r"\.event-type \{(?P<body>[^}]+)\}", css).group('body')
    actions_block = re.search(r"\.event-actions \{(?P<body>[^}]+)\}", css).group('body')
    action_icon_block = re.search(r"\.event-actions \.button-icon \{(?P<body>[^}]+)\}", css).group('body')

    assert 'display: grid;' in event_block
    assert 'grid-template-columns: auto auto minmax(0, 1fr) auto;' in event_block
    assert 'padding: 6px 0;' in event_block
    assert 'min-width: 0;' in body_block
    assert 'overflow-wrap: anywhere;' in body_block
    assert 'white-space: nowrap' not in body_block
    assert 'text-overflow: ellipsis' not in body_block
    assert 'line-clamp' not in body_block
    assert 'white-space: nowrap;' in time_block
    assert 'white-space: nowrap;' in type_block
    assert 'gap: 0.5rem;' in actions_block
    assert 'height: 32px;' in action_icon_block
    assert 'min-height: 32px;' in action_icon_block
    assert 'min-width: 32px;' in action_icon_block
    assert 'width: 32px;' in action_icon_block
    assert '::before' not in action_icon_block
    assert '::after' not in action_icon_block
    assert 'margin' not in action_icon_block
    assert 'position' not in action_icon_block
    assert 'z-index' not in action_icon_block

    global_icon_block = re.search(r"\.button-icon \{(?P<body>[^}]+)\}", css).group('body')
    assert 'height: 32px;' not in global_icon_block
    assert 'width: 32px;' not in global_icon_block


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


def test_delete_event_requires_confirmation_and_cancel_keeps_record() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = { events: [{ id: 'keep' }, { id: 'delete' }], settings: {}, periods: [] };
        let confirmCalls = 0;
        global.confirm = (message) => {
          confirmCalls += 1;
          assert.equal(message, 'この記録を削除しますか？');
          return false;
        };
        saveData = () => { throw new Error('saveData should not run when deletion is canceled'); };
        render = () => { throw new Error('render should not run when deletion is canceled'); };

        deleteEvent('delete');

        assert.equal(confirmCalls, 1);
        assert.deepEqual(appData.events.map((event) => event.id), ['keep', 'delete']);
        """
    )


def test_delete_event_removes_record_after_confirmation() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = { events: [{ id: 'keep' }, { id: 'delete' }], settings: {}, periods: [] };
        let saved = false;
        let rendered = false;
        global.confirm = () => true;
        saveData = () => { saved = true; };
        render = () => { rendered = true; };
        lastSavedEventId = 'delete';
        clearSaveFeedback = () => {};

        deleteEvent('delete');

        assert.deepEqual(appData.events.map((event) => event.id), ['keep']);
        assert.equal(saved, true);
        assert.equal(rendered, true);
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
        assert.match(medicationItem.innerHTML, /合計 14tablet/);
        assert.match(medicationItem.innerHTML, /1日平均 2\\.00tablet/);
        assert.doesNotMatch(medicationItem.innerHTML, / \\/ /);
        assert.equal(medicationItem.innerHTML.includes('visit-summary-metric-group'), true);
        assert.equal(medicationItem.innerHTML.includes('visit-summary-metric'), true);
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
          ['Standing current', 2, 8, 2, '6.5'],
          ['Sitting current', 1, 3, 1, '3.0']
        ]);
        assert.equal(rows.some((row) => row.label === 'Unused active'), false);
        assert.equal(rows.some((row) => row.label === '範囲外'), false);
        """
    )


def test_visit_summary_state_pain_groups_by_option_id_and_uses_current_label() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            painStateOptions: [
              { id: 'state_a', label: '🧍状態A', active: true, sortOrder: 1 },
              { id: 'state_b', label: '🧍状態A', active: true, sortOrder: 2 }
            ]
          },
          events: [
            { type: 'pain', localDate: '2026-07-01', localTime: '09:00', recordedAtUtc: '2026-07-01T00:00:00.000Z', painScore: 4, stateOptionId: 'state_a', stateLabel: '状態A' },
            { type: 'pain', localDate: '2026-07-01', localTime: '10:00', recordedAtUtc: '2026-07-01T01:00:00.000Z', painScore: 8, stateOptionId: 'state_a', stateLabel: '🧍状態A' },
            { type: 'pain', localDate: '2026-07-02', localTime: '09:00', recordedAtUtc: '2026-07-02T00:00:00.000Z', painScore: 6, stateOptionId: 'state_a', stateLabel: '状態A' },
            { type: 'pain', localDate: '2026-07-03', painScore: 7, stateOptionId: 'state_b', stateLabel: '🧍状態A' },
            { type: 'pain', localDate: '2026-07-04', localTime: '08:00', recordedAtUtc: '2026-07-03T23:00:00.000Z', painScore: 5, stateOptionId: 'missing_state', stateLabel: '旧不明' },
            { type: 'pain', localDate: '2026-07-05', localTime: '08:00', recordedAtUtc: '2026-07-04T23:00:00.000Z', painScore: 9, stateOptionId: 'missing_state', stateLabel: '新不明' },
            { type: 'pain', localDate: '2026-07-06', painScore: 3, stateLabel: '旧形式A' },
            { type: 'pain', localDate: '2026-07-07', painScore: 4, stateLabel: '旧形式A' },
            { type: 'pain', localDate: '2026-07-08', painScore: 2, stateLabel: '旧形式B' }
          ]
        };

        const rows = buildStatePainSummary('2026-07-01', '2026-07-08');
        const stateA = rows.filter((row) => row.medicationId !== 'unused').find((row) => row.label === '🧍状態A' && row.recordDays === 2);
        assert.equal(stateA.maxPain, 8);
        assert.equal(stateA.maxPainDays, 1);
        assert.equal(stateA.averagePain.toFixed(1), '6.0');
        assert.equal(rows.filter((row) => row.label === '🧍状態A').length, 2);
        assert.equal(rows.find((row) => row.label === '新不明').recordDays, 2);
        assert.equal(rows.find((row) => row.label === '旧形式A').recordDays, 2);
        assert.equal(rows.find((row) => row.label === '旧形式B').recordDays, 1);
        assert.deepEqual(rows.map((row) => row.label), ['新不明', '🧍状態A', '🧍状態A', '旧形式A', '旧形式B']);
        """
    )


def test_visit_summary_medication_summaries_use_current_labels_and_keep_keys() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            medicationOptions: [
              { id: 'med_a', label: '修正済み薬A', unit: '錠', active: true, sortOrder: 1 },
              { id: 'med_b', label: '同名薬', unit: '錠', active: true, sortOrder: 2 },
              { id: 'med_c', label: '同名薬', unit: '錠', active: true, sortOrder: 3 }
            ]
          },
          events: [
            { type: 'medication', localDate: '2026-07-01', medicationOptionId: 'med_a', medicationLabel: '誤記薬A', amount: 1, unit: '錠' },
            { type: 'medication', localDate: '2026-07-02', medicationOptionId: 'med_a', medicationLabel: '誤記薬A', amount: 2, unit: '錠' },
            { type: 'medication', localDate: '2026-07-03', medicationOptionId: 'med_a', medicationLabel: '古い別単位', amount: 1, unit: '包' },
            { type: 'medication', localDate: '2026-07-01', medicationOptionId: 'med_b', medicationLabel: '同名薬', amount: 1, unit: '錠' },
            { type: 'medication', localDate: '2026-07-01', medicationOptionId: 'med_c', medicationLabel: '同名薬', amount: 1, unit: '錠' },
            { type: 'medication', localDate: '2026-07-01', medicationLabel: '旧形式薬', amount: 1, unit: '滴' },
            { type: 'medication', localDate: '2026-07-02', medicationLabel: '旧形式薬', amount: 2, unit: '滴' },
            { type: 'medication', localDate: '2026-07-01', medicationOptionId: 'missing_med', medicationLabel: '不明旧', amount: 1, unit: '錠' },
            { type: 'medication', localDate: '2026-07-02', medicationOptionId: 'missing_med', medicationLabel: '不明新', amount: 1, unit: '錠' }
          ]
        };

        const rows = buildMedicationSummary('2026-07-01', '2026-07-03').filter((row) => row.total > 0);
        assert.deepEqual(rows.map((row) => [row.label, row.medicationId, row.unit, row.total, row.dates.size, (row.total / 3).toFixed(2)]), [
          ['修正済み薬A', 'med_a', '錠', 3, 2, '1.00'],
          ['修正済み薬A', 'med_a', '包', 1, 1, '0.33'],
          ['同名薬', 'med_b', '錠', 1, 1, '0.33'],
          ['同名薬', 'med_c', '錠', 1, 1, '0.33'],
          ['旧形式薬', '', '滴', 3, 2, '1.00'],
          ['不明新', 'missing_med', '錠', 2, 2, '0.67']
        ]);
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
        assert.match(stateItem.innerHTML, /排便後<\\/strong>：<span class=\"visit-summary-metric-group\"><span class=\"visit-summary-metric\">記録 6日<\\/span><span class=\"visit-summary-metric\">平均 7\\.6<\\/span><span class=\"visit-summary-metric\">最大 9（3日）<\\/span><\\/span>/);
        assert.doesNotMatch(stateItem.innerHTML, /記録日数|最大痛み|平均痛み/);
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
              { id: 'med_001', label: '修正済み薬A', defaultAmount: 1, unit: '錠', active: true, sortOrder: 1 }
            ]
          },
          events: [
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: '旧薬A', amount: 1, unit: '錠', localDate: '2026-07-01' },
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: '旧薬A', amount: 1, unit: '錠', localDate: '2026-07-02' },
            { type: 'medication', medicationOptionId: 'med_001', medicationLabel: '旧薬A', amount: 1, unit: '錠', localDate: '2026-07-03' },
            { type: 'pain', localDate: '2026-07-01', painScore: 7 },
            { type: 'pain', localDate: '2026-07-01', painScore: 7 },
            { type: 'pain', localDate: '2026-07-02', painScore: 5 },
            { type: 'pain', localDate: '2026-07-03', painScore: 7 }
          ]
        };

        const rows = buildDosePainSummary('2026-07-01', '2026-07-03');
        const oneTabletGroup = rows[0].doseGroups.find((group) => group.amount === 1);

        assert.equal(rows[0].label, '修正済み薬A');
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
        assert.match(doseRow.innerHTML, /<strong class=\"visit-summary-dose-heading\">2錠の日<\\/strong><div class=\"visit-summary-metric-group\"><span class=\"visit-summary-metric\">7日（痛み記録 5日）<\\/span><span class=\"visit-summary-metric\">平均 5\\.4<\\/span><span class=\"visit-summary-metric\">最大 7（2日）<\\/span><\\/div>/);
        assert.doesNotMatch(doseRow.innerHTML, /日数 7日|うち|痛みあり|対象|最大痛み|平均痛み/);
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
        assert.equal(formatTimePainSummaryRow(rows[0]), '深夜：記録 2日　平均 6.7　最大 9（1日）');
        assert.doesNotMatch(formatTimePainSummaryRow(rows[0]), /記録日数/);
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
        assert.match(block.children[1].innerHTML, /午前<\/strong>：<span class="visit-summary-metric-group"><span class="visit-summary-metric">記録 1日<\/span><span class="visit-summary-metric">平均 6.5<\/span><span class="visit-summary-metric">最大 8（1日）<\/span><\/span>/);
        assert.doesNotMatch(block.children[1].innerHTML, /記録日数/);
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
              { id: 'med_a', label: '修正済み薬A', active: true, sortOrder: 1 },
              { id: 'med_b', label: '薬B', active: true, sortOrder: 2 }
            ]
          },
          events: [
            { type: 'pain', localDate: '2026-07-01', localTime: '08:00', painScore: 9 },
            { type: 'pain', localDate: '2026-07-01', localTime: '09:30', painScore: 8 },
            { type: 'medication', medicationOptionId: 'med_a', medicationLabel: '旧薬A', localDate: '2026-07-01', localTime: '10:00' },
            { type: 'pain', localDate: '2026-07-01', localTime: '11:00', painScore: 5 },
            { type: 'pain', localDate: '2026-07-01', localTime: '12:00', painScore: 4 },
            { type: 'pain', localDate: '2026-07-01', localTime: '12:30', painScore: 4 },
            { type: 'pain', localDate: '2026-07-02', localTime: '08:10', painScore: 6 },
            { type: 'medication', medicationOptionId: 'med_a', medicationLabel: '旧薬A', localDate: '2026-07-02', localTime: '09:00' },
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
        assert.equal(rows[0].label, '修正済み薬A');
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
        assert.match(items[0].innerHTML, /薬A<\/strong>：<span class=\"visit-summary-metric-group\"><span class=\"visit-summary-metric\">対象 2回<\/span><span class=\"visit-summary-metric\">平均 42%低下<\/span><span class=\"visit-summary-metric\">中央 40%低下<\/span><span class=\"visit-summary-metric\">前後 7\.8→4\.5<\/span><\/span>/);
        assert.match(items[1].innerHTML, /薬B<\/strong>：<span class=\"visit-summary-metric-group\"><span class=\"visit-summary-metric\">対象 1回<\/span><span class=\"visit-summary-metric\">15%上昇<\/span><span class=\"visit-summary-metric\">前後 5→5\.8<\/span><\/span>/);
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
          'A：1日以上',
          'B：5時間25分',
          'No record：記録なし'
        ]);
        global.Date = RealDate;
        """
    )


def test_last_medication_text_elapsed_boundaries_are_compact() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const RealDate = Date;
        const fixedNow = new RealDate('2026-06-20T12:00:00.000Z').getTime();
        global.Date = class extends RealDate {
          constructor(...args) { super(...args); }
          static now() { return fixedNow; }
        };
        const option = { label: 'Medication A' };
        const cases = [
          [null, 'Medication A：記録なし'],
          ['2026-06-20T09:55:00.000Z', 'Medication A：2時間5分'],
          ['2026-06-19T12:01:00.000Z', 'Medication A：23時間59分'],
          ['2026-06-19T12:00:00.000Z', 'Medication A：1日以上'],
          ['2026-06-19T11:59:00.000Z', 'Medication A：1日以上']
        ];
        cases.forEach(([recordedAtUtc, expected]) => {
          const last = recordedAtUtc ? { recordedAtUtc, localDate: '2026-06-19', localTime: '21:01' } : null;
          const actual = lastMedicationText(option, last);
          assert.equal(actual, expected);
          ['前回', '経過', '/', '21:01', '2026-06-19', '6/19'].forEach((forbidden) => {
            assert.equal(actual.includes(forbidden), false, `${actual} should not include ${forbidden}`);
          });
        });
        global.Date = RealDate;
        """
    )


def test_medication_record_buttons_are_labeled_safely_and_click_save_medication() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const buttons = [];
        const medicationButtons = {
          innerHTML: '',
          appendChild(button) { buttons.push(button); }
        };
        global.document = {
          getElementById(id) { return id === 'medication-buttons' ? medicationButtons : { innerHTML: '', appendChild() {} }; },
          createElement(tag) {
            return {
              tag, attributes: {}, listeners: {}, textContent: '', innerHTML: '', children: [], className: '',
              setAttribute(name, value) { this.attributes[name] = value; },
              getAttribute(name) { return this.attributes[name]; },
              addEventListener(name, handler) { this.listeners[name] = handler; },
              append(...items) { this.children.push(...items); },
              appendChild(item) { this.children.push(item); },
              click() { this.listeners.click(); }
            };
          }
        };
        appData = {
          settings: {
            medicationOptions: [
              { id: 'shown', label: 'Medication A', active: true, sortOrder: 1 },
              { id: 'unsafe', label: '<img src=x onerror=alert(1)>', active: true, sortOrder: 2 },
              { id: 'hidden', label: 'Hidden Medication', active: false, sortOrder: 3 }
            ],
            painStateOptions: []
          },
          events: [], periods: []
        };
        nowParts = () => ({ localDate: '2026-06-20', localTime: '12:00', iso: '2026-06-20T12:00:00.000Z' });
        renderLastMedicationList = () => {};
        renderToday = () => {};
        renderPastDates = () => {};
        renderPeriodSettings = () => {};
        renderMedicationSettingsSummary = () => {};
        renderMedicationSettingsList = () => {};
        renderExportStatus = () => {};
        renderPainStateSettingsSummary = () => {};
        renderPainStateSettingsList = () => {};
        renderComparisonPeriodSummary = () => {};
        renderPeriodList = () => {};
        renderEventList = () => {};
        renderHistory = () => {};
        ensureSummaryDefaults = () => {};
        nextMedicationSortOrder = () => 1;
        nextPainSortOrder = () => 1;
        nextPeriodStartSuggestion = () => '2026-06-20';
        const saved = [];
        saveMedication = (id) => { saved.push(id); };

        render();

        assert.equal(buttons.length, 2);
        assert.equal(buttons[0].children[0].tag, 'svg');
        assert.equal(buttons[0].children[0].getAttribute('aria-hidden'), 'true');
        assert.equal(buttons[0].children[0].getAttribute('stroke'), 'currentColor');
        assert.equal(buttons[0].children[1].textContent, 'Medication A');
        assert.equal(buttons[0].getAttribute('aria-label'), 'Medication Aを記録');
        assert.equal(buttons[1].children[1].textContent, '<img src=x onerror=alert(1)>');
        assert.equal(buttons[1].innerHTML, '');
        assert.equal(buttons.some((button) => button.textContent.includes('Hidden Medication')), false);
        buttons[0].click();
        assert.deepEqual(saved, ['shown']);
        """
    )


def test_management_button_labels_are_unified() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    assert 'バックアップを書き出す' in html
    assert 'バックアップから読み込む' in html
    assert '<label for="csv-export-type" class="form-field-label">書き出す内容</label>' in html
    assert '<label for="csv-export-type" class="form-field-label">CSV書き出し</label>' not in html
    assert 'CSVを書き出す' in html
    assert '<option value="all">全記録</option>' in html
    assert '<option value="pain">痛みのみ</option>' in html
    assert '<option value="medication">服薬のみ</option>' in html
    assert '<option value="note">メモのみ</option>' in html
    assert 'バックアップを書き出し</button>' not in html
    assert 'バックアップから読み込み</button>' not in html


def test_record_action_icon_decorator_keeps_text_labels_accessible() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        function makeElement(tag, text = '') {
          return {
            tag, attributes: {}, children: [], textContent: text, className: '',
            setAttribute(name, value) { this.attributes[name] = value; },
            getAttribute(name) { return this.attributes[name]; },
            append(...items) { this.children.push(...items); },
            appendChild(item) { this.children.push(item); }
          };
        }
        const elements = {
          'save-pain': makeElement('button', '痛みを記録'),
          'save-note': makeElement('button', 'メモだけ保存')
        };
        global.document = {
          getElementById(id) { return elements[id]; },
          createElement: makeElement
        };
        decorateRecordActionButtons();
        for (const id of ['save-pain', 'save-note']) {
          assert.equal(elements[id].children[0].tag, 'svg');
          assert.equal(elements[id].children[0].getAttribute('aria-hidden'), 'true');
          assert.equal(elements[id].children[0].getAttribute('stroke'), 'currentColor');
        }
        assert.equal(elements['save-pain'].children[1].textContent, '痛みを記録');
        assert.equal(elements['save-note'].children[1].textContent, 'メモだけ保存');
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


def test_open_edit_event_panel_shows_fields_and_moves_initial_focus() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let focused = false;
        const dateInput = { focus() { focused = true; } };
        const fields = { innerHTML: '' };
        const panel = { hidden: true, querySelector(selector) { return dateInput; }, querySelectorAll(selector) { return [dateInput]; } };
        global.document = { activeElement: null, getElementById(id) { return id === 'edit-event-fields' ? fields : panel; } };
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
        assert.equal(focused, true);
        assert.match(fields.innerHTML, /type="date" value="2026-06-27"/);
        assert.match(fields.innerHTML, /type="time" value="23:45"/);
        assert.equal(fields.innerHTML.includes('<label class="form-field-label" for="edit-medication-option">薬</label>'), true);
        assert.equal(fields.innerHTML.includes('<select id="edit-medication-option" class="form-control-base form-control">'), true);
        assert.equal(fields.innerHTML.includes('<textarea id="edit-note" class="form-control-base form-control" rows="4" placeholder="メモを入力"></textarea>'), true);
        assert.equal(fields.innerHTML.includes('日時を変更'), false);
        assert.equal(fields.innerHTML.includes('内容を変更'), false);
        assert.equal(fields.innerHTML.includes('メモを追加'), false);
        """
    )



def test_edit_event_dialog_traps_focus_and_escape_closes() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let active = null;
        function makeElement(name) {
          return {
            hidden: false,
            offsetParent: {},
            getClientRects() { return [1]; },
            getAttribute() { return null; },
            focus() { active = this; document.activeElement = this; },
            name
          };
        }
        const first = makeElement('first');
        const last = makeElement('last');
        const fields = { innerHTML: '' };
        const panel = {
          hidden: false,
          contains(element) { return element === first || element === last; },
          querySelectorAll() { return [first, last]; }
        };
        global.document = { activeElement: last, getElementById(id) { return id === 'edit-event-fields' ? fields : panel; } };
        editingEventId = 'event-note';
        editEventReturnFocus = { eventId: 'event-note', element: null };

        let prevented = false;
        handleEditEventPanelKeydown({ key: 'Tab', shiftKey: false, preventDefault() { prevented = true; } });
        assert.equal(prevented, true);
        assert.equal(active, first);

        document.activeElement = first;
        prevented = false;
        handleEditEventPanelKeydown({ key: 'Tab', shiftKey: true, preventDefault() { prevented = true; } });
        assert.equal(prevented, true);
        assert.equal(active, last);

        prevented = false;
        handleEditEventPanelKeydown({ key: 'Escape', preventDefault() { prevented = true; } });
        assert.equal(prevented, true);
        assert.equal(panel.hidden, true);
        assert.equal(editingEventId, null);
        """
    )


def test_close_edit_event_panel_restores_original_or_recreated_button_focus() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let focused = '';
        const original = { isConnected: true, focus() { focused = 'original'; } };
        const recreated = { focus() { focused = 'recreated'; } };
        const fields = { innerHTML: '' };
        const panel = { hidden: false };
        global.CSS = { escape(value) { return value; } };
        global.document = {
          getElementById(id) { return id === 'edit-event-fields' ? fields : panel; },
          querySelector(selector) { return selector.includes('event-note') ? recreated : null; }
        };

        editingEventId = 'event-note';
        editEventReturnFocus = { eventId: 'event-note', element: original };
        closeEditEventPanel();
        assert.equal(focused, 'original');

        editingEventId = 'event-note';
        original.isConnected = false;
        editEventReturnFocus = { eventId: 'event-note', element: original };
        closeEditEventPanel();
        assert.equal(focused, 'recreated');
        """
    )


def test_save_edited_event_invalid_datetime_keeps_panel_and_focuses_date_or_time() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let focused = '';
        const elements = {
          'edit-local-date': { value: '', focus() { focused = 'date'; } },
          'edit-local-time': { value: '', focus() { focused = 'time'; } },
          'edit-note': { value: 'changed' },
          'edit-event-error': { textContent: '' },
          'edit-event-panel': { hidden: false },
          'edit-event-fields': { innerHTML: 'kept' }
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
        assert.equal(elements['edit-event-panel'].hidden, false);
        assert.equal(elements['edit-event-fields'].innerHTML, 'kept');
        assert.equal(elements['edit-event-error'].textContent, '日付を入力してください。');
        assert.equal(focused, 'date');
        elements['edit-local-date'].value = '2026-06-28';
        saveEditedEvent();
        assert.equal(focused, 'time');
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

        assert.equal((html.match(/<label class="form-field-label" for="edit-note">メモ<\/label>/g) || []).length, 1);
        assert.match(html, /<textarea id="edit-note" class="form-control-base form-control" rows="4" placeholder="メモを入力"><\/textarea>/);
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
    assert "renderHistoryNavigation(today, list, { showCopy: true });" in source
    assert "renderHistoryNavigation(today, list, { showCopy: false });" in source
    assert "scrollHistoryToStart();" in source
    assert "formatFullDate(dateText)" in source




def test_history_daily_summary_rows_use_accessible_icons_and_commas() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        function makeElement(tag) {
          return {
            tag, attributes: {}, children: [], listeners: {}, textContent: '', className: '', type: '',
            setAttribute(name, value) { this.attributes[name] = value; },
            getAttribute(name) { return this.attributes[name]; },
            addEventListener(name, handler) { this.listeners[name] = handler; },
            append(...items) { this.children.push(...items); },
            appendChild(item) { this.children.push(item); },
            queryByClass(name) {
              const attrClass = this.getAttribute('class') || '';
              if (`${attrClass} ${this.className}`.split(/\s+/).includes(name)) return this;
              for (const child of this.children) if (child && child.queryByClass) {
                const result = child.queryByClass(name);
                if (result) return result;
              }
              return null;
            },
            queryAllByClass(name, found = []) {
              const attrClass = this.getAttribute('class') || '';
              if (`${attrClass} ${this.className}`.split(/\s+/).includes(name)) found.push(this);
              for (const child of this.children) if (child && child.queryAllByClass) child.queryAllByClass(name, found);
              return found;
            },
            allText() { return this.textContent + this.children.map((child) => typeof child === 'string' ? child : child.allText()).join(''); }
          };
        }
        global.document = { createElement: makeElement, createElementNS(ns, tag) { return makeElement(tag); } };
        appData = { settings: { medicationOptions: [] }, periods: [], events: [] };
        const summary = buildDailySummary([
          { id: 'p1', type: 'pain', localDate: '2026-07-11', localTime: '09:00', painScore: 10 },
          { id: 'p2', type: 'pain', localDate: '2026-07-11', localTime: '12:00', painScore: 4 },
          { id: 'm1', type: 'medication', localDate: '2026-07-11', localTime: '10:00', medicationLabel: 'Dummy A', amount: 2, unit: '錠' },
          { id: 'm2', type: 'medication', localDate: '2026-07-11', localTime: '11:00', medicationLabel: 'Dummy B', amount: 3, unit: '錠' },
          { id: 'n1', type: 'note', localDate: '2026-07-11', localTime: '08:00', note: 'Dummy note' },
          { id: 'n2', type: 'note', localDate: '2026-07-11', localTime: '13:00', note: 'Second note' },
          { id: 'n3', type: 'note', localDate: '2026-07-11', localTime: '14:00', note: 'Third note' }
        ]);
        const container = makeElement('div');
        appendDailySummaryRows(container, summary);
        const rows = container.queryAllByClass('history-summary-row');
        assert.equal(rows.length, 3);
        assert.deepEqual(rows.map((row) => row.queryByClass('visually-hidden').textContent), ['痛み', '服薬', 'メモ']);
        assert.deepEqual(rows.map((row) => row.queryByClass('history-summary-icon').tag), ['svg', 'svg', 'svg']);
        assert.deepEqual(rows.map((row) => row.queryByClass('history-summary-icon').getAttribute('aria-hidden')), ['true', 'true', 'true']);
        assert.equal(rows[0].queryByClass('history-summary-text').textContent, '平均7.0、最大10');
        assert.notEqual(rows[0].queryByClass('history-summary-text').textContent, '最大10、平均7.0');
        assert.equal(rows[1].queryByClass('history-summary-text').textContent, 'Dummy A2錠、Dummy B3錠');
        assert.equal(rows[2].queryByClass('history-summary-text').textContent, 'Dummy note、ほか2件');
        assert.equal(container.allText().includes(' / '), false);
        """
    )


def test_history_summary_copy_text_uses_range_data_and_omits_details() -> None:
    run_app_js(
        r"""
        const assert = require('node:assert/strict');
        appData = {
          settings: { medicationOptions: [] }, periods: [],
          events: [
            { id: 'out', type: 'note', localDate: '2026-07-04', localTime: '09:00', note: 'outside' },
            { id: 'p1', type: 'pain', localDate: '2026-07-11', localTime: '09:00', painScore: 10 },
            { id: 'p2', type: 'pain', localDate: '2026-07-11', localTime: '12:00', painScore: 4 },
            { id: 'm1', type: 'medication', localDate: '2026-07-11', localTime: '10:00', medicationLabel: 'Dummy A', amount: 2, unit: '錠' },
            { id: 'm2', type: 'medication', localDate: '2026-07-11', localTime: '11:00', medicationLabel: 'Dummy B', amount: 3, unit: '錠' },
            { id: 'n1', type: 'note', localDate: '2026-07-11', localTime: '08:00', note: 'Dummy note' },
            { id: 'n2', type: 'note', localDate: '2026-07-11', localTime: '13:00', note: 'Second note' },
            { id: 'n3', type: 'note', localDate: '2026-07-11', localTime: '14:00', note: 'Third note' },
            { id: 'only-note', type: 'note', localDate: '2026-07-10', localTime: '09:00', note: 'Only note' }
          ]
        };
        historyRange = { start: '2026-07-05', end: '2026-07-11', mode: 'recent' };
        expandedHistoryDate = '2026-07-11';
        const text = buildHistorySummaryText(historyRange);
        assert.equal(text, [
          '過去の記録',
          '表示範囲：2026/07/10〜2026/07/11',
          '',
          '7/11 土',
          '痛み：平均7.0、最大10',
          '服薬：Dummy A2錠、Dummy B3錠',
          'メモ：Dummy note、ほか2件',
          '',
          '7/10 金',
          'メモ：Only note'
        ].join('\n'));
        assert.equal(text.includes('最大10、平均7.0'), false);
        assert.equal(text.includes('/ '), false);
        assert.equal(text.includes('outside'), false);
        assert.equal(text.endsWith('\n'), false);
        expandedHistoryDate = null;
        assert.equal(buildHistorySummaryText(historyRange), text);
        """
    )


def test_history_copy_button_is_top_only_and_uses_clipboard_safely() -> None:
    run_app_js(
        """
        (async () => {
        const assert = require('node:assert/strict');
        function makeElement(tag) {
          return {
            tag, attributes: {}, children: [], listeners: {}, textContent: '', className: '', type: '', innerHTML: '', open: true,
            classList: { add() {}, remove() {} },
            setAttribute(name, value) { this.attributes[name] = value; },
            getAttribute(name) { return this.attributes[name]; },
            addEventListener(name, handler) { this.listeners[name] = handler; },
            append(...items) { this.children.push(...items); },
            appendChild(item) { this.children.push(item); },
            querySelector(selector) { return this.queryByClass(selector.slice(1)); },
            queryByClass(name) {
              const attrClass = this.getAttribute('class') || '';
              if (`${attrClass} ${this.className}`.split(/\s+/).includes(name)) return this;
              for (const child of this.children) if (child && child.queryByClass) {
                const result = child.queryByClass(name);
                if (result) return result;
              }
              return null;
            },
            queryAllByClass(name, found = []) {
              const attrClass = this.getAttribute('class') || '';
              if (`${attrClass} ${this.className}`.split(/\s+/).includes(name)) found.push(this);
              for (const child of this.children) if (child && child.queryAllByClass) child.queryAllByClass(name, found);
              return found;
            }
          };
        }
        const elements = { 'history-details': makeElement('details'), 'history-list': makeElement('div') };
        global.document = { getElementById(id) { return elements[id]; }, createElement: makeElement, createElementNS(ns, tag) { return makeElement(tag); } };
        appData = { settings: { medicationOptions: [] }, periods: [], events: [{ id: 'n1', type: 'note', localDate: '2026-07-11', localTime: '09:00', note: 'Dummy' }] };
        historyRange = { start: '2026-07-05', end: '2026-07-11', mode: 'recent' };
        renderHistory('2026-07-12');
        const buttons = elements['history-list'].queryAllByClass('history-copy-button');
        assert.equal(buttons.length, 1);
        assert.equal(buttons[0].textContent, 'コピー');
        assert.equal(buttons[0].className, 'button-base button-compact secondary-button history-copy-button');
        const topNav = elements['history-list'].children[0];
        assert.equal(topNav.children[0].className, 'history-range-label');
        assert.equal(topNav.children[1].className, 'history-copy-button-row');
        assert.equal(topNav.children[2].className, 'history-navigation-buttons');
        let clipboardText = '';
        Object.defineProperty(globalThis, 'navigator', { value: { clipboard: { writeText(text) { clipboardText = text; return Promise.resolve(); } } }, configurable: true });
        const toasts = [];
        showToast = (message) => toasts.push(message);
        await copyVisibleHistorySummary();
        assert.equal(clipboardText.includes('過去の記録'), true);
        assert.equal(toasts.at(-1), '表示中の記録をコピーしました');
        navigator.clipboard.writeText = () => Promise.reject(new Error('denied'));
        await copyVisibleHistorySummary();
        assert.equal(toasts.at(-1), 'コピーできませんでした');
        appData.events = [];
        clipboardText = 'unchanged';
        await copyVisibleHistorySummary();
        assert.equal(clipboardText, 'unchanged');
        })();
        """
    )

def test_visit_summary_text_uses_shared_summary_data_without_ui_labels() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          schemaVersion: 1,
          settings: {
            painStateOptions: [{ id: 'state', label: '現在状態', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med', label: '現在薬A', defaultAmount: 1, unit: '錠', active: true, sortOrder: 1 }]
          },
          periods: [],
          events: [
            { id: 'm1', type: 'medication', localDate: '2026-02-16', localTime: '09:00', medicationOptionId: 'med', medicationLabel: '旧薬A', amount: 1, unit: '錠' },
            { id: 'p1', type: 'pain', localDate: '2026-02-16', localTime: '08:30', painScore: 6, stateOptionId: 'state', stateLabel: '旧状態' },
            { id: 'p2', type: 'pain', localDate: '2026-02-16', localTime: '11:00', painScore: 3, stateOptionId: 'state', stateLabel: '旧状態' }
          ]
        };
        const summary = buildVisitSummaryData('2026-02-16', '2026-02-16');
        const text = buildVisitSummaryText(summary);
        assert.match(text, /^TideTrace 記録の集計/);
        assert.equal(text.includes('範囲：2026/02/16〜2026/02/16'), true);
        assert.equal(text.includes('服薬\\n現在薬A：合計 1錠　1日平均 1.00錠'), true);
        assert.equal(text.includes('状態別の痛み\\n現在状態：記録 1日　平均 4.5　最大 6（1日）'), true);
        assert.equal(text.includes('時間帯別の痛み\\n午前：記録 1日　平均 4.5　最大 6（1日）'), true);
        assert.equal(text.includes('服薬前後の痛み変化\\n現在薬A：対象 1回　50%低下　前後 6→3'), true);
        assert.equal(text.includes('旧薬A'), false);
        assert.equal(text.includes('旧状態'), false);
        assert.equal(text.includes('コピー'), false);
        assert.equal(text.includes('テキスト保存'), false);
        assert.equal(visitSummaryTextFilename(summary), 'tidetrace-record-summary-2026-02-16_2026-02-16.txt');
        """
    )


def test_visit_summary_metric_display_uses_grouped_spans_and_new_order() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const elements = { 'visit-summary-result': { innerHTML: '', children: [], appendChild(item) { this.children.push(item); } } };
        global.document = {
          getElementById(id) { return elements[id]; },
          createElement(tag) { return { tag, className: '', innerHTML: '', textContent: '', children: [], appendChild(item) { this.children.push(item); }, append(...items) { this.children.push(...items); } }; }
        };
        renderVisitSummaryResult('2026-06-01', '2026-06-08', 8, [],
          [{ label: '立位', recordDays: 18, averagePain: 6.4, maxPain: 9, maxPainDays: 1 }],
          [{ label: '午後', recordDays: 12, averagePain: 5.8, maxPain: 8, maxPainDays: 2 }],
          [{ label: 'ロキソニン', unit: '錠', doseGroups: [
            { amount: 2, targetDays: 8, painDays: 6, averagePainTotal: 38.4, maxPain: 9, maxPainDays: 2 },
            { amount: 0, targetDays: 5, painDays: 0, averagePainTotal: 0, maxPain: null, maxPainDays: 0 }
          ] }],
          [{ label: 'ロキソニン', count: 6, averageChange: 40, medianChange: 35, averageBefore: 8, averageAfter: 4.8 }]
        );
        function collectHtml(node) { return [node.innerHTML || node.textContent || '', ...(node.children || []).flatMap(collectHtml)].join('\\n'); }
        const html = collectHtml(elements['visit-summary-result'].children[0]);
        assert.match(html, /立位<\/strong>：<span class="visit-summary-metric-group"><span class="visit-summary-metric">記録 18日<\/span><span class="visit-summary-metric">平均 6\.4<\/span><span class="visit-summary-metric">最大 9（1日）<\/span><\/span>/);
        assert.match(html, /午後<\/strong>：<span class="visit-summary-metric-group"><span class="visit-summary-metric">記録 12日<\/span><span class="visit-summary-metric">平均 5\.8<\/span><span class="visit-summary-metric">最大 8（2日）<\/span><\/span>/);
        assert.match(html, /<strong class="visit-summary-dose-heading">2錠の日<\/strong><div class="visit-summary-metric-group"><span class="visit-summary-metric">8日（痛み記録 6日）<\/span><span class="visit-summary-metric">平均 6\.4<\/span><span class="visit-summary-metric">最大 9（2日）<\/span><\/div>/);
        assert.match(html, /<strong class="visit-summary-dose-heading">0錠の日<\/strong><div class="visit-summary-metric-group"><span class="visit-summary-metric">5日（痛み記録 0日）<\/span><span class="visit-summary-metric">平均 —<\/span><span class="visit-summary-metric">最大 —<\/span><\/div>/);
        assert.match(html, /ロキソニン<\/strong>：<span class="visit-summary-metric-group"><span class="visit-summary-metric">対象 6回<\/span><span class="visit-summary-metric">平均 40%低下<\/span><span class="visit-summary-metric">中央 35%低下<\/span><span class="visit-summary-metric">前後 8→4\.8<\/span><\/span>/);
        assert.doesNotMatch(html, /記録日数|うち痛み記録|痛みあり| \/ /);
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
        assert.equal(clipboardText.startsWith('TideTrace 記録の集計'), true);
        assert.equal(blobText.startsWith('TideTrace 記録の集計'), true);
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
    assert 'id="visit-summary-actions" class="result-actions" aria-label="記録の集計の操作" hidden' in html




def test_health_history_import_controls_follow_natural_dom_order_and_label() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    section_start = html.index('<section class="card health-history-card"')
    section_end = html.index('</section>', section_start)
    section = html[section_start:section_end]

    description_index = section.index('記録とヘルスケアデータを日ごとに表示します。')
    supplemental_index = section.index('今日のデータは対象外です。')
    columns_index = section.index('id="health-history-columns-panel"')
    import_label_index = section.index('for="heartwatch-csv-file"')
    actions_index = section.index('id="health-history-actions"')
    result_index = section.index('id="health-history-result"')

    assert description_index < supplemental_index < columns_index < import_label_index < actions_index < result_index
    assert '<summary>表示項目</summary>' in section
    assert '<label class="file-action-label button-base button-full primary-button" for="heartwatch-csv-file">HeartWatch まとめCSVを読み込む</label>' in section
    assert '>HeartWatch CSVを読み込む<' not in section
    assert '<input id="heartwatch-csv-file" class="visually-hidden-file-input" type="file" accept=".csv,text/csv" tabindex="-1">' in section

def test_result_action_print_structure_and_css_regression() -> None:
    root = Path(__file__).parents[1]
    html = (root / "docs" / "index.html").read_text()
    css = (root / "docs" / "styles.css").read_text()
    app_js = (root / "docs" / "app.js").read_text()

    assert 'id="visit-summary-actions" class="result-actions" aria-label="記録の集計の操作" hidden' in html
    assert 'id="health-history-actions" class="result-actions" aria-label="過去の記録とヘルスケアデータの操作" hidden' in html
    assert '<button id="show-visit-summary-print" class="button-base button-full secondary-button result-print-action" type="button">印刷用に表示</button>' in html
    assert '<button id="show-health-history-print" class="button-base button-full secondary-button result-print-action" type="button">印刷用に表示</button>' in html
    assert html.index('id="copy-visit-summary"') < html.index('id="save-visit-summary-text"') < html.index('id="show-visit-summary-print"')
    assert html.index('id="copy-health-history-text"') < html.index('id="copy-health-history-tsv"') < html.index('id="show-health-history-print"')
    assert 'id="visit-summary-print-content"' in html
    assert 'class="print-only print-document-title" hidden>記録の集計</h2>' in html
    assert "showToast('記録の集計をコピーしました');" in app_js
    assert "showToast('記録の集計を保存しました');" in app_js
    assert 'id="health-history-print-help"' not in html

    assert '.result-actions[hidden]' in css
    assert 'display: none;' in css_rule_body(css, '.result-actions[hidden]')
    assert '.result-print-action' in css
    assert 'grid-column: 1 / -1;' in css_rule_body(css, '.result-print-action')
    assert 'body.visit-summary-print-mode' in css
    assert 'body.health-history-print-mode' in css
    assert '#toast-feedback' in css
    assert '#edit-event-panel' in css
    assert '.health-history-table-wrap' in css and 'overflow: visible;' in css

    assert 'function clearPrintModes()' in app_js
    assert 'function printResultView(modeClass, detailsId)' in app_js
    assert 'function showVisitSummaryPrint()' in app_js
    assert "$('show-visit-summary-print').addEventListener('click', showVisitSummaryPrint);" in app_js
    assert 'health-history-print-help' not in app_js


def test_result_print_modes_behavior() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const listeners = {};
        const classValues = new Set(['health-history-print-mode']);
        const elements = {
          'visit-summary-details': { open: false },
          'health-history-details': { open: false }
        };
        global.document = {
          body: { classList: { add(name) { classValues.add(name); }, remove(...names) { names.forEach((name) => classValues.delete(name)); }, contains(name) { return classValues.has(name); } } },
          getElementById(id) { return elements[id] || null; }
        };
        global.window = {
          printCalls: 0,
          addEventListener(name, handler, options) { listeners[name] = { handler, options }; },
          print() { this.printCalls += 1; }
        };

        currentVisitSummaryData = null;
        currentVisitSummaryText = '';
        showVisitSummaryPrint();
        assert.equal(window.printCalls, 0);

        currentVisitSummaryData = { days: 1 };
        currentVisitSummaryText = 'summary';
        showVisitSummaryPrint();
        assert.equal(window.printCalls, 1);
        assert.equal(elements['visit-summary-details'].open, true);
        assert.equal(classValues.has('visit-summary-print-mode'), true);
        assert.equal(classValues.has('health-history-print-mode'), false);
        assert.equal(listeners.afterprint.options.once, true);
        listeners.afterprint.handler();
        assert.equal(classValues.has('visit-summary-print-mode'), false);

        currentHealthHistoryRows = [];
        showHealthHistoryPrint();
        assert.equal(window.printCalls, 1);

        currentHealthHistoryRows = [{ date: '2026-07-01' }];
        showHealthHistoryPrint();
        assert.equal(window.printCalls, 2);
        assert.equal(elements['health-history-details'].open, true);
        assert.equal(classValues.has('health-history-print-mode'), true);
        assert.equal(classValues.has('visit-summary-print-mode'), false);
        listeners.afterprint.handler();
        assert.equal(classValues.has('health-history-print-mode'), false);

        window.print = () => { throw new Error('print failed'); };
        showHealthHistoryPrint();
        assert.equal(classValues.has('health-history-print-mode'), false);
        """
    )


def test_record_input_header_and_last_medication_html_structure() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()

    assert '<h2 id="input-title" class="visually-hidden">記録</h2>' in html
    assert 'aria-labelledby="input-title"' in html
    assert '<h3 class="record-input-heading visually-hidden">薬</h3>' in html
    assert '<h3 class="record-input-heading visually-hidden">痛み</h3>' in html
    assert '<label for="record-note-input" class="form-field-label visually-hidden">メモ（任意）</label>' in html
    assert '<textarea id="record-note-input" class="form-control-base form-control-full"' in html
    assert 'placeholder="薬や痛みの補足、または単独メモ"' in html
    assert '<label for="pain-score" class="form-field-label">痛みスコア</label>' in html
    assert '<label for="pain-state" class="form-field-label">状態</label>' in html
    assert 'ボタンを押すと服薬を記録します。' not in html
    assert '<h2 id="last-med-title">前回の服薬から</h2>' in html


def test_record_input_section_spacing_is_preserved() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()
    section_block = re.search(r"\.record-input-section \{(?P<body>[^}]+)\}", css).group('body')
    first_section_block = re.search(r"\.record-input-section:first-of-type \{(?P<body>[^}]+)\}", css).group('body')

    assert 'margin-top: 14px;' in section_block
    assert 'margin-top: 0;' in first_section_block
    assert 'border' not in section_block
    assert 'background' not in section_block


def test_last_medication_css_is_compact_without_note_button_changes() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()
    item_block = re.search(r"\.last-medication-item \{(?P<body>[^}]+)\}", css).group('body')
    card_block = re.search(r"\.last-medication-card \{(?P<body>[^}]+)\}", css).group('body')
    mobile_block = re.search(r"@media \(max-width: 430px\) \{(?P<body>.*?)\n\}", css, re.S).group('body')
    note_block = re.search(r"\.note-save-button \{(?P<body>[^}]+)\}", css).group('body')

    assert 'border-top' not in item_block
    assert 'padding: 2px 0;' in item_block
    assert 'padding-top: 10px;' in card_block
    assert 'padding-bottom: 10px;' in card_block
    assert '.card.last-medication-card { padding-top: 10px; padding-bottom: 10px; }' in mobile_block
    assert 'margin-top: 10px;' in note_block
    assert 'padding: 10px 14px;' in note_block


def test_targeted_icon_size_css_overrides_only_requested_contexts() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()

    section_icon = css_rule_body(css, ".section-title-icon")
    assert_declarations(section_icon, ["height: 1.05em;", "width: 1.05em;", "stroke-width: 1.55;"])

    disclosure_section_icon = css_rule_body(css, ".section-disclosure > summary .section-title-icon")
    assert_declarations(disclosure_section_icon, ["height: 1.15em;", "width: 1.15em;"])
    assert "stroke-width" not in disclosure_section_icon

    assert '<h2 id="today-title"><span class="section-title-label"><svg class="section-title-icon"' in html
    assert '<h2 id="manage-title"><span class="section-title-label"><svg class="section-title-icon"' in html
    assert '<summary id="history-title"><span class="section-title-label"><svg class="section-title-icon"' in html
    assert '<summary id="visit-summary-title"><span class="section-title-label"><svg class="section-title-icon"' in html
    assert '<summary id="health-history-title"><span class="section-title-label"><svg class="section-title-icon"' in html

    settings_icon = re.search(r"(?<!\.section-title-icon,\n)^\.settings-summary-icon\s*\{(?P<body>.*?)\n\}", css, re.S | re.M).group("body")
    assert_declarations(settings_icon, ["height: 0.95em;", "width: 0.95em;", "stroke-width: 1.6;"])

    settings_summary_icon = css_rule_body(css, ".settings-disclosure > summary .settings-summary-icon")
    assert_declarations(settings_summary_icon, ["height: 1.05em;", "width: 1.05em;"])
    assert "stroke-width" not in settings_summary_icon

    button_icon = css_rule_body(css, ".button-type-icon")
    assert_declarations(button_icon, ["flex: 0 0 auto;", "height: 20px;", "width: 20px;"])

    record_button_icon = css_rule_body(css, ".record-input-section .button-type-icon")
    assert_declarations(record_button_icon, ["height: 22px;", "width: 22px;"])

    action_icon = css_rule_body(css, ".event .event-actions .button-icon")
    assert_declarations(action_icon, ["height: 32px;", "min-height: 32px;", "min-width: 32px;", "width: 32px;"])

    event_icon = css_rule_body(css, ".event-type-icon")
    assert_declarations(event_icon, ["height: 18px;", "width: 18px;"])

    assert 'src="app.js?v=30"' in html


def test_static_asset_versions_are_current_for_targeted_icon_size_update() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    assert 'href="styles.css?v=29"' in html
    assert 'styles.css?v=28"' not in html


def test_app_js_asset_version_is_current_for_past_record_summary_update() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    assert 'src="app.js?v=30"' in html
    assert 'app.js?v=26"' not in html






def test_record_health_icon_is_table_only_and_other_section_icons_stay_unchanged() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    symbol_match = re.search(r'<symbol id="icon-record-health" viewBox="0 0 24 24">(?P<body>.*?)</symbol>', html, re.S)
    assert symbol_match
    body = symbol_match.group('body')

    assert '<rect x="4.8" y="5.2" width="14.4" height="13.6" rx="1.8" />' in body
    assert 'M4.8 9.3h14.4' in body
    assert 'M9.6 5.2v13.6' in body
    assert 'M14.4 5.2v13.6' in body
    assert 'M6.7 14.8h2l1-2.1 1.8 4.1 1.6-3h1.6l1-1.5 1.7 2.5' not in body
    assert not re.search(r'<(?:circle|polyline|polygon)\b', body)
    assert 'use href="#icon-record-health"' in html
    assert '<svg class="section-title-icon" aria-hidden="true" focusable="false"><use href="#icon-record-health"></use></svg>' in html

    assert '<symbol id="icon-record-today" viewBox="0 0 24 24">\n      <rect x="5.5" y="4.5" width="10.5" height="15" rx="2" />' in html
    assert '<symbol id="icon-record-history" viewBox="0 0 24 24">\n      <circle cx="9.2" cy="12" r="5.2" />' in html
    assert '<symbol id="icon-record-summary" viewBox="0 0 24 24">\n      <path d="M5 19h14" />' in html
    assert '<symbol id="icon-management" viewBox="0 0 24 24">' in html

def test_disclosure_html_roles_are_explicit_and_existing_relationships_remain() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()

    assert '<details id="history-details" class="section-disclosure">\n          <summary id="history-title"><span class="section-title-label"><svg class="section-title-icon" aria-hidden="true" focusable="false"><use href="#icon-record-history"></use></svg>過去の記録</span></summary>' in html
    assert '<section class="card history-card" aria-labelledby="history-title">' in html
    assert '<details id="visit-summary-details" class="section-disclosure">\n          <summary id="visit-summary-title"><span class="section-title-label"><svg class="section-title-icon" aria-hidden="true" focusable="false"><use href="#icon-record-summary"></use></svg>記録の集計</span></summary>\n          <p>痛みと服薬の記録を、期間を指定して集計します。</p>' in html
    assert '<section class="card visit-summary-card" aria-labelledby="visit-summary-title">' in html
    assert '<details id="health-history-details" class="section-disclosure">\n          <summary id="health-history-title"><span class="section-title-label"><svg class="section-title-icon" aria-hidden="true" focusable="false"><use href="#icon-record-health"></use></svg>過去の記録とヘルスケアデータ</span></summary>' in html
    assert '<section class="card health-history-card" aria-labelledby="health-history-title">' in html
    assert '<details id="health-history-columns-panel" class="health-history-columns-panel settings-disclosure">\n            <summary>表示項目</summary>' in html
    assert '<details class="medication-settings settings-disclosure">\n          <summary id="medication-settings-title"><span class="settings-summary-label"><svg class="settings-summary-icon" aria-hidden="true" focusable="false"><use href="#icon-medication-settings"></use></svg><span id="medication-settings-summary">薬設定</span></span></summary>' in html
    assert '<details class="pain-state-settings settings-disclosure">\n          <summary id="pain-state-settings-title"><span class="settings-summary-label"><svg class="settings-summary-icon" aria-hidden="true" focusable="false"><use href="#icon-pain-settings"></use></svg><span id="pain-state-settings-summary">痛み状態設定</span></span></summary>' in html
    assert '<details class="comparison-period-settings settings-disclosure">\n          <summary id="comparison-period-title"><span class="settings-summary-label"><svg class="settings-summary-icon" aria-hidden="true" focusable="false"><use href="#icon-period-settings"></use></svg><span id="comparison-period-summary">体調比較用期間の設定</span></span></summary>' in html
    assert '<symbol id="icon-medication-settings" viewBox="0 0 24 24">' in html
    assert '<symbol id="icon-pain-settings" viewBox="0 0 24 24">' in html
    assert '<symbol id="icon-period-settings" viewBox="0 0 24 24">' in html


def test_disclosure_css_uses_role_selectors_without_global_summary_rule() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()

    assert re.search(r"(^|\n)summary\s*\{", css) is None
    assert re.search(r"(^|\n)summary::(?:before|after)\s*\{", css) is None
    assert "summary::-webkit-details-marker" not in css

    section_summary = css_rule_body(css, ".section-disclosure > summary")
    assert_declarations(section_summary, ["cursor: pointer;", "font-weight: 700;", "padding: 8px 0;"])

    settings_summary = css_rule_body(css, ".settings-disclosure > summary")
    assert_declarations(settings_summary, [
        "border: 1px solid var(--border);",
        "border-radius: 12px;",
        "background: var(--surface-muted);",
        "color: var(--text);",
        "cursor: pointer;",
        "line-height: 1.35;",
        "padding: 12px;",
        "overflow-wrap: anywhere;",
    ])
    assert_declarations(css_rule_body(css, ".settings-disclosure > summary:focus-visible"), [
        "outline: 3px solid var(--focus-ring);",
        "outline-offset: 2px;",
    ])
    assert_declarations(css_rule_body(css, ".settings-disclosure[open] > summary"), ["margin-bottom: 14px;"])

    assert re.search(r"(^|\n)\.settings-disclosure summary\s*\{", css) is None
    assert re.search(r"(^|\n)\.settings-disclosure summary:focus-visible\s*\{", css) is None
    assert re.search(r"(^|\n)\.settings-disclosure\[open\] summary\s*\{", css) is None
    assert re.search(r"(^|\n)\.history-card details > summary\s*\{", css) is None

    columns_summary = css_rule_body(css, ".health-history-columns-panel > summary")
    assert_declarations(columns_summary, ["min-height: 44px;"])
    assert_no_declarations(columns_summary, [
        "border:", "border-radius:", "background:", "color:", "cursor:",
        "line-height:", "padding:", "overflow-wrap:", "outline:", "outline-offset:",
    ])
    assert_declarations(css_rule_body(css, ".health-history-columns-panel"), ["margin: 12px 0;"])
    assert_declarations(css_rule_body(css, ".health-history-columns-panel[open] > summary"), ["margin-bottom: 12px;"])


def test_dynamic_summary_styles_are_preserved_after_removing_global_summary_rule() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()
    app_js = (Path(__file__).parents[1] / "docs" / "app.js").read_text()

    assert "details.className = 'visit-summary-dose-pain-item';" in app_js
    assert "const summary = document.createElement('summary');" in app_js
    dose_summary = css_rule_body(css, ".visit-summary-dose-pain-item > summary")
    assert_declarations(dose_summary, ["cursor: pointer;", "font-weight: 700;", "padding: 8px 0;"])

    assert "<details><summary>TideTrace</summary>" in app_js
    assert "<details><summary>${cat}</summary>" in app_js
    nested_columns_summary = css_rule_body(css, ".health-history-columns-panel details > summary")
    assert_declarations(nested_columns_summary, [
        "cursor: pointer;",
        "font-weight: 700;",
        "min-height: 36px;",
        "padding: 8px 0;",
    ])


def test_form_control_classification_regression() -> None:
    root = Path(__file__).parents[1]
    html = (root / "docs" / "index.html").read_text()
    app_js = (root / "docs" / "app.js").read_text()
    css = (root / "docs" / "styles.css").read_text()

    assert '<label for="pain-score" class="form-field-label">痛みスコア</label>' in html
    assert '<select id="pain-score" class="form-control-base form-control-full">' in html
    assert '<textarea id="record-note-input" class="form-control-base form-control-full"' in html
    assert '<input id="summary-start-date" class="form-control-base form-control" type="date">' in html
    assert '<input id="summary-end-yesterday" name="summary-end-mode" type="radio" class="radio-control"' in html
    assert '<input id="medication-active" type="checkbox" class="checkbox-control" checked>' in html
    assert '<input id="import-file" class="visually-hidden-file-input" type="file"' in html
    assert 'visually-hidden-file-input form-control' not in html
    assert '<input id="medication-option-id" type="hidden">' in html

    assert '<label class="form-field-label" for="edit-local-date">日付</label>' in app_js
    assert '<input id="edit-local-time" class="form-control-base form-control" type="time"' in app_js
    assert '<select id="edit-pain-score" class="form-control-base form-control">' in app_js
    assert '<textarea id="edit-note" class="form-control-base form-control"' in app_js
    assert "select.className = 'form-control-base form-control';" in app_js
    assert '<input class="form-control-base form-control-compact" data-column-label-index="${index}"' in app_js
    assert '<input class="checkbox-control" type="checkbox" data-column-toggle=' in app_js
    assert 'form-control-compact form-control' not in app_js

    assert 'input, select, textarea' not in css
    assert 'input, select, textarea, button' not in css
    assert '\nlabel {' not in css
    assert '.form-field-label {' in css
    assert '.form-control-base {' in css
    assert '.form-control-full {' in css or '.form-control-full' in css
    assert '.form-control-compact {' in css
    assert '.checkbox-control,' in css
    assert '.radio-control {' in css


def test_button_role_classification_regression() -> None:
    root = Path(__file__).parents[1]
    html = (root / "docs" / "index.html").read_text()
    app_js = (root / "docs" / "app.js").read_text()
    css = (root / "docs" / "styles.css").read_text()

    static_buttons = re.findall(r"<button\b[^>]*>", html)
    assert static_buttons
    assert all('button-base' in button for button in static_buttons)

    assert 'class="button-base button-full primary-button setup-start-button"' in html
    assert 'class="button-base button-full secondary-button setup-restore-button"' in html
    assert 'class="button-base toast-undo-button"' in html
    assert 'class="button-base button-compact secondary-button note-save-button"' in html
    assert 'class="file-action-label button-base button-full primary-button" for="heartwatch-csv-file"' in html
    assert 'class="button-base button-full danger" type="button">全データ削除' in html

    dynamic_patterns = [
        "editButton.className = 'button-base button-icon secondary-button edit-event-button';",
        "button.className = 'button-base button-icon danger delete-event-button';",
        "deleteButton.className = 'button-base button-icon danger delete-event-button';",
        "toggleButton.className = 'button-base button-compact secondary-button pain-state-toggle-button';",
        "toggleButton.className = 'button-base button-compact secondary-button medication-toggle-button';",
        "button.className = 'button-base button-full primary-button';",
        "button.className = 'button-base button-compact secondary-button history-detail-button';",
        "recentButton.className = 'button-base button-compact secondary-button history-nav-button';",
        "olderButton.className = 'button-base button-compact secondary-button history-nav-button';",
        'class="button-base button-icon secondary-button column-reorder-button"',
        'class="button-base button-icon danger delete-event-button column-remove-button"',
        'class="button-base button-full primary-button">保存',
        'class="button-base button-full secondary-button">初期表示に戻す',
    ]
    for pattern in dynamic_patterns:
        assert pattern in app_js

    assert re.search(r"\.button-full\s*\{\s*width: 100%;\s*\}", css)
    button_base_rule = re.search(r"\.button-base\s*\{(?P<body>.*?)\n\}", css, re.S).group('body')
    assert 'width:' not in button_base_rule
    assert 'background:' not in button_base_rule
    assert 'color:' not in button_base_rule
    assert 'border: 0' not in button_base_rule

    assert 'button:not(' not in css
    assert re.search(r'(^|\n)button:active', css) is None
    assert 'button.danger' not in css
    assert re.search(r"\nbutton\s*\{", css) is None
    assert 'button,\n.primary-button' not in css
    assert '.primary-button:hover' in css
    assert '.primary-button:active' in css
    assert '.secondary-button:active' in css
    assert '.danger:active' in css
    assert '.button-compact {' in css
    assert '.button-icon {' in css


def css_rule_body(css: str, selector: str) -> str:
    match = re.search(rf"(^|\n){re.escape(selector)}\s*\{{(?P<body>.*?)\n\}}", css, re.S)
    assert match, f"Missing CSS rule for {selector}"
    return match.group("body")


def assert_declarations(body: str, declarations: list[str]) -> None:
    for declaration in declarations:
        assert declaration in body


def assert_no_declarations(body: str, declarations: list[str]) -> None:
    for declaration in declarations:
        assert declaration not in body


def test_redundant_component_css_declarations_are_removed() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()

    compact_declarations = [
        "margin: 0;",
        "min-height: 40px;",
        "padding: 8px 12px;",
        "width: auto;",
    ]
    history_detail = css_rule_body(css, ".history-detail-button")
    assert_declarations(history_detail, ["flex: 0 0 auto;"])
    assert_no_declarations(history_detail, compact_declarations)

    history_nav = css_rule_body(css, ".history-nav-button")
    assert_declarations(history_nav, ["align-self: flex-start;"])
    assert_no_declarations(history_nav, compact_declarations)

    checkbox_row_control = css_rule_body(css, ".checkbox-row .checkbox-control")
    assert_declarations(checkbox_row_control, ["flex: 0 0 auto;", "margin: 0;"])
    assert_no_declarations(checkbox_row_control, ["width: auto;"])

    radio_row_control = css_rule_body(css, ".radio-row .radio-control")
    assert_declarations(radio_row_control, ["flex: 0 0 auto;", "margin: 0;"])
    assert_no_declarations(radio_row_control, ["width: auto;"])

    assert re.search(r"(^|\n)\.edit-event-button:active\s*\{", css) is None
    assert re.search(r"(^|\n)\.delete-event-button:active\s*\{", css) is None
    assert re.search(r"(^|\n)\.column-reorder-button\s*\{", css) is None
    assert re.search(r"(^|\n)\.column-reorder-button:active\s*\{", css) is None

    assert_declarations(css_rule_body(css, ".button-compact"), compact_declarations)
    assert "width: auto;" in css_rule_body(css, ".checkbox-control,\n.radio-control")
    assert "width: auto;" in css_rule_body(css, ".radio-control")

    secondary_button = css_rule_body(css, ".secondary-button")
    assert_declarations(secondary_button, [
        "background: var(--surface-muted);",
        "color: var(--text);",
        "border: 1px solid var(--border);",
    ])
    assert ".secondary-button:active { background: var(--surface); }" in css
    assert ".danger:active { background: var(--danger-active-bg); }" in css
    assert "font-weight: 700;" in css_rule_body(css, ".button-base")
    assert re.search(r"\.column-reorder-button,\n\.column-remove-button\.delete-event-button\s*\{\n  font-size: 1rem;\n\}", css)

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


def test_health_review_columns_persist_save_reload_and_heartwatch_selection() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        let stored = '';
        global.localStorage = {
          setItem(key, value) { assert.equal(key, STORAGE_KEY); stored = value; },
          getItem(key) { assert.equal(key, STORAGE_KEY); return stored; }
        };
        appData = {
          schemaVersion: 1,
          appName: 'Tide Trace',
          settings: {
            painStateOptions: [{ id: 'state_a', label: '状態A', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med_a', label: '薬A', active: true, defaultAmount: 1, unit: '錠', sortOrder: 1 }],
            lastJsonExportedAtUtc: null,
            lastCsvExportedAtUtc: null,
            healthReviewColumns: [
              { columnId: 'heartwatch:bp-am-systolic', shortLabel: '朝血', shortLabelMode: 'custom' },
              { columnId: 'tidetrace:note:count', shortLabel: 'メモ', shortLabelMode: 'auto' },
              { columnId: 'heartwatch:steps', shortLabel: '歩', shortLabelMode: 'custom' },
              { columnId: 'tidetrace:medication:med_a:count', shortLabel: '薬A', shortLabelMode: 'custom' }
            ]
          },
          periods: [],
          events: []
        };
        const savedColumns = structuredClone(appData.settings.healthReviewColumns);
        saveData();
        appData = null;
        const loaded = loadStoredData();
        assert.deepEqual(loaded.settings.healthReviewColumns, savedColumns);
        assert.equal(loaded.settings.healthReviewColumns.some((column) => column.columnId === 'heartwatch:sleep-duration'), false);
        assert.deepEqual(loaded.settings.healthReviewColumns.map((column) => column.columnId), savedColumns.map((column) => column.columnId));
        assert.deepEqual(loaded.settings.healthReviewColumns.map((column) => column.shortLabel), ['朝血', 'メモ', '歩', '薬A']);
        """
    )


def test_health_review_import_uses_backup_settings_and_round_trip() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        appData = {
          settings: {
            painStateOptions: [{ id: 'old_state', label: '旧状態', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'old_med', label: '旧薬', active: true, defaultAmount: 1, unit: '錠', sortOrder: 1 }]
          },
          periods: [],
          events: []
        };
        const backup = {
          schemaVersion: 1,
          appName: 'Tide Trace',
          settings: {
            painStateOptions: [{ id: 'backup_state', label: '復元状態', active: false, sortOrder: 1 }],
            medicationOptions: [{ id: 'backup_med', label: '復元薬', active: false, defaultAmount: 1, unit: '錠', sortOrder: 1 }],
            lastJsonExportedAtUtc: '2026-06-20T00:00:00.000Z',
            lastCsvExportedAtUtc: null,
            healthReviewColumns: [
              { columnId: 'tidetrace:medication:backup_med:count', shortLabel: '復薬', shortLabelMode: 'custom' },
              { columnId: 'tidetrace:pain-state:backup_state:average', shortLabel: '復平', shortLabelMode: 'custom' },
              { columnId: 'heartwatch:rest-high-bpm', shortLabel: '安HR', shortLabelMode: 'custom' }
            ]
          },
          periods: [],
          events: []
        };
        const normalized = normalizeImportedData(structuredClone(backup));
        assert.equal(validateData(normalized), true);
        assert.deepEqual(normalized.settings.healthReviewColumns, backup.settings.healthReviewColumns);
        appData = null;
        const roundTrip = normalizeImportedData(JSON.parse(JSON.stringify(normalized)));
        assert.deepEqual(roundTrip.settings.healthReviewColumns, backup.settings.healthReviewColumns);
        assert.equal(healthHistoryMetricById('tidetrace:medication:backup_med:count', roundTrip.settings).option.label, '復元薬');
        assert.equal(healthHistoryMetricById('tidetrace:pain-state:backup_state:average', roundTrip.settings).option.label, '復元状態');
        """
    )


def test_health_review_old_backup_and_malformed_columns_are_repaired_only() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const base = {
          schemaVersion: 1,
          appName: 'Tide Trace',
          settings: {
            painStateOptions: [{ id: 'state_a', label: '状態A', active: true, sortOrder: 1 }],
            medicationOptions: [
              { id: 'med_a', label: '薬A', active: true, defaultAmount: 1, unit: '錠', sortOrder: 1 },
              { id: 'med_b', label: '薬B', active: false, defaultAmount: 1, unit: '錠', sortOrder: 2 }
            ],
            lastJsonExportedAtUtc: '2026-06-20T00:00:00.000Z',
            lastCsvExportedAtUtc: '2026-06-21T00:00:00.000Z'
          },
          periods: [{ id: 'period', label: '期間', startDate: '2026-06-01', endDate: '2026-06-02', note: '' }],
          events: [{ id: 'event', type: 'note', recordedAtUtc: '2026-06-19T00:00:00.000Z', localDate: '2026-06-19', localTime: '09:00', timezone: 'Asia/Tokyo', createdAtUtc: '2026-06-19T00:00:00.000Z', updatedAtUtc: '2026-06-19T00:00:00.000Z', note: '記録' }]
        };
        const oldBackup = normalizeImportedData(structuredClone(base));
        assert.equal(validateData(oldBackup), true);
        assert.deepEqual(oldBackup.settings.healthReviewColumns.map((column) => column.columnId).slice(0, 3), ['tidetrace:pain:max', 'tidetrace:pain:average', 'tidetrace:medication:med_a:count']);
        assert.deepEqual(oldBackup.events, base.events);
        assert.deepEqual(oldBackup.periods, base.periods);
        const malformed = structuredClone(base);
        malformed.settings.healthReviewColumns = [
          null,
          { columnId: 'date', shortLabel: '日付', shortLabelMode: 'custom' },
          { columnId: 'tidetrace:unknown', shortLabel: '不明', shortLabelMode: 'custom' },
          { columnId: 'tidetrace:medication:med_b:count', shortLabel: '非薬', shortLabelMode: 'custom' },
          { columnId: 'tidetrace:medication:med_b:count', shortLabel: '重複', shortLabelMode: 'custom' },
          { columnId: 'tidetrace:pain-state:state_a:max', shortLabel: '', shortLabelMode: 'weird' }
        ];
        const repaired = normalizeImportedData(malformed);
        assert.equal(validateData(repaired), true);
        assert.deepEqual(repaired.settings.healthReviewColumns, [
          { columnId: 'tidetrace:medication:med_b:count', shortLabel: '非薬', shortLabelMode: 'custom' },
          { columnId: 'tidetrace:pain-state:state_a:max', shortLabel: '状最', shortLabelMode: 'auto' }
        ]);
        assert.deepEqual(repaired.events, base.events);
        assert.deepEqual(repaired.periods, base.periods);
        assert.deepEqual(repaired.settings.medicationOptions, base.settings.medicationOptions);
        assert.deepEqual(repaired.settings.painStateOptions, base.settings.painStateOptions);
        assert.equal(repaired.settings.lastJsonExportedAtUtc, base.settings.lastJsonExportedAtUtc);
        assert.equal(repaired.settings.lastCsvExportedAtUtc, base.settings.lastCsvExportedAtUtc);
        """
    )


def test_health_review_startup_persists_normalization_and_source_has_no_silent_delete() -> None:
    source = APP_JS.read_text()
    assert "catch { delete copy.settings.healthReviewColumns; }" not in source
    assert "delete data.settings.healthReviewColumns" not in source
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const storedObject = {
          schemaVersion: 1,
          appName: 'Tide Trace',
          settings: {
            painStateOptions: [{ id: 'state_a', label: '状態A', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med_a', label: '薬A', active: true, defaultAmount: 1, unit: '錠', sortOrder: 1 }],
            lastJsonExportedAtUtc: null,
            lastCsvExportedAtUtc: null
          },
          periods: [],
          events: []
        };
        let stored = JSON.stringify(storedObject);
        let writes = 0;
        global.localStorage = {
          getItem() { return stored; },
          setItem(key, value) { writes += 1; stored = value; }
        };
        const loaded = loadStoredData();
        assert.equal(writes, 1);
        assert.equal(JSON.parse(stored).settings.healthReviewColumns.some((column) => column.columnId === 'tidetrace:medication:med_a:count'), true);
        appData = loaded;
        appData = null;
        const loadedAgain = loadStoredData();
        assert.equal(writes, 1);
        assert.deepEqual(loadedAgain.settings.healthReviewColumns, loaded.settings.healthReviewColumns);
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
        ensureHealthReviewColumns(appData.settings);
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


def test_settings_forms_start_hidden_after_registered_lists() -> None:
    html = (Path(__file__).parents[1] / "docs" / "index.html").read_text()
    management = html[html.index('<section class="card management"'):html.index('<button id="delete-all"')]
    for removed_heading in ["登録済みの薬", "登録済みの痛み状態", "登録済みの体調比較用期間"]:
        assert f'class="settings-list-title">{removed_heading}</' not in management
    for list_id, add_button, form in [
        ("medication-settings-list", "新しい薬を追加", "medication-option-form"),
        ("pain-state-settings-list", "新しい状態を追加", "pain-state-option-form"),
        ("comparison-period-list", "新しい期間を追加", "comparison-period-form"),
    ]:
        list_index = management.index(f'id="{list_id}"')
        add_index = management.index(add_button, list_index)
        assert list_index < add_index < management.index(f'id="{form}"')
        form_tag = re.search(rf'<form id="{form}"[^>]*>', html).group(0)
        assert "settings-form-panel" in form_tag
        assert "hidden" in form_tag
    assert html.count('class="settings-form-actions"') == 3
    assert 'class="settings-add-button"' in html or 'settings-add-button' in html


def test_settings_form_open_edit_cancel_and_validation_states() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        function element(id) {
          return {
            id, value: '', textContent: '', hidden: false, checked: false, className: '', innerHTML: '', children: [],
            classList: { add() {}, remove() {}, toggle() {} },
            reset() { this.value = ''; },
            querySelector() { return submitButtons[id] || null; },
            appendChild(child) { this.children.push(child); },
            append(...items) { this.children.push(...items); },
            addEventListener() {},
            setAttribute(name, value) { this[name] = value; },
            focus() { focused = id; },
            scrollIntoView(options) { scrolled = { id, options }; }
          };
        }
        let focused = '';
        let scrolled = null;
        const ids = ['medication-option-form','open-medication-option-form','medication-label','medication-option-id','medication-default-amount','medication-unit','medication-sort-order','medication-active','save-medication-option','cancel-medication-edit','medication-settings-message','medication-option-form-title','pain-state-option-form','open-pain-state-option-form','pain-state-label','pain-state-option-id','pain-state-sort-order','pain-state-active','save-pain-state-option','cancel-pain-state-edit','pain-state-settings-message','pain-state-option-form-title','comparison-period-form','open-comparison-period-form','comparison-period-label','comparison-period-start','comparison-period-end','comparison-period-note','cancel-comparison-period-edit','comparison-period-message','comparison-period-form-title'];
        const elements = Object.fromEntries(ids.map((id) => [id, element(id)]));
        const submitButtons = {
          'comparison-period-form': { textContent: '', hidden: false },
          'medication-option-form': elements['save-medication-option'],
          'pain-state-option-form': elements['save-pain-state-option']
        };
        global.document = { getElementById: (id) => elements[id] || element(id), createElement: (tag) => element(tag) };
        global.localStorage = { setItem() {}, getItem() { return null; } };
        global.crypto = { randomUUID: () => 'uuid' };
        global.showToast = () => {};
        appData = { schemaVersion: 1, appName: 'Tide Trace', settings: { medicationOptions: [{ id: 'med1', label: '薬A', defaultAmount: 2, unit: '錠', active: true, sortOrder: 4 }], painStateOptions: [{ id: 'pain1', label: '座位', active: false, sortOrder: 3 }], lastJsonExportedAtUtc: null, lastCsvExportedAtUtc: null }, periods: [{ id: 'period1', label: '期間A', startDate: '2026-07-01', endDate: '2026-07-03', note: 'memo' }], events: [] };

        openMedicationOptionForm();
        assert.equal(elements['medication-option-form'].hidden, false);
        assert.equal(elements['open-medication-option-form'].hidden, true);
        assert.equal(elements['medication-default-amount'].value, '1');
        assert.equal(String(elements['medication-sort-order'].value), '5');
        assert.equal(elements['save-medication-option'].textContent, '薬を追加');
        assert.equal(focused, 'medication-label');
        editMedicationOption('med1');
        assert.equal(editingMedicationOptionId, 'med1');
        assert.equal(elements['medication-label'].value, '薬A');
        assert.equal(elements['medication-option-form-title'].textContent, '薬を編集');
        assert.equal(elements['save-medication-option'].textContent, '薬を更新');
        elements['medication-label'].value = '';
        elements['medication-default-amount'].value = String(elements['medication-default-amount'].value);
        elements['medication-sort-order'].value = String(elements['medication-sort-order'].value);
        saveMedicationOptionFromForm();
        assert.equal(elements['medication-option-form'].hidden, false);
        assert.equal(elements['open-medication-option-form'].hidden, true);
        closeMedicationOptionForm();
        assert.equal(editingMedicationOptionId, null);
        assert.equal(elements['medication-option-form'].hidden, true);
        assert.equal(elements['open-medication-option-form'].hidden, false);

        openPainStateOptionForm();
        assert.equal(String(elements['pain-state-sort-order'].value), '4');
        editPainStateOption('pain1');
        assert.equal(editingPainStateOptionId, 'pain1');
        assert.equal(elements['pain-state-option-form-title'].textContent, '痛み状態を編集');
        assert.equal(elements['save-pain-state-option'].textContent, '痛み状態を更新');
        closePainStateOptionForm();
        assert.equal(elements['pain-state-option-form'].hidden, true);

        openPeriodForm();
        assert.equal(elements['comparison-period-start'].value, '2026-07-04');
        editPeriod('period1');
        assert.equal(editingPeriodId, 'period1');
        assert.equal(elements['comparison-period-form-title'].textContent, '体調比較用期間を編集');
        assert.equal(submitButtons['comparison-period-form'].textContent, '体調比較用期間を更新');
        closePeriodForm();
        assert.equal(elements['comparison-period-form'].hidden, true);
        """
    )


def test_settings_forms_share_css_classes() -> None:
    css = (Path(__file__).parents[1] / "docs" / "styles.css").read_text()
    assert ".settings-form-panel" in css
    assert ".settings-add-button" in css
    assert ".settings-form-actions" in css
