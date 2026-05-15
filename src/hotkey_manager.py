import ctypes
import ctypes.wintypes
from PyQt6.QtCore import QThread, pyqtSignal

from src.logger import log_error

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WM_HOTKEY = 0x0312
VK_F9 = 0x78
VK_F10 = 0x79
VK_ESCAPE = 0x1B
MOD_NOREPEAT = 0x4000

HOTKEY_DEFS = [
    (0, MOD_NOREPEAT, VK_F9),
    (1, MOD_NOREPEAT, VK_F10),
    (2, MOD_NOREPEAT, VK_ESCAPE),
]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.wintypes.HWND),
        ("message", ctypes.wintypes.UINT),
        ("wParam", ctypes.wintypes.WPARAM),
        ("lParam", ctypes.wintypes.LPARAM),
        ("time", ctypes.wintypes.DWORD),
        ("pt", ctypes.wintypes.POINT),
    ]


class HotkeyListenerThread(QThread):
    hotkey_triggered = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered = False

    def run(self):
        for hotkey_id, mod, vk in HOTKEY_DEFS:
            if not user32.RegisterHotKey(None, hotkey_id, mod, vk):
                return
        self._registered = True

        msg = MSG()
        while self._registered:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res == 0 or res == -1:
                break
            if msg.message == WM_HOTKEY:
                self.hotkey_triggered.emit(msg.wParam)

    def stop(self):
        self._registered = False
        for hotkey_id, _, _ in HOTKEY_DEFS:
            try:
                user32.UnregisterHotKey(None, hotkey_id)
            except Exception as e:
                log_error(f"UnregisterHotKey 失败: {e}", "HotkeyListenerThread")
        try:
            user32.PostThreadMessageW(self.threadId, 0x0012, 0, 0)
        except Exception as e:
            log_error(f"PostThreadMessageW 失败: {e}", "HotkeyListenerThread")
        self.wait(500)


class HotkeyManager:
    def __init__(self):
        self._thread: HotkeyListenerThread | None = None
        self._callbacks: dict[int, callable] = {}

    def start(self) -> bool:
        if self._thread is not None and self._thread.isRunning():
            return True
        self._thread = HotkeyListenerThread()
        self._thread.hotkey_triggered.connect(self._on_hotkey)
        self._thread.start()
        return True

    def stop(self):
        if self._thread is not None:
            try:
                self._thread.stop()
            except Exception as e:
                log_error(f"停止热键线程失败: {e}", "HotkeyManager")
            self._thread = None
        self._callbacks.clear()

    def register_callback(self, hotkey_id: int, callback: callable):
        self._callbacks[hotkey_id] = callback

    def _on_hotkey(self, hotkey_id: int):
        cb = self._callbacks.get(hotkey_id)
        if cb:
            cb()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()
