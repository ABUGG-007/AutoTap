"""  
系统托盘模块。

提供系统托盘功能，支持录制/回放状态显示和快捷操作菜单。
"""

import os
from typing import Optional, Callable

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMainWindow

from src.logger import log_info, log_debug


class SystemTray(QObject):
    """系统托盘管理类。

    管理应用在系统托盘中的图标显示和菜单交互。

    Attributes:
        _tray_icon: 系统托盘图标实例。
        _window: 主窗口引用。
        _recording_icon: 录制状态的图标。
        _playing_icon: 回放状态的图标。
        _normal_icon: 正常状态的图标。
        _menu: 托盘菜单实例。
        _recording_action: 录制菜单项。
        _playback_action: 回放菜单项。
        _is_visible: 当前托盘是否可见。

    Signals:
        recording_requested: 请求开始/停止录制。
        playback_requested: 请求开始/停止回放。
        show_window_requested: 请求显示主窗口。
        quit_requested: 请求退出应用。
    """

    recording_requested = pyqtSignal(bool)
    playback_requested = pyqtSignal(bool)
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, window: QMainWindow) -> None:
        """初始化系统托盘。

        Args:
            window: 主窗口引用，用于显示/隐藏操作。
        """
        super().__init__()
        self._window: QMainWindow = window
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._recording_icon: Optional[QIcon] = None
        self._playing_icon: Optional[QIcon] = None
        self._normal_icon: Optional[QIcon] = None
        self._menu: Optional[QMenu] = None
        self._recording_action: Optional[QAction] = None
        self._playback_action: Optional[QAction] = None
        self._is_visible: bool = False
        self._is_recording: bool = False
        self._is_playing: bool = False

        self._init_icons()
        self._init_tray_icon()
        self.create_menu()

        log_debug("系统托盘初始化完成", "SystemTray")

    def _init_icons(self) -> None:
        """初始化托盘图标资源。"""
        # 使用主图标文件
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icon.png')
        if os.path.exists(icon_path):
            self._recording_icon = QIcon(icon_path)
            self._playing_icon = QIcon(icon_path)
            self._normal_icon = QIcon(icon_path)
        else:
            # 如果找不到图标文件，使用系统主题图标
            self._recording_icon = QIcon.fromTheme("media-record")
            self._playing_icon = QIcon.fromTheme("media-play")
            self._normal_icon = QIcon.fromTheme("application-x-executable")

    def _init_tray_icon(self) -> None:
        """初始化系统托盘图标。"""
        self._tray_icon = QSystemTrayIcon(self._window)
        self._tray_icon.setIcon(self._normal_icon)
        self._tray_icon.setToolTip("AutoTap")
        self._tray_icon.activated.connect(self._on_activated)
        log_debug("系统托盘图标初始化完成", "SystemTray")

    def create_menu(self) -> None:
        """创建托盘菜单。

        创建包含录制、回放、显示窗口和退出选项的右键菜单。
        """
        self._menu = QMenu()

        self._recording_action = QAction("开始录制", self._menu)
        self._recording_action.triggered.connect(self._on_recording_triggered)
        self._menu.addAction(self._recording_action)

        self._playback_action = QAction("开始回放", self._menu)
        self._playback_action.triggered.connect(self._on_playback_triggered)
        self._menu.addAction(self._playback_action)

        self._menu.addSeparator()

        show_window_action = QAction("显示主窗口", self._menu)
        show_window_action.triggered.connect(self._on_show_window_triggered)
        self._menu.addAction(show_window_action)

        self._menu.addSeparator()

        quit_action = QAction("退出", self._menu)
        quit_action.triggered.connect(self._on_quit_triggered)
        self._menu.addAction(quit_action)

        if self._tray_icon:
            self._tray_icon.setContextMenu(self._menu)

        log_debug("托盘菜单创建完成", "SystemTray")

    def update_icon(self, state: str) -> None:
        """更新托盘图标状态。

        Args:
            state: 状态字符串，可选值为 'normal'、'recording' 或 'playing'。
        """
        if not self._tray_icon:
            return

        if state == "recording":
            self._tray_icon.setIcon(self._recording_icon)
            self._tray_icon.setToolTip("AutoTap - 录制中")
            self._is_recording = True
        elif state == "playing":
            self._tray_icon.setIcon(self._playing_icon)
            self._tray_icon.setToolTip("AutoTap - 回放中")
            self._is_playing = True
        else:
            self._tray_icon.setIcon(self._normal_icon)
            self._tray_icon.setToolTip("AutoTap")
            self._is_recording = False
            self._is_playing = False

        self._update_menu_text()

        log_debug(f"托盘图标更新为状态: {state}", "SystemTray")

    def _update_menu_text(self) -> None:
        """更新菜单项文本以反映当前状态。"""
        if self._recording_action:
            if self._is_recording:
                self._recording_action.setText("停止录制")
            else:
                self._recording_action.setText("开始录制")

        if self._playback_action:
            if self._is_playing:
                self._playback_action.setText("停止回放")
            else:
                self._playback_action.setText("开始回放")

    def _on_recording_triggered(self) -> None:
        """处理录制菜单项点击事件。"""
        self.recording_requested.emit(not self._is_recording)

    def _on_playback_triggered(self) -> None:
        """处理回放菜单项点击事件。"""
        self.playback_requested.emit(not self._is_playing)

    def _on_show_window_triggered(self) -> None:
        """处理显示窗口菜单项点击事件。"""
        self.show_window_requested.emit()

    def _on_quit_triggered(self) -> None:
        """处理退出菜单项点击事件。"""
        self.quit_requested.emit()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """处理托盘图标激活事件。

        Args:
            reason: 激活原因。
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()

    def show(self) -> None:
        """显示系统托盘图标。"""
        if self._tray_icon and not self._is_visible:
            self._tray_icon.show()
            self._is_visible = True
            log_info("系统托盘已显示", "SystemTray")

    def hide(self) -> None:
        """隐藏系统托盘图标。"""
        if self._tray_icon and self._is_visible:
            self._tray_icon.hide()
            self._is_visible = False
            log_info("系统托盘已隐藏", "SystemTray")

    def show_message(self, title: str, message: str) -> None:
        """显示托盘气泡消息。

        Args:
            title: 消息标题。
            message: 消息内容。
        """
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
            log_debug(f"显示托盘消息: {title} - {message}", "SystemTray")

    def is_visible(self) -> bool:
        """检查托盘图标是否可见。

        Returns:
            如果可见返回 True，否则返回 False。
        """
        return self._is_visible

    def set_recording_state(self, is_recording: bool) -> None:
        """设置录制状态。

        Args:
            is_recording: 是否正在录制。
        """
        self._is_recording = is_recording
        if is_recording and self._is_playing:
            self._is_playing = False
        self._update_menu_text()
        if is_recording:
            self.update_icon("recording")
        elif self._is_playing:
            self.update_icon("playing")
        else:
            self.update_icon("normal")

    def set_playing_state(self, is_playing: bool) -> None:
        """设置回放状态。

        Args:
            is_playing: 是否正在回放。
        """
        self._is_playing = is_playing
        if is_playing and self._is_recording:
            self._is_recording = False
        self._update_menu_text()
        if is_playing:
            self.update_icon("playing")
        elif self._is_recording:
            self.update_icon("recording")
        else:
            self.update_icon("normal")
