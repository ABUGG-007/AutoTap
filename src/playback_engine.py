"""
回放引擎模块。

提供操作序列的回放功能，支持播放、暂停、停止和速度调节。
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import threading
import time
from typing import Callable, Optional

import pyautogui

from PyQt6.QtCore import QObject, pyqtSignal

from src.data_models import Operation, OperationSequence
from src.logger import log_info, log_debug, log_error

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

_user32 = ctypes.windll.user32

_VK_MAP: dict[str, int] = {
    "ctrl": 0x11, "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "win": 0x5B, "cmd": 0x5B,
    "tab": 0x09,
    "enter": 0x0D, "return": 0x0D,
    "escape": 0x1B, "esc": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "insert": 0x2D,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21, "page_up": 0x21,
    "pagedown": 0x22, "page_down": 0x22,
    "capslock": 0x14, "caps_lock": 0x14,
    "numlock": 0x90, "num_lock": 0x90,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD),
    ]


class _INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT), ("hi", _HARDWAREINPUT)]

    _anonymous_ = ("_u",)
    _fields_ = [("type", ctypes.wintypes.DWORD), ("_u", _U)]


def _send_key(vk: int, up: bool = False) -> None:
    inp = _INPUT(type=INPUT_KEYBOARD)
    inp.ki.wVk = vk
    inp.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def _key_down(vk: int) -> None:
    _send_key(vk, up=False)


def _key_up(vk: int) -> None:
    _send_key(vk, up=True)


def _press_key(vk: int) -> None:
    _key_down(vk)
    time.sleep(0.05)
    _key_up(vk)


def _send_unicode_char(char: str) -> None:
    inp_down = _INPUT(type=INPUT_KEYBOARD)
    inp_down.ki.wScan = ord(char)
    inp_down.ki.dwFlags = KEYEVENTF_UNICODE
    inp_up = _INPUT(type=INPUT_KEYBOARD)
    inp_up.ki.wScan = ord(char)
    inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    _user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(_INPUT))
    time.sleep(0.01)
    _user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(_INPUT))


class _PlaybackSignals(QObject):
    progress = pyqtSignal(int, int)
    completed = pyqtSignal()


class PlaybackEngine:
    """回放引擎类。

    负责执行录制的操作序列，支持播放控制、速度调节和回调通知。

    Attributes:
        _is_playing: 是否正在播放。
        _is_paused: 是否暂停。
        _current_operation_index: 当前执行的操作索引。
        _operation_sequence: 待回放的操作序列。
        _speed_factor: 播放速度倍率。
        _stop_event: 停止事件，用于中断播放。
        _pause_event: 暂停事件，用于暂停播放。
        _play_thread: 播放线程。
        progress_callback: 进度回调函数 (current, total) -> None。
        completion_callback: 播放完成回调函数 () -> None。
    """

    MIN_SPEED: float = 0.5
    MAX_SPEED: float = 4.0

    def __init__(self) -> None:
        self._is_playing: bool = False
        self._is_paused: bool = False
        self._current_operation_index: int = 0
        self._operation_sequence: Optional[OperationSequence] = None
        self._speed_factor: float = 1.0
        self._loop_count: int = 1
        self._infinite_loop: bool = False
        self._completed_loops: int = 0
        self._stop_event: threading.Event = threading.Event()
        self._pause_event: threading.Event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None
        self._lock: threading.Lock = threading.Lock()
        self._signals: _PlaybackSignals = _PlaybackSignals()

        self.progress_callback: Optional[Callable[[int, int], None]] = None
        self.completion_callback: Optional[Callable[[], None]] = None

        self._signals.progress.connect(self._on_progress_signal)
        self._signals.completed.connect(self._on_completed_signal)

        self._pause_event.set()

    def _on_progress_signal(self, current: int, total: int) -> None:
        if self.progress_callback is not None:
            try:
                self.progress_callback(current, total)
            except Exception as e:
                log_error(f"进度回调执行失败: {e}", "PlaybackEngine")

    def _on_completed_signal(self) -> None:
        if self.completion_callback is not None:
            try:
                self.completion_callback()
            except Exception as e:
                log_error(f"完成回调执行失败: {e}", "PlaybackEngine")

    def load_sequence(self, sequence: OperationSequence) -> bool:
        """加载操作序列。

        Args:
            sequence: 要回放的操作序列。

        Returns:
            如果成功加载返回 True。
        """
        if self._is_playing:
            log_debug("正在播放中，无法加载新序列", "PlaybackEngine")
            return False

        with self._lock:
            self._operation_sequence = sequence
            self._current_operation_index = 0
            op_count = sequence.get_operation_count()
            loop_ops_info = []
            for i, op in enumerate(sequence.operations):
                if op.loop_operations:
                    loop_ops_info.append(
                        f"  #{op.id}(位置{i}): 轮错元素={len(op.loop_operations)}个, "
                        f"类型=[{','.join(lo.type for lo in op.loop_operations)}]"
                    )
            log_info(
                f"已加载操作序列，共 {op_count} 个操作，{len(loop_ops_info)} 个含轮错",
                "PlaybackEngine",
            )
            for info in loop_ops_info:
                log_debug(info, "PlaybackEngine")
            return True

    def set_speed(self, speed: float) -> bool:
        """设置播放速度。

        Args:
            speed: 速度倍率，有效范围 0.5-4.0。

        Returns:
            如果成功设置返回 True，否则返回 False。
        """
        if speed < self.MIN_SPEED or speed > self.MAX_SPEED:
            log_debug(
                f"速度值超出范围 [{self.MIN_SPEED}, {self.MAX_SPEED}]",
                "PlaybackEngine",
            )
            return False

        with self._lock:
            self._speed_factor = speed
            log_debug(f"播放速度已设置为 {speed}x", "PlaybackEngine")
            return True

    def set_loop(self, loop_count: int, infinite: bool) -> None:
        self._loop_count = loop_count
        self._infinite_loop = infinite
        self._completed_loops = 0

    def play(self) -> bool:
        """开始播放操作序列。

        在新线程中执行播放操作。

        Returns:
            如果成功开始播放返回 True，否则返回 False。
        """
        if self._is_playing:
            log_debug("已经在播放中", "PlaybackEngine")
            return False

        if self._operation_sequence is None:
            log_error("未加载操作序列", "PlaybackEngine")
            return False

        if self._operation_sequence.get_operation_count() == 0:
            log_debug("操作序列为空", "PlaybackEngine")
            return False

        self._stop_event.clear()
        self._pause_event.set()
        self._is_paused = False

        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()

        with self._lock:
            self._is_playing = True

        log_info("开始回放操作", "PlaybackEngine")
        return True

    def pause(self) -> bool:
        """暂停播放。

        Returns:
            如果成功暂停返回 True，否则返回 False。
        """
        if not self._is_playing or self._is_paused:
            return False

        self._pause_event.clear()
        self._is_paused = True
        log_info("暂停回放", "PlaybackEngine")
        return True

    def resume(self) -> bool:
        """恢复播放。

        Returns:
            如果成功恢复返回 True，否则返回 False。
        """
        if not self._is_playing or not self._is_paused:
            return False

        self._pause_event.set()
        self._is_paused = False
        log_info("恢复回放", "PlaybackEngine")
        return True

    def stop(self) -> None:
        if not self._is_playing:
            return

        self._stop_event.set()
        self._pause_event.set()

        if self._play_thread is not None and self._play_thread.is_alive():
            self._play_thread.join(timeout=2.0)
            if self._play_thread.is_alive():
                log_error("回放线程未能在超时内退出", "PlaybackEngine")
            self._play_thread = None

        with self._lock:
            self._is_playing = False
            self._is_paused = False

        log_info("停止回放", "PlaybackEngine")

    def is_playing(self) -> bool:
        """检查是否正在播放。

        Returns:
            如果正在播放返回 True，否则返回 False。
        """
        with self._lock:
            return self._is_playing

    def get_progress(self) -> tuple[int, int]:
        with self._lock:
            total = 0
            if self._operation_sequence is not None:
                total = self._operation_sequence.get_operation_count()
            return (self._current_operation_index, total)

    def get_loop_progress(self) -> tuple[int, int]:
        with self._lock:
            return (self._completed_loops, self._loop_count)

    def _play_loop(self) -> None:
        """播放循环，在独立线程中运行。"""
        if self._operation_sequence is None:
            return

        operations = self._operation_sequence.operations
        total = len(operations)

        ops_with_loop = [(i, op) for i, op in enumerate(operations) if op.loop_operations]
        if ops_with_loop:
            log_info(
                f"回放开始: loop_count={self._loop_count}, "
                f"infinite={self._infinite_loop}, "
                f"{total}个操作, {len(ops_with_loop)}个含轮错: "
                + ", ".join(f"位置{i}#{op.id}[{len(op.loop_operations)}]"
                           for i, op in ops_with_loop),
                "PlaybackEngine"
            )

        loop_num = 0
        while True:
            if self._stop_event.is_set():
                break
            if self._infinite_loop:
                loop_num += 1
            else:
                if loop_num >= self._loop_count:
                    break
                loop_num += 1

            with self._lock:
                self._completed_loops = loop_num

            last_timestamp = 0

            log_debug(f"开始第{loop_num}轮回放 (loop_num={loop_num})", "PlaybackEngine")
            for index, operation in enumerate(operations):
                if self._stop_event.is_set():
                    break

                self._pause_event.wait()

                if self._stop_event.is_set():
                    break

                if self._infinite_loop or self._loop_count > 1:
                    global_index = (loop_num - 1) * total + index
                else:
                    global_index = index

                with self._lock:
                    self._current_operation_index = global_index

                if self.progress_callback is not None:
                    try:
                        self._signals.progress.emit(global_index + 1, total)
                    except Exception as e:
                        log_error(f"进度信号发射失败: {e}", "PlaybackEngine")

                interval_ms = operation.timestamp - last_timestamp
                if interval_ms > 0:
                    self._wait_interval(interval_ms)

                last_timestamp = operation.timestamp

                if self._stop_event.is_set():
                    break

                if operation.loop_operations and loop_num > 1:
                    loop_idx = (loop_num - 2) % len(operation.loop_operations)
                    alt_op = operation.loop_operations[loop_idx]
                    log_debug(
                        f"轮错替换: 原操作#{operation.id} → 轮错[{loop_idx}] ID={alt_op.id} type={alt_op.type}",
                        "PlaybackEngine"
                    )
                    self._execute_operation(alt_op)
                else:
                    self._execute_operation(operation)

        with self._lock:
            self._is_playing = False
            if self._operation_sequence is not None:
                self._current_operation_index = self._operation_sequence.get_operation_count()

        if self.progress_callback is not None and not self._stop_event.is_set():
            try:
                self._signals.progress.emit(total, total)
            except Exception as e:
                log_error(f"完成信号发射失败: {e}", "PlaybackEngine")

        if self.completion_callback is not None and not self._stop_event.is_set():
            try:
                self._signals.completed.emit()
            except Exception as e:
                log_error(f"完成信号发射失败: {e}", "PlaybackEngine")

        log_info("回放完成", "PlaybackEngine")

    def _execute_operation(self, op: Operation) -> None:
        """执行单个操作。

        Args:
            op: 要执行的操作。
        """
        try:
            if op.type == "mouse_left_click" or op.type == "mouse_right_click":
                if op.x is not None and op.y is not None:
                    self._execute_mouse_click(op.x, op.y, op.type)
                else:
                    log_error(f"操作#{op.id} 缺少坐标: type={op.type}, x={op.x}, y={op.y}", "PlaybackEngine")
            elif op.type in ("keyboard_type", "keyboard_press", "keyboard_hotkey"):
                self._execute_keyboard(op)
            else:
                log_error(f"不支持的操作类型: {op.type}, 操作#{op.id}", "PlaybackEngine")
        except Exception as e:
            log_error(f"执行操作失败: {e}", "PlaybackEngine")

    def _execute_mouse_click(self, x: int, y: int, click_type: str) -> None:
        try:
            pyautogui.moveTo(x, y, duration=0.0)

            if click_type == "mouse_left_click":
                pyautogui.click(x, y, button='left')
            elif click_type == "mouse_right_click":
                pyautogui.click(x, y, button='right')

            log_debug(f"执行鼠标点击: ({x}, {y}), 类型: {click_type}", "PlaybackEngine")
        except pyautogui.FailSafeException:
            log_error("触发安全保护: 鼠标移至屏幕角落，回放已中断", "PlaybackEngine")
            self._stop_event.set()
        except Exception as e:
            log_error(f"鼠标点击执行失败: {e}", "PlaybackEngine")

    def _execute_keyboard(self, op: Operation) -> None:
        try:
            if op.type == "keyboard_type" and op.content:
                for ch in op.content:
                    _send_unicode_char(ch)
                    time.sleep(0.01)
                log_debug(f"执行键盘输入: '{op.content}'", "PlaybackEngine")

            elif op.type == "keyboard_press" and op.content:
                if op.modifiers:
                    self._execute_hotkey(op.modifiers + [op.content])
                    log_debug(f"执行快捷键(press): {'+'.join(op.modifiers)}+{op.content}", "PlaybackEngine")
                else:
                    vk = self._key_to_vk(op.content)
                    if vk:
                        _press_key(vk)
                        time.sleep(0.01)
                    log_debug(f"执行键盘按键: {op.content}", "PlaybackEngine")

            elif op.type == "keyboard_hotkey" and op.modifiers:
                self._execute_hotkey(op.modifiers)
                log_debug(f"执行快捷键: {'+'.join(op.modifiers)}", "PlaybackEngine")

        except pyautogui.FailSafeException:
            log_error("触发安全保护: 键盘操作期间鼠标在屏幕角落，回放已中断", "PlaybackEngine")
            self._stop_event.set()
        except Exception as e:
            log_error(f"键盘操作执行失败: {e}", "PlaybackEngine")

    def _execute_hotkey(self, keys: list[str]) -> None:
        vks = []
        for k in keys:
            vk = self._key_to_vk(k)
            if vk:
                vks.append(vk)

        for vk in vks:
            _key_down(vk)
            time.sleep(0.02)

        time.sleep(0.05)

        for vk in reversed(vks):
            _key_up(vk)
            time.sleep(0.02)

    def _key_to_vk(self, key: str) -> int:
        key_lower = key.lower()
        vk = _VK_MAP.get(key_lower)
        if vk:
            return vk
        if len(key) == 1:
            return _user32.VkKeyScanW(ord(key)) & 0xFF
        return 0

    def _wait_interval(self, interval_ms: int) -> None:
        wait_seconds = interval_ms / 1000.0 / self._speed_factor

        if wait_seconds > 0:
            steps = max(int(wait_seconds * 100), 1)
            step_time = wait_seconds / steps

            for i in range(steps):
                if self._stop_event.is_set() or not self._pause_event.is_set():
                    remaining_time = wait_seconds - i * step_time
                    if remaining_time > 0 and not self._stop_event.is_set():
                        self._pause_event.wait(timeout=remaining_time)
                    break
                time.sleep(step_time)
