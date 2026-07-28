import subprocess
import tempfile
import textwrap
from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
APP_JS = ROOT / "docs" / "app.js"


def run_app_js(assertions: str) -> None:
    source = APP_JS.read_text()
    source = source[: source.rfind("wireEvents();")]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(source + "\n" + textwrap.dedent(assertions))
        script_path = Path(handle.name)
    try:
        subprocess.run(["node", script_path], check=True, text=True)
    finally:
        script_path.unlink(missing_ok=True)


def test_bottom_navigation_shows_only_the_selected_screen() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        function element(dataset) {
          return {
            dataset, hidden: false, attributes: {},
            setAttribute(name, value) { this.attributes[name] = value; },
            getAttribute(name) { return this.attributes[name]; },
            removeAttribute(name) { delete this.attributes[name]; }
          };
        }
        const screens = ['record', 'history', 'summary', 'manage'].map((name) => element({ appScreen: name }));
        const navigation = ['record', 'history', 'summary', 'manage'].map((name) => element({ appScreenTarget: name }));
        global.document = {
          querySelectorAll(selector) {
            if (selector === '[data-app-screen]') return screens;
            if (selector === '[data-app-screen-target]') return navigation;
            return [];
          }
        };
        appData = null;

        setAppScreen('manage', { scroll: false });

        assert.equal(activeAppScreen, 'manage');
        assert.deepEqual(screens.map((screen) => screen.hidden), [true, true, true, false]);
        assert.deepEqual(navigation.map((button) => button.getAttribute('aria-current') || null), [null, null, null, 'page']);

        setAppScreen('unknown', { scroll: false });
        assert.equal(activeAppScreen, 'manage');
        assert.deepEqual(screens.map((screen) => screen.hidden), [true, true, true, false]);
        """
    )


def test_record_tabs_keep_one_panel_and_matching_save_action_visible() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        function tab(name) {
          return {
            dataset: { recordTab: name }, attributes: {},
            setAttribute(key, value) { this.attributes[key] = value; },
            getAttribute(key) { return this.attributes[key]; }
          };
        }
        function panel(name) { return { dataset: { recordPanel: name }, hidden: false }; }
        function action(name) { return { dataset: { recordAction: name }, hidden: false }; }
        const tabs = ['pain', 'medication', 'note'].map(tab);
        const panels = ['pain', 'medication', 'note'].map(panel);
        const actions = ['pain', 'note'].map(action);
        const layout = { dataset: {} };
        const memo = { placeholder: '' };
        global.document = {
          getElementById(id) { return { 'record-form-layout': layout, 'record-note-input': memo }[id] || null; },
          querySelectorAll(selector) {
            if (selector === '[data-record-tab]') return tabs;
            if (selector === '[data-record-panel]') return panels;
            if (selector === '[data-record-action]') return actions;
            return [];
          }
        };

        setRecordTab('medication');

        assert.equal(activeRecordTab, 'medication');
        assert.equal(layout.dataset.activeRecordTab, 'medication');
        assert.deepEqual(tabs.map((item) => item.getAttribute('aria-selected')), ['false', 'true', 'false']);
        assert.deepEqual(panels.map((item) => item.hidden), [true, false, true]);
        assert.deepEqual(actions.map((item) => item.hidden), [true, true]);
        assert.equal(memo.placeholder, 'メモ（任意）例：夕食後に服用');

        setRecordTab('note');
        assert.deepEqual(panels.map((item) => item.hidden), [true, true, false]);
        assert.deepEqual(actions.map((item) => item.hidden), [true, false]);
        assert.equal(memo.placeholder, 'メモを入力してください');
        """
    )


def test_summary_tabs_show_only_the_selected_summary() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        function tab(name) {
          return {
            dataset: { summaryTab: name }, attributes: {},
            setAttribute(key, value) { this.attributes[key] = value; },
            getAttribute(key) { return this.attributes[key]; }
          };
        }
        const tabs = ['records', 'health'].map(tab);
        const panels = ['records', 'health'].map((name) => ({ dataset: { summaryPanel: name }, hidden: false }));
        global.document = {
          querySelectorAll(selector) {
            if (selector === '[data-summary-tab]') return tabs;
            if (selector === '[data-summary-panel]') return panels;
            return [];
          }
        };

        setSummaryTab('health');

        assert.equal(activeSummaryTab, 'health');
        assert.deepEqual(tabs.map((item) => item.getAttribute('aria-selected')), ['false', 'true']);
        assert.deepEqual(panels.map((item) => item.hidden), [true, false]);
        """
    )


def test_record_entry_toggle_updates_visibility_and_accessible_label() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const label = { textContent: '' };
        const mark = { textContent: '' };
        const button = {
          attributes: {},
          setAttribute(key, value) { this.attributes[key] = value; },
          getAttribute(key) { return this.attributes[key]; },
          querySelector(selector) {
            return selector === '.visually-hidden' ? label : mark;
          }
        };
        const body = { hidden: false };
        global.document = {
          getElementById(id) { return { 'record-entry-body': body, 'record-entry-toggle': button }[id] || null; }
        };

        setRecordEntryExpanded(false);
        assert.equal(body.hidden, true);
        assert.equal(button.getAttribute('aria-expanded'), 'false');
        assert.equal(label.textContent, '記録入力欄を開く');
        assert.equal(mark.textContent, '⌄');

        setRecordEntryExpanded(true);
        assert.equal(body.hidden, false);
        assert.equal(button.getAttribute('aria-expanded'), 'true');
        assert.equal(label.textContent, '記録入力欄を閉じる');
        assert.equal(mark.textContent, '⌃');
        """
    )


def test_csv_export_button_enables_only_after_a_supported_selection() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const select = { value: '' };
        const button = { disabled: false };
        global.document = {
          getElementById(id) { return { 'csv-export-type': select, 'export-csv': button }[id] || null; }
        };

        for (const value of ['', 'not-a-csv-type']) {
          select.value = value;
          updateCsvExportButtonState();
          assert.equal(button.disabled, true);
        }
        for (const value of ['all', 'pain', 'medication', 'note']) {
          select.value = value;
          updateCsvExportButtonState();
          assert.equal(button.disabled, false);
        }
        """
    )


def test_management_exports_share_the_primary_button_semantics() -> None:
    html = (ROOT / "docs" / "index.html").read_text()
    for button_id in ("export-json", "import-json", "export-csv"):
        match = re.search(rf'<button id="{button_id}" class="(?P<classes>[^"]+)"', html)
        assert match, f"{button_id} is missing"
        assert "primary-button" in match.group("classes").split()

    assert 'id="export-csv" class="button-base button-full primary-button" type="button" disabled' in html


def test_initial_restore_reports_the_missing_file_next_to_the_restore_control() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const restoreError = { textContent: '' };
        const fileInput = {
          files: null, value: 'old-value', clicked: false,
          click() { this.clicked = true; }
        };
        global.document = {
          getElementById(id) {
            return { 'setup-restore-error': restoreError, 'setup-import-file': fileInput }[id] || null;
          }
        };

        requestInitialBackupRestore();

        assert.equal(restoreError.textContent, 'Tide TraceのJSONバックアップを選択してください。');
        assert.equal(fileInput.value, '');
        assert.equal(fileInput.clicked, true);
        """
    )


def test_valid_backup_replaces_stored_data_without_changing_its_schema() -> None:
    run_app_js(
        """
        const assert = require('node:assert/strict');
        const backup = {
          schemaVersion: 1,
          appName: 'Tide Trace',
          settings: {
            painStateOptions: [{ id: 'pain', label: '座位', active: true, sortOrder: 1 }],
            medicationOptions: [{ id: 'med', label: '薬', defaultAmount: 1, unit: '錠', active: true, sortOrder: 1 }],
            lastJsonExportedAtUtc: null,
            lastCsvExportedAtUtc: null
          },
          periods: [],
          events: [{
            id: 'note-1', type: 'note', recordedAtUtc: '2026-07-28T00:00:00.000Z',
            localDate: '2026-07-28', localTime: '09:00', timezone: 'Asia/Tokyo',
            createdAtUtc: '2026-07-28T00:00:00.000Z', updatedAtUtc: '2026-07-28T00:00:00.000Z', note: 'メモ'
          }]
        };
        const stored = [];
        const error = { textContent: 'old error' };
        global.localStorage = { setItem(key, value) { stored.push([key, value]); } };
        global.document = {
          getElementById(id) {
            return {
              'toast-feedback': { hidden: false },
              'toast-message': { textContent: 'old message' }
            }[id] || null;
          }
        };
        showApp = () => {};

        assert.equal(initializeFromText(JSON.stringify(backup), error), true);
        assert.equal(error.textContent, '');
        assert.equal(appData.schemaVersion, 1);
        assert.equal(appData.events[0].note, 'メモ');
        assert.equal(stored.length, 1);
        assert.equal(stored[0][0], STORAGE_KEY);
        assert.equal(JSON.parse(stored[0][1]).events[0].id, 'note-1');
        """
    )
