"""
ランダムグループ分けアプリ
実行: python main.py

要点:
- 人名リストとグループ数はコード内の定数で制御可能
- UI をアクセシビリティ優先に刷新（大きなボタン、見やすい配色、キーボード操作）
- グループ区画は `GroupPanel` クラスでカプセル化しメンテナンス性を向上
- Tkinter の after() を用いて非同期的にルーレット演出を実装

公開関数:
- create_ui()
- highlight_group(index)
- clear_highlight()
- play_roulette(target_index, on_finish, preview_name=None)
- assign_person(person_name)
"""

import os
import random
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

# 設定（固定）
PEOPLE = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]  # 13人のサンプル名簿
NUM_GROUPS = 4  # m


# 画像表示を行う対象の名前（ここを変えれば別の人を画像表示にできます）
SPECIAL_PERSON = "A"  # 例: 'A' を猫画像に置き換える


# UI 設定（アクセシビリティ優先のデフォルト）
HIGHLIGHT_BG = "#fff59d"  # 優しい黄色
GROUP_BG = "#f5f5f5"
PANEL_PADDING = 12
UNASSIGNED_BTN_PADX = 10
UNASSIGNED_BTN_PADY = 8
UNASSIGNED_BTN_IPAD = 12


class GroupPanel:
    """グループ区画の UI をカプセル化するヘルパクラス。"""

    def __init__(self, parent, title: str, padding: int = PANEL_PADDING, background: str = GROUP_BG):
        self.frame = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=2, padding=padding, style="Group.TFrame")
        self.title = ttk.Label(self.frame, text=title, font=(None, 12, "bold"))
        self.title.pack()
        self.members_container = ttk.Frame(self.frame)
        self.members_container.pack(expand=True, fill=tk.BOTH, pady=(8, 0))

    def highlight(self):
        try:
            self.frame.config(style="Highlighted.TFrame")
        except Exception:
            self.frame.config(background=HIGHLIGHT_BG)

    def clear_highlight(self):
        try:
            self.frame.config(style="Group.TFrame")
        except Exception:
            self.frame.config(background=GROUP_BG)

    def add_member_label(self, name: str, image=None):
        if image is not None:
            label = ttk.Label(self.members_container, image=image)
            label.image = image
            label.pack(anchor="center", pady=4)
        else:
            label = ttk.Label(self.members_container, text=name, justify=tk.LEFT, anchor="w")
            label.pack(anchor="w")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ランダムグループ分け（最小実装）")

        # グループデータ: 各グループは名前リストを持つ
        self.groups = [[] for _ in range(NUM_GROUPS)]

        # UI要素格納: GroupPanel オブジェクトを格納する
        self.group_panels = []  # list of GroupPanel

        # 現在ハイライト中のインデックス
        self.current_highlight = None

        # 人名処理インデックス
        self.person_index = 0

        # リソースとスタイル・フォントを初期化
        self.cat_image = self.load_image("cat.png", desired_w=100, desired_h=100)
        # 小さいサムネイルも作る（未割当用）
        self.small_images = {}
        small = self.load_image("cat.png", desired_w=72, desired_h=72)
        if small is not None:
            self.small_images[SPECIAL_PERSON] = small

        self.setup_fonts()
        self.setup_styles()

        # UI 作成
        self.create_ui()

        # 未割当メンバー UI 初期化
        self.unassigned_buttons = {}
        self.is_busy = False  # 他の演出と競合しないようロック
        self.create_unassigned_ui()

    def create_ui(self):
        """画面を構築し、各グループ区画を作る"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Group パネルを作成
        self.group_panels = self.create_group_panels(main_frame)
        # 各列が均等に広がるようにする
        for i in range(NUM_GROUPS):
            main_frame.columnconfigure(i, weight=1)

        # 下部：コントロール群を作成
        self.create_controls_ui()

    # ---- Helper / refactor methods ----
    def load_image(self, path, desired_w=100, desired_h=100):
        """Load an image with subsampling to roughly fit desired sizes. Returns PhotoImage or None.

        - ファイルが存在しない場合は None を返す
        - 読み込みに失敗しても None を返す
        """
        try:
            if not os.path.exists(path):
                return None
            img = tk.PhotoImage(file=path)
            iw, ih = img.width(), img.height()
            factor = max(1, int(max(iw / desired_w, ih / desired_h)))
            if factor > 1:
                img = img.subsample(factor, factor)
            return img
        except Exception:
            return None

    def setup_fonts(self):
        """Create font objects used throughout the UI."""
        # 未割当を大きめに、プレビュー・メンバー名も大きめに設定
        self.unassigned_font = tkfont.Font(size=18, weight="bold")
        self.preview_font = tkfont.Font(size=20, weight="bold")
        self.member_font = tkfont.Font(size=18)
        # ストップボタン用の大きめフォント
        self.stop_font = tkfont.Font(size=18, weight="bold")

    def setup_styles(self):
        """Configure ttk styles. Call after root exists."""
        style = ttk.Style(self.root)
        style.configure("Highlighted.TFrame", background=HIGHLIGHT_BG)
        style.configure("Group.TFrame", background=GROUP_BG)
        style.configure("TFrame", background=GROUP_BG)

    def choose_target(self):
        """Return an index of a group chosen to keep groups balanced."""
        sizes = [len(g) for g in self.groups]
        min_size = min(sizes)
        candidates = [i for i, s in enumerate(sizes) if s == min_size]
        return random.choice(candidates)

    # ---- UI helper methods (refactor targets) ----
    def create_group_panels(self, parent):
        """Create and return a list of GroupPanel instances attached to parent."""
        panels = []
        for i in range(NUM_GROUPS):
            gp = GroupPanel(parent, f"Group {i+1}", padding=PANEL_PADDING, background=GROUP_BG)
            gp.frame.grid(row=0, column=i, padx=10, pady=10, sticky=tk.NSEW)
            panels.append(gp)
        return panels

    def create_controls_ui(self):
        """Create the bottom control area (unassigned list and action buttons)."""
        self.controls_frame = ttk.Frame(self.root, padding=8)
        self.controls_frame.pack(fill=tk.X, pady=(10, 0))
        lbl = ttk.Label(self.controls_frame, text="Unassigned:", font=(None, 12, "bold"))
        lbl.pack(side=tk.LEFT, anchor="w")
        # ユーザに操作方法を示すヘルプラベル
        info = ttk.Label(self.controls_frame, text="(Stop: Space / S / Esc)", font=(None, 10))
        info.pack(side=tk.LEFT, anchor="w", padx=(8, 0))

        # 未割当リストはスクロール可能にして固定高さを確保（Start/Stop が隠れないように）
        self.unassigned_container_frame = ttk.Frame(self.controls_frame)
        self.unassigned_container_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # Canvas を使って横スクロール可能にする（ボタン多数時は横スクロール）
        self.unassigned_canvas = tk.Canvas(self.unassigned_container_frame, height=120, highlightthickness=0)
        self.unassigned_scrollbar = ttk.Scrollbar(self.unassigned_container_frame, orient='horizontal', command=self.unassigned_canvas.xview)
        self.unassigned_canvas.configure(xscrollcommand=self.unassigned_scrollbar.set)
        self.unassigned_canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        self.unassigned_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        # 内側のフレームを作り、そこにボタンを配置する
        self.unassigned_inner = ttk.Frame(self.unassigned_canvas)
        self.unassigned_canvas.create_window((0, 0), window=self.unassigned_inner, anchor='nw')
        # inner のサイズ変化でスクロール領域を更新
        try:
            self.unassigned_inner.bind('<Configure>', lambda e: self.unassigned_canvas.configure(scrollregion=self.unassigned_canvas.bbox('all')))
        except Exception:
            pass

        btn_frame = ttk.Frame(self.controls_frame)
        btn_frame.pack(side=tk.RIGHT)

        self.start_auto_btn = tk.Button(btn_frame, text="Start Auto", command=self.start_assignments, font=self.stop_font, bg="#2e7d32", fg="white", width=12)
        self.start_auto_btn.pack(side=tk.RIGHT, padx=8, pady=4)

        self.stop_button = tk.Button(btn_frame, text="Stop", command=self.request_stop, font=self.stop_font, bg="#b71c1c", fg="white", width=12, bd=3, relief='raised', highlightthickness=2)
        self.stop_button.pack(side=tk.RIGHT, padx=8, pady=4)

        # 初期は無効化しておく（見えるようにするが押せない）
        try:
            self.stop_button.configure(state='disabled')
        except Exception:
            pass

        # レイアウトの更新を強制してボタンが表示されることを確実にする
        try:
            self.root.update_idletasks()
        except Exception:
            pass

        # キーボードショートカットで停止できるようにする（Space/S/Ctrl+S/Esc）
        self.root.bind_all('<space>', lambda e: self.request_stop())
        self.root.bind_all('<s>', lambda e: self.request_stop())
        self.root.bind_all('<S>', lambda e: self.request_stop())
        self.root.bind_all('<Control-s>', lambda e: self.request_stop())
        self.root.bind_all('<Escape>', lambda e: self.request_stop())

    def create_preview_widget(self, preview_name):
        """Create and return a preview widget (label or image) or None."""
        if preview_name is None:
            return None
        if preview_name == SPECIAL_PERSON and self.cat_image is not None:
            preview_widget = tk.Label(self.root, image=self.cat_image)
            preview_widget.image = self.cat_image
        else:
            preview_widget = tk.Label(self.root, text=preview_name, foreground="#1565c0", font=self.preview_font)
        self._preview_widget = preview_widget
        return preview_widget

    def update_unassigned_scroll(self):
        """Update the scrollregion of the unassigned canvas to fit its contents."""
        if getattr(self, 'unassigned_canvas', None) is None:
            return
        try:
            self.unassigned_inner.update_idletasks()
            self.unassigned_canvas.configure(scrollregion=self.unassigned_canvas.bbox("all"))
        except Exception:
            pass

    def create_unassigned_button(self, person):
        """Create and return a button widget for an unassigned person."""
        parent = getattr(self, 'unassigned_inner', getattr(self, 'unassigned_list_container', self.controls_frame))
        if person in self.small_images:
            img = self.small_images[person]
            btn = tk.Button(parent, text=person, image=img, compound='top', command=lambda p=person: self.on_unassigned_click(p), font=self.unassigned_font)
            btn.image = img
        else:
            btn = tk.Button(parent, text=person, command=lambda p=person: self.on_unassigned_click(p), font=self.unassigned_font)
        btn.pack(side=tk.LEFT, padx=UNASSIGNED_BTN_PADX, pady=UNASSIGNED_BTN_PADY, ipadx=UNASSIGNED_BTN_IPAD, ipady=6)
        # update scroll region when new button is added
        try:
            self.update_unassigned_scroll()
        except Exception:
            pass
        return btn

    def set_unassigned_buttons_enabled(self, enabled: bool):
        """Enable or disable all unassigned buttons."""
        state = 'normal' if enabled else 'disabled'
        for btn in self.unassigned_buttons.values():
            try:
                btn.configure(state=state)
            except Exception:
                pass

    def request_stop(self):
        """User requested to stop the roulette early."""
        if not getattr(self, 'roulette_running', False):
            return
        # If currently highlighted is the target, finish immediately
        if self.current_highlight is not None and getattr(self, '_roulette_target', None) == self.current_highlight:
            try:
                self._on_finish(self._preview_widget)
            finally:
                self._end_roulette_cleanup()
            return

        # Signal the running roulette to stop at the next time it reaches target
        self.stop_requested = True
        # Give immediate visual feedback and prevent repeated presses
        try:
            self.stop_button.configure(state='disabled', text='Stopping...')
            self.stop_button.update_idletasks()
        except Exception:
            pass

    def _end_roulette_cleanup(self):
        """Cleanup after roulette stops: re-enable buttons and clear flags."""
        self.roulette_running = False
        self.stop_requested = False
        self.is_busy = False
        # 再度未割当ボタンを有効化
        self.set_unassigned_buttons_enabled(True)
        # stop button 無効化して文言を戻す
        try:
            self.stop_button.configure(state='disabled', text='Stop')
        except Exception:
            pass
        # 自動割当ボタンを再度有効化
        try:
            self.start_auto_btn.configure(state='normal')
        except Exception:
            pass

    def highlight_group(self, index):
        """指定したグループ区画をハイライト（背景色を変更）"""
        self.clear_highlight()
        self.group_panels[index].highlight()
        self.current_highlight = index

    def clear_highlight(self):
        """すべてのハイライトを解除してデフォルトに戻す"""
        for gp in self.group_panels:
            gp.clear_highlight()
        self.current_highlight = None

    def play_roulette(self, target_index, on_finish, preview_name=None):
        """
        ルーレット演出を行い、最後に target_index で停止して on_finish を呼ぶ
        - target_index は演出開始前に決めて渡される（ロジックと分離）
        - preview_name を渡すと、名前（または画像）をハイライトに合わせて移動させる
        - non-blocking: after() を用いる
        """
        interval = 150  # ms（点滅間隔）

        # mark roulette running and disable unassigned buttons; stop button remains enabled
        self.roulette_running = True
        self.stop_requested = False
        self._roulette_target = target_index
        self._on_finish = on_finish
        self._preview_widget = None
        self.set_unassigned_buttons_enabled(False)
        # 自動割当ボタンを無効化しておく
        try:
            self.start_auto_btn.configure(state='disabled')
        except Exception:
            pass
        # ensure stop button is enabled (user must click to stop)
        try:
            self.stop_button.configure(state='normal', text='Stop', relief='raised')
            self.stop_button.lift()
            self.root.update_idletasks()
            # optionally set focus to button for keyboard accessibility
            try:
                self.stop_button.focus_set()
            except Exception:
                pass
        except Exception:
            pass
        self.is_busy = True

        # 準備: プレビュー用ウィジェットを作成（必要時）
        preview_widget = self.create_preview_widget(preview_name)
        # 最初はどこにも配置しない（各ステップで移動して表示する）

        # 開始位置は現在のハイライトの次（ランダムでもOK）
        start = (self.current_highlight + 1) if (self.current_highlight is not None) else 0

        step = 0

        def step_fn():
            nonlocal step
            idx = (start + step) % NUM_GROUPS
            # ハイライトとプレビュー移動を同期
            self.highlight_group(idx)
            if preview_widget is not None:
                try:
                    # preview_widget を現在のグループのメンバーコンテナ内に移動
                    preview_widget.pack_forget()
                    container = self.group_panels[idx].members_container
                    # pack into the container; in_ parameter ensures correct parent
                    preview_widget.pack(in_=container, anchor="center", pady=4)
                except Exception:
                    # 何か問題があってもスキップ
                    pass

            # 停止要求が出ていて、かつ現在のインデックスが目標なら停止させる
            if getattr(self, 'stop_requested', False) and idx == self._roulette_target:
                try:
                    on_finish(preview_widget)
                finally:
                    # cleanup
                    self._end_roulette_cleanup()
                return

            # 継続してループ
            step += 1
            self.root.after(interval, step_fn)

        # 演出開始
        step_fn()

    def assign_person(self, person_name, preview_widget=None):
        """決定したグループに名前を追加して UI を更新する

        preview_widget が与えられた場合はそれを恒久表示に変換し、与えられない場合は新規にウィジェットを作る
        """
        # target_index は事前に決定しているため、この関数は単に追加処理を行う
        # (呼び出し元が適切に target を決める)
        # 実装上は直前に current_highlight が最終グループになっている
        if self.current_highlight is None:
            # safety fallback: ランダム
            target = random.randrange(NUM_GROUPS)
        else:
            target = self.current_highlight

        self.groups[target].append(person_name)
        # 表示を更新（GroupPanel を通して追加）
        panel = self.group_panels[target]

        if preview_widget is not None:
            try:
                preview_widget.pack_forget()
                if person_name == SPECIAL_PERSON and self.cat_image is not None:
                    preview_widget.config(image=self.cat_image)
                    preview_widget.image = self.cat_image
                    preview_widget.pack(in_=panel.members_container, anchor="center", pady=4)
                else:
                    preview_widget.config(text=person_name, image="")
                    preview_widget.pack(in_=panel.members_container, anchor="w")
            except Exception:
                # フォールバック: GroupPanel のヘルパで追加
                panel.add_member_label(person_name, image=(self.cat_image if person_name == SPECIAL_PERSON else None))
        else:
            panel.add_member_label(person_name, image=(self.cat_image if person_name == SPECIAL_PERSON else None))

        # 未割当 UI を更新してスクロール領域も調整
        try:
            self.create_unassigned_ui()
            self.update_unassigned_scroll()
        except Exception:
            pass

    def start_assignments(self):
        """名簿に沿って順次、割当処理を行う。非ブロッキングで次に進む。"""
        # 再入防止
        if getattr(self, 'auto_assigning', False) or self.is_busy:
            return
        self.auto_assigning = True
        try:
            self.start_auto_btn.configure(state='disabled')
        except Exception:
            pass

        self.person_index = 0

        def process_next():
            if self.person_index >= len(PEOPLE):
                # 全員完了
                self.auto_assigning = False
                try:
                    self.start_auto_btn.configure(state='normal')
                except Exception:
                    pass
                return

            person = PEOPLE[self.person_index]
            # 事前に均等になるよう割当先を決める
            target = self.choose_target()

            # 演出を再生してから確定処理を行う
            def on_finish(preview_widget=None):
                # preview_widget が渡されればそれを恒久化して使う
                self.assign_person(person, preview_widget)
                self.person_index += 1
                # 次の人は少し遅らせて開始（見やすさのため）
                self.root.after(250, process_next)

            self.play_roulette(target, on_finish, preview_name=person)

        process_next()

    def create_unassigned_ui(self):
        """未割当メンバーのボタンを作成する"""
        # container がある場合はそちらを使う（スクロール領域）
        container = getattr(self, 'unassigned_inner', getattr(self, 'unassigned_list_container', None))
        if container is None:
            return
        # 既存のボタンを片付ける
        for child in container.winfo_children():
            child.destroy()
        self.unassigned_buttons = {}

        for person in PEOPLE:
            # 未割当の人だけボタン化する
            if any(person in g for g in self.groups):
                continue
            btn = self.create_unassigned_button(person)
            self.unassigned_buttons[person] = btn
        # スクロール領域を更新
        try:
            self.update_unassigned_scroll()
        except Exception:
            pass

    def on_unassigned_click(self, person):
        """未割当の名前がクリックされたときに呼ばれる。ルーレットを開始する"""
        if self.is_busy:
            return
        if person not in self.unassigned_buttons:
            return
        # ロック
        self.is_busy = True
        btn = self.unassigned_buttons[person]
        try:
            btn.state(['disabled'])
        except Exception:
            pass

        # 事前に均等になるよう割当先を決める
        target = self.choose_target()

        def on_finish(preview_widget=None):
            self.assign_person(person, preview_widget)
            # ボタンを削除
            try:
                btn.destroy()
                del self.unassigned_buttons[person]
            except Exception:
                pass
            # UI を最新化
            try:
                self.create_unassigned_ui()
            except Exception:
                pass
            # アンロック
            self.is_busy = False

        self.play_roulette(target, on_finish, preview_name=person)


# ---- Top-level wrappers: 要件で指定された関数名をトップレベルでも提供 ----
_app_instance = None

def create_ui():
    global _app_instance
    if _app_instance is None:
        root = tk.Tk()
        # ウィンドウを画面いっぱいに最大化（Windows の場合）
        try:
            root.state('zoomed')
        except Exception:
            # フォールバックで画面サイズを取得して設定
            w, h = root.winfo_screenwidth(), root.winfo_screenheight()
            root.geometry(f"{w}x{h}")

        _app_instance = App(root)
        return root

def highlight_group(index):
    if _app_instance:
        _app_instance.highlight_group(index)

def clear_highlight():
    if _app_instance:
        _app_instance.clear_highlight()

def play_roulette(target_index, on_finish, preview_name=None):
    if _app_instance:
        _app_instance.play_roulette(target_index, on_finish, preview_name)

def assign_person(person_name):
    if _app_instance:
        _app_instance.assign_person(person_name)


# エントリポイント
if __name__ == "__main__":
    root = create_ui()
    # Tk mainloop（ウィンドウは処理完了後も表示し続ける）
    root.mainloop()
