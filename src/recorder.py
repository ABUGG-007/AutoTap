"""
录制管理器模块。

提供操作录制功能，监听并记录用户的鼠标和键盘输入操作。
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from src.data_models import (
    Operation,
    OperationSequence,
    MOUSE_LEFT_CLICK,
    MOUSE_RIGHT_CLICK,
    KEYBOARD_TYPE,
    KEYBOARD_PRESS,
    KEYBOARD_HOTKEY,
)
from src.logger import log_info, log_debug, log_error


class Recorder:

    SPECIAL_KEYS = frozenset({
        "up", "down", "left", "right", "home", "end",
        "page_up", "page_down", "esc", "enter", "space",
        "tab", "backspace", "delete", "insert",
        "f1", "f2", "f3", "f4", "f5", "f6",
        "f7", "f8", "f9", "f10", "f11", "f12",
    })

    MODIFIER_KEY_NAMES = frozenset({"ctrl", "shift", "alt", "cmd"})

    HOTKEY_FILTER = frozenset({"f9", "f10", "esc", "escape"})

    def __init__(self) -> None:
        try:
            from pynput import keyboard
            from pynput.mouse import Button, Listener as MouseListener
        except ImportError:
            raise ImportError("pynput 库未安装，请运行: pip install pynput")

        self._state: str = "idle"
        self._operation_sequence: OperationSequence = OperationSequence()
        self._operation_id_counter: int = 0
        self._start_time: float = 0.0
        self._pressed_keys: set[str] = set()
        self._key_buffer: list[str] = []
        self._last_key_time: float = 0.0
        self._KEY_BUFFER_INTERVAL: float = 0.5
        self._lock: threading.Lock = threading.Lock()

        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[MouseListener] = None
        self._is_listening: bool = False
        self._active_modifiers: set[str] = set()
        self._lock_key: str = ""

    def start_recording(self) -> bool:
        """开始录制操作。

        初始化操作序列并启动输入监听。

        Returns:
            如果成功开始录制返回 True，否则返回 False。
        """
        if self._state == "recording":
            log_debug("已经在录制中，无法重复开始", "Recorder")
            return False

        try:
            from pynput import keyboard
            from pynput.mouse import Listener as MouseListener

            self._operation_sequence = OperationSequence()
            self._operation_id_counter = 0
            self._start_time = time.time() * 1000
            self._pressed_keys.clear()
            self._key_buffer.clear()
            self._last_key_time = 0.0

            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_keyboard_press_wrapper,
                on_release=self._on_keyboard_release_wrapper,
            )
            self._mouse_listener = MouseListener(
                on_click=self._on_mouse_click_wrapper,
            )

            self._keyboard_listener.start()
            self._mouse_listener.start()
            self._is_listening = True

            self._state = "recording"
            log_info("开始录制操作", "Recorder")
            return True

        except Exception as e:
            log_error(f"开始录制失败: {e}", "Recorder")
            self._state = "idle"
            self._cleanup_listeners()
            return False

    def _cleanup_listeners(self) -> None:
        """清理监听器。"""
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        self._is_listening = False

    def stop_recording(self) -> OperationSequence:
        """停止录制操作。

        停止输入监听并返回录制生成的操作序列。

        Returns:
            录制完成的操作序列。
        """
        if self._state != "recording":
            log_debug("当前未在录制状态", "Recorder")
            return OperationSequence()

        self._flush_key_buffer()

        self._cleanup_listeners()
        self._state = "idle"

        log_info(
            f"停止录制，共记录 {self.get_operation_count()} 个操作",
            "Recorder",
        )

        return self._operation_sequence

    def get_state(self) -> str:
        with self._lock:
            return self._state

    def get_operation_count(self) -> int:
        with self._lock:
            return self._operation_sequence.get_operation_count()

    def _generate_operation_id(self) -> int:
        """生成唯一的操作 ID。

        Returns:
            下一个可用的操作 ID。
        """
        self._operation_id_counter += 1
        return self._operation_id_counter

    def _get_relative_timestamp(self) -> int:
        """获取相对于录制开始时间的毫秒时间戳。

        Returns:
            相对于开始录制时的时间戳（毫秒）。
        """
        return int((time.time() * 1000) - self._start_time)

    def _flush_key_buffer(self) -> None:
        """将按键缓冲区的内容刷新为键盘输入操作。"""
        if not self._key_buffer:
            return

        content = "".join(self._key_buffer)
        if content:
            operation = Operation(
                id=self._generate_operation_id(),
                type=KEYBOARD_TYPE,
                content=content,
                timestamp=self._get_relative_timestamp(),
            )
            self._operation_sequence.add_operation(operation)
            log_debug(f"录制键盘输入: '{content}'", "Recorder")

        self._key_buffer.clear()

    def _check_hotkey(self, key: str, modifiers: list[str]) -> bool:
        key_lower = key.lower()

        if key_lower in self.MODIFIER_KEY_NAMES:
            return False

        has_ctrl = any(m.lower() in {"ctrl", "control", "control_l", "control_r"} for m in modifiers)
        has_alt = any(m.lower() in {"alt", "alt_l", "alt_r"} for m in modifiers)
        has_shift = any(m.lower() in {"shift", "shift_l", "shift_r"} for m in modifiers)

        is_hotkey = False
        if has_ctrl or has_alt:
            is_hotkey = True
        elif has_shift and key_lower in self.SPECIAL_KEYS:
            is_hotkey = True

        if is_hotkey:
            self._flush_key_buffer()
            all_keys = [m.lower() for m in modifiers] + [key_lower]
            operation = Operation(
                id=self._generate_operation_id(),
                type=KEYBOARD_HOTKEY,
                content="+".join(all_keys),
                modifiers=all_keys,
                timestamp=self._get_relative_timestamp(),
            )
            self._operation_sequence.add_operation(operation)
            log_debug(f"录制快捷键: {'+'.join(all_keys)}", "Recorder")
            return True

        return False

    SPECIAL_KEYS = frozenset({
        "up", "down", "left", "right", "home", "end",
        "page_up", "page_down", "esc", "enter", "space",
        "tab", "backspace", "delete", "insert",
        "f1", "f2", "f3", "f4", "f5", "f6",
        "f7", "f8", "f9", "f10", "f11", "f12",
    })

    MODIFIER_KEY_NAMES = frozenset({"ctrl", "shift", "alt", "cmd"})

    HOTKEY_FILTER = frozenset({"f9", "f10", "esc", "escape"})

    def _on_keyboard_press_wrapper(self, key) -> None:
        with self._lock:
            if self._state != "recording":
                return

            self._update_modifiers(key, True)
            key_name = self._get_key_name(key)
            if key_name.lower() in self.HOTKEY_FILTER:
                return
            modifiers = self._get_active_modifiers()
            self._pressed_keys.add(key_name.lower())

            if key_name.lower() in self.MODIFIER_KEY_NAMES:
                return

            if self._check_hotkey(key_name, modifiers):
                return

            if key_name.lower() in self.SPECIAL_KEYS:
                self._flush_key_buffer()
                operation = Operation(
                    id=self._generate_operation_id(),
                    type=KEYBOARD_PRESS,
                    content=key_name,
                    modifiers=modifiers,
                    timestamp=self._get_relative_timestamp(),
                )
                self._operation_sequence.add_operation(operation)
                log_debug(f"录制键盘按键: {key_name}, 修饰键: {modifiers}", "Recorder")
                return

            if modifiers:
                self._flush_key_buffer()
                self._key_buffer.append(key_name)
                self._last_key_time = time.time()
            else:
                current_time = time.time()
                if (
                    current_time - self._last_key_time < self._KEY_BUFFER_INTERVAL
                    and key_name.lower() not in self._pressed_keys
                ):
                    self._key_buffer.append(key_name)
                else:
                    self._flush_key_buffer()
                    self._key_buffer.append(key_name)

                self._last_key_time = current_time

    def _on_keyboard_release_wrapper(self, key) -> None:
        with self._lock:
            if self._state != "recording":
                return

            self._update_modifiers(key, False)
            key_name = self._get_key_name(key)
            if key_name.lower() in self.HOTKEY_FILTER:
                return
            key_lower = key_name.lower()
            if key_lower in self._pressed_keys:
                self._pressed_keys.discard(key_lower)

    def _on_mouse_click_wrapper(self, x: int, y: int, button, pressed: bool) -> None:
        if not pressed:
            return
        with self._lock:
            if self._state != "recording":
                return
            button_name = self._get_mouse_button_name(button)
            self.on_mouse_click(x, y, button_name)

    def _get_key_name(self, key) -> str:
        """获取按键的可读名称。

        Args:
            key: pynput 按键对象。

        Returns:
            按键名称字符串。
        """
        try:
            from pynput import keyboard
        except ImportError:
            return str(key)

        if isinstance(key, keyboard.Key):
            key_map = {
                keyboard.Key.ctrl: "ctrl",
                keyboard.Key.shift: "shift",
                keyboard.Key.alt: "alt",
                keyboard.Key.esc: "esc",
                keyboard.Key.enter: "enter",
                keyboard.Key.space: "space",
                keyboard.Key.tab: "tab",
                keyboard.Key.backspace: "backspace",
                keyboard.Key.delete: "delete",
                keyboard.Key.up: "up",
                keyboard.Key.down: "down",
                keyboard.Key.left: "left",
                keyboard.Key.right: "right",
                keyboard.Key.home: "home",
                keyboard.Key.end: "end",
                keyboard.Key.page_up: "page_up",
                keyboard.Key.page_down: "page_down",
            }
            for k, v in key_map.items():
                if key == k:
                    return v
            return str(key).replace("Key.", "")
        elif isinstance(key, keyboard.KeyCode):
            char = key.char
            if char:
                return char.lower()
            return str(key)
        return str(key)

    def _get_mouse_button_name(self, button) -> str:
        """获取鼠标按钮名称。

        Args:
            button: 鼠标按钮对象。

        Returns:
            按钮名称 'left' 或 'right'。
        """
        try:
            from pynput.mouse import Button
        except ImportError:
            return str(button)

        if button == Button.left:
            return "left"
        elif button == Button.right:
            return "right"
        elif button == Button.middle:
            return "middle"
        return str(button)

    def _get_active_modifiers(self) -> list[str]:
        """获取当前激活的修饰键列表。

        Returns:
            修饰键名称列表。
        """
        return sorted(list(self._active_modifiers))

    def _update_modifiers(self, key, is_press: bool) -> None:
        """更新修饰键状态。

        Args:
            key: 按键对象。
            is_press: 是否按下。
        """
        try:
            from pynput import keyboard
        except ImportError:
            return

        modifier_map = {
            keyboard.Key.ctrl: "ctrl",
            keyboard.Key.shift: "shift",
            keyboard.Key.alt: "alt",
            keyboard.Key.cmd: "cmd",
        }

        modifier_name = None
        if isinstance(key, keyboard.Key):
            modifier_name = modifier_map.get(key)

        if modifier_name:
            if is_press:
                self._active_modifiers.add(modifier_name)
            else:
                self._active_modifiers.discard(modifier_name)

    def on_mouse_click(self, x: int, y: int, button: str) -> None:
        """处理鼠标点击事件。

        当录制状态时，将鼠标点击记录为操作。

        Args:
            x: 鼠标点击的 X 坐标。
            y: 鼠标点击的 Y 坐标。
            button: 鼠标按钮类型 ('left' 或 'right')。
        """
        if self._state != "recording":
            return

        self._flush_key_buffer()

        if button == "left":
            click_type = MOUSE_LEFT_CLICK
        elif button == "right":
            click_type = MOUSE_RIGHT_CLICK
        else:
            return

        operation = Operation(
            id=self._generate_operation_id(),
            type=click_type,
            x=x,
            y=y,
            timestamp=self._get_relative_timestamp(),
        )
        self._operation_sequence.add_operation(operation)
        log_debug(f"录制鼠标{button}键点击: ({x}, {y})", "Recorder")

    def on_keyboard_press(self, key: str, modifiers: list[str]) -> None:
        """处理键盘按键按下事件。

        当录制状态时，检测并记录键盘输入或快捷键。

        Args:
            key: 按下的键名。
            modifiers: 修饰键列表。
        """
        if self._state != "recording":
            return

        self._pressed_keys.add(key.lower())

        if self._check_hotkey(key, modifiers):
            return

        if modifiers:
            operation = Operation(
                id=self._generate_operation_id(),
                type=KEYBOARD_PRESS,
                content=key,
                modifiers=modifiers,
                timestamp=self._get_relative_timestamp(),
            )
            self._operation_sequence.add_operation(operation)
            log_debug(f"录制键盘按键: {key}, 修饰键: {modifiers}", "Recorder")
        else:
            current_time = time.time()
            if (
                current_time - self._last_key_time < self._KEY_BUFFER_INTERVAL
                and key.lower() not in self._pressed_keys
            ):
                self._key_buffer.append(key)
            else:
                self._flush_key_buffer()
                self._key_buffer.append(key)

            self._last_key_time = current_time

    def on_keyboard_release(self, key: str) -> None:
        """处理键盘按键释放事件。

        用于快捷键检测后的状态清理。

        Args:
            key: 释放的键名。
        """
        if self._state != "recording":
            return

        key_lower = key.lower()
        if key_lower in self._pressed_keys:
            self._pressed_keys.discard(key_lower)

        # 不再在释放Ctrl时清除其他键的状态，避免干扰正常的快捷键录制
