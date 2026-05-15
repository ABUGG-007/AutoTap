from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QCursor, QPainter, QBrush, QPen

import threading
import time

from src.recorder import Recorder
from src.playback_engine import PlaybackEngine
from src.config_manager import ConfigManager, AppSettings
from src.data_models import OperationSequence, Operation
from src.template_manager import TemplateManager
from src.hotkey_manager import HotkeyManager


_BTN_STYLE = "QPushButton {{ background-color: {}; color: white; padding: 10px 20px; font-weight: bold; border: none; border-radius: 6px; font-size: 13px; }} QPushButton:hover {{ background-color: {}; }} QPushButton:pressed {{ background-color: {}; }} QPushButton:disabled {{ background-color: #bdc3c7; }}"
_BTN_STYLE_SM = "QPushButton {{ background-color: {}; color: white; padding: 6px 14px; font-weight: 600; border: none; border-radius: 5px; font-size: 12px; }} QPushButton:hover {{ background-color: {}; }} QPushButton:pressed {{ background-color: {}; }}"

_C_REC = "#27ae60"
_C_REC_H = "#2ecc71"
_C_REC_P = "#1e8449"
_C_STOP = "#e74c3c"
_C_STOP_H = "#ec7063"
_C_STOP_P = "#c0392b"
_C_PLAY = "#3498db"
_C_PLAY_H = "#5dade2"
_C_PLAY_P = "#2980b9"
_C_TPL = "#9b59b6"
_C_TPL_H = "#af7ac5"
_C_TPL_P = "#8e44ad"
_C_PRI = "#34495e"
_C_PRI_H = "#5d6d7e"
_C_PRI_P = "#2c3e50"
_C_WARN = "#f39c12"
_C_OK = "#27ae60"


class AutoTapWindow(QMainWindow):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    operation_added = pyqtSignal()

    def __init__(
        self,
        recorder: Optional[Recorder] = None,
        playback_engine: Optional[PlaybackEngine] = None,
        config_manager: Optional[ConfigManager] = None,
    ) -> None:
        super().__init__()

        self._recorder: Recorder = recorder if recorder else Recorder()
        self._playback_engine: PlaybackEngine = playback_engine if playback_engine else PlaybackEngine()
        self._config_manager: ConfigManager = config_manager if config_manager else ConfigManager()
        self._settings: AppSettings = self._config_manager.load_settings()
        self._current_sequence: OperationSequence = OperationSequence()
        self._template_manager: TemplateManager = TemplateManager()
        self._hotkey_manager: HotkeyManager = HotkeyManager()
        self._template_recording_name: str = ""
        self._has_unsaved_template_data: bool = False
        self._editing_template_name: str = ""
        self._update_timer: QTimer = QTimer(self)
        self._timestamp_unit_ms: bool = True
        self._position_marker: _PositionMarker | None = None

        self._init_ui()
        self._init_signals()
        self._init_hotkeys()
        self._apply_settings()
        self._start_update_timer()
        self._refresh_template_list()

    def _init_ui(self) -> None:
        self.setWindowTitle("AutoTap")
        self.setMinimumSize(860, 720)
        self.resize(960, 780)

        import os, sys
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setSpacing(12)
        main.setContentsMargins(16, 16, 16, 16)

        main.addWidget(self._create_toolbar())
        main.addWidget(self._create_status_line())

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self._create_left_panel())
        body.addWidget(self._create_right_panel())
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 2)
        body.setHandleWidth(6)
        main.addWidget(body, 1)

        main.addWidget(self._create_footer())

    def _create_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; }")
        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 10, 14, 10)

        title = QLabel("AutoTap")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        layout.addSpacing(20)

        self._btn_start_record = QPushButton("开始录制")
        self._btn_start_record.setStyleSheet(_BTN_STYLE.format(_C_REC, _C_REC_H, _C_REC_P))
        self._btn_start_record.setMinimumWidth(100)
        self._btn_start_record.clicked.connect(self._on_start_record_clicked)

        self._btn_stop_record = QPushButton("结束录制")
        self._btn_stop_record.setEnabled(False)
        self._btn_stop_record.setStyleSheet(_BTN_STYLE.format(_C_STOP, _C_STOP_H, _C_STOP_P))
        self._btn_stop_record.setMinimumWidth(100)
        self._btn_stop_record.clicked.connect(self._on_stop_record_clicked)

        self._btn_create_template = QPushButton("创建模板")
        self._btn_create_template.setStyleSheet(_BTN_STYLE.format(_C_TPL, _C_TPL_H, _C_TPL_P))
        self._btn_create_template.setMinimumWidth(100)
        self._btn_create_template.clicked.connect(self._on_create_template_clicked)

        self._btn_start_template_record = QPushButton("开始录入")
        self._btn_start_template_record.setStyleSheet(_BTN_STYLE.format(_C_REC, _C_REC_H, _C_REC_P))
        self._btn_start_template_record.setMinimumWidth(100)
        self._btn_start_template_record.clicked.connect(self._on_start_template_record_clicked)
        self._btn_start_template_record.setVisible(False)

        self._btn_cancel_template = QPushButton("取消")
        self._btn_cancel_template.setStyleSheet(_BTN_STYLE_SM.format(_C_PRI, _C_PRI_H, _C_PRI_P))
        self._btn_cancel_template.clicked.connect(self._on_cancel_template_creation_clicked)
        self._btn_cancel_template.setVisible(False)

        layout.addWidget(self._btn_start_record)
        layout.addWidget(self._btn_stop_record)
        layout.addWidget(self._btn_create_template)
        layout.addWidget(self._btn_start_template_record)
        layout.addWidget(self._btn_cancel_template)
        layout.addSpacing(20)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #dee2e6;")
        sep.setFixedWidth(1)
        layout.addWidget(sep)
        layout.addSpacing(20)

        self._btn_start_playback = QPushButton("开始回放")
        self._btn_start_playback.setStyleSheet(_BTN_STYLE.format(_C_PLAY, _C_PLAY_H, _C_PLAY_P))
        self._btn_start_playback.setMinimumWidth(100)
        self._btn_start_playback.clicked.connect(self._on_start_playback_clicked)

        self._btn_stop_playback = QPushButton("停止回放")
        self._btn_stop_playback.setEnabled(False)
        self._btn_stop_playback.setStyleSheet(_BTN_STYLE.format(_C_STOP, _C_STOP_H, _C_STOP_P))
        self._btn_stop_playback.setMinimumWidth(100)
        self._btn_stop_playback.clicked.connect(self._on_stop_playback_clicked)

        layout.addWidget(self._btn_start_playback)
        layout.addWidget(self._btn_stop_playback)
        layout.addStretch()

        shortcut_tip = QLabel("F9 录制  |  F10 回放  |  Esc 停止")
        shortcut_tip.setStyleSheet("color: #6c757d; font-size: 12px;")
        layout.addWidget(shortcut_tip)

        return frame

    def _create_status_line(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e9ecef; border-radius: 6px; }")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(20)

        self._lbl_status = QLabel("就绪")
        self._lbl_status.setStyleSheet("font-weight: bold; color: #495057; font-size: 13px;")

        self._lbl_save_status = QLabel("")
        self._lbl_save_status.setStyleSheet("font-weight: bold; font-size: 12px;")
        self._lbl_save_status.setVisible(False)

        self._lbl_recorded_count = QLabel("已录制: 0")
        self._lbl_recorded_count.setStyleSheet("color: #6c757d; font-size: 12px;")

        self._lbl_progress = QLabel("进度: 0/0")
        self._lbl_progress.setStyleSheet("color: #6c757d; font-size: 12px;")

        self._lbl_loop_progress = QLabel("")
        self._lbl_loop_progress.setStyleSheet("color: #6c757d; font-size: 12px;")
        self._lbl_loop_progress.setVisible(False)

        layout.addWidget(self._lbl_status)
        layout.addWidget(self._lbl_save_status)
        layout.addStretch()
        layout.addWidget(self._lbl_recorded_count)
        layout.addWidget(self._lbl_progress)
        layout.addWidget(self._lbl_loop_progress)

        return frame

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._create_settings_panel())
        layout.addWidget(self._create_operation_panel(), 1)
        layout.addWidget(self._create_data_panel())

        return panel

    def _create_settings_panel(self) -> QGroupBox:
        group = QGroupBox("回放设置")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #495057; border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }")
        layout = QHBoxLayout(group)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 8, 12, 8)

        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(6)
        speed_label = QLabel("速度:")
        speed_label.setStyleSheet("color: #495057;")
        self._slider_speed = QSlider(Qt.Orientation.Horizontal)
        self._slider_speed.setMinimum(5)
        self._slider_speed.setMaximum(40)
        self._slider_speed.setValue(int(self._settings.playback_speed * 10))
        self._slider_speed.setFixedWidth(140)
        self._slider_speed.valueChanged.connect(self._on_speed_changed)
        self._lbl_speed_value = QLabel(f"{self._settings.playback_speed:.1f}x")
        self._lbl_speed_value.setStyleSheet("font-weight: bold; color: #495057; min-width: 36px;")
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self._slider_speed)
        speed_layout.addWidget(self._lbl_speed_value)

        loop_layout = QHBoxLayout()
        loop_layout.setSpacing(6)
        loop_label = QLabel("循环:")
        loop_label.setStyleSheet("color: #495057;")
        self._spin_loop_count = QSpinBox()
        self._spin_loop_count.setMinimum(1)
        self._spin_loop_count.setMaximum(99999)
        self._spin_loop_count.setValue(self._settings.loop_count)
        self._spin_loop_count.setFixedWidth(80)
        self._spin_loop_count.valueChanged.connect(self._on_loop_count_changed)
        self._chk_infinite_loop = QCheckBox("无限")
        self._chk_infinite_loop.setChecked(self._settings.infinite_loop)
        self._chk_infinite_loop.toggled.connect(self._on_infinite_loop_toggled)
        loop_layout.addWidget(loop_label)
        loop_layout.addWidget(self._spin_loop_count)
        loop_layout.addWidget(self._chk_infinite_loop)

        layout.addLayout(speed_layout)
        layout.addSpacing(20)
        layout.addLayout(loop_layout)
        layout.addStretch()

        return group

    def _create_operation_panel(self) -> QGroupBox:
        group = QGroupBox("操作列表")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #495057; border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 4, 8, 8)

        header_layout = QHBoxLayout()
        header_layout.addStretch()
        unit_label = QLabel("时间单位:")
        unit_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        self._combo_timestamp_unit = QComboBox()
        self._combo_timestamp_unit.addItems(["毫秒(ms)", "秒(s)"])
        self._combo_timestamp_unit.setFixedWidth(100)
        self._combo_timestamp_unit.setStyleSheet("QComboBox { font-size: 11px; padding: 2px 4px; border: 1px solid #dee2e6; border-radius: 3px; }")
        self._combo_timestamp_unit.currentIndexChanged.connect(self._on_timestamp_unit_changed)
        header_layout.addWidget(unit_label)
        header_layout.addWidget(self._combo_timestamp_unit)
        layout.addLayout(header_layout)

        self._table_operations = QTableWidget()
        self._table_operations.setColumnCount(4)
        self._table_operations.setHorizontalHeaderLabels(["#", "类型", "详情", "间隔"])
        self._table_operations.setStyleSheet("QTableWidget { border: 1px solid #dee2e6; border-radius: 4px; gridline-color: #e9ecef; } QHeaderView::section { background-color: #f8f9fa; padding: 6px; border: none; border-bottom: 1px solid #dee2e6; font-weight: 600; color: #495057; }")

        header = self._table_operations.horizontalHeader()
        if isinstance(header, QHeaderView):
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self._table_operations.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table_operations.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table_operations.setAlternatingRowColors(True)
        self._table_operations.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table_operations.customContextMenuRequested.connect(self._on_table_context_menu)
        self._table_operations.cellDoubleClicked.connect(self._on_table_cell_double_clicked)

        layout.addWidget(self._table_operations)
        return group

    def _create_data_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; }")
        layout = QHBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 8, 10, 8)

        self._btn_clear = QPushButton("清空")
        self._btn_clear.setStyleSheet(_BTN_STYLE_SM.format(_C_PRI, _C_PRI_H, _C_PRI_P))
        self._btn_clear.clicked.connect(self._on_clear_clicked)

        self._btn_save = QPushButton("保存序列")
        self._btn_save.setStyleSheet(_BTN_STYLE_SM.format(_C_PRI, _C_PRI_H, _C_PRI_P))
        self._btn_save.clicked.connect(self._on_save_clicked)

        self._btn_load = QPushButton("加载序列")
        self._btn_load.setStyleSheet(_BTN_STYLE_SM.format(_C_PRI, _C_PRI_H, _C_PRI_P))
        self._btn_load.clicked.connect(self._on_load_clicked)

        self._btn_save_as_template = QPushButton("保存为模板")
        self._btn_save_as_template.setStyleSheet(_BTN_STYLE_SM.format(_C_TPL, _C_TPL_H, _C_TPL_P))
        self._btn_save_as_template.clicked.connect(self._on_save_as_template_clicked)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #dee2e6;")
        sep.setFixedWidth(1)

        self._btn_save_template = QPushButton("保存模板")
        self._btn_save_template.setStyleSheet(_BTN_STYLE_SM.format(_C_OK, "#2ecc71", "#1e8449"))
        self._btn_save_template.clicked.connect(self._on_save_template_clicked)
        self._btn_save_template.setVisible(False)

        self._btn_discard_template = QPushButton("放弃保存")
        self._btn_discard_template.setStyleSheet(_BTN_STYLE_SM.format(_C_STOP, _C_STOP_H, _C_STOP_P))
        self._btn_discard_template.clicked.connect(self._on_discard_template_clicked)
        self._btn_discard_template.setVisible(False)

        layout.addWidget(self._btn_clear)
        layout.addWidget(self._btn_save)
        layout.addWidget(self._btn_load)
        layout.addWidget(self._btn_save_as_template)
        layout.addWidget(sep)
        layout.addWidget(self._btn_save_template)
        layout.addWidget(self._btn_discard_template)
        layout.addStretch()

        return frame

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._create_template_panel(), 1)
        layout.addWidget(self._create_system_panel())

        return panel

    def _create_template_panel(self) -> QGroupBox:
        group = QGroupBox("模板管理")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #495057; border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 4, 8, 8)

        self._template_list = QListWidget()
        self._template_list.setStyleSheet("QListWidget { border: 1px solid #dee2e6; border-radius: 4px; padding: 4px; } QListWidget::item { padding: 6px; border-radius: 3px; } QListWidget::item:selected { background-color: #e3f2fd; color: #1976d2; } QListWidget::item:hover { background-color: #f5f5f5; }")
        self._template_list.itemDoubleClicked.connect(self._on_template_double_clicked)
        self._template_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._template_list.customContextMenuRequested.connect(self._on_template_context_menu)
        layout.addWidget(self._template_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._btn_use_template = QPushButton("使用模板")
        self._btn_use_template.setStyleSheet(_BTN_STYLE_SM.format(_C_PLAY, _C_PLAY_H, _C_PLAY_P))
        self._btn_use_template.clicked.connect(self._on_use_template_clicked)

        self._btn_delete_template = QPushButton("删除")
        self._btn_delete_template.setStyleSheet(_BTN_STYLE_SM.format(_C_STOP, _C_STOP_H, _C_STOP_P))
        self._btn_delete_template.clicked.connect(self._on_delete_template_clicked)

        btn_layout.addWidget(self._btn_use_template)
        btn_layout.addWidget(self._btn_delete_template)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return group

    def _create_system_panel(self) -> QGroupBox:
        group = QGroupBox("系统设置")
        group.setStyleSheet("QGroupBox { font-weight: bold; color: #495057; border: 1px solid #dee2e6; border-radius: 6px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 8, 12, 8)

        self._chk_auto_startup = QCheckBox("开机自启动")
        self._chk_auto_startup.setChecked(self._settings.auto_startup)
        self._chk_auto_startup.toggled.connect(self._on_auto_startup_toggled)
        self._chk_auto_startup.setStyleSheet("color: #495057;")

        self._chk_show_notifications = QCheckBox("显示完成通知")
        self._chk_show_notifications.setChecked(self._settings.show_notifications)
        self._chk_show_notifications.toggled.connect(self._on_show_notifications_toggled)
        self._chk_show_notifications.setStyleSheet("color: #495057;")

        layout.addWidget(self._chk_auto_startup)
        layout.addWidget(self._chk_show_notifications)
        layout.addStretch()

        return group

    def _create_footer(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: #f8f9fa; border-top: 1px solid #e9ecef; }")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        info = QLabel("AutoTap v2.0  |  全局快捷键: F9录制 F10回放 Esc停止")
        info.setStyleSheet("color: #adb5bd; font-size: 11px;")
        layout.addWidget(info)
        layout.addStretch()

        return frame

    def _init_signals(self) -> None:
        self._playback_engine.progress_callback = self._on_playback_progress
        self._playback_engine.completion_callback = self._on_playback_completed_signal

    def _init_hotkeys(self) -> None:
        self._hotkey_manager.register_callback(0, self._on_hotkey_record_toggle)
        self._hotkey_manager.register_callback(1, self._on_hotkey_playback_toggle)
        self._hotkey_manager.register_callback(2, self._on_hotkey_stop)
        self._hotkey_manager.start()

    def _apply_settings(self) -> None:
        self._playback_engine.set_speed(self._settings.playback_speed)
        self._spin_loop_count.setValue(self._settings.loop_count)
        self._chk_infinite_loop.setChecked(self._settings.infinite_loop)
        self._chk_auto_startup.setChecked(self._settings.auto_startup)
        self._chk_show_notifications.setChecked(self._settings.show_notifications)
        self._spin_loop_count.setEnabled(not self._settings.infinite_loop)

    def _start_update_timer(self) -> None:
        self._update_timer.timeout.connect(self._update_ui)
        self._update_timer.start(100)

    def _update_ui(self) -> None:
        try:
            if self._recorder.get_state() == "recording":
                count = self._recorder.get_operation_count()
                self._lbl_recorded_count.setText(f"已录制: {count}")
            else:
                self._lbl_recorded_count.setText(f"已录制: {self._current_sequence.get_operation_count()}")

            if self._playback_engine.is_playing():
                current, total = self._playback_engine.get_progress()
                self._lbl_progress.setText(f"进度: {current}/{total}")
                completed_loops, total_loops = self._playback_engine.get_loop_progress()
                if total_loops > 1 or self._settings.infinite_loop:
                    if self._settings.infinite_loop:
                        self._lbl_loop_progress.setText(f"循环: 第{completed_loops}次")
                    else:
                        self._lbl_loop_progress.setText(f"循环: {completed_loops}/{total_loops}")
                    self._lbl_loop_progress.setVisible(True)
        except RuntimeError:
            pass

    def _refresh_operation_list(self) -> None:
        self._table_operations.setRowCount(0)
        prev_ts = 0
        for op in self._current_sequence.operations:
            row = self._table_operations.rowCount()
            self._table_operations.insertRow(row)
            self._table_operations.setItem(row, 0, QTableWidgetItem(str(op.id)))
            type_text = self._get_operation_type_text(op.type)
            if op.loop_operations:
                type_text += f" [轮×{len(op.loop_operations)}]"
            self._table_operations.setItem(row, 1, QTableWidgetItem(type_text))
            self._table_operations.setItem(row, 2, QTableWidgetItem(self._get_operation_detail(op)))
            raw_interval = op.timestamp - prev_ts
            interval_item = QTableWidgetItem(self._format_interval(raw_interval))
            interval_item.setData(Qt.ItemDataRole.UserRole, raw_interval)
            self._table_operations.setItem(row, 3, interval_item)
            prev_ts = op.timestamp

    def _refresh_template_list(self) -> None:
        self._template_list.clear()
        for t in self._template_manager.list_templates():
            self._template_list.addItem(f"{t['name']}  ({t['operation_count']}个操作)")

    def _get_operation_type_text(self, op_type: str) -> str:
        return {
            "mouse_left_click": "鼠标左键",
            "mouse_right_click": "鼠标右键",
            "mouse_move": "鼠标移动",
            "keyboard_type": "键盘输入",
            "keyboard_press": "键盘按键",
            "keyboard_hotkey": "快捷键",
        }.get(op_type, op_type)

    def _get_operation_detail(self, op) -> str:
        if op.type in ("mouse_left_click", "mouse_right_click"):
            return f"({op.x}, {op.y})"
        elif op.type == "keyboard_type":
            return f"输入: {op.content}"
        elif op.type == "keyboard_press":
            mods = ",".join(op.modifiers) if op.modifiers else ""
            return f"{mods}{op.content}" if mods else op.content
        elif op.type == "keyboard_hotkey":
            return "+".join(op.modifiers) if op.modifiers else op.content
        return ""

    def _set_status(self, text: str, color: str) -> None:
        self._lbl_status.setText(text)
        self._lbl_status.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 13px;")

    def _format_interval(self, interval_ms: int) -> str:
        scaled = interval_ms / self._settings.playback_speed
        if self._timestamp_unit_ms:
            if scaled == int(scaled):
                return f"{int(scaled)}ms"
            return f"{scaled:.1f}ms"
        else:
            return f"{scaled / 1000:.3f}s"

    def _on_timestamp_unit_changed(self, index: int) -> None:
        self._timestamp_unit_ms = (index == 0)
        self._refresh_operation_list()

    def _on_table_cell_double_clicked(self, row: int, col: int) -> None:
        if col != 3:
            return
        if row < 0 or row >= len(self._current_sequence.operations):
            return
        op = self._current_sequence.operations[row]
        if row == 0:
            prev_ts = 0
        else:
            prev_ts = self._current_sequence.operations[row - 1].timestamp
        current_interval = op.timestamp - prev_ts
        if self._timestamp_unit_ms:
            current_text = str(current_interval)
            unit_hint = "毫秒"
        else:
            current_text = f"{current_interval / 1000:.3f}"
            unit_hint = "秒"
        value, ok = QInputDialog.getText(
            self, "编辑间隔",
            f"请输入新的间隔时间（{unit_hint}）:",
            text=current_text,
        )
        if not ok or not value.strip():
            return
        try:
            if self._timestamp_unit_ms:
                new_interval = int(value.strip())
            else:
                new_interval = int(float(value.strip()) * 1000)
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的数值")
            return
        if new_interval < 0:
            QMessageBox.warning(self, "错误", "间隔时间不能为负数")
            return
        diff = new_interval - current_interval
        for i in range(row, len(self._current_sequence.operations)):
            self._current_sequence.operations[i].timestamp += diff
        self._refresh_operation_list()
        self._playback_engine.load_sequence(self._current_sequence)

    def _on_start_record_clicked(self) -> None:
        if self._playback_engine.is_playing():
            QMessageBox.warning(self, "警告", "正在回放中，请先停止回放")
            return
        if self._has_unsaved_template_data:
            QMessageBox.warning(self, "警告", "请先保存或放弃当前未保存的模板数据")
            return
        if self._template_recording_name:
            QMessageBox.warning(self, "警告", "请先完成或取消模板创建")
            return
        if self._recorder.start_recording():
            self._template_recording_name = ""
            self._editing_template_name = ""
            self._btn_start_record.setEnabled(False)
            self._btn_stop_record.setEnabled(True)
            self._btn_create_template.setVisible(False)
            self._btn_start_template_record.setVisible(False)
            self._btn_cancel_template.setVisible(False)
            self._btn_start_playback.setEnabled(False)
            self._set_status("录制中...", _C_REC)
            self.recording_started.emit()
        else:
            QMessageBox.warning(self, "错误", "无法开始录制")

    def _on_stop_record_clicked(self) -> None:
        self._stop_recording()

    def _stop_recording(self) -> None:
        if self._recorder.get_state() != "recording":
            return
        sequence = self._recorder.stop_recording()
        self._current_sequence = sequence
        self._btn_stop_record.setEnabled(False)
        self._btn_start_playback.setEnabled(True)
        self._refresh_operation_list()
        self._playback_engine.load_sequence(self._current_sequence)

        if self._template_recording_name:
            self._has_unsaved_template_data = True
            self._btn_save_template.setVisible(True)
            self._btn_discard_template.setVisible(True)
            self._btn_start_record.setEnabled(False)
            self._btn_create_template.setVisible(False)
            self._set_status(f"录入完成: {self._template_recording_name}", _C_WARN)
            self._set_save_status("未保存", _C_WARN)
        else:
            self._btn_start_record.setEnabled(True)
            self._btn_create_template.setVisible(True)
            self._set_status("就绪", "#495057")

        self.recording_stopped.emit()
        self.operation_added.emit()

    def _on_start_playback_clicked(self) -> None:
        self._start_playback()

    def _start_playback(self) -> None:
        if self._recorder.get_state() == "recording":
            QMessageBox.warning(self, "警告", "正在录制中，请先结束录制")
            return
        if self._has_unsaved_template_data:
            QMessageBox.warning(self, "警告", "请先保存或放弃当前未保存的模板数据")
            return
        if not self._playback_engine.load_sequence(self._current_sequence):
            QMessageBox.warning(self, "警告", "操作序列为空")
            return
        self._playback_engine.set_loop(self._settings.loop_count, self._settings.infinite_loop)
        if self._playback_engine.play():
            self._btn_start_playback.setEnabled(False)
            self._btn_stop_playback.setEnabled(True)
            self._btn_start_record.setEnabled(False)
            self._btn_create_template.setVisible(False)
            self._btn_start_template_record.setVisible(False)
            self._btn_cancel_template.setVisible(False)
            self._set_status("回放中...", _C_STOP)
            self.playback_started.emit()
        else:
            QMessageBox.warning(self, "错误", "无法开始回放")

    def _on_stop_playback_clicked(self) -> None:
        self._stop_playback()

    def _stop_playback(self) -> None:
        completed_loops, total_loops = self._playback_engine.get_loop_progress()
        is_infinite = self._settings.infinite_loop
        self._playback_engine.stop()
        self._btn_start_playback.setEnabled(True)
        self._btn_stop_playback.setEnabled(False)
        self._btn_start_record.setEnabled(not self._has_unsaved_template_data)
        self._btn_create_template.setVisible(not self._has_unsaved_template_data and not self._template_recording_name)
        if self._template_recording_name and not self._has_unsaved_template_data:
            self._btn_start_template_record.setVisible(True)
            self._btn_cancel_template.setVisible(True)
        if (total_loops > 1 or is_infinite) and completed_loops > 0:
            if is_infinite:
                self._lbl_loop_progress.setText(f"循环: 已完成{completed_loops}次")
            else:
                self._lbl_loop_progress.setText(f"循环: 已完成{completed_loops}/{total_loops}次")
            self._lbl_loop_progress.setStyleSheet("color: #e67e22; font-weight: bold; font-size: 12px;")
            self._lbl_loop_progress.setVisible(True)
        else:
            self._lbl_loop_progress.setVisible(False)
        self._set_status("就绪", "#495057")
        self.playback_stopped.emit()

    def _on_create_template_clicked(self) -> None:
        if self._playback_engine.is_playing():
            QMessageBox.warning(self, "警告", "正在回放中，请先停止回放")
            return
        if self._has_unsaved_template_data:
            QMessageBox.warning(self, "警告", "请先保存或放弃当前未保存的模板数据")
            return
        name, ok = QInputDialog.getText(self, "创建模板", "请输入模板名称:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if self._template_manager.template_exists(name):
            QMessageBox.warning(self, "警告", f"模板 '{name}' 已存在")
            return
        self._template_recording_name = name
        self._btn_create_template.setVisible(False)
        self._btn_start_template_record.setVisible(True)
        self._btn_cancel_template.setVisible(True)
        self._btn_start_record.setEnabled(False)
        self._btn_start_playback.setEnabled(False)
        self._set_status(f"模板已创建: {name}", _C_TPL)
        self._set_save_status("等待录入", _C_WARN)

    def _on_start_template_record_clicked(self) -> None:
        if not self._template_recording_name:
            return
        if self._playback_engine.is_playing():
            QMessageBox.warning(self, "警告", "正在回放中，请先停止回放")
            return
        if self._recorder.start_recording():
            self._btn_start_template_record.setVisible(False)
            self._btn_cancel_template.setVisible(False)
            self._btn_stop_record.setEnabled(True)
            self._btn_start_record.setEnabled(False)
            self._btn_start_playback.setEnabled(False)
            self._set_status(f"录入模板: {self._template_recording_name}", _C_REC)
            self._set_save_status("录入中...", _C_WARN)
            self.recording_started.emit()
        else:
            QMessageBox.warning(self, "错误", "无法开始录制")

    def _on_cancel_template_creation_clicked(self) -> None:
        self._template_recording_name = ""
        self._btn_create_template.setVisible(True)
        self._btn_start_template_record.setVisible(False)
        self._btn_cancel_template.setVisible(False)
        self._btn_start_record.setEnabled(True)
        self._btn_start_playback.setEnabled(True)
        self._set_status("就绪", "#495057")
        self._clear_save_status()

    def _on_save_template_clicked(self) -> None:
        if not self._template_recording_name:
            return
        if self._current_sequence.get_operation_count() == 0:
            QMessageBox.warning(self, "警告", "操作列表为空，无法保存")
            return
        self._template_manager.create_template(self._template_recording_name, self._current_sequence)
        self._refresh_template_list()
        self._has_unsaved_template_data = False
        self._template_recording_name = ""
        self._btn_save_template.setVisible(False)
        self._btn_discard_template.setVisible(False)
        self._btn_create_template.setVisible(True)
        self._btn_start_record.setEnabled(True)
        self._btn_start_playback.setEnabled(True)
        self._set_status("就绪", "#495057")
        self._set_save_status("已保存", _C_OK)
        QTimer.singleShot(2000, self._clear_save_status)

    def _on_discard_template_clicked(self) -> None:
        self._has_unsaved_template_data = False
        self._template_recording_name = ""
        self._btn_save_template.setVisible(False)
        self._btn_discard_template.setVisible(False)
        self._btn_create_template.setVisible(True)
        self._btn_start_record.setEnabled(True)
        self._btn_start_playback.setEnabled(True)
        self._set_status("就绪", "#495057")
        self._set_save_status("已放弃", _C_STOP)
        QTimer.singleShot(2000, self._clear_save_status)

    def _on_save_as_template_clicked(self) -> None:
        if self._current_sequence.get_operation_count() == 0:
            QMessageBox.warning(self, "警告", "操作列表为空，无法保存为模板")
            return
        if self._recorder.get_state() == "recording":
            QMessageBox.warning(self, "警告", "正在录制中，请先结束录制")
            return
        if self._playback_engine.is_playing():
            QMessageBox.warning(self, "警告", "正在回放中，请先停止回放")
            return
        name, ok = QInputDialog.getText(self, "保存为模板", "请输入模板名称:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if self._template_manager.template_exists(name):
            reply = QMessageBox.question(
                self, "覆盖确认", f"模板 '{name}' 已存在，是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._template_manager.create_template(name, self._current_sequence)
        self._refresh_template_list()
        self._set_save_status(f"已保存为模板: {name}", _C_OK)
        QTimer.singleShot(3000, self._clear_save_status)

    def _set_save_status(self, text: str, color: str) -> None:
        self._lbl_save_status.setText(text)
        self._lbl_save_status.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {color};")
        self._lbl_save_status.setVisible(True)

    def _clear_save_status(self) -> None:
        self._lbl_save_status.setText("")
        self._lbl_save_status.setVisible(False)

    def _on_use_template_clicked(self) -> None:
        current_item = self._template_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "警告", "请先选择一个模板")
            return
        template_name = current_item.text().split("  (")[0]
        self._load_and_play_template(template_name)

    def _on_template_double_clicked(self, item) -> None:
        template_name = item.text().split("  (")[0]
        self._load_and_play_template(template_name)

    def _load_and_play_template(self, name: str) -> None:
        if self._recorder.get_state() == "recording":
            QMessageBox.warning(self, "警告", "正在录制中，请先结束录制")
            return
        if self._has_unsaved_template_data:
            QMessageBox.warning(self, "警告", "请先保存或放弃当前未保存的模板数据")
            return
        if self._playback_engine.is_playing():
            self._stop_playback()
        sequence = self._template_manager.get_template(name)
        if sequence is None:
            QMessageBox.warning(self, "警告", f"无法加载模板: {name}")
            return
        self._current_sequence = sequence
        self._refresh_operation_list()
        self._playback_engine.load_sequence(self._current_sequence)
        self._start_playback()

    def _on_delete_template_clicked(self) -> None:
        current_item = self._template_list.currentItem()
        if current_item is None:
            QMessageBox.warning(self, "警告", "请先选择一个模板")
            return
        template_name = current_item.text().split("  (")[0]
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除模板 '{template_name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._template_manager.delete_template(template_name)
            self._refresh_template_list()

    def _on_template_context_menu(self, pos) -> None:
        item = self._template_list.itemAt(pos)
        if item is None:
            return
        template_name = item.text().split("  (")[0]
        menu = QMenu(self)
        use_action = menu.addAction("使用模板")
        edit_action = menu.addAction("编辑")
        menu.addSeparator()
        delete_action = menu.addAction("删除")
        action = menu.exec(self._template_list.viewport().mapToGlobal(pos))
        if action == use_action:
            self._load_and_play_template(template_name)
        elif action == edit_action:
            self._on_edit_template(template_name)
        elif action == delete_action:
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除模板 '{template_name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._template_manager.delete_template(template_name)
                self._refresh_template_list()

    def _on_edit_template(self, name: str) -> None:
        if self._recorder.get_state() == "recording":
            QMessageBox.warning(self, "警告", "正在录制中，请先结束录制")
            return
        if self._has_unsaved_template_data:
            QMessageBox.warning(self, "警告", "请先保存或放弃当前未保存的模板数据")
            return
        if self._playback_engine.is_playing():
            self._stop_playback()
        sequence = self._template_manager.get_template(name)
        if sequence is None:
            QMessageBox.warning(self, "警告", f"无法加载模板: {name}")
            return
        self._editing_template_name = name
        self._current_sequence = sequence
        self._refresh_operation_list()
        self._playback_engine.load_sequence(self._current_sequence)
        self._set_status(f"编辑模板: {name}", _C_TPL)

    def _on_hotkey_record_toggle(self) -> None:
        if self._recorder.get_state() == "recording":
            self._stop_recording()
        elif self._template_recording_name and not self._has_unsaved_template_data:
            self._on_start_template_record_clicked()
        else:
            self._on_start_record_clicked()

    def _on_hotkey_playback_toggle(self) -> None:
        if self._playback_engine.is_playing():
            self._stop_playback()
        else:
            self._on_start_playback_clicked()

    def _on_hotkey_stop(self) -> None:
        if self._recorder.get_state() == "recording":
            self._stop_recording()
        elif self._playback_engine.is_playing():
            self._stop_playback()

    def _on_speed_changed(self, value: int) -> None:
        speed = value / 10.0
        self._lbl_speed_value.setText(f"{speed:.1f}x")
        self._settings.playback_speed = speed
        self._playback_engine.set_speed(speed)
        self._save_settings()
        self._update_interval_column()

    def _update_interval_column(self) -> None:
        for row in range(self._table_operations.rowCount()):
            item = self._table_operations.item(row, 3)
            if item is not None:
                raw = item.data(Qt.ItemDataRole.UserRole)
                if raw is not None:
                    item.setText(self._format_interval(raw))

    def _on_loop_count_changed(self, value: int) -> None:
        self._settings.loop_count = value
        self._save_settings()

    def _on_infinite_loop_toggled(self, checked: bool) -> None:
        self._settings.infinite_loop = checked
        self._spin_loop_count.setEnabled(not checked)
        self._save_settings()

    def _on_auto_startup_toggled(self, checked: bool) -> None:
        self._settings.auto_startup = checked
        self._save_settings()

    def _on_show_notifications_toggled(self, checked: bool) -> None:
        self._settings.show_notifications = checked
        self._save_settings()

    def _on_playback_progress(self, current: int, total: int) -> None:
        self._lbl_progress.setText(f"进度: {current}/{total}")

    def _on_playback_completed_signal(self) -> None:
        QTimer.singleShot(0, self._on_playback_completed)

    def _on_playback_completed(self) -> None:
        self._btn_start_playback.setEnabled(True)
        self._btn_stop_playback.setEnabled(False)
        self._btn_start_record.setEnabled(not self._has_unsaved_template_data)
        self._btn_create_template.setVisible(not self._has_unsaved_template_data and not self._template_recording_name)
        if self._template_recording_name and not self._has_unsaved_template_data:
            self._btn_start_template_record.setVisible(True)
            self._btn_cancel_template.setVisible(True)
        self._lbl_loop_progress.setVisible(False)
        self._lbl_loop_progress.setStyleSheet("color: #6c757d; font-size: 12px;")
        self._set_status("就绪", "#495057")
        if self._settings.show_notifications:
            QTimer.singleShot(100, self._show_playback_complete_notification)

    def _show_playback_complete_notification(self) -> None:
        try:
            QMessageBox.information(self, "完成", "回放完成")
        except RuntimeError:
            pass

    def _on_table_context_menu(self, pos) -> None:
        row = self._table_operations.rowAt(pos.y())
        if row < 0:
            return
        op = self._current_sequence.operations[row] if row < len(self._current_sequence.operations) else None
        menu = QMenu(self)
        delete_action = menu.addAction("删除")
        edit_interval_action = menu.addAction("编辑间隔")
        loop_action = menu.addAction("插入轮错")
        show_pos_action = None
        if op and op.type in ("mouse_left_click", "mouse_right_click") and op.x is not None and op.y is not None:
            show_pos_action = menu.addAction("显示位置")
        if self._editing_template_name:
            save_action = menu.addAction("保存到模板")
        action = menu.exec(self._table_operations.viewport().mapToGlobal(pos))
        if action == delete_action:
            self._delete_operation_at_row(row)
        elif action == edit_interval_action:
            self._on_table_cell_double_clicked(row, 3)
        elif action == loop_action:
            self._on_insert_loop_operation(row)
        elif show_pos_action and action == show_pos_action:
            self._show_position_marker(op.x, op.y)
        elif self._editing_template_name and action == save_action:
            self._save_current_to_template()

    def _save_current_to_template(self) -> None:
        if not self._editing_template_name:
            return
        self._template_manager.create_template(self._editing_template_name, self._current_sequence)
        self._refresh_template_list()
        self._set_status("就绪", "#495057")
        self._editing_template_name = ""

    def _delete_operation_at_row(self, row: int) -> None:
        if row < 0 or row >= len(self._current_sequence.operations):
            return
        op = self._current_sequence.operations[row]
        self._current_sequence.remove_operation(op.id)
        self._refresh_operation_list()
        self._playback_engine.load_sequence(self._current_sequence)
        self._lbl_progress.setText(f"进度: 0/{self._current_sequence.get_operation_count()}")

    def _on_clear_clicked(self) -> None:
        if self._current_sequence.get_operation_count() == 0:
            return
        if self._has_unsaved_template_data:
            QMessageBox.warning(self, "警告", "请先保存或放弃当前未保存的模板数据")
            return
        reply = QMessageBox.question(
            self, "确认", "确定要清空操作列表吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._current_sequence.clear()
            self._refresh_operation_list()
            self._lbl_progress.setText("进度: 0/0")

    def _on_save_clicked(self) -> None:
        if self._current_sequence.get_operation_count() == 0:
            QMessageBox.warning(self, "警告", "操作列表为空，无法保存")
            return
        if self._has_unsaved_template_data and self._template_recording_name:
            self._on_save_template_clicked()
            return
        if self._editing_template_name:
            self._save_current_to_template()
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "保存序列", "", "JSON Files (*.json);;All Files (*)")
        if filepath:
            try:
                self._current_sequence.save_to_file(filepath)
                QMessageBox.information(self, "成功", f"序列已保存到: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _on_load_clicked(self) -> None:
        if self._playback_engine.is_playing():
            QMessageBox.warning(self, "警告", "正在回放中，请先停止回放")
            return
        if self._has_unsaved_template_data:
            QMessageBox.warning(self, "警告", "请先保存或放弃当前未保存的模板数据")
            return
        filepath, _ = QFileDialog.getOpenFileName(self, "加载序列", "", "JSON Files (*.json);;All Files (*)")
        if filepath:
            try:
                self._current_sequence = OperationSequence.load_from_file(filepath)
                self._refresh_operation_list()
                self._playback_engine.load_sequence(self._current_sequence)
                self._lbl_progress.setText(f"进度: 0/{self._current_sequence.get_operation_count()}")
                QMessageBox.information(self, "成功", f"已加载 {self._current_sequence.get_operation_count()} 个操作")
            except FileNotFoundError:
                QMessageBox.critical(self, "错误", f"文件不存在: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载失败: {e}")

    def _save_settings(self) -> None:
        self._config_manager.save_settings(self._settings)

    def _show_position_marker(self, x: int, y: int) -> None:
        if self._position_marker is not None:
            self._position_marker.close()
            self._position_marker = None
        marker = _PositionMarker(x, y)
        marker_ref = marker

        def _on_marker_destroyed():
            if self._position_marker is marker_ref:
                self._position_marker = None

        marker.destroyed.connect(_on_marker_destroyed)
        self._position_marker = marker

    def _on_insert_loop_operation(self, row: int) -> None:
        if row < 0 or row >= len(self._current_sequence.operations):
            return
        op = self._current_sequence.operations[row]
        dlg = _LoopOperationDialog(op, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_operation_list()
            self._playback_engine.load_sequence(self._current_sequence)

    def closeEvent(self, event) -> None:
        if self._has_unsaved_template_data and self._template_recording_name:
            reply = QMessageBox.question(
                self, "未保存的模板", f"模板 '{self._template_recording_name}' 尚未保存，是否保存？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._template_manager.create_template(self._template_recording_name, self._current_sequence)
            self._has_unsaved_template_data = False

        if self._recorder.get_state() == "recording":
            self._recorder.stop_recording()
        if self._playback_engine.is_playing():
            self._playback_engine.stop()
        self._hotkey_manager.stop()
        self._update_timer.stop()
        self._config_manager.save_settings(self._settings)

        event.accept()


class _LoopOperationDialog(QDialog):
    def __init__(self, operation: Operation, parent=None) -> None:
        super().__init__(parent)
        self._operation = operation
        self._original_loop_ops = list(operation.loop_operations)
        self._op_id_counter = max((lo.id for lo in operation.loop_operations), default=0)
        self._capturing = False
        self._capture_btn = None
        self.setWindowTitle("插入轮错")
        self.setMinimumSize(520, 440)
        self.setStyleSheet("QDialog { background-color: #ffffff; }")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QLabel(f"原操作: {self._get_op_brief(self._operation)}")
        info.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 13px; padding: 6px; background-color: #f0f0f0; border-radius: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        hint = QLabel("循环操作列表（第1次回放执行原操作，第2次起依次执行下方列表中的操作，循环往复）:")
        hint.setStyleSheet("color: #6c757d; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        warn = QLabel('⚠ 注意：需将主界面的"循环次数"设置为 ≥2 或勾选"无限"，轮错才会生效')
        warn.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: 600;")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["#", "类型", "详情"])
        self._table.setStyleSheet("QTableWidget { border: 1px solid #dee2e6; border-radius: 4px; gridline-color: #e9ecef; } QHeaderView::section { background-color: #f8f9fa; padding: 4px; border: none; border-bottom: 1px solid #dee2e6; font-weight: 600; color: #495057; font-size: 11px; }")
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        header = self._table.horizontalHeader()
        if isinstance(header, QHeaderView):
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._capture_btn = QPushButton("🖱 点击捕获坐标")
        self._capture_btn.setStyleSheet(_BTN_STYLE_SM.format(_C_PLAY, _C_PLAY_H, _C_PLAY_P))
        self._capture_btn.clicked.connect(self._on_start_capture)

        btn_add_key = QPushButton("+ 键盘按键")
        btn_add_key.setStyleSheet(_BTN_STYLE_SM.format(_C_TPL, _C_TPL_H, _C_TPL_P))
        btn_add_key.clicked.connect(self._on_add_key)

        btn_add_text = QPushButton("+ 键盘输入")
        btn_add_text.setStyleSheet(_BTN_STYLE_SM.format(_C_REC, _C_REC_H, _C_REC_P))
        btn_add_text.clicked.connect(self._on_add_text)

        btn_delete = QPushButton("删除选中")
        btn_delete.setStyleSheet(_BTN_STYLE_SM.format(_C_STOP, _C_STOP_H, _C_STOP_P))
        btn_delete.clicked.connect(self._on_delete_selected)

        btn_layout.addWidget(self._capture_btn)
        btn_layout.addWidget(btn_add_key)
        btn_layout.addWidget(btn_add_text)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        btn_ok = QPushButton("确定")
        btn_ok.setStyleSheet(_BTN_STYLE.format(_C_OK, "#2ecc71", "#1e8449"))
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet(_BTN_STYLE.format(_C_PRI, _C_PRI_H, _C_PRI_P))
        btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(btn_ok)
        bottom_layout.addWidget(btn_cancel)
        layout.addLayout(bottom_layout)

        self._refresh_table()

    def reject(self) -> None:
        self._operation.loop_operations = self._original_loop_ops
        super().reject()

    def _on_start_capture(self) -> None:
        self._capturing = True
        self._capture_btn.setText("⏳ 点击屏幕任意位置...")
        self._capture_btn.setStyleSheet(_BTN_STYLE_SM.format(_C_WARN, "#f5b041", "#d68910"))
        self.showMinimized()
        QTimer.singleShot(200, self._do_grab_mouse)

    def _do_grab_mouse(self) -> None:
        if not self._capturing:
            return
        self.grabMouse()
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def mouseReleaseEvent(self, event) -> None:
        if self._capturing:
            self._capturing = False
            self.releaseMouse()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self._capture_btn.setText("🖱 点击捕获坐标")
            self._capture_btn.setStyleSheet(_BTN_STYLE_SM.format(_C_PLAY, _C_PLAY_H, _C_PLAY_P))
            self._restore_from_capture()
            pos = event.globalPosition().toPoint()
            x, y = pos.x(), pos.y()
            self._op_id_counter += 1
            self._operation.loop_operations.append(Operation(
                id=self._op_id_counter,
                type="mouse_left_click",
                x=x, y=y,
                timestamp=0,
            ))
            self._refresh_table()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if self._capturing and event.key() == Qt.Key.Key_Escape:
            self._capturing = False
            self.releaseMouse()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            self._capture_btn.setText("🖱 点击捕获坐标")
            self._capture_btn.setStyleSheet(_BTN_STYLE_SM.format(_C_PLAY, _C_PLAY_H, _C_PLAY_P))
            self._restore_from_capture()
            return
        super().keyPressEvent(event)

    def _restore_from_capture(self) -> None:
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _get_op_brief(self, op: Operation) -> str:
        type_map = {
            "mouse_left_click": "鼠标左键",
            "mouse_right_click": "鼠标右键",
            "keyboard_type": "键盘输入",
            "keyboard_press": "键盘按键",
            "keyboard_hotkey": "快捷键",
        }
        t = type_map.get(op.type, op.type)
        if op.type in ("mouse_left_click", "mouse_right_click"):
            return f"{t} ({op.x}, {op.y})"
        elif op.type == "keyboard_type":
            return f"{t}: {op.content}"
        elif op.type == "keyboard_press":
            mods = "+".join(op.modifiers) + "+" if op.modifiers else ""
            return f"{t}: {mods}{op.content}"
        elif op.type == "keyboard_hotkey":
            return f"{t}: {'+'.join(op.modifiers)}"
        return t

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        for i, lo in enumerate(self._operation.loop_operations):
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(str(i + 1)))
            self._table.setItem(row, 1, QTableWidgetItem(self._get_op_type_text(lo)))
            self._table.setItem(row, 2, QTableWidgetItem(self._get_op_detail(lo)))

    def _get_op_type_text(self, op: Operation) -> str:
        type_map = {
            "mouse_left_click": "鼠标左键",
            "mouse_right_click": "鼠标右键",
            "keyboard_type": "键盘输入",
            "keyboard_press": "键盘按键",
            "keyboard_hotkey": "快捷键",
        }
        return type_map.get(op.type, op.type)

    def _get_op_detail(self, op: Operation) -> str:
        if op.type in ("mouse_left_click", "mouse_right_click"):
            return f"({op.x}, {op.y})"
        elif op.type == "keyboard_type":
            return f"输入: {op.content}"
        elif op.type == "keyboard_press":
            mods = ",".join(op.modifiers) if op.modifiers else ""
            return f"{mods}{op.content}" if mods else op.content
        elif op.type == "keyboard_hotkey":
            return "+".join(op.modifiers) if op.modifiers else op.content
        return ""

    def _on_add_key(self) -> None:
        key, ok = QInputDialog.getText(self, "添加键盘按键", "按键名称 (如 enter, space, a):")
        if not ok or not key.strip():
            return
        self._op_id_counter += 1
        self._operation.loop_operations.append(Operation(
            id=self._op_id_counter,
            type="keyboard_press",
            content=key.strip(),
            timestamp=0,
        ))
        self._refresh_table()

    def _on_add_text(self) -> None:
        text, ok = QInputDialog.getText(self, "添加键盘输入", "输入文本:")
        if not ok or not text.strip():
            return
        self._op_id_counter += 1
        self._operation.loop_operations.append(Operation(
            id=self._op_id_counter,
            type="keyboard_type",
            content=text.strip(),
            timestamp=0,
        ))
        self._refresh_table()

    def _on_delete_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._operation.loop_operations):
            return
        self._operation.loop_operations.pop(row)
        self._refresh_table()

    def _on_context_menu(self, pos) -> None:
        row = self._table.rowAt(pos.y())
        if row < 0 or row >= len(self._operation.loop_operations):
            return
        op = self._operation.loop_operations[row]
        menu = QMenu(self)
        delete_action = menu.addAction("删除")
        show_pos_action = None
        if op.type in ("mouse_left_click", "mouse_right_click") and op.x is not None and op.y is not None:
            show_pos_action = menu.addAction("显示位置")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == delete_action:
            self._operation.loop_operations.pop(row)
            self._refresh_table()
        elif show_pos_action and action == show_pos_action:
            self._show_loop_position(op.x, op.y)

    def _show_loop_position(self, x: int, y: int) -> None:
        _PositionMarker(x, y)


class _PositionMarker(QWidget):
    def __init__(self, x: int, y: int) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(25, 25)

        screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio() if screen else 1.0
        self.move(int(x / ratio) - 12, int(y / ratio) - 12)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self._timer.start(3000)

        self.show()
        self.raise_()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(255, 0, 0)))
        painter.setPen(QPen(QColor(180, 0, 0), 2))
        painter.drawEllipse(2, 2, 21, 21)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)
