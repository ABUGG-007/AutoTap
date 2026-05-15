"""
数据模型模块。

提供自动化点击工具的核心数据结构定义，包括操作记录、操作序列和应用设置。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


MOUSE_LEFT_CLICK = "mouse_left_click"
MOUSE_RIGHT_CLICK = "mouse_right_click"
MOUSE_MOVE = "mouse_move"
KEYBOARD_TYPE = "keyboard_type"
KEYBOARD_PRESS = "keyboard_press"
KEYBOARD_HOTKEY = "keyboard_hotkey"


@dataclass
class Operation:
    """表示单个操作的数据类。

    Attributes:
        id: 操作的唯一标识符。
        type: 操作类型（如 mouse_left_click, keyboard_type 等）。
        x: 鼠标操作的 X 坐标（对于非鼠标操作可为 None）。
        y: 鼠标操作的 Y 坐标（对于非鼠标操作可为 None）。
        content: 文本内容（如键盘输入的内容，可为 None）。
        modifiers: 修饰键列表（如 ['ctrl', 'shift']）。
        timestamp: 操作相对于录制开始的时间戳（毫秒）。
    """

    id: int
    type: str
    x: Optional[int] = None
    y: Optional[int] = None
    content: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    timestamp: int = 0
    loop_operations: list[Operation] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "content": self.content,
            "modifiers": self.modifiers,
            "timestamp": self.timestamp,
        }
        if self.loop_operations:
            d["loop_operations"] = [op.to_dict() for op in self.loop_operations]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Operation:
        loop_ops_data = data.get("loop_operations", [])
        loop_ops = [cls.from_dict(lo) for lo in loop_ops_data]
        return cls(
            id=data.get("id", 0),
            type=data.get("type", ""),
            x=data.get("x"),
            y=data.get("y"),
            content=data.get("content"),
            modifiers=data.get("modifiers", []),
            timestamp=data.get("timestamp", 0),
            loop_operations=loop_ops,
        )


@dataclass
class OperationSequence:
    """表示操作序列的数据类，包含元数据和操作列表。

    Attributes:
        metadata: 序列元数据字典，包含版本、创建时间等信息。
        operations: 操作列表。
    """

    metadata: dict = field(default_factory=dict)
    operations: list[Operation] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化元数据默认值。"""
        if not self.metadata:
            self.metadata = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "total_duration": 0,
            }

    def add_operation(self, operation: Operation) -> None:
        """添加一个操作到序列中。

        Args:
            operation: 要添加的 Operation 实例。
        """
        self.operations.append(operation)
        self._update_duration()

    def remove_operation(self, op_id: int) -> bool:
        """从序列中移除指定 ID 的操作。

        Args:
            op_id: 要移除的操作的 ID。

        Returns:
            如果找到并移除操作返回 True，否则返回 False。
        """
        for i, op in enumerate(self.operations):
            if op.id == op_id:
                self.operations.pop(i)
                self._update_duration()
                return True
        return False

    def clear(self) -> None:
        """清空所有操作并重置元数据。"""
        self.operations.clear()
        self.metadata = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "total_duration": 0,
        }

    def get_operation_count(self) -> int:
        """获取当前操作数量。

        Returns:
            操作列表中的操作数量。
        """
        return len(self.operations)

    def to_dict(self) -> dict:
        """将操作序列转换为字典格式。

        Returns:
            包含元数据和操作列表的字典。
        """
        return {
            "metadata": self.metadata,
            "operations": [op.to_dict() for op in self.operations],
        }

    @classmethod
    def from_dict(cls, data: dict) -> OperationSequence:
        """从字典创建操作序列对象。

        Args:
            data: 包含操作序列数据的字典。

        Returns:
            新创建的 OperationSequence 实例。
        """
        metadata = data.get("metadata", {})
        operations_data = data.get("operations", [])
        operations = [Operation.from_dict(op_data) for op_data in operations_data]

        sequence = cls(metadata=metadata, operations=operations)
        return sequence

    def save_to_file(self, filepath: str) -> None:
        """将操作序列保存到 JSON 文件。

        Args:
            filepath: 保存文件的路径。

        Raises:
            IOError: 文件写入失败时抛出。
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, filepath: str) -> OperationSequence:
        """从 JSON 文件加载操作序列。

        Args:
            filepath: 要加载的文件的路径。

        Returns:
            加载的 OperationSequence 实例。

        Raises:
            FileNotFoundError: 文件不存在时抛出。
            json.JSONDecodeError: JSON 解析失败时抛出。
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)

    def _update_duration(self) -> None:
        """更新序列的总持续时间。"""
        if self.operations:
            last_op = max(self.operations, key=lambda op: op.timestamp)
            self.metadata["total_duration"] = last_op.timestamp
        else:
            self.metadata["total_duration"] = 0


@dataclass
class AppSettings:
    """应用设置的数据类。

    Attributes:
        playback_speed: 回放速度倍率（1.0 表示正常速度）。
        loop_count: 循环次数（仅在 infinite_loop 为 False 时有效）。
        infinite_loop: 是否无限循环播放。
        auto_startup: 是否开机自启动。
        show_notifications: 是否显示通知。
        global_hotkeys: 全局快捷键配置字典。
    """

    playback_speed: float = 1.0
    loop_count: int = 1
    infinite_loop: bool = False
    auto_startup: bool = False
    show_notifications: bool = True
    global_hotkeys: dict[str, str] = field(default_factory=lambda: {
        "start_recording": "F9",
        "start_playback": "F10",
        "stop": "Esc",
    })

    DEFAULT_FILE_PATH: str = field(default="settings.json", repr=False)

    @classmethod
    def get_default_settings(cls) -> AppSettings:
        """获取默认设置。

        Returns:
            包含默认值的 AppSettings 实例。
        """
        return cls()

    def load_from_file(self, filepath: str | None = None) -> bool:
        """从 JSON 文件加载设置。

        Args:
            filepath: 设置文件路径，默认为 DEFAULT_FILE_PATH。

        Returns:
            如果成功加载返回 True，否则返回 False。
        """
        filepath = filepath or self.DEFAULT_FILE_PATH

        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.playback_speed = data.get("playback_speed", 1.0)
            self.loop_count = data.get("loop_count", 1)
            self.infinite_loop = data.get("infinite_loop", False)
            self.auto_startup = data.get("auto_startup", False)
            self.show_notifications = data.get("show_notifications", True)
            self.global_hotkeys = data.get("global_hotkeys", self.global_hotkeys)

            return True
        except (json.JSONDecodeError, IOError):
            return False

    def save_to_file(self, filepath: str | None = None) -> bool:
        """将设置保存到 JSON 文件。

        Args:
            filepath: 保存文件的路径，默认为 DEFAULT_FILE_PATH。

        Returns:
            如果成功保存返回 True，否则返回 False。
        """
        filepath = filepath or self.DEFAULT_FILE_PATH

        try:
            data = {
                "playback_speed": self.playback_speed,
                "loop_count": self.loop_count,
                "infinite_loop": self.infinite_loop,
                "auto_startup": self.auto_startup,
                "show_notifications": self.show_notifications,
                "global_hotkeys": self.global_hotkeys,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except IOError:
            return False
