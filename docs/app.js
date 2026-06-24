const STORAGE_KEY = 'tideTrace.data.v1';
const TIMEZONE = 'Asia/Tokyo';
const SCHEMA_ERROR = 'このJSONは読み込めません。\nsettings / periods / events の形式を確認してください。';
const JSON_ERROR = 'JSONの形式を確認してください。';

let appData = null;
let lastSavedEventId = null;
let saveFeedbackTimer = null;
let elapsedRefreshTimer = null;
let editingEventId = null;
let editingPeriodId = null;
let editingMedicationOptionId = null;
let editingPainStateOptionId = null;

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

function normalizeImportedData(data) {
  if (!data || typeof data !== 'object') return data;
  if (data.settings && Array.isArray(data.settings.painStateOptions)) {
    const usedPainIds = new Set();
    data.settings.painStateOptions = data.settings.painStateOptions.map((option, index) => {
      const source = option && typeof option === 'object' ? option : {};
      const { isActive: _legacyIsActive, ...normalizedSource } = source;
      let id = typeof source.id === 'string' && source.id ? source.id : `ps_imported_${index + 1}`;
      while (usedPainIds.has(id)) id = `${id}_${index + 1}`;
      usedPainIds.add(id);
      return {
        ...normalizedSource,
        id,
        label: typeof source.label === 'string' && source.label.trim() ? source.label : `状態 ${index + 1}`,
        active: source.active ?? source.isActive ?? true,
        sortOrder: Number.isFinite(Number(source.sortOrder)) ? Number(source.sortOrder) : index + 1
      };
    });
  }
  if (data.settings && Array.isArray(data.settings.medicationOptions)) {
    const usedIds = new Set();
    data.settings.medicationOptions = data.settings.medicationOptions.map((option, index) => {
      const source = option && typeof option === 'object' ? option : {};
      const { isActive: _legacyIsActive, ...normalizedSource } = source;
      let id = typeof source.id === 'string' && source.id ? source.id : `med_imported_${index + 1}`;
      while (usedIds.has(id)) id = `${id}_${index + 1}`;
      usedIds.add(id);
      return {
        ...normalizedSource,
        id,
        label: typeof source.label === 'string' && source.label ? source.label : `Medication ${index + 1}`,
        defaultAmount: source.defaultAmount ?? 1,
        unit: typeof source.unit === 'string' ? source.unit : '',
        active: source.active ?? source.isActive ?? true,
        sortOrder: source.sortOrder ?? index + 1
      };
    });
  }
  data.periods = Array.isArray(data.periods) ? data.periods : [];
  data.periods.forEach((period) => {
    if (!period || typeof period !== 'object') return;
    period.note = typeof period.note === 'string' ? period.note : '';
  });
  if (!Array.isArray(data.events)) return data;
  data.events.forEach((event) => {
    if (!event || typeof event !== 'object') return;
    event.updatedAtUtc = event.updatedAtUtc || event.createdAtUtc || event.recordedAtUtc;
  });
  return data;
}

function isDateString(value) {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

function sortedPeriods(periods = appData.periods) {
  return [...periods].sort((a, b) => a.startDate.localeCompare(b.startDate));
}

function findOverlappingPeriod(candidate, ignoredId = null) {
  return appData.periods.find((period) => period.id !== ignoredId && period.startDate <= candidate.endDate && candidate.startDate <= period.endDate);
}

function validatePeriods(periods) {
  if (!Array.isArray(periods)) return false;
  for (const period of periods) {
    if (!period || typeof period !== 'object') return false;
    if (typeof period.id !== 'string') return false;
    if (typeof period.label !== 'string') return false;
    if (!isDateString(period.startDate) || !isDateString(period.endDate)) return false;
    if (period.note !== undefined && typeof period.note !== 'string') return false;
    if (period.startDate > period.endDate) return false;
  }
  for (let i = 0; i < periods.length; i += 1) {
    for (let j = i + 1; j < periods.length; j += 1) {
      const a = periods[i];
      const b = periods[j];
      if (a.startDate <= b.endDate && b.startDate <= a.endDate) return false;
    }
  }
  return true;
}

function validateData(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return false;
  if (typeof data.schemaVersion !== 'number' || data.schemaVersion !== 1) return false;
  if (typeof data.appName !== 'string') return false;
  if (!data.settings || typeof data.settings !== 'object' || Array.isArray(data.settings)) return false;
  if (!Array.isArray(data.settings.painStateOptions) || !Array.isArray(data.settings.medicationOptions)) return false;
  if (!Array.isArray(data.periods) || !Array.isArray(data.events)) return false;
  if (!validatePeriods(data.periods)) return false;

  const validOption = (option) => option && typeof option.id === 'string' && typeof option.label === 'string' && typeof option.active === 'boolean';
  const validPainOption = (option) => validOption(option) && typeof option.sortOrder === 'number' && Number.isFinite(option.sortOrder);
  const validMedicationOption = (option) => validOption(option) &&
    typeof option.defaultAmount === 'number' && Number.isFinite(option.defaultAmount) &&
    typeof option.unit === 'string' &&
    typeof option.sortOrder === 'number' && Number.isFinite(option.sortOrder);
  if (!data.settings.painStateOptions.every(validPainOption)) return false;
  if (!data.settings.medicationOptions.every(validMedicationOption)) return false;

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
        typeof event.stateOptionId === 'string' &&
        (event.stateLabel === undefined || typeof event.stateLabel === 'string');
    }
    if (event.type === 'medication') {
      return (event.medicationOptionId === undefined || typeof event.medicationOptionId === 'string') &&
        (event.medicationLabel === undefined || typeof event.medicationLabel === 'string') &&
        (event.amount === undefined || (typeof event.amount === 'number' && Number.isFinite(event.amount))) &&
        (event.unit === undefined || typeof event.unit === 'string');
    }
    return typeof event.note === 'string';
  });
}

function saveData() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(appData));
}

function supplementSettings(data) {
  if (!data || !data.settings) return { data, changed: false };
  const changed = !Object.prototype.hasOwnProperty.call(data.settings, 'lastJsonExportedAtUtc') ||
    !Object.prototype.hasOwnProperty.call(data.settings, 'lastCsvExportedAtUtc') ||
    data.settings.lastJsonExportedAtUtc === undefined ||
    data.settings.lastCsvExportedAtUtc === undefined;
  data.settings.lastJsonExportedAtUtc ??= null;
  data.settings.lastCsvExportedAtUtc ??= null;
  return { data, changed };
}

function loadStoredData() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;
  const parsed = parseJson(stored);
  if (!parsed.data) return null;
  const normalized = normalizeImportedData(parsed.data);
  if (!validateData(normalized)) return null;
  const supplemented = supplementSettings(normalized);
  if (supplemented.changed) localStorage.setItem(STORAGE_KEY, JSON.stringify(supplemented.data));
  return supplemented.data;
}

function showSetup(message = '') {
  stopElapsedRefresh();
  $('setup-screen').classList.remove('hidden');
  $('app-screen').classList.add('hidden');
  $('setup-error').textContent = message;
}

function showApp() {
  startElapsedRefresh();
  $('setup-screen').classList.add('hidden');
  $('app-screen').classList.remove('hidden');
  render();
}

function initializeFromText(text, errorElement) {
  const parsed = parseJson(text);
  if (parsed.error) { errorElement.textContent = parsed.error; return false; }
  const normalized = normalizeImportedData(parsed.data);
  if (!validateData(normalized)) { errorElement.textContent = SCHEMA_ERROR; return false; }
  appData = supplementSettings(normalized).data;
  clearSaveFeedback();
  saveData();
  errorElement.textContent = '';
  showApp();
  return true;
}

function sortedPainOptions(options) {
  return [...options].sort((a, b) =>
    a.sortOrder - b.sortOrder ||
    a.label.localeCompare(b.label, 'ja') ||
    a.id.localeCompare(b.id)
  );
}
function activePainOptions() { return sortedPainOptions(appData.settings.painStateOptions.filter((option) => option.active)); }
function allPainOptions() { return sortedPainOptions(appData.settings.painStateOptions); }
function nextPainSortOrder() {
  const orders = appData.settings.painStateOptions.map((option) => Number(option.sortOrder)).filter(Number.isFinite);
  return orders.length ? Math.max(...orders) + 1 : 1;
}
function createPainStateOptionId() {
  const time = nowParts();
  const stamp = `${time.localDate.replace(/-/g, '')}_${time.localTime.replace(':', '')}`;
  let id = `ps_${stamp}_${Math.random().toString(36).slice(2, 7)}`;
  while (appData.settings.painStateOptions.some((option) => option.id === id)) {
    id = `ps_${stamp}_${Math.random().toString(36).slice(2, 7)}`;
  }
  return id;
}
function sortedMedicationOptions(options) {
  return [...options].sort((a, b) =>
    a.sortOrder - b.sortOrder ||
    a.label.localeCompare(b.label, 'ja') ||
    a.id.localeCompare(b.id)
  );
}
function activeMedicationOptions() {
  return sortedMedicationOptions(appData.settings.medicationOptions.filter((option) => option.active));
}
function allMedicationOptions() {
  return sortedMedicationOptions(appData.settings.medicationOptions);
}
function nextMedicationSortOrder() {
  const orders = appData.settings.medicationOptions.map((option) => Number(option.sortOrder)).filter(Number.isFinite);
  return orders.length ? Math.max(...orders) + 1 : 1;
}
function createMedicationOptionId() {
  const time = nowParts();
  const stamp = `${time.localDate.replace(/-/g, '')}_${time.localTime.replace(':', '')}`;
  let id = `med_${stamp}_${Math.random().toString(36).slice(2, 7)}`;
  while (appData.settings.medicationOptions.some((option) => option.id === id)) {
    id = `med_${stamp}_${Math.random().toString(36).slice(2, 7)}`;
  }
  return id;
}
function findPainLabel(id) { return (appData.settings.painStateOptions.find((option) => option.id === id) || {}).label || ''; }
function painEventLabel(event) { return event.stateLabel || findPainLabel(event.stateOptionId) || '不明な状態'; }
function findMedicationLabel(id) { return (appData.settings.medicationOptions.find((option) => option.id === id) || {}).label || ''; }
function medicationEventLabel(event) { return event.medicationLabel || findMedicationLabel(event.medicationOptionId); }

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
  const feedback = $('toast-feedback');
  const message = $('toast-message');
  if (!feedback || !message) return;
  feedback.hidden = true;
  message.textContent = '';
}

function showSaveFeedback(eventId, message) {
  showToast(message, eventId);
}

function showToast(message, undoEventId = null) {
  if (saveFeedbackTimer) clearTimeout(saveFeedbackTimer);
  lastSavedEventId = undoEventId;
  const feedback = $('toast-feedback');
  const text = $('toast-message');
  const undoButton = $('toast-undo-button');
  if (!feedback || !text || !undoButton) return;
  text.textContent = message;
  undoButton.hidden = !undoEventId;
  feedback.hidden = false;
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

function sortedEventsDescending(events) {
  return [...events].sort((a, b) => (b.localDate + b.localTime + b.createdAtUtc).localeCompare(a.localDate + a.localTime + a.createdAtUtc));
}

function eventText(event) {
  const parts = [`${event.localTime}`, event.type];
  if (event.type === 'pain') parts.push(`score ${event.painScore}`, painEventLabel(event));
  if (event.type === 'medication') {
    parts.push(medicationEventLabel(event) || '不明な薬');
    if (event.amount !== undefined || event.unit) parts.push(`${event.amount ?? ''}${event.unit || ''}`);
  }
  if (event.note) parts.push(event.note);
  return parts.filter(Boolean).join(' / ');
}

function renderEventList(container, events, sortEvents = sortedEvents, options = {}) {
  container.innerHTML = '';
  if (events.length === 0) {
    container.innerHTML = '<p class="empty">記録はありません。</p>';
    return;
  }
  const showDate = options.showDate !== false;
  sortEvents(events).forEach((event) => {
    const item = document.createElement('div');
    item.className = 'event';
    const content = document.createElement('div');
    content.className = 'event-content';
    const body = document.createElement('div');
    body.textContent = eventText(event);
    const meta = document.createElement('div');
    meta.className = 'event-meta';
    meta.textContent = event.localDate;
    const actions = document.createElement('div');
    actions.className = 'event-actions';
    const editButton = document.createElement('button');
    editButton.className = 'edit-event-button';
    editButton.type = 'button';
    editButton.textContent = '✎';
    editButton.setAttribute('aria-label', '編集');
    editButton.addEventListener('click', () => openEditEventPanel(event.id));
    const button = document.createElement('button');
    button.className = 'delete-event-button';
    button.type = 'button';
    button.textContent = '×';
    button.setAttribute('aria-label', '記録を削除');
    button.addEventListener('click', () => deleteEvent(event.id));
    actions.append(editButton, button);
    if (showDate) content.append(meta);
    content.append(body);
    item.append(content, actions);
    container.appendChild(item);
  });
}

function optionHtml(options, selectedId) {
  return options.map((option) => `<option value="${escapeHtml(option.id)}"${option.id === selectedId ? ' selected' : ''}>${escapeHtml(option.displayLabel || option.label)}</option>`).join('');
}

function painEditOptions(event) {
  const options = activePainOptions();
  const current = appData.settings.painStateOptions.find((option) => option.id === event.stateOptionId);
  if (current && !current.active) {
    options.push({ ...current, displayLabel: `${event.stateLabel || current.label}（非表示）` });
  } else if (current && event.stateLabel) {
    return options.map((option) => option.id === event.stateOptionId ? { ...option, displayLabel: event.stateLabel } : option);
  } else if (!current) {
    options.push({
      id: event.stateOptionId,
      label: event.stateLabel || '不明な状態',
      displayLabel: `${event.stateLabel || '不明な状態'}（設定なし）`
    });
  }
  return options;
}

function medicationEditOptions(event) {
  const options = activeMedicationOptions();
  const current = appData.settings.medicationOptions.find((option) => option.id === event.medicationOptionId);
  if (current && !current.active) {
    options.push({ ...current, displayLabel: `${current.label}（非表示）` });
  } else if (!current) {
    options.push({
      id: event.medicationOptionId,
      label: event.medicationLabel || '不明な薬',
      displayLabel: `${event.medicationLabel || '不明な薬'}（設定なし）`
    });
  }
  return options;
}

function editTextareaHtml(value = '') {
  return `<label for="edit-note">メモ</label><textarea id="edit-note" rows="4">${escapeHtml(value)}</textarea>`;
}

function openEditEventPanel(id) {
  const event = appData.events.find((item) => item.id === id);
  if (!event) return;
  editingEventId = id;
  const fields = $('edit-event-fields');
  if (event.type === 'pain') {
    fields.innerHTML = `
      <label for="edit-pain-score">痛みスコア</label>
      <select id="edit-pain-score">${Array.from({ length: 11 }, (_, value) => `<option value="${value}"${value === event.painScore ? ' selected' : ''}>${value}</option>`).join('')}</select>
      <label for="edit-pain-state">痛みの状態</label>
      <select id="edit-pain-state">${optionHtml(painEditOptions(event), event.stateOptionId)}</select>
      ${editTextareaHtml(event.note || '')}`;
  } else if (event.type === 'medication') {
    fields.innerHTML = `
      <label for="edit-medication-option">Medication</label>
      <select id="edit-medication-option">${optionHtml(medicationEditOptions(event), event.medicationOptionId)}</select>
      ${editTextareaHtml(event.note || '')}`;
  } else {
    fields.innerHTML = editTextareaHtml(event.note || '');
  }
  $('edit-event-panel').hidden = false;
  const firstInput = fields.querySelector('select, textarea');
  if (firstInput) firstInput.focus();
}

function closeEditEventPanel() {
  editingEventId = null;
  $('edit-event-panel').hidden = true;
  $('edit-event-fields').innerHTML = '';
}

function saveEditedEvent() {
  if (!editingEventId) return;
  const event = appData.events.find((item) => item.id === editingEventId);
  if (!event) { closeEditEventPanel(); return; }
  if (event.type === 'pain') {
    const stateOptionId = $('edit-pain-state').value;
    if (!stateOptionId) return;
    event.painScore = Number($('edit-pain-score').value);
    if (stateOptionId !== event.stateOptionId) {
      const option = appData.settings.painStateOptions.find((item) => item.id === stateOptionId);
      if (!option) return;
      event.stateOptionId = option.id;
      event.stateLabel = option.label;
    }
    event.note = $('edit-note').value.trim();
  } else if (event.type === 'medication') {
    const medicationOptionId = $('edit-medication-option').value;
    if (!medicationOptionId) return;
    if (medicationOptionId !== event.medicationOptionId) {
      const option = appData.settings.medicationOptions.find((item) => item.id === medicationOptionId);
      if (!option) return;
      event.medicationOptionId = option.id;
      event.medicationLabel = option.label;
      event.amount = option.defaultAmount;
      event.unit = option.unit;
    }
    event.note = $('edit-note').value.trim();
  } else {
    event.note = $('edit-note').value.trim();
  }
  event.updatedAtUtc = new Date().toISOString();
  saveData();
  render();
  closeEditEventPanel();
  showToast('編集を保存しました');
}

function deleteEvent(id) {
  if (!confirm('この記録を削除しますか？')) return;
  appData.events = appData.events.filter((event) => event.id !== id);
  if (lastSavedEventId === id) clearSaveFeedback();
  saveData();
  render();
}

function elapsedMinutes(iso) {
  return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
}

function elapsedText(iso) {
  const minutes = elapsedMinutes(iso);
  return `${Math.floor(minutes / 60)}時間${minutes % 60}分`;
}

function formatShortDate(dateText) {
  const [, month, day] = dateText.split('-');
  return `${Number(month)}/${Number(day)}`;
}

function formatFullDate(dateText) {
  return dateText.replaceAll('-', '/');
}

function lastMedicationText(option, last) {
  if (!last) return `${option.label}：記録なし`;
  if (elapsedMinutes(last.recordedAtUtc) >= 1440) {
    return `${option.label}：前回 ${formatShortDate(last.localDate)} / 1日以上`;
  }
  return `${option.label}：前回 ${last.localTime} / 経過 ${elapsedText(last.recordedAtUtc)}`;
}

function addDays(dateText, days) {
  const date = new Date(`${dateText}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function isValidDateString(value) {
  if (!isDateString(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function inclusiveDays(startDate, endDate) {
  return Math.floor((new Date(`${endDate}T00:00:00Z`) - new Date(`${startDate}T00:00:00Z`)) / 86400000) + 1;
}

function setDefaultSummaryRange() {
  const endDate = addDays(nowParts().localDate, -1);
  $('summary-start-date').value = addDays(endDate, -29);
  $('summary-end-date').value = endDate;
  $('summary-end-today').checked = false;
  $('summary-end-custom').checked = true;
  updateSummaryEndDateMode();
}

function ensureSummaryDefaults() {
  if (!$('summary-start-date').value) setDefaultSummaryRange();
  renderSummaryPeriodPicker();
}

function updateSummaryEndDateMode() {
  const today = nowParts().localDate;
  const useToday = $('summary-end-today').checked;
  $('summary-end-today-label').textContent = `今日（${formatFullDate(today)}）`;
  $('summary-end-date').disabled = useToday;
  $('summary-end-date').hidden = useToday;
  if (useToday) $('summary-end-date').value = today;
}

function renderSummaryPeriodPicker() {
  const container = $('summary-period-picker');
  container.innerHTML = '';
  if (!appData.periods.length) return;
  const label = document.createElement('label');
  label.setAttribute('for', 'summary-period-select');
  label.textContent = '体調比較用期間から選択';
  const select = document.createElement('select');
  select.id = 'summary-period-select';
  select.className = 'form-control';
  select.innerHTML = '<option value="">選択してください</option>' + sortedPeriods().map((period) =>
    `<option value="${escapeHtml(period.id)}">${escapeHtml(period.label)}（${escapeHtml(period.startDate)}〜${escapeHtml(period.endDate)}）</option>`
  ).join('');
  select.addEventListener('change', () => {
    const period = appData.periods.find((item) => item.id === select.value);
    if (!period) return;
    $('summary-start-date').value = period.startDate;
    $('summary-end-date').value = period.endDate;
    $('summary-end-today').checked = false;
    $('summary-end-custom').checked = true;
    updateSummaryEndDateMode();
  });
  container.append(label, select);
}

function summaryValidationMessage(startDate, endDate) {
  if (!startDate) return '集計開始日を入力してください。';
  if (!endDate) return '集計終了日を入力してください。';
  if (!isValidDateString(startDate) || !isValidDateString(endDate)) return '日付はYYYY-MM-DD形式で入力してください。';
  if (startDate > endDate) return '集計開始日は集計終了日以前の日付にしてください。';
  return '';
}

function medicationSummaryUnit(event, option) {
  if (typeof event.unit === 'string' && event.unit) return event.unit;
  return (option && option.unit) || '';
}

function medicationSummaryKey(event, option) {
  const medicationKey = event.medicationOptionId ? `id:${event.medicationOptionId}` : `label:${event.medicationLabel || '不明な薬'}`;
  const unit = medicationSummaryUnit(event, option);
  return `${medicationKey}|unit:${unit}`;
}

function amountForSummary(event) {
  return typeof event.amount === 'number' && Number.isFinite(event.amount) ? event.amount : 1;
}

function buildMedicationSummary(startDate, endDate) {
  const optionById = new Map(appData.settings.medicationOptions.map((option) => [option.id, option]));
  const rows = new Map();
  const ensureRow = (key, base) => {
    if (!rows.has(key)) rows.set(key, { ...base, total: 0, dates: new Set(), latestLabelDate: '' });
    return rows.get(key);
  };

  appData.settings.medicationOptions.filter((option) => option.active).forEach((option) => {
    const key = `id:${option.id}|unit:${option.unit || ''}`;
    ensureRow(key, { medicationSortOrder: option.sortOrder, medicationId: option.id, label: option.label || '不明な薬', unit: option.unit || '' });
  });

  appData.events.filter((event) => event.type === 'medication' && event.localDate >= startDate && event.localDate <= endDate).forEach((event) => {
    const option = event.medicationOptionId ? optionById.get(event.medicationOptionId) : null;
    const key = medicationSummaryKey(event, option);
    const label = event.medicationLabel || (option && option.label) || event.medicationLabel || '不明な薬';
    const unit = medicationSummaryUnit(event, option);
    const row = ensureRow(key, {
      medicationSortOrder: option ? option.sortOrder : Number.MAX_SAFE_INTEGER,
      medicationId: event.medicationOptionId || '',
      label,
      unit
    });
    const amount = amountForSummary(event);
    row.total += amount;
    if (amount > 0) row.dates.add(event.localDate);
    if (event.medicationLabel && event.localDate >= row.latestLabelDate) {
      row.label = event.medicationLabel;
      row.latestLabelDate = event.localDate;
    }
  });

  return [...rows.values()].sort((a, b) =>
    a.medicationSortOrder - b.medicationSortOrder ||
    a.label.localeCompare(b.label, 'ja') ||
    a.unit.localeCompare(b.unit, 'ja') ||
    a.medicationId.localeCompare(b.medicationId)
  );
}

function amountText(value, unit) {
  const text = Number.isInteger(value) ? String(value) : String(Math.round(value * 100) / 100);
  return unit ? `${text}${unit}` : text;
}

function dateRange(startDate, endDate) {
  const dates = [];
  for (let date = startDate; date <= endDate; date = addDays(date, 1)) dates.push(date);
  return dates;
}

function buildDailyPainSummary(startDate, endDate) {
  const daily = new Map();
  appData.events.filter((event) => event.type === 'pain' && event.localDate >= startDate && event.localDate <= endDate).forEach((event) => {
    if (typeof event.painScore !== 'number' || !Number.isFinite(event.painScore)) return;
    if (!daily.has(event.localDate)) daily.set(event.localDate, { max: event.painScore, total: 0, count: 0 });
    const day = daily.get(event.localDate);
    day.max = Math.max(day.max, event.painScore);
    day.total += event.painScore;
    day.count += 1;
    day.average = day.total / day.count;
  });
  return daily;
}

function buildDosePainSummary(startDate, endDate) {
  const dates = dateRange(startDate, endDate);
  const optionById = new Map(appData.settings.medicationOptions.map((option) => [option.id, option]));
  const dailyPain = buildDailyPainSummary(startDate, endDate);
  const rows = new Map();
  const ensureRow = (key, base) => {
    if (!rows.has(key)) rows.set(key, { ...base, dailyAmounts: new Map() });
    return rows.get(key);
  };

  appData.settings.medicationOptions.filter((option) => option.active).forEach((option) => {
    const unit = option.unit || '';
    const key = `id:${option.id}|unit:${unit}`;
    ensureRow(key, { medicationSortOrder: option.sortOrder, medicationId: option.id, label: option.label || '不明な薬', unit, latestLabelDate: '' });
  });

  appData.events.filter((event) => event.type === 'medication' && event.localDate >= startDate && event.localDate <= endDate).forEach((event) => {
    const option = event.medicationOptionId ? optionById.get(event.medicationOptionId) : null;
    const key = medicationSummaryKey(event, option);
    const label = event.medicationLabel || (option && option.label) || '不明な薬';
    const unit = medicationSummaryUnit(event, option);
    const row = ensureRow(key, {
      medicationSortOrder: option ? option.sortOrder : Number.MAX_SAFE_INTEGER,
      medicationId: event.medicationOptionId || '',
      label,
      unit,
      latestLabelDate: ''
    });
    row.dailyAmounts.set(event.localDate, (row.dailyAmounts.get(event.localDate) || 0) + amountForSummary(event));
    if (event.medicationLabel && event.localDate >= row.latestLabelDate) {
      row.label = event.medicationLabel;
      row.latestLabelDate = event.localDate;
    }
  });

  return [...rows.values()].map((row) => {
    const doseGroups = new Map();
    dates.forEach((date) => {
      const amount = row.dailyAmounts.get(date) || 0;
      if (!doseGroups.has(amount)) doseGroups.set(amount, { amount, targetDays: 0, painDays: 0, maxPain: null, averagePainTotal: 0 });
      const group = doseGroups.get(amount);
      group.targetDays += 1;
      const pain = dailyPain.get(date);
      if (!pain) return;
      group.painDays += 1;
      group.maxPain = group.maxPain === null ? pain.max : Math.max(group.maxPain, pain.max);
      group.averagePainTotal += pain.average;
    });
    return {
      ...row,
      doseGroups: [...doseGroups.values()].sort((a, b) => b.amount - a.amount)
    };
  }).sort((a, b) =>
    a.medicationSortOrder - b.medicationSortOrder ||
    a.label.localeCompare(b.label, 'ja') ||
    a.unit.localeCompare(b.unit, 'ja') ||
    a.medicationId.localeCompare(b.medicationId)
  );
}

function formatPainValue(value) {
  return value === null ? '—' : String(value);
}

function formatAveragePain(group) {
  return group.painDays ? (group.averagePainTotal / group.painDays).toFixed(1) : '—';
}

function renderDosePainSummary(block, dosePainRows) {
  const heading = document.createElement('h3');
  heading.textContent = '痛み：薬量別';
  block.appendChild(heading);

  const notice = document.createElement('p');
  notice.className = 'visit-summary-notice';
  notice.textContent = '薬ごとに日単位で集計しています。他の薬との併用条件は分けていません。';
  block.appendChild(notice);

  if (!dosePainRows.length) {
    const empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = '服薬記録がないため、薬量別の痛みサマリーはありません。';
    block.appendChild(empty);
    return;
  }

  dosePainRows.forEach((row) => {
    const details = document.createElement('details');
    details.className = 'visit-summary-dose-pain-item';
    details.open = true;
    const summary = document.createElement('summary');
    summary.textContent = row.unit ? `${row.label}（${row.unit}）` : row.label;
    const body = document.createElement('div');
    row.doseGroups.forEach((group) => {
      const item = document.createElement('div');
      item.className = 'visit-summary-dose-pain-row';
      const doseLabel = `${amountText(group.amount, row.unit)}の日`;
      item.innerHTML = `<strong>${escapeHtml(doseLabel)}</strong><br>対象 ${group.targetDays}日 / 痛み記録あり ${group.painDays}日<br>最大痛み ${escapeHtml(formatPainValue(group.maxPain))} / 平均痛み ${escapeHtml(formatAveragePain(group))}`;
      body.appendChild(item);
    });
    details.append(summary, body);
    block.appendChild(details);
  });
}

function renderVisitSummaryResult(startDate, endDate, days, rows, dosePainRows) {
  const result = $('visit-summary-result');
  result.innerHTML = '';
  const block = document.createElement('div');
  block.className = 'visit-summary-result-block';
  block.innerHTML = `<p><strong>集計期間：</strong>${escapeHtml(startDate)}〜${escapeHtml(endDate)}</p><p><strong>日数：</strong>${days}日</p><h3>服薬</h3>`;
  if (!rows.length) {
    const empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = '服薬記録はありません。';
    block.appendChild(empty);
  } else {
    rows.forEach((row) => {
      const item = document.createElement('div');
      item.className = 'visit-summary-medication-item';
      const average = row.total / days;
      item.innerHTML = `<strong>${escapeHtml(row.label)}</strong><br>合計 ${escapeHtml(amountText(row.total, row.unit))} / 1日平均 ${escapeHtml(average.toFixed(2) + row.unit)}`;
      block.appendChild(item);
    });
  }
  renderDosePainSummary(block, dosePainRows);
  result.appendChild(block);
}

function runVisitSummary() {
  updateSummaryEndDateMode();
  const startDate = $('summary-start-date').value;
  const endDate = $('summary-end-today').checked ? nowParts().localDate : $('summary-end-date').value;
  const message = summaryValidationMessage(startDate, endDate);
  $('visit-summary-message').textContent = message;
  $('visit-summary-message').classList.toggle('error', Boolean(message));
  $('visit-summary-result').innerHTML = '';
  if (message) return;
  const days = inclusiveDays(startDate, endDate);
  const rows = buildMedicationSummary(startDate, endDate);
  const dosePainRows = buildDosePainSummary(startDate, endDate);
  renderVisitSummaryResult(startDate, endDate, days, rows, dosePainRows);
}

function nextPeriodStartSuggestion() {
  if (!appData.periods.length) return '';
  const latest = [...appData.periods].sort((a, b) => b.endDate.localeCompare(a.endDate))[0];
  return addDays(latest.endDate, 1);
}

function resetPeriodForm() {
  editingPeriodId = null;
  $('comparison-period-form').reset();
  $('comparison-period-start').value = nextPeriodStartSuggestion();
  $('comparison-period-form').querySelector('button[type="submit"]').textContent = '体調比較用期間を追加';
  $('cancel-comparison-period-edit').hidden = true;
}

function periodFormValue() {
  return {
    label: $('comparison-period-label').value.trim(),
    startDate: $('comparison-period-start').value,
    endDate: $('comparison-period-end').value,
    note: $('comparison-period-note').value.trim()
  };
}

function setPeriodMessage(message, isError = false) {
  const element = $('comparison-period-message');
  element.textContent = message;
  element.classList.toggle('error', isError);
}

function validatePeriodFormValue(value, ignoredId = null) {
  if (!value.label) return '期間名を入力してください。';
  if (!value.startDate) return '開始日を入力してください。';
  if (!value.endDate) return '終了日を入力してください。';
  if (!isDateString(value.startDate) || !isDateString(value.endDate)) return '日付はYYYY-MM-DD形式で入力してください。';
  if (value.startDate > value.endDate) return '開始日は終了日以前の日付にしてください。';
  const overlap = findOverlappingPeriod(value, ignoredId);
  if (overlap) return `既存の体調比較用期間「${overlap.label}」と日付が重なっています。
開始日または終了日を変更してください。`;
  return '';
}

function createPeriod(value) {
  const id = crypto.randomUUID ? crypto.randomUUID() : `period_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return { id, ...value };
}

function savePeriodFromForm() {
  const value = periodFormValue();
  const validationMessage = validatePeriodFormValue(value, editingPeriodId);
  if (validationMessage) { setPeriodMessage(validationMessage, true); return; }
  if (editingPeriodId) {
    const period = appData.periods.find((item) => item.id === editingPeriodId);
    if (!period) { resetPeriodForm(); return; }
    Object.assign(period, value);
    saveData();
    render();
    resetPeriodForm();
    showToast('体調比較用期間を更新しました');
    setPeriodMessage('体調比較用期間を更新しました');
    return;
  }
  appData.periods.push(createPeriod(value));
  saveData();
  render();
  resetPeriodForm();
  showToast('体調比較用期間を追加しました');
  setPeriodMessage('体調比較用期間を追加しました');
}

function editPeriod(id) {
  const period = appData.periods.find((item) => item.id === id);
  if (!period) return;
  editingPeriodId = id;
  $('comparison-period-label').value = period.label;
  $('comparison-period-start').value = period.startDate;
  $('comparison-period-end').value = period.endDate;
  $('comparison-period-note').value = period.note || '';
  $('comparison-period-form').querySelector('button[type="submit"]').textContent = '体調比較用期間を更新';
  $('cancel-comparison-period-edit').hidden = false;
  setPeriodMessage('');
  $('comparison-period-label').focus();
}

function deletePeriod(id) {
  if (!confirm('この体調比較用期間を削除します。\n記録自体は削除されません。')) return;
  appData.periods = appData.periods.filter((period) => period.id !== id);
  if (editingPeriodId === id) resetPeriodForm();
  saveData();
  render();
  resetPeriodForm();
  showToast('体調比較用期間を削除しました');
  setPeriodMessage('体調比較用期間を削除しました');
}

function renderPeriodList() {
  const list = $('comparison-period-list');
  list.innerHTML = '';
  if (!appData.periods.length) {
    list.innerHTML = '<p class="empty">登録済みの体調比較用期間はありません。</p>';
    return;
  }
  sortedPeriods().forEach((period) => {
    const item = document.createElement('div');
    item.className = 'comparison-period-item';
    const content = document.createElement('div');
    content.className = 'comparison-period-content';
    content.textContent = `${period.startDate}〜${period.endDate}　${period.label}`;
    const actions = document.createElement('div');
    actions.className = 'event-actions';
    const editButton = document.createElement('button');
    editButton.className = 'edit-event-button';
    editButton.type = 'button';
    editButton.textContent = '✎';
    editButton.setAttribute('aria-label', '体調比較用期間を編集');
    editButton.addEventListener('click', () => editPeriod(period.id));
    const deleteButton = document.createElement('button');
    deleteButton.className = 'delete-event-button';
    deleteButton.type = 'button';
    deleteButton.textContent = '×';
    deleteButton.setAttribute('aria-label', '体調比較用期間を削除');
    deleteButton.addEventListener('click', () => deletePeriod(period.id));
    actions.append(editButton, deleteButton);
    item.append(content, actions);
    list.appendChild(item);
  });
}


function renderPainStateSettingsSummary() {
  const options = appData.settings.painStateOptions;
  const visibleCount = options.filter((option) => option.active).length;
  const hiddenCount = options.length - visibleCount;
  $('pain-state-settings-summary').textContent = `痛み状態設定　表示中${visibleCount}件 / 非表示${hiddenCount}件`;
}

function resetPainStateOptionForm() {
  editingPainStateOptionId = null;
  $('pain-state-option-form').reset();
  $('pain-state-option-id').value = '';
  $('pain-state-label').value = '';
  $('pain-state-sort-order').value = nextPainSortOrder();
  $('pain-state-active').checked = true;
  $('save-pain-state-option').textContent = '状態を追加';
  $('cancel-pain-state-edit').hidden = true;
}

function setPainStateSettingsMessage(message, isError = false) {
  const element = $('pain-state-settings-message');
  element.textContent = message;
  element.classList.toggle('error', isError);
}

function painStateOptionFormValue() {
  return {
    label: $('pain-state-label').value.trim(),
    sortOrderText: $('pain-state-sort-order').value.trim(),
    active: $('pain-state-active').checked
  };
}

function validatePainStateOptionFormValue(value) {
  if (!value.label) return '状態名を入力してください。';
  if (!value.sortOrderText) return '表示順を入力してください。';
  if (!Number.isFinite(Number(value.sortOrderText))) return '表示順は数値で入力してください。';
  return '';
}

function savePainStateOptionFromForm() {
  const value = painStateOptionFormValue();
  const validationMessage = validatePainStateOptionFormValue(value);
  if (validationMessage) { setPainStateSettingsMessage(validationMessage, true); return; }
  const normalizedValue = { label: value.label, sortOrder: Number(value.sortOrderText), active: value.active };
  if (editingPainStateOptionId) {
    const option = appData.settings.painStateOptions.find((item) => item.id === editingPainStateOptionId);
    if (!option) { resetPainStateOptionForm(); return; }
    Object.assign(option, normalizedValue);
    saveData();
    render();
    resetPainStateOptionForm();
    showToast('痛み状態設定を更新しました。');
    setPainStateSettingsMessage('痛み状態設定を更新しました。');
    return;
  }
  appData.settings.painStateOptions.push({ id: createPainStateOptionId(), ...normalizedValue });
  saveData();
  render();
  resetPainStateOptionForm();
  showToast('状態を追加しました。');
  setPainStateSettingsMessage('状態を追加しました。');
}

function editPainStateOption(id) {
  const option = appData.settings.painStateOptions.find((item) => item.id === id);
  if (!option) return;
  editingPainStateOptionId = id;
  $('pain-state-option-id').value = option.id;
  $('pain-state-label').value = option.label;
  $('pain-state-sort-order').value = option.sortOrder;
  $('pain-state-active').checked = option.active;
  $('save-pain-state-option').textContent = '痛み状態設定を更新';
  $('cancel-pain-state-edit').hidden = false;
  setPainStateSettingsMessage('');
  $('pain-state-label').focus();
}

function togglePainStateOptionActive(id) {
  const option = appData.settings.painStateOptions.find((item) => item.id === id);
  if (!option) return;
  option.active = !option.active;
  saveData();
  render();
  showToast('痛み状態設定を更新しました。');
  setPainStateSettingsMessage('痛み状態設定を更新しました。');
}

function renderPainStateSettingsList() {
  const list = $('pain-state-settings-list');
  list.innerHTML = '';
  if (!appData.settings.painStateOptions.length) {
    list.innerHTML = '<p class="empty">登録済みの痛み状態はありません。</p>';
    return;
  }
  allPainOptions().forEach((option) => {
    const item = document.createElement('div');
    item.className = 'pain-state-settings-item';
    const content = document.createElement('div');
    content.className = 'pain-state-settings-content';
    const status = option.active ? '表示中' : '非表示';
    content.textContent = `${option.label} / 表示順 ${option.sortOrder} / ${status}`;
    const actions = document.createElement('div');
    actions.className = 'pain-state-settings-actions';
    const editButton = document.createElement('button');
    editButton.className = 'edit-event-button';
    editButton.type = 'button';
    editButton.textContent = '✎';
    editButton.setAttribute('aria-label', '痛み状態設定を編集');
    editButton.addEventListener('click', () => editPainStateOption(option.id));
    const toggleButton = document.createElement('button');
    toggleButton.className = 'secondary-button pain-state-toggle-button';
    toggleButton.type = 'button';
    toggleButton.textContent = option.active ? '非表示' : '表示';
    toggleButton.addEventListener('click', () => togglePainStateOptionActive(option.id));
    actions.append(editButton, toggleButton);
    item.append(content, actions);
    list.appendChild(item);
  });
}

function renderMedicationSettingsSummary() {
  const options = appData.settings.medicationOptions;
  const visibleCount = options.filter((option) => option.active).length;
  const hiddenCount = options.length - visibleCount;
  $('medication-settings-summary').textContent = `薬設定　表示中${visibleCount}件 / 非表示${hiddenCount}件`;
}

function renderComparisonPeriodSummary() {
  $('comparison-period-summary').textContent = `体調比較用期間の設定　登録済み${appData.periods.length}件`;
}

function resetMedicationOptionForm() {
  editingMedicationOptionId = null;
  $('medication-option-form').reset();
  $('medication-option-id').value = '';
  $('medication-default-amount').value = '1';
  $('medication-sort-order').value = nextMedicationSortOrder();
  $('medication-active').checked = true;
  $('save-medication-option').textContent = '薬を追加';
  $('cancel-medication-edit').hidden = true;
}

function setMedicationSettingsMessage(message, isError = false) {
  const element = $('medication-settings-message');
  element.textContent = message;
  element.classList.toggle('error', isError);
}

function medicationOptionFormValue() {
  return {
    label: $('medication-label').value.trim(),
    defaultAmountText: $('medication-default-amount').value.trim(),
    unit: $('medication-unit').value.trim(),
    sortOrderText: $('medication-sort-order').value.trim(),
    active: $('medication-active').checked
  };
}

function validateMedicationOptionFormValue(value) {
  if (!value.label) return '薬名を入力してください。';
  if (!value.defaultAmountText) return 'よく使う量を入力してください。';
  const defaultAmount = Number(value.defaultAmountText);
  if (!Number.isFinite(defaultAmount)) return 'よく使う量は数値で入力してください。';
  if (!value.sortOrderText) return '表示順を入力してください。';
  const sortOrder = Number(value.sortOrderText);
  if (!Number.isFinite(sortOrder)) return '表示順は数値で入力してください。';
  return '';
}

function saveMedicationOptionFromForm() {
  const value = medicationOptionFormValue();
  const validationMessage = validateMedicationOptionFormValue(value);
  if (validationMessage) { setMedicationSettingsMessage(validationMessage, true); return; }
  const normalizedValue = {
    label: value.label,
    defaultAmount: Number(value.defaultAmountText),
    unit: value.unit,
    sortOrder: Number(value.sortOrderText),
    active: value.active
  };
  if (editingMedicationOptionId) {
    const option = appData.settings.medicationOptions.find((item) => item.id === editingMedicationOptionId);
    if (!option) { resetMedicationOptionForm(); return; }
    Object.assign(option, normalizedValue);
    saveData();
    render();
    resetMedicationOptionForm();
    showToast('薬設定を更新しました。');
    setMedicationSettingsMessage('薬設定を更新しました。');
    return;
  }
  appData.settings.medicationOptions.push({ id: createMedicationOptionId(), ...normalizedValue });
  saveData();
  render();
  resetMedicationOptionForm();
  showToast('薬を追加しました。');
  setMedicationSettingsMessage('薬を追加しました。');
}

function editMedicationOption(id) {
  const option = appData.settings.medicationOptions.find((item) => item.id === id);
  if (!option) return;
  editingMedicationOptionId = id;
  $('medication-option-id').value = option.id;
  $('medication-label').value = option.label;
  $('medication-default-amount').value = option.defaultAmount;
  $('medication-unit').value = option.unit || '';
  $('medication-sort-order').value = option.sortOrder;
  $('medication-active').checked = option.active;
  $('save-medication-option').textContent = '薬設定を更新';
  $('cancel-medication-edit').hidden = false;
  setMedicationSettingsMessage('');
  $('medication-label').focus();
}

function toggleMedicationOptionActive(id) {
  const option = appData.settings.medicationOptions.find((item) => item.id === id);
  if (!option) return;
  option.active = !option.active;
  saveData();
  render();
  showToast(option.active ? '薬設定を更新しました。' : '薬設定を更新しました。');
  setMedicationSettingsMessage('薬設定を更新しました。');
}

function renderMedicationSettingsList() {
  const list = $('medication-settings-list');
  list.innerHTML = '';
  if (!appData.settings.medicationOptions.length) {
    list.innerHTML = '<p class="empty">登録済みの薬はありません。</p>';
    return;
  }
  allMedicationOptions().forEach((option) => {
    const item = document.createElement('div');
    item.className = 'medication-settings-item';
    const content = document.createElement('div');
    content.className = 'medication-settings-content';
    const status = option.active ? '表示中' : '非表示';
    content.textContent = `${option.label} / ${option.defaultAmount}${option.unit || ''} / 表示順 ${option.sortOrder} / ${status}`;
    const actions = document.createElement('div');
    actions.className = 'medication-settings-actions';
    const editButton = document.createElement('button');
    editButton.className = 'edit-event-button';
    editButton.type = 'button';
    editButton.textContent = '✎';
    editButton.setAttribute('aria-label', '薬設定を編集');
    editButton.addEventListener('click', () => editMedicationOption(option.id));
    const toggleButton = document.createElement('button');
    toggleButton.className = 'secondary-button medication-toggle-button';
    toggleButton.type = 'button';
    toggleButton.textContent = option.active ? '非表示' : '表示';
    toggleButton.addEventListener('click', () => toggleMedicationOptionActive(option.id));
    actions.append(editButton, toggleButton);
    item.append(content, actions);
    list.appendChild(item);
  });
}

function renderLastMedicationList() {
  const list = $('last-medication-list');
  list.innerHTML = '';
  activeMedicationOptions().forEach((option) => {
    const last = sortedEvents(appData.events.filter((event) => event.type === 'medication' && event.medicationOptionId === option.id)).at(-1);
    const item = document.createElement('div');
    item.className = 'last-medication-item';
    item.textContent = lastMedicationText(option, last);
    list.appendChild(item);
  });
}

function startElapsedRefresh() {
  if (elapsedRefreshTimer) clearInterval(elapsedRefreshTimer);
  elapsedRefreshTimer = setInterval(() => {
    if (appData) renderLastMedicationList();
  }, 60000);
}

function stopElapsedRefresh() {
  if (!elapsedRefreshTimer) return;
  clearInterval(elapsedRefreshTimer);
  elapsedRefreshTimer = null;
}

function formatExportedAt(utcIso) {
  if (!utcIso) return '未実行';
  const date = new Date(utcIso);
  if (Number.isNaN(date.getTime())) return '未実行';
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: TIMEZONE,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false
  }).formatToParts(date).reduce((acc, part) => {
    acc[part.type] = part.value;
    return acc;
  }, {});
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
}

function renderExportStatus() {
  $('last-json-exported-at').textContent = formatExportedAt(appData.settings.lastJsonExportedAtUtc);
  $('last-csv-exported-at').textContent = formatExportedAt(appData.settings.lastCsvExportedAtUtc);
}

function render() {
  const today = nowParts().localDate;
  $('pain-score').innerHTML = Array.from({ length: 11 }, (_, value) => `<option value="${value}">${value}</option>`).join('');
  $('pain-state').innerHTML = activePainOptions().map((option) => `<option value="${option.id}">${escapeHtml(option.label)}</option>`).join('');
  $('medication-buttons').innerHTML = '';
  const medicationOptions = activeMedicationOptions();
  medicationOptions.forEach((option) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = option.label;
    button.addEventListener('click', () => saveMedication(option.id));
    $('medication-buttons').appendChild(button);
  });
  if (medicationOptions.length === 0) {
    $('medication-buttons').innerHTML = '<p class="empty">有効な薬ボタンがありません。</p>';
  }

  ensureSummaryDefaults();
  renderLastMedicationList();
  renderExportStatus();
  renderMedicationSettingsSummary();
  renderMedicationSettingsList();
  renderPainStateSettingsSummary();
  renderPainStateSettingsList();
  if (!editingMedicationOptionId && !$('medication-sort-order').value) $('medication-sort-order').value = nextMedicationSortOrder();
  if (!editingPainStateOptionId && !$('pain-state-sort-order').value) $('pain-state-sort-order').value = nextPainSortOrder();
  renderComparisonPeriodSummary();
  renderPeriodList();
  if (!editingPeriodId && !$('comparison-period-start').value) $('comparison-period-start').value = nextPeriodStartSuggestion();

  renderEventList($('today-list'), appData.events.filter((event) => event.localDate === today), sortedEventsDescending, { showDate: false });
  renderWeek(today);
}

function renderWeek(today) {
  const list = $('week-list');
  list.innerHTML = '';
  const dates = [];
  const base = new Date(`${today}T00:00:00+09:00`);
  for (let i = 1; i <= 7; i += 1) {
    const d = new Date(base.getTime() - i * 86400000);
    dates.push(new Intl.DateTimeFormat('en-CA', { timeZone: TIMEZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d));
  }
  dates.forEach((date) => {
    const events = appData.events.filter((event) => event.localDate === date);
    if (events.length === 0) return;
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = `${date}：${events.length}件`;
    const body = document.createElement('div');
    renderEventList(body, events, sortedEvents, { showDate: false });
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

const CSV_EXPORT_TYPES = {
  all: {
    filenamePart: 'all',
    headers: ['id','local_date','local_time','recorded_at_utc','timezone','type','pain_score','state_option_label','medication_option_label','note','created_at_utc','updated_at_utc','schema_version']
  },
  pain: {
    filenamePart: 'pain',
    headers: ['id','local_date','local_time','recorded_at_utc','timezone','pain_score','state_option_label','note','created_at_utc','updated_at_utc','schema_version']
  },
  medication: {
    filenamePart: 'medication',
    headers: ['id','local_date','local_time','recorded_at_utc','timezone','medication_option_label','note','created_at_utc','updated_at_utc','schema_version']
  },
  note: {
    filenamePart: 'notes',
    headers: ['id','local_date','local_time','recorded_at_utc','timezone','note','created_at_utc','updated_at_utc','schema_version']
  }
};

function getCsvExportType() {
  const selectedType = $('csv-export-type').value;
  return Object.prototype.hasOwnProperty.call(CSV_EXPORT_TYPES, selectedType) ? selectedType : 'all';
}

function filterEventsForCsv(type) {
  const events = type === 'all' ? appData.events : appData.events.filter((event) => event.type === type);
  return sortedEvents(events);
}

function csvValueForHeader(event, header) {
  if (header === 'id') return event.id;
  if (header === 'local_date') return event.localDate;
  if (header === 'local_time') return event.localTime;
  if (header === 'recorded_at_utc') return event.recordedAtUtc;
  if (header === 'timezone') return event.timezone;
  if (header === 'type') return event.type;
  if (header === 'pain_score') return event.type === 'pain' ? event.painScore : '';
  if (header === 'state_option_label') return event.type === 'pain' ? painEventLabel(event) : '';
  if (header === 'medication_option_label') return event.type === 'medication' ? medicationEventLabel(event) : '';
  if (header === 'note') return event.note || '';
  if (header === 'created_at_utc') return event.createdAtUtc;
  if (header === 'updated_at_utc') return event.updatedAtUtc;
  if (header === 'schema_version') return appData.schemaVersion;
  return '';
}

function buildCsvRows(events, type) {
  const headers = CSV_EXPORT_TYPES[type].headers;
  return events.map((event) => headers.map((header) => csvEscape(csvValueForHeader(event, header))).join(','));
}

function csvTimestampForFilename() {
  const time = nowParts();
  return `${time.localDate.replace(/-/g, '')}-${time.localTime.replace(':', '')}`;
}

function downloadCsv(csvText, filename) {
  download(filename, '\uFEFF' + csvText, 'text/csv;charset=utf-8');
}

function exportCsv() {
  const type = getCsvExportType();
  const config = CSV_EXPORT_TYPES[type];
  const events = filterEventsForCsv(type);
  const rows = buildCsvRows(events, type);
  const csvText = [config.headers.join(','), ...rows].join('\r\n');
  downloadCsv(csvText, `tide-trace-${config.filenamePart}-${csvTimestampForFilename()}.csv`);
  appData.settings.lastCsvExportedAtUtc = new Date().toISOString();
  saveData();
  renderExportStatus();
}

function exportJson() {
  appData.settings.lastJsonExportedAtUtc = new Date().toISOString();
  saveData();
  renderExportStatus();
  download(`tide-trace-backup-${nowParts().localDate}.json`, JSON.stringify(appData, null, 2), 'application/json;charset=utf-8');
}

function readFile(input, callback, errorElement, missingFileMessage = 'JSONファイルを選択してください。') {
  const file = input.files[0];
  if (!file) { errorElement.textContent = missingFileMessage; return; }
  const reader = new FileReader();
  reader.onload = () => callback(String(reader.result));
  reader.onerror = () => { errorElement.textContent = JSON_ERROR; };
  reader.readAsText(file);
}

function importBackupText(text) {
  const succeeded = initializeFromText(text, $('app-message'));
  if (succeeded) {
    showToast('バックアップを読み込みました');
    return true;
  }
  console.error('Backup import failed', new Error($('app-message').textContent || 'Invalid backup data'));
  $('app-message').textContent = 'バックアップを読み込めませんでした。ファイルの形式または内容を確認してください。';
  return false;
}

function handleBackupFileSelected(event) {
  const input = event.target;
  const file = input.files && input.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    try {
      importBackupText(String(reader.result));
    } catch (error) {
      console.error('Backup import failed', error);
      $('app-message').textContent = 'バックアップを読み込めませんでした。ファイルの形式または内容を確認してください。';
    } finally {
      input.value = '';
    }
  };
  reader.onerror = () => {
    console.error('Backup import failed', reader.error);
    $('app-message').textContent = 'バックアップを読み込めませんでした。ファイルの形式または内容を確認してください。';
    input.value = '';
  };
  reader.readAsText(file);
}

function requestBackupImport() {
  const confirmed = globalThis.confirm('バックアップを読み込みます。\n現在のブラウザ内の記録は、読み込むデータに置き換わります。\n必要な場合は、先に現在のデータをバックアップしてください。');
  if (!confirmed) return;

  const input = $('import-file');
  if (!input) {
    console.error('Backup import failed', new Error('Backup file input was not found'));
    $('app-message').textContent = 'バックアップを読み込めませんでした。画面を再読み込みしてから再度お試しください。';
    return;
  }
  if (input.files && input.files[0]) {
    handleBackupFileSelected({ target: input });
    return;
  }
  input.value = '';
  input.click();
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
  const option = appData.settings.medicationOptions.find((item) => item.id === medicationOptionId && item.active);
  if (!option) return;
  addEvent(createEvent({
    type: 'medication',
    medicationOptionId: option.id,
    medicationLabel: option.label,
    amount: option.defaultAmount,
    unit: option.unit,
    note: sharedNoteValue()
  }), `${option.label}を記録しました`);
  clearSharedNote();
  $('app-message').textContent = '';
}

function wireEvents() {
  $('load-pasted-json').addEventListener('click', () => initializeFromText($('setup-json').value, $('setup-error')));
  $('load-file-json').addEventListener('click', () => readFile($('setup-file'), (text) => initializeFromText(text, $('setup-error')), $('setup-error')));
  $('save-pain').addEventListener('click', () => {
    const stateOptionId = $('pain-state').value;
    if (!stateOptionId) { $('app-message').textContent = '痛みの状態を選択してください。'; return; }
    const option = appData.settings.painStateOptions.find((item) => item.id === stateOptionId && item.active);
    if (!option) { $('app-message').textContent = '痛みの状態を選択してください。'; return; }
    addEvent(createEvent({ type: 'pain', painScore: Number($('pain-score').value), stateOptionId: option.id, stateLabel: option.label, note: sharedNoteValue() }), '痛みを記録しました');
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
  $('medication-option-form').addEventListener('submit', (event) => {
    event.preventDefault();
    saveMedicationOptionFromForm();
  });
  $('pain-state-option-form').addEventListener('submit', (event) => {
    event.preventDefault();
    savePainStateOptionFromForm();
  });
  $('summary-end-today').addEventListener('change', updateSummaryEndDateMode);
  $('summary-end-custom').addEventListener('change', updateSummaryEndDateMode);
  $('run-visit-summary').addEventListener('click', runVisitSummary);
  $('cancel-medication-edit').addEventListener('click', () => {
    resetMedicationOptionForm();
    setMedicationSettingsMessage('');
  });
  $('cancel-pain-state-edit').addEventListener('click', () => {
    resetPainStateOptionForm();
    setPainStateSettingsMessage('');
  });
  $('comparison-period-form').addEventListener('submit', (event) => {
    event.preventDefault();
    savePeriodFromForm();
  });
  $('cancel-comparison-period-edit').addEventListener('click', () => {
    resetPeriodForm();
    setPeriodMessage('');
  });
  $('export-csv').addEventListener('click', exportCsv);
  $('export-json').addEventListener('click', exportJson);
  $('toast-undo-button').addEventListener('click', undoLastSavedEvent);
  $('edit-event-form').addEventListener('submit', (event) => {
    event.preventDefault();
    saveEditedEvent();
  });
  $('cancel-edit-event').addEventListener('click', closeEditEventPanel);
  $('edit-event-panel').addEventListener('click', (event) => {
    if (event.target === $('edit-event-panel')) closeEditEventPanel();
  });
  $('import-json').addEventListener('click', requestBackupImport);
  $('import-file').addEventListener('change', handleBackupFileSelected);
  $('delete-all').addEventListener('click', () => {
    if (!confirm('全データを削除します。\n必要な場合は、先に現在のデータをバックアップしてください。')) return;
    localStorage.removeItem(STORAGE_KEY);
    appData = null;
    showSetup();
  });
}

wireEvents();
appData = loadStoredData();
if (appData) showApp(); else showSetup();
