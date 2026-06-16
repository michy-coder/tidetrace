const STORAGE_KEY = 'tideTrace.data.v1';
const TIMEZONE = 'Asia/Tokyo';
const SCHEMA_ERROR = 'このJSONは読み込めません。\nsettings / periods / events の形式を確認してください。';
const JSON_ERROR = 'JSONの形式を確認してください。';

let appData = null;
let lastSavedEventId = null;
let saveFeedbackTimer = null;

const $ = (id) => document.getElementById(id);

function nowParts() {
  const now = new Date();
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIMEZONE,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false
  }).formatToParts(now).reduce((acc, part) => {
    acc[part.type] = part.value;
    return acc;
  }, {});
  return {
    iso: now.toISOString(),
    localDate: `${parts.year}-${parts.month}-${parts.day}`,
    localTime: `${parts.hour}:${parts.minute}`
  };
}

function parseJson(text) {
  try { return { data: JSON.parse(text), error: null }; }
  catch { return { data: null, error: JSON_ERROR }; }
}

function validateData(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return false;
  if (typeof data.schemaVersion !== 'number' || data.schemaVersion !== 1) return false;
  if (typeof data.appName !== 'string') return false;
  if (!data.settings || typeof data.settings !== 'object' || Array.isArray(data.settings)) return false;
  if (!Array.isArray(data.settings.painStateOptions) || !Array.isArray(data.settings.medicationOptions)) return false;
  if (!Array.isArray(data.periods) || !Array.isArray(data.events)) return false;

  const validOption = (option) => option && typeof option.id === 'string' && typeof option.label === 'string' && typeof option.active === 'boolean';
  if (!data.settings.painStateOptions.every(validOption)) return false;
  if (!data.settings.medicationOptions.every(validOption)) return false;

  const painIds = new Set(data.settings.painStateOptions.map((option) => option.id));
  const medicationIds = new Set(data.settings.medicationOptions.map((option) => option.id));
  return data.events.every((event) => {
    if (!event || typeof event !== 'object') return false;
    if (typeof event.id !== 'string') return false;
    if (!['pain', 'medication', 'note'].includes(event.type)) return false;
    for (const key of ['recordedAtUtc', 'localDate', 'localTime', 'timezone', 'createdAtUtc', 'updatedAtUtc']) {
      if (typeof event[key] !== 'string') return false;
    }
    if (event.note !== undefined && typeof event.note !== 'string') return false;
    if (event.type === 'pain') {
      return typeof event.painScore === 'number' && event.painScore >= 0 && event.painScore <= 10 &&
        typeof event.stateOptionId === 'string' && painIds.has(event.stateOptionId);
    }
    if (event.type === 'medication') {
      return typeof event.medicationOptionId === 'string' && medicationIds.has(event.medicationOptionId);
    }
    return typeof event.note === 'string';
  });
}

function saveData() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(appData));
}

function loadStoredData() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;
  const parsed = parseJson(stored);
  return parsed.data && validateData(parsed.data) ? parsed.data : null;
}

function showSetup(message = '') {
  $('setup-screen').classList.remove('hidden');
  $('app-screen').classList.add('hidden');
  $('setup-error').textContent = message;
}

function showApp() {
  $('setup-screen').classList.add('hidden');
  $('app-screen').classList.remove('hidden');
  render();
}

function initializeFromText(text, errorElement) {
  const parsed = parseJson(text);
  if (parsed.error) { errorElement.textContent = parsed.error; return; }
  if (!validateData(parsed.data)) { errorElement.textContent = SCHEMA_ERROR; return; }
  appData = parsed.data;
  clearSaveFeedback();
  saveData();
  errorElement.textContent = '';
  showApp();
}

function activePainOptions() { return appData.settings.painStateOptions.filter((option) => option.active); }
function activeMedicationOptions() { return appData.settings.medicationOptions.filter((option) => option.active); }
function findPainLabel(id) { return (appData.settings.painStateOptions.find((option) => option.id === id) || {}).label || ''; }
function findMedicationLabel(id) { return (appData.settings.medicationOptions.find((option) => option.id === id) || {}).label || ''; }

function createEvent(base) {
  const time = nowParts();
  const id = crypto.randomUUID ? crypto.randomUUID() : `evt_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return { id, recordedAtUtc: time.iso, localDate: time.localDate, localTime: time.localTime, timezone: TIMEZONE, createdAtUtc: time.iso, updatedAtUtc: time.iso, ...base };
}

function addEvent(event, feedbackMessage = '') {
  appData.events.push(event);
  saveData();
  render();
  if (feedbackMessage) showSaveFeedback(event.id, feedbackMessage);
}

function clearSaveFeedback() {
  if (saveFeedbackTimer) {
    clearTimeout(saveFeedbackTimer);
    saveFeedbackTimer = null;
  }
  lastSavedEventId = null;
  const feedback = $('save-feedback');
  if (!feedback) return;
  feedback.classList.add('hidden');
  feedback.replaceChildren();
}

function showSaveFeedback(eventId, message) {
  if (saveFeedbackTimer) clearTimeout(saveFeedbackTimer);
  lastSavedEventId = eventId;
  const feedback = $('save-feedback');
  feedback.classList.remove('hidden');
  feedback.replaceChildren();

  const text = document.createElement('span');
  text.className = 'save-feedback-message';
  text.textContent = message;

  const button = document.createElement('button');
  button.className = 'undo-save-button';
  button.type = 'button';
  button.textContent = '取り消す';
  button.addEventListener('click', undoLastSavedEvent);

  feedback.append(text, button);
  saveFeedbackTimer = setTimeout(clearSaveFeedback, 8000);
}

function undoLastSavedEvent() {
  if (!lastSavedEventId) return;
  const eventId = lastSavedEventId;
  appData.events = appData.events.filter((event) => event.id !== eventId);
  saveData();
  clearSaveFeedback();
  render();
}

function sortedEvents(events) {
  return [...events].sort((a, b) => (a.localDate + a.localTime + a.createdAtUtc).localeCompare(b.localDate + b.localTime + b.createdAtUtc));
}

function eventText(event) {
  const parts = [`${event.localTime}`, event.type];
  if (event.type === 'pain') parts.push(`score ${event.painScore}`, findPainLabel(event.stateOptionId));
  if (event.type === 'medication') parts.push(findMedicationLabel(event.medicationOptionId));
  if (event.note) parts.push(event.note);
  return parts.filter(Boolean).join(' / ');
}

function renderEventList(container, events) {
  container.innerHTML = '';
  if (events.length === 0) {
    container.innerHTML = '<p class="empty">記録はありません。</p>';
    return;
  }
  sortedEvents(events).forEach((event) => {
    const item = document.createElement('div');
    item.className = 'event';
    const content = document.createElement('div');
    content.className = 'event-content';
    const body = document.createElement('div');
    body.textContent = eventText(event);
    const meta = document.createElement('div');
    meta.className = 'event-meta';
    meta.textContent = event.localDate;
    const button = document.createElement('button');
    button.className = 'delete-event-button';
    button.type = 'button';
    button.textContent = '×';
    button.setAttribute('aria-label', '記録を削除');
    button.addEventListener('click', () => deleteEvent(event.id));
    content.append(meta, body);
    item.append(content, button);
    container.appendChild(item);
  });
}

function deleteEvent(id) {
  if (!confirm('この記録を削除しますか？')) return;
  appData.events = appData.events.filter((event) => event.id !== id);
  if (lastSavedEventId === id) clearSaveFeedback();
  saveData();
  render();
}

function elapsedText(iso) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
  return `${Math.floor(minutes / 60)}時間${minutes % 60}分`;
}

function render() {
  const today = nowParts().localDate;
  $('pain-score').innerHTML = Array.from({ length: 11 }, (_, value) => `<option value="${value}">${value}</option>`).join('');
  $('pain-state').innerHTML = activePainOptions().map((option) => `<option value="${option.id}">${escapeHtml(option.label)}</option>`).join('');
  $('medication-buttons').innerHTML = '';
  activeMedicationOptions().forEach((option) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = option.label;
    button.addEventListener('click', () => saveMedication(option.id));
    $('medication-buttons').appendChild(button);
  });

  $('last-medication-list').innerHTML = '';
  appData.settings.medicationOptions.forEach((option) => {
    const last = sortedEvents(appData.events.filter((event) => event.type === 'medication' && event.medicationOptionId === option.id)).at(-1);
    const item = document.createElement('div');
    item.className = 'last-medication-item';
    item.textContent = last ? `${option.label}：前回 ${last.localTime} / 経過 ${elapsedText(last.recordedAtUtc)}` : `${option.label}：記録なし`;
    $('last-medication-list').appendChild(item);
  });

  renderEventList($('today-list'), appData.events.filter((event) => event.localDate === today));
  renderWeek(today);
}

function renderWeek(today) {
  const list = $('week-list');
  list.innerHTML = '';
  const dates = [];
  const base = new Date(`${today}T00:00:00+09:00`);
  for (let i = 0; i < 7; i += 1) {
    const d = new Date(base.getTime() - i * 86400000);
    dates.push(new Intl.DateTimeFormat('en-CA', { timeZone: TIMEZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d));
  }
  dates.forEach((date) => {
    const events = appData.events.filter((event) => event.localDate === date);
    if (events.length === 0) return;
    const details = document.createElement('details');
    details.open = date === today;
    const summary = document.createElement('summary');
    summary.textContent = `${date}：${events.length}件`;
    const body = document.createElement('div');
    renderEventList(body, events);
    details.append(summary, body);
    list.appendChild(details);
  });
  if (!list.children.length) list.innerHTML = '<p class="empty">記録はありません。</p>';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
}

function csvEscape(value) {
  const text = value === undefined || value === null ? '' : String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportCsv() {
  const headers = ['id','local_date','local_time','recorded_at_utc','timezone','type','pain_score','state_option_label','medication_option_label','note','created_at_utc','updated_at_utc','schema_version'];
  const rows = sortedEvents(appData.events).map((event) => [
    event.id, event.localDate, event.localTime, event.recordedAtUtc, event.timezone, event.type,
    event.type === 'pain' ? event.painScore : '',
    event.type === 'pain' ? findPainLabel(event.stateOptionId) : '',
    event.type === 'medication' ? findMedicationLabel(event.medicationOptionId) : '',
    event.note || '', event.createdAtUtc, event.updatedAtUtc, appData.schemaVersion
  ].map(csvEscape).join(','));
  download(`tide-trace-events-${nowParts().localDate}.csv`, '\uFEFF' + [headers.join(','), ...rows].join('\r\n'), 'text/csv;charset=utf-8');
}

function exportJson() {
  download(`tide-trace-backup-${nowParts().localDate}.json`, JSON.stringify(appData, null, 2), 'application/json;charset=utf-8');
}

function readFile(input, callback, errorElement) {
  const file = input.files[0];
  if (!file) { errorElement.textContent = 'JSONファイルを選択してください。'; return; }
  const reader = new FileReader();
  reader.onload = () => callback(String(reader.result));
  reader.onerror = () => { errorElement.textContent = JSON_ERROR; };
  reader.readAsText(file);
}

function sharedNoteInput() {
  return $('shared-note-input');
}

function sharedNoteValue() {
  const input = sharedNoteInput();
  return input.value.trim();
}

function clearSharedNote() {
  const input = sharedNoteInput();
  input.value = '';
}

function saveMedication(medicationOptionId) {
  const label = findMedicationLabel(medicationOptionId);
  addEvent(createEvent({ type: 'medication', medicationOptionId, note: sharedNoteValue() }), `${label}を記録しました`);
  clearSharedNote();
  $('app-message').textContent = '';
}

function wireEvents() {
  $('load-pasted-json').addEventListener('click', () => initializeFromText($('setup-json').value, $('setup-error')));
  $('load-file-json').addEventListener('click', () => readFile($('setup-file'), (text) => initializeFromText(text, $('setup-error')), $('setup-error')));
  $('save-pain').addEventListener('click', () => {
    const stateOptionId = $('pain-state').value;
    if (!stateOptionId) { $('app-message').textContent = '痛みの状態を選択してください。'; return; }
    addEvent(createEvent({ type: 'pain', painScore: Number($('pain-score').value), stateOptionId, note: sharedNoteValue() }), '痛みを記録しました');
    clearSharedNote();
    $('app-message').textContent = '';
  });
  $('save-note').addEventListener('click', () => {
    const note = sharedNoteValue();
    if (!note) { $('app-message').textContent = 'メモを入力すると保存できます。'; return; }
    addEvent(createEvent({ type: 'note', note }), 'メモを保存しました');
    clearSharedNote();
    $('app-message').textContent = '';
  });
  $('export-csv').addEventListener('click', exportCsv);
  $('export-json').addEventListener('click', exportJson);
  $('import-json').addEventListener('click', () => {
    if (!confirm('JSONバックアップを読み込みます。\n現在のブラウザ内の記録は、読み込むデータに置き換わります。\n必要な場合は、先に現在のデータを書き出してください。')) return;
    readFile($('import-file'), (text) => initializeFromText(text, $('app-message')), $('app-message'));
  });
  $('delete-all').addEventListener('click', () => {
    if (!confirm('全データを削除します。\n必要な場合は、先にJSONバックアップまたはCSVを書き出してください。')) return;
    localStorage.removeItem(STORAGE_KEY);
    appData = null;
    showSetup();
  });
}

wireEvents();
appData = loadStoredData();
if (appData) showApp(); else showSetup();
