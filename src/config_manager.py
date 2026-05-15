"""
配置管理模块

提供应用程序配置的加载、保存和默认值管理功能。
支持 JSON 格式的配置文件持久化存储。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .logger import log_info, log_warning
except ImportError:
    from logger import log_info, log_warning


@dataclass
class AppSettings:
    """应用程序设置数据类

    包含所有可配置的应用程序参数。

    Attributes:
        playback_speed: 回放速度倍率 (0.5-4.0)
        loop_count: 循环次数
        infinite_loop: 是否无限循环
        auto_startup: 是否开机自启动
        show_notifications: 是否显示通知
        global_hotkeys: 全局快捷键配置
    """

    playback_speed: float = 1.0
    loop_count: int = 1
    infinite_loop: bool = False
    auto_startup: bool = False
    show_notifications: bool = True
    global_hotkeys: Dict[str, str] = field(
        default_factory=lambda: {
            "record": "F9",
            "playback": "F10",
            "stop": "ESC",
        }
    )

    def validate(self) -> bool:
        """验证配置项是否有效

        Returns:
            配置是否有效
        """
        if not 0.5 <= self.playback_speed <= 4.0:
            log_warning(
                f"playback_speed 必须在 0.5-4.0 范围内，当前值: {self.playback_speed}"
            )
            return False

        if self.loop_count < 1:
            log_warning(
                f"loop_count 必须 >= 1，当前值: {self.loop_count}"
            )
            return False

        required_hotkeys = {"record", "playback", "stop"}
        if set(self.global_hotkeys.keys()) != required_hotkeys:
            log_warning(
                f"global_hotkeys 必须包含 {required_hotkeys}，当前键: {set(self.global_hotkeys.keys())}"
            )
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            "playback_speed": self.playback_speed,
            "loop_count": self.loop_count,
            "infinite_loop": self.infinite_loop,
            "auto_startup": self.auto_startup,
            "show_notifications": self.show_notifications,
            "global_hotkeys": self.global_hotkeys.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        """从字典创建实例

        Args:
            data: 配置字典

        Returns:
            AppSettings 实例
        """
        return cls(
            playback_speed=data.get("playback_speed", 1.0),
            loop_count=data.get("loop_count", 1),
            infinite_loop=data.get("infinite_loop", False),
            auto_startup=data.get("auto_startup", False),
            show_notifications=data.get("show_notifications", True),
            global_hotkeys=data.get(
                "global_hotkeys",
                {"record": "F9", "playback": "F10", "stop": "ESC"},
            ),
        )


class ConfigManager:
    """配置管理器类

    负责配置文件的加载、保存和默认值管理。

    Attributes:
        _config_path: 配置文件路径
        _settings: 当前配置实例
    """

    DEFAULT_CONFIG_PATH: str = "config/settings.json"

    def __init__(self, config_path: Optional[str] = None) -> None:
        """初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为 "config/settings.json"
        """
        self._config_path = Path(
            config_path if config_path else self.DEFAULT_CONFIG_PATH
        )
        self._settings: Optional[AppSettings] = None
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

    def get_default_settings(self) -> AppSettings:
        """获取默认配置

        Returns:
            AppSettings 默认配置实例
        """
        return AppSettings()

    def load_settings(self) -> AppSettings:
        """加载配置文件

        如果配置文件不存在或读取失败，返回默认配置。

        Returns:
            AppSettings 配置实例
        """
        if not self._config_path.exists():
            log_info(
                f"配置文件不存在，使用默认配置: {self._config_path}"
            )
            self._settings = self.get_default_settings()
            return self._settings

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._settings = AppSettings.from_dict(data)

            if not self._settings.validate():
                log_warning("配置验证失败，使用默认配置")
                self._settings = self.get_default_settings()

            log_info(f"成功加载配置: {self._config_path}")
            return self._settings

        except json.JSONDecodeError as e:
            log_warning(f"配置文件格式错误: {e}，使用默认配置")
            self._settings = self.get_default_settings()
            return self._settings

        except Exception as e:
            log_warning(f"加载配置文件失败: {e}，使用默认配置")
            self._settings = self.get_default_settings()
            return self._settings

    def save_settings(self, settings: Optional[AppSettings] = None) -> bool:
        """保存配置到文件

        Args:
            settings: 要保存的配置，为 None 时保存当前配置

        Returns:
            保存是否成功
        """
        if settings is None:
            settings = self._settings

        if settings is None:
            log_warning("没有可保存的配置")
            return False

        if not settings.validate():
            log_warning("配置验证失败，取消保存")
            return False

        try:
            self._ensure_config_dir()

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=4, ensure_ascii=False)

            self._settings = settings
            log_info(f"配置已保存: {self._config_path}")
            return True

        except Exception as e:
            log_warning(f"保存配置失败: {e}")
            return False

    @property
    def settings(self) -> Optional[AppSettings]:
        """获取当前配置

        Returns:
            当前配置实例
        """
        return self._settings

    @property
    def config_path(self) -> Path:
        """获取配置文件路径

        Returns:
            配置文件路径
        """
        return self._config_path


_config_manager_instance: Optional[ConfigManager] = None


def init_config(config_path: Optional[str] = None) -> ConfigManager:
    """初始化全局配置管理器

    Args:
        config_path: 配置文件路径

    Returns:
        ConfigManager 实例
    """
    global _config_manager_instance
    _config_manager_instance = ConfigManager(config_path)
    return _config_manager_instance


def load_settings() -> AppSettings:
    """便捷函数：加载配置

    Returns:
        AppSettings 配置实例
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        init_config()
    return _config_manager_instance.load_settings()


def save_settings(settings: AppSettings) -> bool:
    """便捷函数：保存配置

    Args:
        settings: 要保存的配置

    Returns:
        保存是否成功
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        init_config()
    return _config_manager_instance.save_settings(settings)


def get_settings() -> Optional[AppSettings]:
    """获取当前配置

    Returns:
        当前配置实例
    """
    global _config_manager_instance
    if _config_manager_instance is not None:
        return _config_manager_instance.settings
    return None
