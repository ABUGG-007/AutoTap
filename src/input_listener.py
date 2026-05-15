"""
输入监听模块

使用 pynput 库监听键盘和鼠标事件，
支持多种事件类型的回调注册。
"""

import threading
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

try:
    from pynput import keyboard
    from pynput.mouse import Button, Controller as MouseController, Listener as MouseListener
except ImportError:
    raise ImportError("pynput 库未安装，请运行: pip install pynput")

try:
    from .logger import log_info, log_error, log_debug
except ImportError:
    from logger import log_info, log_error, log_debug


class EventType(Enum):
    """事件类型枚举"""

    MOUSE_CLICK = "on_mouse_click"
    MOUSE_MOVE = "on_mouse_move"
    KEYBOARD_PRESS = "on_keyboard_press"
    KEYBOARD_RELEASE = "on_keyboard_release"


class InputListener:
    """输入监听器类

    使用 pynput 库监听系统键盘和鼠标事件，
    支持注册回调函数处理各种输入事件。

    Attributes:
        _keyboard_listener: 键盘监听器实例
        _mouse_listener: 鼠标监听器实例
        _callbacks: 事件回调函数字典
        _is_listening: 监听状态标志
        _active_modifiers: 当前按下的修饰键集合
        _lock: 线程锁

    Example:
        >>> def on_click(x, y, button):
        ...     print(f"鼠标点击: ({x}, {y}), 按钮: {button}")
        ...
        >>> listener = InputListener()
        >>> listener.register_callback("on_mouse_click", on_click)
        >>> listener.start()
    """

    SUPPORTED_EVENTS: Set[str] = {
        EventType.MOUSE_CLICK.value,
        EventType.MOUSE_MOVE.value,
        EventType.KEYBOARD_PRESS.value,
        EventType.KEYBOARD_RELEASE.value,
    }

    def __init__(self) -> None:
        """初始化输入监听器"""
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[MouseListener] = None
        self._callbacks: Dict[str, List[Callable]] = {}
        self._is_listening: bool = False
        self._active_modifiers: Set[str] = set()
        self._lock = threading.Lock()
        self._mouse_controller = MouseController()

    def register_callback(self, event_type: str, callback: Callable) -> bool:
        """注册事件回调函数

        Args:
            event_type: 事件类型名称
            callback: 回调函数

        Returns:
            注册是否成功
        """
        if event_type not in self.SUPPORTED_EVENTS:
            log_error(f"不支持的事件类型: {event_type}")
            return False

        with self._lock:
            if event_type not in self._callbacks:
                self._callbacks[event_type] = []
            self._callbacks[event_type].append(callback)

        log_debug(f"已注册回调: {event_type}")
        return True

    def unregister_callback(self, event_type: str, callback: Optional[Callable] = None) -> bool:
        """取消注册回调函数

        Args:
            event_type: 事件类型名称
            callback: 要取消的回调函数，为 None 时取消该类型所有回调

        Returns:
            取消注册是否成功
        """
        if event_type not in self._callbacks:
            return False

        with self._lock:
            if callback is None:
                self._callbacks[event_type].clear()
            else:
                if callback in self._callbacks[event_type]:
                    self._callbacks[event_type].remove(callback)

        log_debug(f"已取消注册回调: {event_type}")
        return True

    def _on_mouse_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        """鼠标点击事件处理

        Args:
            x: 鼠标 x 坐标
            y: 鼠标 y 坐标
            button: 鼠标按钮
            pressed: 是否按下
        """
        if not pressed:
            return

        button_name = self._get_mouse_button_name(button)

        with self._lock:
            callbacks = self._callbacks.get(EventType.MOUSE_CLICK.value, []).copy()

        for callback in callbacks:
            try:
                callback(x, y, button_name)
            except Exception as e:
                log_error(f"鼠标点击回调执行失败: {e}")

    def _on_mouse_move(self, x: int, y: int) -> None:
        """鼠标移动事件处理

        Args:
            x: 鼠标 x 坐标
            y: 鼠标 y 坐标
        """
        with self._lock:
            callbacks = self._callbacks.get(EventType.MOUSE_MOVE.value, []).copy()

        for callback in callbacks:
            try:
                callback(x, y)
            except Exception as e:
                log_error(f"鼠标移动回调执行失败: {e}")

    def _get_key_name(self, key) -> str:
        """获取按键的可读名称

        Args:
            key: pynput 按键对象

        Returns:
            按键名称字符串
        """
        if isinstance(key, keyboard.Key):
            if key == keyboard.Key.ctrl:
                return "ctrl"
            elif key == keyboard.Key.shift:
                return "shift"
            elif key == keyboard.Key.alt:
                return "alt"
            elif key == keyboard.Key.esc:
                return "esc"
            elif key == keyboard.Key.enter:
                return "enter"
            elif key == keyboard.Key.space:
                return "space"
            elif key == keyboard.Key.tab:
                return "tab"
            elif key == keyboard.Key.backspace:
                return "backspace"
            elif key == keyboard.Key.delete:
                return "delete"
            elif key == keyboard.Key.up:
                return "up"
            elif key == keyboard.Key.down:
                return "down"
            elif key == keyboard.Key.left:
                return "left"
            elif key == keyboard.Key.right:
                return "right"
            elif key == keyboard.Key.home:
                return "home"
            elif key == keyboard.Key.end:
                return "end"
            elif key == keyboard.Key.page_up:
                return "page_up"
            elif key == keyboard.Key.page_down:
                return "page_down"
            else:
                return str(key).replace("Key.", "")
        elif isinstance(key, keyboard.KeyCode):
            char = key.char
            if char:
                return char.lower()
            return str(key)
        return str(key)

    def _get_mouse_button_name(self, button: Button) -> str:
        """获取鼠标按钮名称

        Args:
            button: 鼠标按钮对象

        Returns:
            按钮名称 'left' 或 'right'
        """
        if button == Button.left:
            return "left"
        elif button == Button.right:
            return "right"
        elif button == Button.middle:
            return "middle"
        return str(button)

    def _update_modifiers(self, key, is_press: bool) -> None:
        """更新修饰键状态

        Args:
            key: 按键对象
            is_press: 是否按下
        """
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
            with self._lock:
                if is_press:
                    self._active_modifiers.add(modifier_name)
                else:
                    self._active_modifiers.discard(modifier_name)

    def _get_active_modifiers(self) -> List[str]:
        """获取当前激活的修饰键列表

        Returns:
            修饰键名称列表
        """
        with self._lock:
            return sorted(list(self._active_modifiers))

    def _on_keyboard_press(self, key) -> None:
        """键盘按键按下事件处理

        Args:
            key: 按键对象
        """
        self._update_modifiers(key, True)

        key_name = self._get_key_name(key)
        modifiers = self._get_active_modifiers()

        with self._lock:
            callbacks = self._callbacks.get(EventType.KEYBOARD_PRESS.value, []).copy()

        for callback in callbacks:
            try:
                callback(key_name, modifiers)
            except Exception as e:
                log_error(f"键盘按下回调执行失败: {e}")

    def _on_keyboard_release(self, key) -> None:
        """键盘按键释放事件处理

        Args:
            key: 按键对象
        """
        self._update_modifiers(key, False)

        key_name = self._get_key_name(key)

        with self._lock:
            callbacks = self._callbacks.get(EventType.KEYBOARD_RELEASE.value, []).copy()

        for callback in callbacks:
            try:
                callback(key_name)
            except Exception as e:
                log_error(f"键盘释放回调执行失败: {e}")

    def start(self) -> bool:
        """启动输入监听

        使用守护线程在后台运行监听器。

        Returns:
            启动是否成功
        """
        if self._is_listening:
            log_info("输入监听器已在运行")
            return True

        try:
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_keyboard_press,
                on_release=self._on_keyboard_release,
            )

            self._mouse_listener = MouseListener(
                on_click=self._on_mouse_click,
                on_move=self._on_mouse_move,
            )

            self._keyboard_listener.start()
            self._mouse_listener.start()

            self._keyboard_listener.join_options(
                thread_name="KeyboardListener", daemon=True
            )
            self._mouse_listener.join_options(
                thread_name="MouseListener", daemon=True
            )

            self._is_listening = True
            log_info("输入监听器已启动")
            return True

        except Exception as e:
            log_error(f"启动输入监听器失败: {e}")
            self.stop()
            return False

    def stop(self) -> None:
        """停止输入监听"""
        if not self._is_listening:
            return

        try:
            if self._keyboard_listener is not None:
                self._keyboard_listener.stop()
                self._keyboard_listener = None

            if self._mouse_listener is not None:
                self._mouse_listener.stop()
                self._mouse_listener = None

            with self._lock:
                self._active_modifiers.clear()

            self._is_listening = False
            log_info("输入监听器已停止")

        except Exception as e:
            log_error(f"停止输入监听器时出错: {e}")

    def is_listening(self) -> bool:
        """检查监听状态

        Returns:
            是否正在监听
        """
        return self._is_listening

    def clear_callbacks(self) -> None:
        """清除所有回调函数"""
        with self._lock:
            self._callbacks.clear()
        log_debug("已清除所有回调函数")

    def get_current_modifiers(self) -> List[str]:
        """获取当前激活的修饰键

        Returns:
            修饰键名称列表
        """
        return self._get_active_modifiers()

    def __enter__(self) -> "InputListener":
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.stop()
