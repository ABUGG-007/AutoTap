<br />

# AutoTap

轻量级 Windows 桌面自动化操作录制与回放工具

录制 → 回放 → 循环 → 轮错

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.5+-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

***

## 功能特性

- 🎬 **操作录制** — 录制鼠标点击（左键/右键）和键盘输入（字符、独立按键、组合快捷键），自动过滤系统快捷键
- ⏱️ **精准回放** — 按原始时间间隔回放，支持 0.5x \~ 4.0x 速度调节
- 🔁 **循环执行** — 支持有限次循环和无限循环
- 🔄 **轮错机制** — 为操作配置多个备选坐标/按键，循环回放时自动轮换，适应动态界面
- ⏸️ **暂停/恢复** — 回放过程中按 F10 暂停，再按 F10 从暂停位置继续，无需从头开始
- 📺 **回放悬浮窗** — 回放时屏幕右上角显示半透明进度悬浮窗，实时显示轮数进度（已完成/总轮数）
- ⌨️ **全局热键** — F9 录制 / F10 暂停与回放 / Esc 停止，基于 Win32 RegisterHotKey 实现，不与录制监听冲突
- 📋 **模板管理** — 保存操作序列为模板，随时加载复用
- 🖥️ **系统托盘** — 最小化到托盘后台运行，托盘菜单控制核心功能
- 📦 **双版本分发** — 绿色便携版（ZIP）和 Windows 安装包（Setup.exe）

## 快速开始

### 下载安装

从 [Releases](https://github.com/ABUGG-007/AutoTap/releases) 下载最新版本：

| 包类型 | 文件                           | 说明               |
| --- | ---------------------------- | ---------------- |
| 安装包 | `AutoTap_2.0.0_Setup.exe` | 解压后运行 install.bat 安装，自动创建桌面快捷方式 |
| 便携版 | `AutoTap_2.0.0_Portable.zip` | 解压即用，无需安装 |

> 系统要求：Windows 10 64bit 及以上

### 从源码运行

```bash
git clone https://github.com/ABUGG-007/AutoTap.git
cd AutoTap
pip install -r requirements.txt
python src/main.py
```

## 使用指南

### 基本流程

1. 按 `F9` 或点击 **开始录制**，正常操作鼠标和键盘
2. 再按 `F9` 停止录制，操作序列显示在列表中
3. 调整回放速度和循环次数
4. 按 `F10` 或点击 **开始回放**，主窗口自动最小化，右上角显示回放进度悬浮窗
5. 回放中按 `F10` 暂停，再按 `F10` 从暂停位置继续
6. 按 `Esc` 停止回放

### 快捷键

| 快捷键   | 功能          |
| ----- | ----------- |
| `F9`  | 切换录制（开始/停止） |
| `F10` | 暂停/恢复回放，未回放时开始回放 |
| `Esc` | 停止录制或回放 |

### 回放悬浮窗

回放开始后，屏幕右上角自动显示半透明进度悬浮窗：

- **有限循环模式**：显示 `已完成轮数/总轮数`（如 `7/10`），附带进度条
- **无限循环模式**：显示已完成轮数（如 `15`）
- 悬浮窗不接受任何交互，点击穿透
- 回放完成或按 Esc 停止后自动关闭

### 操作列表管理

- **删除** — 右键操作 → 删除
- **编辑间隔** — 双击间隔单元格直接修改
- **插入轮错** — 右键操作 → 插入轮错，配置备选坐标或按键
- **保存/加载** — 保存为 JSON 文件或加载已有文件
- **保存为模板** — 将当前序列保存为模板供后续复用

### 轮错机制说明

轮错（Round-Robin Error Offset）允许为单个操作配置多个备选执行方案。回放时，第 1 轮执行原始操作，从第 2 轮起依次轮换执行备选操作，循环复用。

例如：某点击操作配置了 3 个轮错坐标 A、B、C，则：

- 第 1 轮 → 原始坐标
- 第 2 轮 → 坐标 A
- 第 3 轮 → 坐标 B
- 第 4 轮 → 坐标 C
- 第 5 轮 → 坐标 A（循环）

## 技术栈

| 类别     | 技术                           |
| ------ | ---------------------------- |
| 编程语言   | Python 3.10+                 |
| GUI 框架 | PyQt6                        |
| 输入监听   | pynput                       |
| 鼠标模拟   | pyautogui                    |
| 键盘模拟   | Win32 SendInput API (ctypes) |
| 全局热键   | Win32 RegisterHotKey API     |
| 数据存储   | JSON                         |
| 打包分发   | PyInstaller + Inno Setup     |

## 项目结构

```
AutoTap/
├── src/                     # 源代码
│   ├── main.py              # 程序入口
│   ├── main_window.py       # 主窗口 UI（PyQt6）
│   ├── data_models.py       # 数据模型（Operation / OperationSequence）
│   ├── recorder.py          # 操作录制管理器
│   ├── playback_engine.py   # 回放引擎
│   ├── input_listener.py    # 输入监听封装（pynput）
│   ├── hotkey_manager.py    # 全局快捷键管理（Win32 API）
│   ├── config_manager.py    # 配置管理
│   ├── template_manager.py  # 模板管理
│   ├── logger.py            # 日志系统
│   └── system_tray.py       # 系统托盘
├── config/
│   └── settings.json        # 应用配置
├── requirements.txt         # Python 依赖
├── AutoTap.spec             # PyInstaller 打包配置
├── installer.iss            # Inno Setup 安装脚本
└── build_installer.py       # 构建安装包脚本
```

## 从源码构建

### 打包为可执行文件

```bash
pip install pyinstaller
pyinstaller AutoTap.spec
```

输出在 `dist/AutoTap/` 目录。

### 构建安装包

需先安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)，然后：

```bash
python build_installer.py
```

自动生成：

- `dist/AutoTap_x.x.x_Portable.zip` — 便携版
- `dist/AutoTap_x.x.x_Setup.exe` — 安装包

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
