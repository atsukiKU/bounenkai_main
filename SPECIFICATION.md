# ランダムグループ分けアプリ 仕様書 📝

## 概要
- 目的: 未割当の名簿から人を均等に複数グループへ割り当てる GUI アプリケーション。割当時にルーレット風の演出を表示し、ユーザーが停止操作で割当を決定できる。
- 技術スタック: Python 3.x, Tkinter（UI）、標準ライブラリのみ想定（将来的に拡張可）

---

## 目標（Goal） ✅
- 保守性・テスト容易性を高めるため、**ロジック（モデル）と UI（ビュー/コントローラ）を明確に分離**する。
- 依存注入と抽象化により、`tkinter.after` 等の非同期タイミングをテスト可能にする。
- アクセシビリティ（大きなフォント、キーボード操作、良好なコントラスト）を備える。

## 非ゴール（Out of scope） ⚠️
- ネットワーク同期・リアルタイムの複数端末対応
- データベース永続化（ただし将来の差分のみ設計に留意）

---

## 要件
### 機能要件（必須）
1. 名簿（`PEOPLE`）を表示し、未割当は横スクロール可能なボタン群で表現する。  
2. ユーザーがボタンをクリックすると、その人がルーレット演出によりグループへ割当される。  
3. `Start Auto` をクリックすると名簿順に自動で割当を行う（各人ごとにルーレットを再生）。  
4. `Stop`（および Space / s / S / Ctrl+S / Esc キー）でルーレット停止を要求できる。  
5. 割当先は常に最小メンバー数のグループからランダムで選ぶ（負荷分散）。
6. 特定の名前（`SPECIAL_PERSON`）は画像で表示できる（画像が無ければテキスト）。

### 非機能要件
- UI の目視認性: 大きめフォントと色分け、コントラスト配慮
- テスト可能性: 非同期処理は抽象化してユニットテスト可能
- エラー耐性: 画像が無い等のフォールバックを行う

---

## ドメインモデル
- People: list[str]
- Group: {
  - id: int
  - members: list[str]
}
- AppState: {
  - groups: list[Group]
  - unassigned: set[str]
  - flags: { is_busy, auto_assigning, roulette_running, stop_requested }
}

---

## アーキテクチャ提案
- package layout (推奨):
  - src/
    - __init__.py
    - model.py         # グループ分けロジック、選択アルゴリズム
    - scheduler.py     # after の抽象 (リアル or テスト用同期実装)
    - ui.py            # Tkinter を使う全 UI、イベントバインド
    - controller.py    # UI と model を繋ぐ Orchestrator
    - assets/          # 画像等
  - tests/
    - test_model.py
    - test_controller.py
    - test_ui_integration.py (軽量)
  - SPECIFICATION.md

---

## 主要コンポーネントと責務
### model.py
- choose_target(groups) -> int
- assign(groups, person, target_index) -> None
- is_unassigned(groups, person) -> bool
- get_unassigned(people, groups) -> list[str]

※ **純関数**で副作用を持たない実装を推奨（テスト容易性）

### scheduler.py
- インターフェース: Scheduler
  - call_after(ms: int, callback: Callable) -> CancelToken
  - cancel(token)
- 実装
  - TkScheduler: 内部で `tk.after` を使う
  - TestScheduler: 即時実行やプログラム的にステップ進行できるもの

### controller.py
- AppController クラス（モデルと UI の橋渡し）
- 責務
  - `start_auto()` / `stop_auto()` / `on_unassigned_click(person)`
  - `play_roulette(target_index, on_finish, preview_name)` を scheduler ベースで実行
  - 状態管理（is_busy, roulette_running, stop_requested）
  - 例外ハンドリングとリソース管理

### ui.py
- GroupPanel（View 部分）
- メインウィンドウの構築
- UI の初期化・更新メソッド（render 風に清潔に）
- キー、ボタンのイベントを Controller に委譲

---

## ルーレット演出の設計詳細
- 目的: 視覚的な「どのグループに止まるか？」の期待感を作ること
- 仕様
  - interval: 基本は 150ms／step だが可変にする（設定で変更可能）
  - start index: `(current_highlight + 1) % NUM_GROUPS` か 0
  - 毎 step:
    - controller は `highlight_group(idx)` を呼ぶ
    - preview widget があれば `pack(in_=container)` で移動
  - 停止ロジック:
    - ユーザーは `request_stop()` を呼ぶ (stop_requested = True)
    - 次に idx == target_index のタイミングで `on_finish(preview_widget)` を呼び、演出を終了する
  - cleanup: ボタン状態とフラグの復帰を保証

---

---

## 例: 主要関数シグネチャ（参考）
```py
# model.py
def choose_target(groups: list[list[str]]) -> int: ...

def assign(groups: list[list[str]], person: str, target: int) -> None: ...

# scheduler.py
class Scheduler(Protocol):
    def call_after(self, ms: int, callback: Callable) -> Any: ...
    def cancel(self, token: Any) -> None: ...

# controller.py
class AppController:
    def __init__(self, model, ui, scheduler: Scheduler): ...
    def play_roulette(self, target_index: int, on_finish: Callable, preview_name: Optional[str]): ...
    def request_stop(self) -> None: ...
    def start_auto(self) -> None: ...
```

---



## 拡張案（将来）💡
- 割当ルール（重み付け、スキップ、ペア固定）をプラグイン可能にする
- 結果のエクスポート（CSV / JSON）
- 複数プロファイル（異なる `PEOPLE` / `NUM_GROUPS`）の保存

---
その他要求事項

人数追加、テーブルの追加、写真の追加に柔軟であること
ルーレット開始やストップなど、段階がきちんと分かれていてバグが出にくい設計にすること。

---
