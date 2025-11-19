import argparse
import math
import random
import sys
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, List, Optional, Sequence, Tuple


DEFAULT_COLORS = [
    '#FFE1E1',
    '#FFF5CC',
    '#E2F4FF',
    '#DFF8E1',
    '#F7E2FF',
    '#FFF0E6',
    '#E6F8FF',
    '#FDEBFF',
    '#FFFAE2',
    '#E9FFF5',
]

DEFAULT_MESSAGES = [
    '我想你了',
    '多晒晒太阳',
    '多喝水哦',
    '保持微笑呀',
    '有我在呢',
    '加油你最棒',
    '慢慢来会好的',
    '记得吃早餐',
    '保持热爱',
    '小确幸正在路上',
    '不许熬夜',
    '早点休息呀',
    '好心情要常在',
    '开心每一天',
    '要对自己好一点',
    '记得吃午饭',
    '给自己一个拥抱',
    '相信好事正在发生',
    '笑一笑吧',
    '愿你所想皆成真',
    '今天也要元气满满',
]


NOTE_SHADOW_COLOR = '#FFC1CC'
NOTE_SHADOW_ALPHA = 0.22
NOTE_GLOW_PADDING = 18
FADE_INTERVAL_MS = 20 # Smoother fade
FADE_IN_DURATION_MS = 500 # Total duration for a note to fade in


def load_messages(messages_path: Optional[str]) -> List[str]:
    if messages_path:
        try:
            with open(messages_path, 'r', encoding='utf-8') as message_file:
                lines = [line.strip() for line in message_file if line.strip()]
            if lines:
                return lines
        except OSError as exc:
            print(f'无法读取消息文件: {exc}', file=sys.stderr)
    return DEFAULT_MESSAGES.copy()


def lighten_color(hex_color: str, factor: float = 0.25) -> str:
    color = hex_color.lstrip('#')
    if len(color) != 6:
        return '#F0F0F0'
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    red = min(255, int(red + (255 - red) * factor))
    green = min(255, int(green + (255 - green) * factor))
    blue = min(255, int(blue + (255 - blue) * factor))
    return f'#{red:02X}{green:02X}{blue:02X}'


def create_shadow_window(
    master: tk.Misc,
    padding: int,
    alpha: float,
) -> Optional[tk.Toplevel]:
    try:
        shadow = tk.Toplevel(master)
        shadow.withdraw()
        shadow.overrideredirect(True)
        shadow.attributes('-alpha', alpha)
        shadow.attributes('-topmost', False)
        canvas = tk.Canvas(shadow, highlightthickness=0, bd=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        shadow._canvas = canvas  # type: ignore[attr-defined]
        return shadow
    except tk.TclError:
        return None


def update_shadow_geometry(
    shadow: Optional[tk.Toplevel],
    target: tk.Toplevel,
    padding: int,
    fill_color: str,
) -> None:
    if shadow is None or not shadow.winfo_exists():
        return
    width = target.winfo_width()
    height = target.winfo_height()
    x_pos = target.winfo_x() - padding
    y_pos = target.winfo_y() - padding
    shadow.geometry(f'{width + padding * 2}x{height + padding * 2}+{x_pos}+{y_pos}')
    canvas: tk.Canvas = shadow._canvas  # type: ignore[attr-defined]
    canvas.configure(width=width + padding * 2, height=height + padding * 2)
    canvas.delete('all')
    canvas.create_oval(
        0,
        0,
        width + padding * 2,
        height + padding * 2,
        fill=fill_color,
        outline='',
    )


def draw_vertical_gradient(
    canvas: tk.Canvas,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    start_color: str,
    end_color: str,
    tag: str = 'gradient',
) -> None:
    steps = max(2, y1 - y0)
    start_rgb = int(start_color[1:3], 16), int(start_color[3:5], 16), int(start_color[5:7], 16)
    end_rgb = int(end_color[1:3], 16), int(end_color[3:5], 16), int(end_color[5:7], 16)
    canvas.delete(tag)
    for index in range(steps):
        ratio = index / (steps - 1)
        red = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
        green = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
        blue = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)
        color = f'#{red:02X}{green:02X}{blue:02X}'
        canvas.create_rectangle(
            x0,
            y0 + index,
            x1,
            y0 + index + 1,
            outline='',
            fill=color,
            tags=tag,
        )


class StickyNote(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        color: str,
        width: int,
        height: int,
        font_size: int,
        stay_on_top: bool,
        title_text: str,
        position: Tuple[int, int],
        on_close: Optional[Callable[['StickyNote'], None]] = None,
    ) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-alpha', 0.0)
        self.resizable(False, False)
        self.configure(bg=color)
        self.attributes('-topmost', stay_on_top)
        self._drag_origin: Optional[Tuple[int, int, int, int]] = None
        self._on_close = on_close
        self._shadow = create_shadow_window(self, padding=NOTE_GLOW_PADDING, alpha=0.0)

        title_color = lighten_color(color, 0.4)
        border_frame = tk.Frame(
            self,
            bg=color,
            bd=0,
            highlightthickness=1,
            highlightbackground=lighten_color(color, 0.25),
            highlightcolor=lighten_color(color, 0.25),
        )
        border_frame.pack(fill=tk.BOTH, expand=True)

        title_bar = tk.Frame(border_frame, bg=title_color, height=30)
        title_bar.pack(fill=tk.X, side=tk.TOP)

        title_label = tk.Label(
            title_bar,
            text=title_text,
            bg=title_color,
            fg='#3F3F3F',
            font=('Microsoft YaHei', 10, 'bold'),
        )
        title_label.pack(side=tk.LEFT, padx=(14, 0))

        close_button = tk.Label(
            title_bar,
            text='×',
            bg=title_color,
            fg='#555555',
            font=('Microsoft YaHei', 12, 'bold'),
            cursor='hand2',
        )
        close_button.pack(side=tk.RIGHT, padx=(0, 12))
        close_button.bind('<Button-1>', lambda _event: self.destroy())

        body_canvas = tk.Canvas(
            border_frame,
            bg=color,
            bd=0,
            highlightthickness=0,
        )
        body_canvas.pack(fill=tk.BOTH, expand=True, padx=18, pady=(14, 18))
        draw_vertical_gradient(
            body_canvas,
            0,
            0,
            width - 36,
            height - 50,
            start_color=lighten_color(color, 0.05),
            end_color=lighten_color(color, 0.25),
            tag='note-bg',
        )

        text_font = tkfont.Font(family='Microsoft YaHei', size=font_size)
        text_label = tk.Label(
            body_canvas,
            text=text,
            bg=color,
            fg='#2A2A2A',
            justify=tk.LEFT,
            anchor='nw',
            wraplength=width - 64,
            font=text_font,
        )
        body_canvas.create_window(10, 10, anchor='nw', window=text_label)

        for widget in (title_bar, title_label, body_canvas, text_label):
            widget.bind('<Button-1>', self._start_move)
            widget.bind('<B1-Motion>', self._drag_move)
            widget.bind('<ButtonRelease-1>', self._stop_move)

        text_label.bind('<Double-Button-1>', lambda _event: self.destroy())
        self.bind('<Escape>', lambda _event: self.destroy())

        x_pos, y_pos = position
        self.geometry(f'{width}x{height}+{x_pos}+{y_pos}')
        self.fade_in(FADE_IN_DURATION_MS, on_complete=self._lift_with_shadow)

    def destroy(self) -> None:
        if self._on_close is not None:
            callback = self._on_close
            self._on_close = None
            callback(self)
        if self._shadow is not None and self._shadow.winfo_exists():
            self._shadow.destroy()
        super().destroy()

    def _start_move(self, event: tk.Event) -> None:
        self._drag_origin = (event.x_root, event.y_root, self.winfo_x(), self.winfo_y())

    def _drag_move(self, event: tk.Event) -> None:
        if not self._drag_origin:
            return
        origin_x, origin_y, window_x, window_y = self._drag_origin
        delta_x = event.x_root - origin_x
        delta_y = event.y_root - origin_y
        new_x = window_x + delta_x
        new_y = window_y + delta_y
        self.geometry(f'+{new_x}+{new_y}')
        update_shadow_geometry(self._shadow, self, NOTE_GLOW_PADDING, NOTE_SHADOW_COLOR)

    def _stop_move(self, _event: tk.Event) -> None:
        self._drag_origin = None

    def _lift_with_shadow(self) -> None:
        update_shadow_geometry(self._shadow, self, NOTE_GLOW_PADDING, NOTE_SHADOW_COLOR)
        if self._shadow is not None and self._shadow.winfo_exists():
            self._shadow.lower()
        self.lift()

    def fade_in(self, duration_ms: int, on_complete: Optional[Callable[[], None]] = None) -> None:
        steps = max(1, duration_ms // FADE_INTERVAL_MS)
        increment = 1.0 / steps

        def step(index: int = 0) -> None:
            if not self.winfo_exists():
                if on_complete is not None:
                    on_complete()
                return

            new_alpha = min(1.0, (index + 1) * increment)
            self.attributes('-alpha', new_alpha)
            if self._shadow is not None and self._shadow.winfo_exists():
                self._shadow.attributes('-alpha', min(NOTE_SHADOW_ALPHA, new_alpha * NOTE_SHADOW_ALPHA))

            if new_alpha >= 1.0:
                if on_complete is not None:
                    on_complete()
            else:
                self.after(FADE_INTERVAL_MS, lambda: step(index + 1))
        
        step()

    def animate_spiral(
        self,
        center_x: int,
        center_y: int,
        duration_ms: int,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        if not self.winfo_exists():
            if on_complete:
                on_complete()
            return

        start_x, start_y = self.winfo_x(), self.winfo_y()
        start_radius = math.hypot(start_x - center_x, start_y - center_y)
        start_angle = math.atan2(start_y - center_y, start_x - center_x)
        
        total_rotations = 2.5
        steps = max(1, duration_ms // FADE_INTERVAL_MS)

        def ease_in_out_quad(t: float) -> float:
            return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2

        def step(index: int = 0) -> None:
            if not self.winfo_exists():
                if on_complete:
                    on_complete()
                return

            progress = (index + 1) / steps
            eased_progress = ease_in_out_quad(progress)

            current_radius = start_radius * (1 - eased_progress)
            current_angle = start_angle + total_rotations * 2 * math.pi * eased_progress
            
            new_x = center_x + current_radius * math.cos(current_angle)
            new_y = center_y + current_radius * math.sin(current_angle)
            self.geometry(f'+{int(new_x)}+{int(new_y)}')

            new_alpha = 1.0 - eased_progress
            self.attributes('-alpha', max(0.0, new_alpha))
            if self._shadow and self._shadow.winfo_exists():
                self._shadow.attributes('-alpha', max(0.0, new_alpha * NOTE_SHADOW_ALPHA))
                update_shadow_geometry(self._shadow, self, NOTE_GLOW_PADDING, NOTE_SHADOW_COLOR)

            if progress >= 1.0:
                if on_complete:
                    on_complete()
                self.destroy()
            else:
                self.after(FADE_INTERVAL_MS, lambda: step(index + 1))

        step()

    def animate_to_position(
        self,
        target_x: int,
        target_y: int,
        duration_ms: int,
        rotation_count: float = 2.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        if not self.winfo_exists():
            if on_complete:
                on_complete()
            return

        start_x, start_y = self.winfo_x(), self.winfo_y()
        steps = max(1, duration_ms // FADE_INTERVAL_MS)
        total_rotation = rotation_count * 360

        def ease_in_out_quad(t: float) -> float:
            return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2

        def step(index: int = 0) -> None:
            if not self.winfo_exists():
                if on_complete:
                    on_complete()
                return

            progress = (index + 1) / steps
            eased_progress = ease_in_out_quad(progress)

            new_x = start_x + (target_x - start_x) * eased_progress
            new_y = start_y + (target_y - start_y) * eased_progress
            
            # 更平滑的旋转效果：减小摆动幅度，使用渐弱的摆动
            rotation_angle = progress * total_rotation
            angle_rad = math.radians(rotation_angle)
            # 摆动幅度随进度递减，让动画更顺畅
            swing_factor = (1 - eased_progress) * 5  # 从5像素逐渐减小到0，更平滑
            offset_x = math.sin(angle_rad * 4) * swing_factor
            offset_y = math.cos(angle_rad * 4) * swing_factor
            
            self.geometry(f'+{int(new_x + offset_x)}+{int(new_y + offset_y)}')
            update_shadow_geometry(self._shadow, self, NOTE_GLOW_PADDING, NOTE_SHADOW_COLOR)

            if progress >= 1.0:
                self.geometry(f'+{int(target_x)}+{int(target_y)}')
                update_shadow_geometry(self._shadow, self, NOTE_GLOW_PADDING, NOTE_SHADOW_COLOR)
                if on_complete:
                    on_complete()
            else:
                self.after(FADE_INTERVAL_MS, lambda: step(index + 1))

        step()


def fade_in_widget(
    widget: tk.Toplevel,
    duration_ms: int,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    steps = max(1, duration_ms // FADE_INTERVAL_MS)
    increment = 1.0 / steps

    def step(index: int = 0) -> None:
        if not widget.winfo_exists():
            if on_complete is not None:
                on_complete()
            return

        new_alpha = min(1.0, (index + 1) * increment)
        widget.attributes('-alpha', new_alpha)

        if new_alpha >= 1.0:
            if on_complete is not None:
                on_complete()
        else:
            widget.after(FADE_INTERVAL_MS, lambda: step(index + 1))
    
    step()


def generate_positions(
    count: int,
    note_width: int,
    note_height: int,
    screen_width: int,
    screen_height: int,
) -> List[Tuple[int, int]]:
    if count <= 0:
        return []

    positions: List[Tuple[int, int]] = []
    
    # Estimate number of columns based on note width and some padding
    cols = max(1, int(screen_width / (note_width + 40)))
    rows = -(-count // cols)  # Ceiling division to get required rows
    
    cell_width = screen_width / cols
    cell_height = screen_height / rows

    for i in range(count):
        col = i % cols
        row = i // cols
        
        # Add some random jitter within the cell for a more natural look
        jitter_x = (cell_width - note_width) / 2
        jitter_y = (cell_height - note_height) / 2
        
        x = col * cell_width + random.uniform(-jitter_x, jitter_x) + jitter_x
        y = row * cell_height + random.uniform(-jitter_y, jitter_y) + jitter_y
        
        # Clamp values to ensure they stay within screen bounds
        x = max(NOTE_GLOW_PADDING, min(x, screen_width - note_width - NOTE_GLOW_PADDING))
        y = max(NOTE_GLOW_PADDING, min(y, screen_height - note_height - NOTE_GLOW_PADDING))
        
        positions.append((int(x), int(y)))
        
    random.shuffle(positions)  # Shuffle to make the appearance order non-linear
    return positions


def pick_messages(messages: Sequence[str], amount: int) -> List[str]:
    if not messages:
        return []
    chosen: List[str] = []
    for _ in range(amount):
        chosen.append(random.choice(messages))
    return chosen


def generate_heart_positions(
    count: int,
    screen_width: int,
    screen_height: int,
    note_width: int,
    note_height: int,
) -> List[Tuple[int, int]]:
    if count <= 0:
        return []
    
    positions: List[Tuple[int, int]] = []
    scale_x, scale_y = 25, 28
    offset_x = screen_width / 2
    offset_y = screen_height / 2 - 120
    
    for i in range(count):
        angle = (i / count) * 360
        rad = math.radians(angle)
        x = 16 * math.sin(rad) ** 3
        y = 13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad)
        
        pos_x = offset_x + x * scale_x - note_width / 2
        pos_y = offset_y - y * scale_y - note_height / 2
        
        pos_x = max(NOTE_GLOW_PADDING, min(pos_x, screen_width - note_width - NOTE_GLOW_PADDING))
        pos_y = max(NOTE_GLOW_PADDING, min(pos_y, screen_height - note_height - NOTE_GLOW_PADDING))
        
        positions.append((int(pos_x), int(pos_y)))
    
    return positions


class StickyWallApp:
    HEART_DELAY_MS = 250
    
    def __init__(
        self,
        root: tk.Tk,
        texts: Sequence[str],
        positions: Sequence[Tuple[int, int]],
        width: int,
        height: int,
        font_size: int,
        stay_on_top: bool,
        title_text: str,
        interval_ms: int,
    ) -> None:
        self.root = root
        self.texts = list(texts)
        self.positions = list(positions)
        self.width = width
        self.height = height
        self.font_size = font_size
        self.stay_on_top = stay_on_top
        self.title_text = title_text
        self.interval_ms = max(0, interval_ms)
        self._index = 0
        self._creation_cancelled = False
        self._merge_scheduled = False
        self._heart_shown = False

        self.sticky_notes: List[StickyNote] = []
        self._total = len(self.texts)

        if self._total == 0:
            self._schedule_merge()
        else:
            initial_delay = 150
            self.root.after(initial_delay, self._create_single_note)

    def _create_single_note(self) -> None:
        if self._creation_cancelled or self._index >= self._total:
            return

        note = StickyNote(
            master=self.root,
            text=self.texts[self._index],
            color=random.choice(DEFAULT_COLORS),
            width=self.width,
            height=self.height,
            font_size=self.font_size,
            stay_on_top=self.stay_on_top,
            title_text=self.title_text,
            position=self.positions[self._index],
            on_close=self._handle_note_close,
        )
        self.sticky_notes.append(note)
        self._index += 1

        if self._index >= self._total:
            # All notes have been created. Wait for the last one to fade in, then schedule the merge.
            self.root.after(FADE_IN_DURATION_MS, self._schedule_merge)
            return

        if self.interval_ms <= 0:
            self.root.after_idle(self._create_single_note)
        else:
            self.root.after(self.interval_ms, self._create_single_note)

    def _handle_note_close(self, note: 'StickyNote') -> None:
        if note in self.sticky_notes:
            self.sticky_notes.remove(note)
        
        # If all notes are closed (either by user or animation), schedule the merge.
        # The check `any(n.winfo_exists() for n in self.sticky_notes)` is crucial
        # to prevent rescheduling if the merge is already in progress.
        if not self._merge_scheduled and not any(n.winfo_exists() for n in self.sticky_notes):
            self._schedule_merge()

    def _schedule_merge(self) -> None:
        if self._merge_scheduled:
            return
        self._merge_scheduled = True
        # Stop any further note creation immediately
        self._creation_cancelled = True
        self.root.after(self.HEART_DELAY_MS, self._start_merge_animation)

    def _start_merge_animation(self) -> None:
        # Filter out notes that might have been closed by the user already
        active_notes = [note for note in self.sticky_notes if note.winfo_exists()]
        if not active_notes:
            self._show_merged_heart_note()
            return

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Generate heart positions for all active notes
        heart_positions = generate_heart_positions(
            count=len(active_notes),
            screen_width=screen_width,
            screen_height=screen_height,
            note_width=self.width,
            note_height=self.height,
        )

        remaining_animations = len(active_notes)

        def on_anim_complete() -> None:
            nonlocal remaining_animations
            remaining_animations -= 1
            if remaining_animations == 0:
                # All animations finished, show the final message after a delay
                self.root.after(500, self._show_merged_heart_note)

        # Animate each note to its heart position with rotation
        for i, note in enumerate(active_notes):
            target_x, target_y = heart_positions[i]
            # 每个便签旋转1.5-3圈
            rotation_count = 1.5 + random.random() * 1.5
            note.animate_to_position(target_x, target_y, 500, rotation_count, on_complete=on_anim_complete)

    def _show_merged_heart_note(self) -> None:
        if self._heart_shown:
            return
        self._heart_shown = True

        heart_window = tk.Toplevel(self.root)
        heart_window.overrideredirect(True)
        heart_window.attributes('-alpha', 0.0)
        heart_window.configure(bg='black')
        heart_window.attributes('-transparentcolor', 'black')
        heart_window.attributes('-topmost', self.stay_on_top)

        width, height = 600, 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_pos = (screen_width - width) // 2
        y_pos = (screen_height - height) // 2 - 100
        heart_window.geometry(f'{width}x{height}+{x_pos}+{y_pos}')

        canvas = tk.Canvas(heart_window, width=width, height=height, highlightthickness=0, bg='black')
        canvas.pack(fill=tk.BOTH, expand=True)

        heart_points = []
        scale_x, scale_y = 18, 20
        offset_x, offset_y = width / 2, 280
        
        for angle in range(0, 360, 1):
            rad = math.radians(angle)
            x = 16 * math.sin(rad) ** 3
            y = 13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad)
            heart_points.append((offset_x + x * scale_x, offset_y - y * scale_y))

        canvas.create_polygon(
            heart_points,
            fill='#FF6F92',
            outline='#FFC0CB',
            width=2,
            tags='heart_shape'
        )

        canvas.create_text(
            width / 2 + 2, 290 + 2,
            text='祝你天天开心', fill='#800000',
            font=('Microsoft YaHei', 30, 'bold'),
            tags='text_shadow'
        )
        canvas.create_text(
            width / 2, 290,
            text='祝你天天开心', fill='#FFFFFF',
            font=('Microsoft YaHei', 30, 'bold'),
            tags='main_text'
        )

        def close_and_quit() -> None:
            # Fade out and then quit
            def fade_out_and_destroy():
                steps = 10
                decrement = 1.0 / steps
                def step(count):
                    new_alpha = 1.0 - count * decrement
                    if new_alpha > 0:
                        heart_window.attributes('-alpha', new_alpha)
                        heart_window.after(20, lambda: step(count + 1))
                    else:
                        heart_window.destroy()
                        self.root.quit()
                step(0)
            
            # Start the fade out after a delay
            heart_window.after(1500, fade_out_and_destroy)

        fade_in_widget(heart_window, 500, on_complete=close_and_quit)


def main() -> None:
    parser = argparse.ArgumentParser(description='生成类似便签墙的桌面窗口')
    parser.add_argument('--messages', type=str, help='包含便签内容的文本文件，每行一条消息')
    parser.add_argument('--count', type=int, default=80, help='便签数量')
    parser.add_argument('--width', type=int, default=260, help='单个便签的宽度')
    parser.add_argument('--height', type=int, default=160, help='单个便签的高度')
    parser.add_argument('--font-size', type=int, default=16, help='便签正文的字号')
    parser.add_argument('--no-topmost', action='store_true', help='不要让便签保持置顶')
    parser.add_argument('--seed', type=int, help='指定随机种子以复现布局')
    parser.add_argument('--title', type=str, default='', help='便签标题栏文字')
    parser.add_argument('--interval', type=int, default=150, help='逐个显示便签的时间间隔（毫秒），0 表示立即显示')
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    messages = load_messages(args.messages)
    if not messages:
        print('缺少可用的便签内容。', file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    root.withdraw()

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    positions = generate_positions(
        count=args.count,
        note_width=args.width,
        note_height=args.height,
        screen_width=screen_width,
        screen_height=screen_height,
    )

    texts = pick_messages(messages, len(positions))

    StickyWallApp(
        root=root,
        texts=texts,
        positions=positions,
        width=args.width,
        height=args.height,
        font_size=args.font_size,
        stay_on_top=not args.no_topmost,
        title_text=args.title,
        interval_ms=args.interval,
    )

    root.mainloop()


if __name__ == '__main__':
    main()
