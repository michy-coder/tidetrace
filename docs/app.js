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
  const validMedicationOption = (option) => validOption(option) &&
    typeof option.defaultAmount === 'number' && Number.isFinite(option.defaultAmount) &&
    typeof option.unit === 'string' &&
    typeof option.sortOrder === 'number' && Number.isFinite(option.sortOrder);
  if (!data.settings.painStateOptions.every(validOption)) return false;
  if (!data.settings.medicationOptions.every(validMedicationOption)) return false;

  const painIds = new Set(data.settings.painStateOptions.map((option) => option.id));
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
      return typeof event.medicationOptionId === 'string' &&
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

function activePainOptions() { return appData.settings.painStateOptions.filter((option) => option.active); }
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
function findPainLabel(id) { return (appData.settings.painStateOptions.find((option) => option.id === id) || {}).label || ''; }
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
  if (event.type === 'pain') parts.push(`score ${event.painScore}`, findPainLabel(event.stateOptionId));
  if (event.type === 'medication') {
    parts.push(medicationEventLabel(event) || '不明な薬');
    if (event.amount !== undefined || event.unit) parts.push(`${event.amount ?? ''}${event.unit || ''}`);
  }
  if (event.note) parts.push(event.note);
  return parts.filter(Boolean).join(' / ');
}

function renderEventList(container, events, sortEvents = sortedEvents) {
  container.innerHTML = '';
  if (events.length === 0) {
    container.innerHTML = '<p class="empty">記録はありません。</p>';
    return;
  }
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
    content.append(meta, body);
    item.append(content, actions);
    container.appendChild(item);
  });
}

function optionHtml(options, selectedId) {
  return options.map((option) => `<option value="${escapeHtml(option.id)}"${option.id === selectedId ? ' selected' : ''}>${escapeHtml(option.displayLabel || option.label)}</option>`).join('');
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
      <select id="edit-pain-state">${optionHtml(activePainOptions(), event.stateOptionId)}</select>
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
    event.stateOptionId = stateOptionId;
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

function elapsedText(iso) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
  return `${Math.floor(minutes / 60)}時間${minutes % 60}分`;
}

function addDays(dateText, days) {
  const date = new Date(`${dateText}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
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

function renderLastMedicationList() {
  const list = $('last-medication-list');
  list.innerHTML = '';
  appData.settings.medicationOptions.forEach((option) => {
    const last = sortedEvents(appData.events.filter((event) => event.type === 'medication' && event.medicationOptionId === option.id)).at(-1);
    const item = document.createElement('div');
    item.className = 'last-medication-item';
    item.textContent = last ? `${option.label}：前回 ${last.localTime} / 経過 ${elapsedText(last.recordedAtUtc)}` : `${option.label}：記録なし`;
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

  renderLastMedicationList();
  renderExportStatus();
  renderPeriodList();
  if (!editingPeriodId && !$('comparison-period-start').value) $('comparison-period-start').value = nextPeriodStartSuggestion();

  renderEventList($('today-list'), appData.events.filter((event) => event.localDate === today), sortedEventsDescending);
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
  if (header === 'state_option_label') return event.type === 'pain' ? findPainLabel(event.stateOptionId) : '';
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
  if (succeeded) showToast('バックアップを読み込みました');
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
  const confirmed = confirm('バックアップを読み込みます。\n現在のブラウザ内の記録は、読み込むデータに置き換わります。\n必要な場合は、先に現在のデータをバックアップしてください。');
  if (!confirmed) return;

  const input = $('import-file');
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
