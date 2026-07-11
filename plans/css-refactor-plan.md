# TideTrace CSS整理計画

## 1. 現状の問題

- `docs/styles.css` では `label` が全体に `display: block; font-weight: 700; margin: 12px 0 6px;` を適用している。これにより、フォーム項目用ではないインラインラベルにも太字と上下余白が入り、`.checkbox-row`、`.radio-row`、`.column-short-label`、`.file-action-label` などで個別の打ち消しが必要になっている。
- `input, select, textarea, button` が `width: 100%; border-radius: 12px; font: inherit;` を共有している。チェックボックス、ラジオボタン、短縮名入力、編集・削除・並べ替えの小型ボタン、ファイル選択用の隠し input まで全幅前提になるため、`.checkbox-row input`、`.radio-row input`、`.column-short-label input`、`.column-reorder-button`、`.delete-event-button` などで上書きしている。
- `input, select, textarea` が `display: block; max-width: 100%; min-width: 0; border; padding; background; color;` を全 input に適用している。`input[type="checkbox"]`、`input[type="radio"]`、`input[type="hidden"]`、`input[type="file"]` にも一度は入力欄風の見た目が当たるため、フォーム以外の用途で意図しない継承が起きやすい。
- `.form-control` は全幅 sizing だけを持つが、見た目はグローバル `input, select, textarea` に依存している。責務が分かれきっておらず、新規要素を追加すると「見た目」と「全幅」のどちらを付けるべきか判断しづらい。
- `input[type="date"].form-control` は date input の全幅化と `appearance` を個別に再指定している。iPhone Safari で幅が崩れやすい領域なので維持が必要だが、将来は date 用ではなく全幅入力用クラスに紐づけた方が分かりやすい。
- `button, .primary-button` が標準ボタンの見た目、余白、全幅前提の sizing を広く適用している。`.primary-button` を付けた `.file-action-label` もボタン風にするため同じスタイルを共有している一方、アイコンボタンやコンパクト操作ボタンは `button` 側の大きい見た目を打ち消している。
- `button:not(.secondary-button):not(.danger):not(.toast-undo-button):not(.edit-event-button):not(.delete-event-button):not(.column-reorder-button):hover` は除外リストでホバーを制御しており、新しい小型ボタンを追加するたびに除外漏れが起きる可能性がある。
- `button:active, .primary-button:active` はすべての button に active 色を広く適用している。`.secondary-button:active`、`.toast-undo-button:active`、`.edit-event-button:active`、`.delete-event-button:active`、`.column-reorder-button:active` が競合・上書きしている。
- `input:focus, select:focus, textarea:focus, button:focus-visible, .file-action-label:focus-visible` は focus の見た目をグローバル要素に当てている。対象要素の整理時に focus-visible の対象から外れないよう注意が必要。
- 関連する media query は `@media (max-width: 360px)` の初期設定・痛み入力グリッド、`@media (max-width: 430px)` の編集ダイアログ、`@media (min-width: 520px)` のヘルスケア列ボタン配置。幅クラスを変更すると、これらのレイアウト条件で意図せず全幅化・縮小が変わる可能性がある。
- ダークモードは `@media (prefers-color-scheme: dark)` の CSS 変数に依存している。新クラスへ値を移す場合、`var(--input-bg)`、`var(--input-border)`、`var(--button-bg)`、`var(--button-text)` などをそのまま参照し、色値を複製しない。
- 印刷は `@media print` で `body.health-history-print-mode` の表示対象とテーブル overflow を制御している。ボタンやフォームを印刷用に増減しない計画だが、ヘルスケアデータ画面の操作要素に関するクラス変更が印刷表示へ波及しないことを確認する。
- 将来の UI 回帰の主因は、「HTML 要素名を使った初期値」が強すぎること、除外リスト型 selector が増えていること、`.primary-button` のような見た目クラスが幅・余白・ボタン以外の役割も持っていること、動的生成 HTML が同じ規則に依存していること。

## 2. 整理後の分類案

- `.form-field-label`: 通常のフォーム項目ラベル用。`display: block`、太字、フォーム項目としての上下余白だけを担当する。
- `.form-control-base`: text、number、date、time、select、textarea に共通する入力欄の見た目。`box-sizing`、`border`、`border-radius`、`padding`、`background`、`color`、`font` を担当し、幅は担当しない。
- `.form-control-full`: 全幅入力欄の sizing。`display: block`、`width: 100%`、`max-width: 100%`、`min-width: 0`、`inline-size` 系を担当する。
- `.form-control-compact`: 短い入力欄の sizing。全幅にせず、親の flex/grid 内で必要な `min-width: 0`、コンパクトな `min-height`、小さめ padding を担当する。設定可能な日ごとサマリー列エディタの短縮名 input はこの分類に置き、全幅化しない。
- `.checkbox-control`: チェックボックス本体用。`width: auto`、`flex: 0 0 auto`、不要な padding/border/background を持たない状態を明示する。
- `.checkbox-row`: チェックボックスとテキストを並べる行。既存の責務を維持しつつ、ラベル全体のインライン配置と余白だけを担当する。
- `.radio-control`: ラジオボタン本体用。現在使われている `summary-end-mode` の radio input に適用し、全幅入力欄スタイルから独立させる。
- `.radio-row`: radio とテキストを並べる行。既存の inline-flex と余白を維持する。
- `.file-input-hidden`: ファイル input の視覚的非表示用。現在の `.visually-hidden-file-input` と同等の責務を明確にする。既存クラスを残すか rename する場合は互換リスクを低くするため段階的に行う。
- `.file-action-label`: input file を開くラベルの構造・カーソル・inline-flex を担当する。ボタン色や幅は別クラスで付ける。
- `.button-base`: button とボタン風ラベルの共通見た目。`border-radius`、`font`、`font-weight`、`padding`、`min-height`、基本背景色を担当し、幅は担当しない。
- `.button-full`: 全幅ボタンの sizing。`width: 100%` と標準の上余白を担当する。
- `.button-primary`: primary 色を担当する。`.primary-button` を互換 alias として残すか、段階的に置き換える。
- `.button-secondary`: secondary 色と border を担当する。既存 `.secondary-button` の責務を色・状態に絞る。
- `.button-danger`: danger 色を担当する。既存 `.danger` は段階的に alias として扱う。
- `.button-compact`: 設定リストの表示/非表示切替や履歴詳細など、文字付きの小型操作ボタン用。`width: auto`、小さい `min-height`、小さい padding、`margin: 0` を担当する。
- `.button-icon`: 編集、削除、列の上下移動、削除などアイコン・1文字操作用。正方形サイズ、丸形または既存形状、中央揃え、`width: auto` を担当する。
- 見た目と幅は分ける。例: 通常の保存ボタンは `.button-base .button-primary .button-full`、ヘルスケア CSV ラベルは `.file-action-label .button-base .button-primary .button-full`、短縮名 input は `.form-control-base .form-control-compact` とする。

## 3. 移行手順

1. 現在のグローバル `label`、`input, select, textarea, button`、`button, .primary-button` を残したまま、既存 HTML と動的生成 HTML に目的別クラスを追加する。
2. 既存の宣言値を意図的に変えず、新クラスへ移す。色、余白、padding、min-height、border-radius はまず現状と同じ値を使う。
3. すべての対象要素に、用途に合うラベル・入力・幅・ボタン種別・コンパクト/アイコンのクラスが付いたことを確認する。
4. クラス付与が完了してから、広い `label`、`input, select, textarea, button`、`input, select, textarea`、`button` selector を狭める、または最小限のリセットだけにする。
5. 新クラスで不要になった override だけを削除する。見た目変更を目的にした値の調整はこの refactor では行わない。
6. 実装 PR では `docs/index.html` の静的 CSS cache-busting version を更新する。JavaScript を変更した場合は JS の cache-busting version も確認する。
7. 利用可能なテスト、JavaScript syntax check、HTML/CSS の静的確認、`git diff --check`、selector/class coverage の確認を実行する。
8. iPhone Safari の最終的な見た目確認は利用者に依頼する。Codex は実機ブラウザ確認を実施したとは主張しない。

## 4. 変更が必要な要素一覧

| 画面・機能 | 現在の selector / class | 提案 selector / class | 期待リスク | iPhone Safari確認 |
| --- | --- | --- | --- | --- |
| 初期設定 | 動的 `label`、`.setup-option-list input`、`.setup-start-button`、`.setup-restore-button` | `.form-field-label`、`.form-control-base`、`.form-control-full`、`.button-base`、`.button-full`、`.button-primary/.button-secondary` | 初期設定フォームの幅、360px以下の折り返し | 必要 |
| 日次記録フォーム | `label`、`select`、`textarea`、`button`、`.pain-input-grid label` | `.form-field-label`、`.form-control-base`、`.form-control-full`、`.button-base`、`.button-full` | 痛み select とメモ textarea の高さ・余白 | 必要 |
| 薬ボタン | `.button-list button` と広い `button` | `.button-base .button-primary .button-full` または `.medication-record-button` | 薬ボタンの全幅・タップ領域 | 必要 |
| 痛みスコア・状態 controls | `#pain-score`、`#pain-state` がグローバル select 依存 | `.form-control-base .form-control-full` | select の幅と grid 内縮小 | 必要 |
| メモ input | `#record-note-input` が textarea グローバル依存 | `.form-control-base .form-control-full` | textarea padding、高さ | 必要 |
| 今日の記録 | `.edit-event-button`、`.delete-event-button` | `.button-icon` + 種別 class | アイコンボタンのサイズと並び | 必要 |
| 過去の記録 | `.history-detail-button.secondary-button`、`.history-nav-button.secondary-button` | `.button-base .button-secondary` + 必要なら `.button-compact` / `.button-full` | 詳細・ナビボタンの幅と折り返し | 必要 |
| 記録編集 | 動的 `label/input/select/textarea`、`.edit-event-actions button` | `.form-field-label`、`.form-control-base`、`.form-control-full`、`.button-base`、`.button-full`、`.button-secondary` | date/time input の iOS 幅、430px以下の dialog | 必要 |
| 診察用サマリー | `.form-control`、`.radio-row input`、`.visit-summary-actions button` | `.form-control-base .form-control-full`、`.radio-control`、`.button-base`、`.button-secondary`、必要なら `.button-compact` | radio のサイズ、action ボタンの flex 幅 | 必要 |
| 過去の記録とヘルスケアデータ | `.file-action-label.primary-button`、`.visit-summary-actions button` | `.file-action-label .button-base .button-primary .button-full`、`.button-secondary` | ファイルラベルのボタン風表示、印刷モード | 必要 |
| 設定可能な日ごとサマリー列 | `.column-short-label input`、`.column-reorder-button`、`.column-remove-button.delete-event-button`、`.health-column-check input[type="checkbox"]` | `.form-control-base .form-control-compact`、`.button-icon`、`.checkbox-control` | 短縮名 input が全幅化しないこと、列操作ボタンの正方形維持 | 必要 |
| 薬設定 | `.form-control`、`.checkbox-row input`、`.medication-toggle-button`、動的 `.edit-event-button` | `.form-control-base .form-control-full`、`.checkbox-control`、`.button-compact`、`.button-icon` | checkbox と小型ボタンの幅 | 必要 |
| 痛み状態設定 | `.form-control`、`.checkbox-row input`、`.pain-state-toggle-button`、動的 `.edit-event-button` | `.form-control-base .form-control-full`、`.checkbox-control`、`.button-compact`、`.button-icon` | checkbox と小型ボタンの幅 | 必要 |
| 期間設定 | `.form-control`、`.comparison-period-form-actions button`、動的 edit/delete | `.form-control-base .form-control-full`、`.button-base`、`.button-full`、`.button-icon` | date input 幅、削除ボタンサイズ | 必要 |
| バックアップ・CSV controls | `#export-json`、`#import-json`、`#csv-export-type`、`#export-csv` | `.button-base .button-full`、`.form-control-base .form-control-full` | 管理画面ボタンの全幅 | 必要 |
| ファイル選択 controls | `.visually-hidden-file-input`、`.file-action-label.primary-button` | `.file-input-hidden`、`.file-action-label .button-base .button-primary .button-full` | 隠し input の focus/クリック連携 | 必要 |
| 削除確認 controls | `#delete-all.danger`、削除系 `.delete-event-button` | `.button-base .button-danger .button-full`、`.button-icon .button-danger` | danger 色とサイズの分離 | 必要 |
| print view | `@media print body.health-history-print-mode ...` | 原則 selector 維持。必要なら操作ボタン分類後も print 対象が変わらないことを確認 | 操作要素が印刷に混入するリスク | 必要 |

## 5. 影響を受けやすい箇所

- iPhone Safari: date/time input、select、全幅ボタン、flex 内の compact input が特に崩れやすい。`min-width: 0` と `inline-size` 系の指定は移行後も維持する。
- date inputs: `input[type="date"].form-control` の `-webkit-appearance: none` と全幅指定を、新しい full-width date input でも保持する。
- checkbox sizing: checkbox/radio は `input` の padding、border、background、width から切り離し、`width: auto` と `flex: 0 0 auto` を明示する。
- file-action labels: `.file-action-label` は label だがボタンとして振る舞う。`.form-field-label` を付けず、button 系 class で見た目と幅を付ける。
- full-width buttons: 既存の button は多くが全幅前提。`.button-full` を付け忘れると横幅が縮むため、coverage check が必要。
- compact operation buttons: 編集、削除、表示/非表示、列の上下移動は `.button-full` を付けない。全幅化の再発を防ぐ。
- focus-visible styles: `button:focus-visible` と `.file-action-label:focus-visible` の現状を保つ。input/select/textarea の focus も新クラス化で失われないよう確認する。
- dark mode: 新クラスに移しても CSS 変数参照を維持し、色値の重複や light 固定色を追加しない。
- print styles: print selector は最小変更にし、ヘルスケア表と印刷モードの表示/非表示を変えない。
- selector specificity: `.button-secondary` と `.button-primary` の状態 style は、広い `button:active` より明確に強いか、広い selector 自体を弱める。
- source order: base → sizing → variant → component override の順に置き、後半の component override が必要最小限で済むようにする。
- touch-target size: 標準ボタンは現状の `min-height: 48px`、ファイル action は `44px`、小型操作は既存値を維持し、意図せず小さくしない。
- static asset caching: 実装 PR では CSS 変更後に `docs/index.html` の CSS version を更新する。JS の動的生成 class 変更がある場合は JS version も確認する。

## 6. PRの分割案

- 推奨は 2 PR。
  1. labels と input controls: `.form-field-label`、`.form-control-base`、`.form-control-full`、`.form-control-compact`、checkbox/radio/file input の分類を追加・移行する。
  2. buttons と compact/icon operations: `.button-base`、`.button-full`、variant、compact/icon 操作ボタン、file-action label のボタン化を移行する。
- 2 PR に分ける理由は、入力欄とボタンの影響範囲がどちらも広く、同時に狭めると見た目差分の原因を追いづらいため。入力欄の分類が先に必要なのは、file input と file-action label の責務を明確にしてからボタン側の分類を進める方が安全だから。
- 1 PR も可能だが、`docs/index.html` と `docs/app.js` の動的 HTML に多数の class 追加が集中し、review が重くなる。
- 3 PR 以上は現時点では推奨しない。selector 分離そのものが目的であり、過度に細かく分けると cache-busting 更新と確認作業が重複する。

## 7. 自動確認

- 既存テスト: `pytest` を実行する。
- JavaScript syntax check: `node --check docs/app.js` を実行する。
- 静的 HTML 確認: `python - <<'PY' ...` などで `docs/index.html` を parse し、CSS/JS version query の存在、主要 id の存在を確認する。
- 差分確認: `git diff --check` を実行する。
- class coverage: `rg` と簡単な script で、`label`、`input`、`select`、`textarea`、`button` のうち対象外を除いたものに新分類 class が付いているか確認する。動的 HTML 文字列も `docs/app.js` 内で確認する。
- broad selector narrowing check: 実装時は、広い selector を狭める commit の前に新 class が付いていることを `git diff` と `rg` で確認する。
- cache-busting check: CSS 変更がある実装 PR では `docs/index.html` の CSS version が更新されているか確認する。JS 変更もある場合は JS version も確認する。
- ブラウザ screenshot、実機 iPhone Safari、印刷ダイアログでの実レンダリングは Codex の自動確認としては主張しない。

## 8. 利用者による確認項目

- light mode
  - 初期設定、記録、設定、過去データ画面で入力欄とボタンの幅が以前と大きく変わらないこと。
- dark mode
  - 入力欄、ボタン、focus 表示、ヘルスケア列エディタの色が読めること。
- normal app use
  - 薬、痛み、メモを追加し、今日の記録と過去の記録で編集・削除できること。
- settings
  - 薬設定、痛み状態設定、期間設定で追加・編集・キャンセル・表示切替が操作しやすいこと。
- configurable-column editor
  - 短縮名 input がコンパクトなままで、上下移動・削除ボタンが全幅になっていないこと。
- file selection
  - バックアップ読み込みと HeartWatch CSV 読み込みのボタン風ラベルでファイル選択が開くこと。
- print view
  - ヘルスケアデータの印刷用表示で不要な画面が混ざらないこと。

## 9. 対象外

- visual redesign は行わない。
- 意図的な spacing 変更は行わない。
- color 変更は行わない。
- typography redesign は行わない。
- UI wording 変更は行わない。
- behavior 変更は行わない。
- localStorage key、event field、settings field の変更は行わない。
- data-format 変更は行わない。
- medical-content 変更は行わない。
- 外部依存関係は追加しない。
- selector 分離により避けられない微小差分が見つかった場合は、「改善」として扱わず、差分・理由・影響範囲を明示して review する。
- 後続実装が見た目と挙動を保つ限り、`CHANGELOG.md`、`specs/SPEC.md`、`specs/DATA_FORMAT.md` は変更しない想定。

## 10. 実装指示に必要な決定事項

- 既存クラス名を alias として残すか
  - 推奨: `.primary-button`、`.secondary-button`、`.danger` などは当面 alias として残し、新クラスを追加して段階的に整理する。
  - 代替: 既存クラス名を一括で新名へ置換する。
  - trade-off: alias 維持は互換性と review の安全性が高いが、CSS が一時的に冗長になる。一括置換は最終形が綺麗だが差分と回帰リスクが大きい。
- 実装 PR の分割数
  - 推奨: 2 PR（入力系 → ボタン系）。
  - 代替: 1 PR で一括実装。
  - trade-off: 2 PR は review と原因切り分けが容易だが、cache-busting と確認が2回必要。1 PR は作業回数が少ないが影響範囲が広い。
- class 命名の粒度
  - 推奨: base、width/sizing、variant、component を分ける。
  - 代替: `.form-control` や `.primary-button` に幅と見た目をまとめる。
  - trade-off: 分離は class 数が増えるが将来の override を減らせる。統合は短く書けるが、compact input や icon button で再び打ち消しが増える。
- cache-busting の対象
  - 推奨: CSS 変更時は CSS version を更新し、JS を変更した PR では JS version も確認して必要なら更新する。
  - 代替: CSS version のみ更新する。
  - trade-off: 必要な asset だけ更新する方が最小差分だが、動的 class 変更が JS 側にある場合は JS cache の影響を見落としやすい。
