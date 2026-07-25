from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).parents[1]
APP_JS = ROOT / "docs" / "app.js"


def run_app_js(assertions: str) -> None:
    source = APP_JS.read_text()
    source = source[: source.rfind("wireEvents();")]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
        handle.write(source + "\n" + assertions)
        script_path = Path(handle.name)
    try:
        subprocess.run(["node", script_path], check=True, text=True)
    finally:
        script_path.unlink(missing_ok=True)


def test_initial_pain_state_defaults_use_requested_labels() -> None:
    run_app_js("""
const assert = require("node:assert/strict");
assert.deepEqual(
  INITIAL_PAIN_STATE_OPTIONS.map((option) => option.label),
  ["☕️安静時", "🪑座位", "🧍立位", "🚶‍♂️‍➡️歩行時", "🛏️臥位", "その他"]
);
assert.deepEqual(
  INITIAL_PAIN_STATE_OPTIONS.map((option) => option.id),
  ["ps_001", "ps_002", "ps_003", "ps_004", "ps_005", "ps_006"]
);
""");


def test_initial_restore_precedes_the_setup_card() -> None:
    html = (ROOT / "docs" / "index.html").read_text()
    assert html.index('id="restore-initial-backup"') < html.index('id="setup-title"')
    assert html.index('id="initial-restore-error"') < html.index('id="setup-title"')


def test_initial_restore_status_is_shown_below_its_button() -> None:
    run_app_js("""
const assert = require("node:assert/strict");
const restoreError = { textContent: "" };
const setupError = { textContent: "入力エラー" };
const fileInput = {
  files: null,
  value: "",
  clicked: false,
  click() { this.clicked = true; }
};
global.document = {
  getElementById(id) {
    return {
      "initial-restore-error": restoreError,
      "setup-error": setupError,
      "setup-import-file": fileInput
    }[id];
  }
};
requestInitialBackupRestore();
assert.equal(restoreError.textContent, "Tide TraceのJSONバックアップを選択してください。");
assert.equal(setupError.textContent, "入力エラー");
assert.equal(fileInput.clicked, true);
""")
