# Pythonistaでの使い方:
# 1. Tide Traceからbackup JSONを書き出す
# 2. このスクリプトと同じフォルダに tide_trace_backup.json と loxonin_log.csv を置く
# 3. Pythonistaでこのスクリプトを実行する
# 4. tide_trace_merged_backup.json をTide Traceにインポートする
# 5. インポート後、Tide Traceで記録内容を確認する
# 6. 問題なければ、Tide Traceから新しいバックアップを保存する

import csv
import json
import datetime
import hashlib
import pathlib
import sys

BACKUP_FILE = 'tide_trace_backup.json'
CSV_FILE = 'loxonin_log.csv'
MERGED_FILE = 'tide_trace_merged_backup.json'
REPORT_FILE = 'legacy_import_report.txt'
TIMEZONE_LABEL = 'local'

MEDICATION_RULES = {
    'loxonin': {
        'label': 'ロキソニン',
        'option_id': 'medication_loxonin',
        'note_name': 'Loxonin',
    },
    'calonal': {
        'label': 'カロナール',
        'option_id': 'medication_calonal',
        'note_name': 'CALONAL',
    },
}

PAIN_RULES = {
    'pain high': {
        'score': 8,
        'label': 'その他',
        'option_id': 'pain_state_other',
        'note_name': 'Pain High',
    },
}


def script_dir():
    try:
        return pathlib.Path(__file__).resolve().parent
    except NameError:
        return pathlib.Path.cwd()


def find_input_file(filename):
    cwd_path = pathlib.Path.cwd() / filename
    if cwd_path.exists():
        return cwd_path
    script_path = script_dir() / filename
    if script_path.exists():
        return script_path
    return None


def output_path(filename):
    return pathlib.Path.cwd() / filename


def fail(message):
    print('エラー: ' + message)
    return 1


def normalize_text(value):
    return ' '.join(value.strip().lower().split())


def parse_date(value):
    text = value.strip()
    for fmt in ('%Y/%m/%d', '%Y-%m-%d'):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_time(value):
    text = value.strip()
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.datetime.strptime(text, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            pass
    return None


def parse_datetime_and_content(row):
    cells = [cell.strip() for cell in row]
    non_empty = [cell for cell in cells if cell]
    if len(non_empty) < 2:
        return None, None, '列数が不足しています'

    # 形式: "YYYY/MM/DD HH:mm", "内容"
    first_parts = non_empty[0].split()
    if len(first_parts) >= 2:
        date_value = parse_date(first_parts[0])
        time_value = parse_time(first_parts[1])
        if date_value and time_value:
            return combine_local_datetime(date_value, time_value), ' '.join(non_empty[1:]), ''

    # 形式: "YYYY/MM/DD", "HH:mm", "内容"
    if len(non_empty) >= 3:
        date_value = parse_date(non_empty[0])
        time_value = parse_time(non_empty[1])
        if date_value and time_value:
            return combine_local_datetime(date_value, time_value), ' '.join(non_empty[2:]), ''

    return None, None, '日時を読み取れません'


def combine_local_datetime(date_value, time_value):
    return datetime.datetime(
        date_value.year,
        date_value.month,
        date_value.day,
        time_value.hour,
        time_value.minute,
    )


def local_to_utc_iso(local_dt):
    # naive datetime.astimezone() は実行環境のローカル時刻として解釈されます。
    utc_dt = local_dt.astimezone(datetime.timezone.utc)
    text = utc_dt.replace(microsecond=0).isoformat()
    if text.endswith('+00:00'):
        return text[:-6] + 'Z'
    return text


def next_sort_order(options):
    max_order = 0
    for option in options:
        order = option.get('sortOrder')
        if isinstance(order, (int, float)) and order > max_order:
            max_order = order
    return max_order + 1


def find_option_by_label(options, label):
    for option in options:
        if option.get('label') == label:
            return option
    return None


def ensure_option(options, option):
    existing = find_option_by_label(options, option['label'])
    if existing:
        return existing, None

    option_id = option['id']
    ids = set(item.get('id') for item in options)
    if option_id in ids:
        suffix = 2
        while option_id + '_' + str(suffix) in ids:
            suffix += 1
        option_id = option_id + '_' + str(suffix)

    new_option = dict(option)
    new_option['id'] = option_id
    new_option['sortOrder'] = next_sort_order(options)
    options.append(new_option)
    return new_option, new_option


def stable_event_id(raw_line, local_dt, event_type):
    source = '|'.join([
        raw_line.strip(),
        local_dt.strftime('%Y-%m-%dT%H:%M'),
        event_type,
    ])
    digest = hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]
    return 'legacy_' + digest


def make_base_event(event_id, local_dt):
    local_date = local_dt.strftime('%Y-%m-%d')
    local_time = local_dt.strftime('%H:%M')
    recorded_at = local_to_utc_iso(local_dt)
    return {
        'id': event_id,
        'recordedAtUtc': recorded_at,
        'localDate': local_date,
        'localTime': local_time,
        'timezone': TIMEZONE_LABEL,
        'createdAtUtc': recorded_at,
        'updatedAtUtc': recorded_at,
    }


def classify_content(content):
    normalized = normalize_text(content)
    if normalized in MEDICATION_RULES:
        return 'medication', MEDICATION_RULES[normalized]
    if normalized in PAIN_RULES:
        return 'pain', PAIN_RULES[normalized]
    return None, None


def read_csv_rows(csv_path):
    rows = []
    with csv_path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle)
        for row in reader:
            raw_line = ','.join(row)
            rows.append((row, raw_line))
    return rows


def load_backup(backup_path):
    with backup_path.open('r', encoding='utf-8') as handle:
        data = json.load(handle)
    if 'events' not in data or 'settings' not in data:
        raise ValueError('backup JSONに events / settings がありません')
    if not isinstance(data['events'], list) or not isinstance(data['settings'], dict):
        raise ValueError('backup JSONの events / settings の形式が正しくありません')
    settings = data['settings']
    if not isinstance(settings.get('medicationOptions'), list) or not isinstance(settings.get('painStateOptions'), list):
        raise ValueError('backup JSONの settings に medicationOptions / painStateOptions がありません')
    return data


def convert(data, rows):
    report = {
        'csv_rows': len(rows),
        'added_medication': 0,
        'added_pain': 0,
        'skipped_duplicates': 0,
        'unreadable': [],
        'added_settings': [],
    }

    settings = data['settings']
    medication_options = settings['medicationOptions']
    pain_options = settings['painStateOptions']

    loxonin_option, added = ensure_option(medication_options, {
        'id': 'medication_loxonin', 'label': 'ロキソニン', 'active': True,
        'defaultAmount': 1, 'unit': '錠', 'sortOrder': 0,
    })
    if added:
        report['added_settings'].append('medicationOptions: ロキソニン')
    calonal_option, added = ensure_option(medication_options, {
        'id': 'medication_calonal', 'label': 'カロナール', 'active': True,
        'defaultAmount': 1, 'unit': '錠', 'sortOrder': 0,
    })
    if added:
        report['added_settings'].append('medicationOptions: カロナール')
    pain_other_option, added = ensure_option(pain_options, {
        'id': 'pain_state_other', 'label': 'その他', 'active': True, 'sortOrder': 0,
    })
    if added:
        report['added_settings'].append('painStateOptions: その他')

    medication_by_label = {
        'ロキソニン': loxonin_option,
        'カロナール': calonal_option,
    }
    existing_ids = set(event.get('id') for event in data['events'] if isinstance(event, dict))

    for row, raw_line in rows:
        local_dt, content, error = parse_datetime_and_content(row)
        if error:
            report['unreadable'].append(raw_line + ' -- ' + error)
            continue

        event_type, rule = classify_content(content)
        if not event_type:
            report['unreadable'].append(raw_line + ' -- 内容を読み取れません')
            continue

        event_id = stable_event_id(raw_line, local_dt, event_type)
        if event_id in existing_ids:
            report['skipped_duplicates'] += 1
            continue

        event = make_base_event(event_id, local_dt)
        if event_type == 'medication':
            option = medication_by_label[rule['label']]
            event.update({
                'type': 'medication',
                'medicationOptionId': option.get('id'),
                'medicationLabel': rule['label'],
                'amount': 1,
                'unit': '錠',
                'note': '旧CSV: ' + rule['note_name'],
            })
            report['added_medication'] += 1
        else:
            event.update({
                'type': 'pain',
                'painScore': rule['score'],
                'stateOptionId': pain_other_option.get('id'),
                'stateLabel': rule['label'],
                'note': '旧CSV: ' + rule['note_name'],
            })
            report['added_pain'] += 1

        data['events'].append(event)
        existing_ids.add(event_id)

    return report


def write_report(report, path):
    lines = [
        'legacy CSV import report',
        '',
        '読み込んだCSV行数: ' + str(report['csv_rows']),
        '追加した服薬記録数: ' + str(report['added_medication']),
        '追加した痛み記録数: ' + str(report['added_pain']),
        'スキップした重複行数: ' + str(report['skipped_duplicates']),
        '読み取れなかった行数: ' + str(len(report['unreadable'])),
        '読み取れなかった行の内容:',
    ]
    if report['unreadable']:
        for item in report['unreadable']:
            lines.append('- ' + item)
    else:
        lines.append('- なし')

    lines.append('追加したsettings項目:')
    if report['added_settings']:
        for item in report['added_settings']:
            lines.append('- ' + item)
    else:
        lines.append('- なし')

    lines.extend([
        '出力ファイル名:',
        '- ' + MERGED_FILE,
        '- ' + REPORT_FILE,
        '',
    ])
    path.write_text('\n'.join(lines), encoding='utf-8')


def main():
    backup_path = find_input_file(BACKUP_FILE)
    if not backup_path:
        return fail(BACKUP_FILE + ' が見つかりません')
    csv_path = find_input_file(CSV_FILE)
    if not csv_path:
        return fail(CSV_FILE + ' が見つかりません')

    try:
        data = load_backup(backup_path)
    except Exception as exc:
        return fail('backup JSONが読めません: ' + str(exc))

    try:
        rows = read_csv_rows(csv_path)
    except Exception as exc:
        return fail('CSVが読めません: ' + str(exc))

    report = convert(data, rows)
    merged_path = output_path(MERGED_FILE)
    report_path = output_path(REPORT_FILE)
    merged_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_report(report, report_path)

    print('変換が完了しました。')
    print('読み込んだCSV行数: ' + str(report['csv_rows']))
    print('追加した服薬記録数: ' + str(report['added_medication']))
    print('追加した痛み記録数: ' + str(report['added_pain']))
    print('スキップした重複行数: ' + str(report['skipped_duplicates']))
    print('読み取れなかった行数: ' + str(len(report['unreadable'])))
    print('出力: ' + str(merged_path))
    print('レポート: ' + str(report_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
