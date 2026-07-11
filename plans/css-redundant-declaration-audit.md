# CSS冗長宣言監査（フォーム制御・ボタン役割リファクタリング後）

## 1. 監査対象と前提

- 監査 PR の base branch: `main`
- 監査 PR の base commit: `de8bffa10a7fe3f0f6688164d284552eb59f93d0`（`Merge pull request #142 from michy-coder/codex/ui-5n8724`）
- 監査 PR の head branch: `codex/audit-css-for-redundant-declarations`
- Codex 作業環境では `origin` リモートが設定されていなかったためネットワーク経由の `main` 更新確認はできなかったが、GitHub 上の Draft PR #143 の base は上記 commit として識別されている。
- 監査したファイル:
  - `docs/styles.css`
  - `docs/index.html`
  - `docs/app.js` の動的生成 HTML、`className`、`classList`、状態クラス付与
  - `tests/test_app_js.py` のフォーム制御・ボタン役割に関する集中的なアサーション
- 監査対象の共有クラス:
  - `.form-field-label`
  - `.form-control-base`
  - `.form-control`
  - `.form-control-full`
  - `.form-control-compact`
  - `.checkbox-control`
  - `.radio-control`
  - `.button-base`
  - `.button-full`
  - `.button-compact`
  - `.button-icon`
  - `.primary-button`
  - `.secondary-button`
  - `.danger`
- GitHub Codex 環境では、ブラウザスクリーンショット、実機 iPhone Safari、DevTools の computed style 検査は利用していない。この監査はソース確認、セレクタ検索、テスト実行に基づく。
- この PR ではアプリケーション HTML、CSS、JavaScript、テスト、仕様、CHANGELOG は変更していない。作成したファイルは `plans/css-redundant-declaration-audit.md` のみ。

## 2. 結論

件数の単位は、原則として個別 CSS 宣言（`property: value`）である。複数セレクタに同じ宣言ブロックが適用されている場合は、CSS 上の宣言 1 件として数える。表内で複数プロパティを 1 行にまとめている場合も、件数は列挙された個別プロパティ数で集計する。

| 分類 | 個別 CSS 宣言数 | 備考 |
| --- | ---: | --- |
| A. 安全に削除できる候補 | 17 | section 3 の 17 行すべて。すべて高信頼度。 |
| B. 維持すべき指定 | 95 | section 4 の表で列挙した候補宣言。dark-mode 変数の説明行は通常の色源説明であり、この候補宣言数には含めない。 |
| C. 実機確認が必要な候補 | 18 | section 5 の 18 行。 |
| D. 未使用セレクタまたは到達不能ルール | 0 | section 6 の結論。 |

## 3. 安全に削除できる候補

次の候補は、現在一致する要素すべてに同じ有効値を供給する共有クラスが付いており、同じプロパティについて疑わしいメディアクエリ、ダークモード、印刷、属性状態、疑似クラス依存が見つからなかったものに限る。

| 信頼度 | セレクタ | プロパティ | 現在値 | 場所 | 影響要素 / クラス組み合わせ | 等価な共有値 | 詳細なカスケード確認 | 分類 | 理由 | 削除時の期待効果 | 手動確認 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 高 | `.history-detail-button` | `margin` | `0` | `docs/styles.css` 約 L1011-L1017 | 履歴日の「詳細/閉じる」ボタン。`button-base button-compact secondary-button history-detail-button` | `.button-compact { margin: 0; }` | `.history-detail-button` は詳細度 0-1-0、`.button-compact` も 0-1-0。`.history-detail-button` が後続だが同値。非継承。ショートハンド衝突なし。該当生成箇所は `docs/app.js` の `history-detail-button` 付与のみ。疑似クラス、属性、メディア、印刷、ダークモードで `margin` 上書きなし。 | A | コンポーネント固有の追加責任がなく、共有 compact button と完全に同じ値。 | 見た目・レイアウト変化なし。 | 不要 |
| 高 | `.history-detail-button` | `min-height` | `40px` | `docs/styles.css` 約 L1011-L1017 | 同上 | `.button-compact { min-height: 40px; }` | 同じ詳細度で共有値が先、コンポーネント値が後だが同値。`button-base` の `48px` を `.button-compact` が上書き済み。固定アイコン寸法対象ではない。 | A | compact button の責任と一致。 | 変化なし。 | 不要 |
| 高 | `.history-detail-button` | `padding` | `8px 12px` | `docs/styles.css` 約 L1011-L1017 | 同上 | `.button-compact { padding: 8px 12px; }` | ショートハンド同士で同値。後続疑似クラスなし。 | A | compact button の責任と一致。 | 変化なし。 | 不要 |
| 高 | `.history-detail-button` | `width` | `auto` | `docs/styles.css` 約 L1011-L1017 | 同上 | `.button-compact { width: auto; }` | `.button-full` は付かない。inline-size 指定なし。flex 子だが `flex: 0 0 auto` は維持対象。 | A | compact button の責任と一致。 | 変化なし。 | 不要 |
| 高 | `.history-nav-button` | `margin` | `0` | `docs/styles.css` 約 L1052-L1058 | 履歴ナビゲーションの「新しい記録」「古い記録」ボタン。`button-base button-compact secondary-button history-nav-button` | `.button-compact { margin: 0; }` | `.history-nav-button` と `.button-compact` は同詳細度、後続同値。`history-navigation-buttons` の flex layout は別責任。 | A | compact button と完全一致。 | 変化なし。 | 不要 |
| 高 | `.history-nav-button` | `min-height` | `40px` | `docs/styles.css` 約 L1052-L1058 | 同上 | `.button-compact { min-height: 40px; }` | 同値。タッチターゲットとしては共有 compact button に残る。 | A | 共有責任に集約済み。 | 変化なし。 | 不要 |
| 高 | `.history-nav-button` | `padding` | `8px 12px` | `docs/styles.css` 約 L1052-L1058 | 同上 | `.button-compact { padding: 8px 12px; }` | ショートハンド同値。 | A | 共有責任に集約済み。 | 変化なし。 | 不要 |
| 高 | `.history-nav-button` | `width` | `auto` | `docs/styles.css` 約 L1052-L1058 | 同上 | `.button-compact { width: auto; }` | `.button-full` なし。flex の `align-self` は別責任として残す。 | A | 共有責任に集約済み。 | 変化なし。 | 不要 |
| 高 | `.edit-event-button:active` | `background` | `var(--surface)` | `docs/styles.css` 約 L530-L536 | 記録、期間、薬設定、痛み状態設定の編集アイコン。すべて `button-base button-icon secondary-button edit-event-button` | `.secondary-button:active { background: var(--surface); }` | 両方とも詳細度 0-2-0。`.edit-event-button:active` は後続だが同値。該当要素はすべて `.secondary-button` 付きで、`.danger` との併用なし。ダークモードは変数値を変えるだけで、宣言責任は同じ。 | A | コンポーネント固有 active 色ではなく secondary active と同一。 | active 時の背景変化なし。 | 不要 |
| 高 | `.delete-event-button:active` | `background` | `var(--danger-active-bg)` | `docs/styles.css` 約 L538-L544 | 記録、期間、列削除の削除アイコン。すべて `button-base button-icon danger delete-event-button` | `.danger:active { background: var(--danger-active-bg); }` | 両方とも詳細度 0-2-0。後続同値。列削除は `.column-remove-button.delete-event-button` も付くが active background の別上書きなし。 | A | danger active と同一。 | active 時の背景変化なし。 | 不要 |
| 高 | `.checkbox-row .checkbox-control` | `width` | `auto` | `docs/styles.css` 約 L771-L775 | 薬設定・痛み状態設定の有効チェックボックス。`checkbox-row` 内の `input.checkbox-control` | `.checkbox-control { width: auto; }` | `.checkbox-row .checkbox-control` は 0-2-0、共有は 0-1-0。後続・高詳細度だが同値で、同じ selector 内の `flex` と `margin` は維持分類に分離済み。`height`、`max-width`、`min-width` はこの selector では指定されず、`health-column-check .checkbox-control` は別セレクタで対象外。 | A | 行内チェックボックスの幅は共有の初期化と同一で、`flex` と `margin` は残せば責任が分離できる。 | 幅変化なし。 | 不要 |
| 高 | `.radio-row .radio-control` | `width` | `auto` | `docs/styles.css` 約 L864-L868 | サマリー終了日の radio。`radio-row` 内の `input.radio-control` | `.radio-control { width: auto; }` | 0-2-0 が 0-1-0 より強いが同値で、同じ selector 内の `flex` と `margin` は維持分類に分離済み。radio 固有の疑似クラス、属性状態、media/print/dark-mode 上書きは見つからない。 | A | radio 幅は共有初期化と同一。 | 幅変化なし。 | 不要 |
| 高 | `.column-reorder-button` | `background` | `var(--surface-muted)` | `docs/styles.css` 約 L1154-L1159 | 表示項目エディタの上下移動アイコン。`button-base button-icon secondary-button column-reorder-button` | `.secondary-button { background: var(--surface-muted); }` | `.column-reorder-button` と `.secondary-button` は 0-1-0。後続同値。すべての生成箇所で `.secondary-button` 付き。active は別行で検証済み。該当 markup は `docs/app.js` の上下移動ボタン 2 箇所で、いずれも `.secondary-button` を同時に持つ。 | A | secondary visual role と同一。 | 通常時背景変化なし。 | 不要 |
| 高 | `.column-reorder-button` | `border` | `1px solid var(--border)` | `docs/styles.css` 約 L1154-L1159 | 同上 | `.secondary-button { border: 1px solid var(--border); }` | ショートハンド同値。`.button-icon` は border を設定しない。 | A | secondary visual role と同一。 | 境界線変化なし。 | 不要 |
| 高 | `.column-reorder-button` | `color` | `var(--text)` | `docs/styles.css` 約 L1154-L1159 | 同上 | `.secondary-button { color: var(--text); }` | 同詳細度、後続同値。ダークモードは変数で追従。 | A | secondary visual role と同一。 | 文字色変化なし。 | 不要 |
| 高 | `.column-reorder-button` | `font-weight` | `700` | `docs/styles.css` 約 L1154-L1159 | 同上 | `.button-base { font-weight: 700; }` | 同詳細度、後続同値。`.button-icon` は font-weight を設定しない。 | A | button base の責任と同一。 | 太さ変化なし。 | 不要 |
| 高 | `.column-reorder-button:active` | `background` | `var(--surface)` | `docs/styles.css` 約 L1161 | 同上 | `.secondary-button:active { background: var(--surface); }` | 両方 0-2-0、後続同値。該当要素はすべて `.secondary-button`。 | A | secondary active と同一。 | active 背景変化なし。 | 不要 |

## 4. 維持すべき指定

### component responsibility（コンポーネント責任）

| セレクタ | プロパティ | 現在値 | 場所 | 関連要素 / クラス組み合わせ | 分類 | 理由 | 削除時の影響 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `.setup-start-button` | `min-height` | `54px` | 約 L223-L225 | 初回設定開始ボタン。`button-base button-full primary-button setup-start-button` | B | `.button-base` の 48px より大きい初回設定固有のタッチ領域。 | 開始ボタンが低くなる。 |
| `.setup-restore-button` | `min-height` | `50px` | 約 L227-L229 | 初回バックアップ復元。`button-base button-full secondary-button setup-restore-button` | B | `.button-base` より大きいが開始ボタンより小さい初回設定固有サイズ。 | 復元ボタンが低くなる。 |
| `.note-save-button` | `display`, `align-items`, `justify-content`, `width`, `min-width`, `min-height`, `padding` | 各値 | 約 L409-L417 | 「メモだけ保存」。`button-base button-compact secondary-button note-save-button` | B | compact と一部重なるが、入力欄直下の短いボタンを inline-flex かつ 9rem 以上にする固有責任。`min-height:44px` と `padding:10px 14px` は compact の 40px/8px 12px を意図的に上書き。 | 幅・高さ・中央揃えが変わる。 |
| `.toast-undo-button` | `flex`, `width`, `min-height`, `margin`, `padding`, `border-radius`, `background`, `color`, `border` | 各値 | 約 L487-L497 | Toast 内の取り消しボタン。`button-base toast-undo-button` | B | 役割クラスを付けない専用ボタンで、toast 内の pill 形状・透明背景・枠線色を担う。 | toast 内の見た目と収まりが変わる。 |
| `.history-detail-button` | `flex` | `0 0 auto` | 約 L1011-L1017 | 履歴詳細ボタン。`button-base button-compact secondary-button history-detail-button` | B | header flex 行でタイトルを圧迫しないための固有レイアウト。共有 compact は flex を持たない。 | 狭幅でボタンが伸縮する可能性。 |
| `.history-nav-button` | `align-self` | `flex-start` | 約 L1052-L1058 | 履歴ナビボタン。`button-base button-compact secondary-button history-nav-button` | B | 縦横 flex コンテナ内でボタン幅を内容に合わせる配置責任。 | ボタンが行内で予期せず伸びる可能性。 |
| `.medication-toggle-button, .pain-state-toggle-button` | `align-self`, `min-height`, `padding` | `flex-start`, `2rem`, `0.2rem 0.55rem` | 約 L818-L825 | 設定リストの表示/非表示切替。`button-base button-compact secondary-button medication-toggle-button/pain-state-toggle-button` | B | compact よりさらに小さいリスト内 toggle の固有配置・高さ・padding。`margin` と `width` はここに含めず section 5 の C にのみ分類する。 | リスト行の高さ、密度、縦位置が変わる。 |
| `.file-action-label` | `align-items`, `cursor`, `display`, `justify-content`, `margin`, `min-height` | 各値 | 約 L925-L933 | HeartWatch CSV ファイル選択 label。`file-action-label button-base button-full primary-button` | B | button に見せる label のクリック可能性、inline-flex 中央揃え、配置余白、component-specific minimum height を担う。`width` はここに含めず section 5 の C にのみ分類する。 | ファイル選択 label のクリック affordance、中央揃え、配置が弱くなる。 |
| `.column-short-label input` | `color`, `flex`, `font-size`, `font-weight`, `max-width`, `min-height`, `padding` | 各値 | 約 L1130-L1139 | 表示項目エディタの短縮名入力。`form-control-base form-control-compact` | B | component-specific color、flex sizing、font、max-width、高さ、padding を担う。`min-width` はここに含めず section 5 の C にのみ分類する。 | エディタ行の幅、文字サイズ、密度が変わる。 |
| `.health-column-check .checkbox-control` | `height`, `margin`, `max-width`, `min-width`, `width` | 各値 | 約 L1200-L1206 | 表示項目エディタの checkbox。`health-column-check > input.checkbox-control` | B | grid の 1.25rem 列に合わせた正方形サイズ。共有 checkbox は width auto で寸法固定しない。 | チェックボックスとラベルの整列が変わる。 |

### layout（レイアウト）

| セレクタ | プロパティ | 現在値 | 場所 | 分類 | 理由 | 削除時の影響 |
| --- | --- | --- | --- | --- | --- | --- |
| `.record-input-section > .button-full, .management > .button-full, .medication-form-actions .button-full, .pain-state-form-actions .button-full, .comparison-period-form-actions .button-full, .health-column-buttons .button-full, #run-visit-summary` | `margin` | `10px 0 0` | 約 L308-L316 | B | full width button の幅ではなく、各フォーム/管理領域での上余白責任。 | ボタン間隔が詰まる。 |
| `.setup-actions button` | `margin-top` | `0` | 約 L219-L221 | B | `.setup-actions` grid gap を余白源にするための container 固有リセット。 | grid gap と既定/他ルール余白が重なる可能性。 |
| `.edit-event-actions button` | `margin-top` | `0` | 約 L640 | B | edit dialog の 2 列 grid gap を余白源にする。 | 保存/キャンセル行の縦位置が変わる。 |
| `.visit-summary-actions button` | `flex` | `1 1 9rem` | 約 L839-L843 | B | summary/action の折り返し可能な横並び layout。`.button-full` は `width:100%` を持つが、この flex 指定で 9rem 基準に分配する。`margin` と `min-height` はここに含めず section 5 の C にのみ分類する。 | action ボタンが全幅縦積み寄りになり、狭幅/広幅の挙動が変わる。 |
| `.checkbox-row .checkbox-control` | `flex`, `margin` | `0 0 auto`, `0` | 約 L771-L775 | B | 行内 checkbox の伸縮防止と label 行の整列。 | checkbox が余白を持つ、または伸縮する可能性。 |
| `.radio-row .radio-control` | `flex`, `margin` | `0 0 auto`, `0` | 約 L864-L868 | B | radio row の整列責任。 | radio とラベルの位置が変わる。 |
| `.event-actions` | `align-self`, `display`, `flex`, `gap` | 各値 | 約 L523-L528 | B | 記録・期間リストの icon button container。 | アイコンボタン群の整列が変わる。 |
| `.medication-settings-actions, .pain-state-settings-actions` | `align-self`, `display`, `flex`, `gap` | 各値 | 約 L810-L816 | B | 設定リスト右側操作の container。 | 編集/toggle の横並びが崩れる。 |
| `.column-selected-actions` | `align-items`, `display`, `flex`, `gap`, `grid-template-columns` | 各値 | 約 L1141-L1147 | B | 2rem の icon button 3 個を固定列で並べる。 | icon button の正方形前提が弱くなる。 |

### browser compatibility（ブラウザ互換・iPhone Safari 含む）

| セレクタ | プロパティ | 現在値 | 場所 | 分類 | 理由 | 削除時の影響 |
| --- | --- | --- | --- | --- | --- | --- |
| `input[type="date"].form-control, input[type="date"].form-control-full, input[type="time"].form-control, input[type="time"].form-control-full` | `-webkit-appearance`, `appearance` | `none` | 約 L275-L280 | B | date/time input の iPhone Safari 対応に関わるブラウザ依存指定。共有 form control にはない。 | モバイル Safari の見た目・幅計算が変わる可能性。 |
| 同上 | `box-sizing`, `display`, `width`, `max-width`, `min-width`, `inline-size`, `max-inline-size`, `min-inline-size` | 各値 | 約 L281-L288 | B | `.form-control` と重複するが date/time 専用の browser safeguard として保守的に維持。 | Safari の date/time 幅が崩れる可能性。 |
| `.visually-hidden-file-input` | visually hidden 一式 | 各値 | 約 L729 付近 | B | file input を画面外に隠しつつ label で操作するためのアクセシビリティ/ブラウザ対応。 | ファイル入力が表示される、または操作性が変わる。 |
| `.health-history-table-wrap` | `-webkit-overflow-scrolling`, `overflow-x` | `touch`, `auto` | 約 L935-L938 | B | 横スクロール表の iOS 慣性スクロール。 | iPhone の表スクロール体験が変わる。 |

### interaction state（hover / active）

| セレクタ | プロパティ | 現在値 | 場所 | 分類 | 理由 | 削除時の影響 |
| --- | --- | --- | --- | --- | --- | --- |
| `.primary-button:hover` | `background` | `var(--button-hover-bg, var(--button-bg))` | 約 L346-L348 | B | primary 固有 hover。 | hover フィードバック消失。 |
| `.primary-button:active` | `background` | `var(--button-active-bg)` | 約 L350 | B | primary active。 | active フィードバック消失。 |
| `.secondary-button:active` | `background` | `var(--surface)` | 約 L366 | B | secondary active の共有責任。 | secondary button 全体の active フィードバック消失。 |
| `.danger:active` | `background` | `var(--danger-active-bg)` | 約 L358 | B | danger active の共有責任。 | danger button 全体の active フィードバック消失。 |
| `.toast-undo-button:active` | `background` | `var(--surface)` | 約 L499 | B | toast undo は `.secondary-button` を持たないため専用 active が必要。 | toast undo の active フィードバック消失。 |

### accessibility（アクセシビリティ）

| セレクタ | プロパティ | 現在値 | 場所 | 分類 | 理由 | 削除時の影響 |
| --- | --- | --- | --- | --- | --- | --- |
| `.form-control-base:focus, .checkbox-control:focus, .radio-control:focus, button:focus-visible, .file-action-label:focus-visible` | `outline`, `outline-offset` | `3px solid var(--focus-ring)`, `2px` | 約 L291-L294 | B | keyboard focus の視認性。file label も含む。 | フォーカスリングが弱くなる。 |
| `.health-history-columns-panel > summary:focus-visible` | `outline`, `outline-offset` | 同上 | 約 L1076-L1079 | B | summary は button class を持たないため専用 focus が必要。 | summary の keyboard focus が見えにくくなる。 |

### print or dark mode（印刷・ダークモード）

| セレクタ | プロパティ | 現在値 | 場所 | 分類 | 理由 | 削除時の影響 |
| --- | --- | --- | --- | --- | --- | --- |
| `@media print body.health-history-print-mode ...` | `display`, `box-shadow`, `overflow` | 各値 | 約 L967-L981 | B | 印刷用表示の明示的挙動。共有ボタン/フォームとは無関係。 | 印刷時に不要カードが出る、表 overflow が残る。 |
| `:root` / `prefers-color-scheme: dark` の button/input 変数 | CSS 変数 | 各値 | 冒頭 | B | 同じ宣言名でも light/dark の色源として必要。 | dark mode 色が崩れる。 |

## 5. 実機確認が必要な候補

以下は重複に見えるが、ソース確認だけでは安全削除を断定しない。削除推奨ではない。

| セレクタ | プロパティ | 現在値 | 場所 | 影響要素 / クラス組み合わせ | 重複に見える理由 | 分類 | 保留理由 | 具体的な確認手順 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `.edit-datetime-field input[type="date"]` | `box-sizing` | `border-box` | 約 L615-L621 | 編集ダイアログの日付。`form-control-base form-control` | `.form-control-base` と date/time rule も `box-sizing` を指定 | C | date input はブラウザ依存。selector 詳細度が高く、iPhone Safari 保護の可能性。 | 一時削除後、iPhone Safari で編集ダイアログの日付欄の幅、padding、クリッピングを比較。 |
| `.edit-datetime-field input[type="time"]` | `box-sizing` | `border-box` | 約 L615-L621 | 編集ダイアログの時刻。`form-control-base form-control` | 同上 | C | time input は Safari の UI 差が大きい。 | 同上、時刻欄で比較。 |
| `.edit-datetime-field input[type="date"]` | `width` | `100%` | 約 L615-L621 | 同上 | `.form-control` と date/time rule が同値 | C | inline-size と width の相互作用、dialog 幅、Safari を computed style なしで断定不可。 | 320-390px 幅で編集ダイアログを開き、左右 overflow の有無を比較。 |
| `.edit-datetime-field input[type="time"]` | `width` | `100%` | 約 L615-L621 | 同上 | 同上 | C | 同上。 | 同上。 |
| `.edit-datetime-field input[type="date"]` | `min-width` | `0` | 約 L615-L621 | 同上 | `.form-control` と date/time rule が同値 | C | flex/grid 子ではないが、dialog 内の shrink safeguard の可能性。 | 320px 幅でラベル・入力の横 overflow を比較。 |
| `.edit-datetime-field input[type="time"]` | `min-width` | `0` | 約 L615-L621 | 同上 | 同上 | C | 同上。 | 同上。 |
| `.edit-event-form input, .edit-event-form select` | `min-height` | `2.6rem` | 約 L608-L613 | 編集ダイアログ内 input/select | `.form-control-base` padding と `.button-base` 高さに近い | C | form control 共有クラスは min-height を持たず、date/time の native UI と相互作用する。削除は編集ダイアログ全体の密度変更。 | 編集ダイアログで note/pain/medication 各種編集を開き、高さ・タップ領域を比較。 |
| `.edit-event-form input, .edit-event-form select` | `padding-top` | `0.55rem` | 約 L608-L613 | 同上 | `.form-control-base` の `padding:12px` と相互作用 | C | longhand が shorthand を後続上書き。削除すると上下 padding が 12px に戻る。視覚差がある可能性。 | 編集ダイアログの input/select 高さと文字の垂直位置を比較。 |
| `.edit-event-form input, .edit-event-form select` | `padding-bottom` | `0.55rem` | 約 L608-L613 | 同上 | 同上 | C | 同上。 | 同上。 |
| `.column-short-label input` | `min-width` | `0` | 約 L1130-L1139 | 短縮名 input。`form-control-base form-control-compact` | `.form-control-compact` も `min-width:0` | C | 同じ値だが、selector は flex 子 input の component responsibility を明示。削除安全性より意図の確認が必要。 | 320px portrait 幅で列エディタを開き、短縮名入力と上下/削除ボタンの折り返しを比較。 |
| `.medication-toggle-button, .pain-state-toggle-button` | `margin` | `0` | 約 L818-L825 | 設定 toggle。`button-base button-compact secondary-button ...` | `.button-compact` と同値 | C | 一括で compact より小さい toggle 寸法を定義しており、component responsibility として残す可能性。 | 設定リストで表示/非表示ボタンの行高と位置を一時削除前後で比較。 |
| `.medication-toggle-button, .pain-state-toggle-button` | `width` | `auto` | 約 L818-L825 | 同上 | `.button-compact` と同値 | C | 同上。 | 同上。 |
| `.file-action-label` | `width` | `100%` | 約 L925-L933 | HeartWatch CSV label。`file-action-label button-base button-full primary-button` | `.button-full` と同値 | C | label は button ではなく、inline-flex と width の関係を computed style なしで断定不可。component responsibility として保持の可能性。 | HeartWatch CSV 読み込み label の横幅とタップ領域を 320px/390px 幅で比較。 |
| `.visit-summary-actions button` | `margin` | `0` | 約 L839-L843 | サマリー/Health history action。`button-base button-full secondary-button` | action-container rules が button margin を reset | C | `.button-full` の margin ではなく container flex gap との相互作用。全幅 button と flex basis の関係確認が必要。 | 診察用サマリー実行後と HealthWatch CSV 読込後の action button の折り返し・隙間を比較。 |
| `.visit-summary-actions button` | `min-height` | `44px` | 約 L839-L843 | 同上 | `.button-base` は 48px | C | 重複ではなく上書きだが、touch target と密度の意図確認が必要。 | 44px と 48px の差で portrait 幅の表示密度と押しやすさを確認。 |
| `.column-reorder-button, .column-remove-button.delete-event-button` | `font-size` | `1rem` | 約 L1149-L1152 | 列エディタ icon buttons | `.button-icon` 固定寸法内で glyph size を調整 | C | 削除すると `.delete-event-button` の 1.2rem やブラウザ既定に戻る。重複ではないが refactor 後に責任確認が必要。 | 列エディタの ↑/↓/× glyph の中央揃えと見え方を比較。 |
| `.edit-event-button` | `font-size` | `1.1rem` | 約 L530-L534 | 編集アイコン。`button-icon secondary-button edit-event-button` | icon button 固定寸法と重なる可能性 | C | 固定 2rem icon button 内の glyph サイズ責任。削除で edit glyph の見た目が変わる。 | 記録一覧・設定リストの ✎ アイコンサイズを比較。 |
| `.delete-event-button` | `font-size` | `1.2rem` | 約 L538-L542 | 削除アイコン。`button-icon danger delete-event-button` | icon button 固定寸法と重なる可能性 | C | × glyph の視認性調整。列削除では別 selector が 1rem に戻している。 | 記録一覧/期間一覧/列エディタの × サイズを比較。 |

## 6. 未使用セレクタ

未使用または到達不能として分類できる selector は 0 件。

検索方法:

- `docs/index.html` で静的 class/id を検索した。
- `docs/app.js` で `className = ...`、template literal 内 class、`classList.add/remove`、runtime state class、`body.health-history-print-mode` を検索した。
- `tests/test_app_js.py` で refactor 後の class assignment アサーションを確認した。
- `docs/styles.css` 内で候補 selector と関連する疑似クラス、属性 selector、media/print rule を検索した。

主な確認結果:

| セレクタ | 結論 | 静的 / 動的確認 |
| --- | --- | --- |
| `.button-list button` | 使用中 | `docs/index.html` の `#medication-buttons.button-list` に対し、`docs/app.js` が薬ボタンを動的生成するため到達可能。 |
| `.visually-hidden-file-input` | 使用中 | 初回復元、管理画面 import、HeartWatch CSV input に静的付与。 |
| `.file-action-label` | 使用中 | HeartWatch CSV label に静的付与。 |
| `body.health-history-print-mode ...` | 使用中 | `showHealthHistoryPrint()` が `document.body.classList.add('health-history-print-mode')` を実行。 |
| `.column-remove-button.delete-event-button` | 使用中 | 表示項目エディタの削除ボタンに動的付与。 |
| `.history-detail-button`, `.history-nav-button` | 使用中 | 履歴描画で動的付与。 |
| `.medication-toggle-button`, `.pain-state-toggle-button` | 使用中 | 設定リスト描画で動的付与。 |

## 7. 削除実装PRの推奨範囲

### すぐに削除できる最小 PR

最初の cleanup PR は、section 3 と完全に一致する次の 17 宣言だけを対象にするのが安全。ここには C 分類の宣言を含めない。

- `.history-detail-button` の `margin`, `min-height`, `padding`, `width`
- `.history-nav-button` の `margin`, `min-height`, `padding`, `width`
- `.edit-event-button:active` の `background`
- `.delete-event-button:active` の `background`
- `.checkbox-row .checkbox-control` の `width`
- `.radio-row .radio-control` の `width`
- `.column-reorder-button` の `background`, `border`, `color`, `font-weight`
- `.column-reorder-button:active` の `background`

この PR では新しい抽象化、class rename、selector redesign、HTML 変更、JavaScript 変更は行わない。

### 最初の cleanup PR から外す候補

- date/time input 関連の重複に見える宣言
- `.edit-event-form input, .edit-event-form select` の高さ・padding
- `.file-action-label` の `width`
- `.visit-summary-actions button` の `margin`, `min-height`（`flex` は B 分類として維持）
- `.medication-toggle-button`, `.pain-state-toggle-button` の一括寸法定義
- `.column-short-label input` の `min-width`
- icon button の `font-size` 調整

### 実機確認後に再検討できる候補

- iPhone Safari で date/time input の幅・見た目が変わらないことを確認できた場合の `.edit-datetime-field input[type="date/time"]` の重複指定。
- 狭幅 portrait で表示項目エディタが崩れないことを確認できた場合の `.column-short-label input { min-width: 0; }`。
- HeartWatch CSV label が全幅 clickable のままであることを確認できた場合の `.file-action-label { width: 100%; }`。
- 診察用サマリー/Health history action の折り返しが維持されることを確認できた場合の action button margin/min-height。

## 8. 実装時の確認項目

- [ ] light mode で通常ボタン、primary/secondary/danger、フォーム入力の見た目を確認する。
- [ ] dark mode で primary/secondary/danger active 状態と入力枠を確認する。
- [ ] iPhone portrait 相当幅（320px〜390px）で記録入力、履歴、管理画面、列エディタを確認する。
- [ ] 記録編集ダイアログで日付、時刻、痛み、服薬、メモ編集を確認する。
- [ ] 履歴ナビゲーションの「詳細/閉じる」「新しい記録」「古い記録」を確認する。
- [ ] configurable-column editor の短縮名入力、上下移動、削除、checkbox を確認する。
- [ ] medication settings と pain-state settings の編集 icon と表示/非表示 toggle を確認する。
- [ ] visit-summary buttons と Health history action buttons の折り返しを確認する。
- [ ] HeartWatch file selection label が全幅でタップ可能なことを確認する。
- [ ] print view で Health history print mode の表示/非表示と横 overflow を確認する。

## 9. 対象外

この監査および後続の最小 cleanup PR では、次を対象外とする。

- visual redesign
- spacing improvements
- typography changes
- new CSS utility classes
- class renaming
- HTML restructuring
- JavaScript behavior changes
- localStorage or data-format changes
- documentation changes outside the audit file
