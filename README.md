<br />

***

# Features

- **操作录制** — 录制鼠标左/右键点击（记录坐标）和键盘输入（字符缓冲合并、独立按键、组合快捷键）
- **精准回放** — 按原始时间间隔回放，支持 0.5x\~4.0x 速度调节
- **循环执行** — 支持有限次循环和无限循环
- **轮错机制** — 为操作配置多个备选坐标/按键，循环回放时自动轮换，适应动态变化的界面
- **全局热键** — F9 录制切换、F10 回放切换、Esc 紧急停止（基于 Win32 RegisterHotKey，不与录制监听冲突）
- **模板管理** — 将操作序列保存为模板，随时加载复用
- **系统托盘** — 最小化到托盘，后台运行，托盘菜单控制核心功能
- **便携/安装双版本** — 提供绿色便携版（ZIP）和 Windows 安装包（Setup.exe）

## Quick Start

### 下载即用（推荐）

从 [Releases](https://github.com/yourusername/AutoTap/releases) 下载最新版本：

| 包类型 | 文件                           | 说明               |
| --- | ---------------------------- | ---------------- |
| 安装包 | `AutoTap_Setup_x.x.x.exe`    | 带安装向导，自动创建桌面快捷方式 |
| 便携版 | `AutoTap_x.x.x_Portable.zip` | 解压即用，无需安装        |

> 最低要求：Windows 10 64bit

### 从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/AutoTap.git
cd AutoTap

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python src/main.py
```

## Usage

### 录制操作

1. 点击 **开始录制**（或按 `F9`）
2. 正常操作你的鼠标和键盘，所有操作将被记录
3. 点击 **停止录制**（或按 `F9`）
4. 录制的操作序列显示在操作列表中

> 录制过程中会自动过滤 F9/F10/Esc 等系统快捷键。

### 回放操作

1. 录制完成后，调整 **回放速度** 和 **循环次数**
2. 点击 **开始回放**（或按 `F10`）
3. 回放过程中可点击 **停止**（或按 `Esc`）紧急终止

### 操作列表管理

| 操作    | 说明                      |
| ----- | ----------------------- |
| 删除操作  | 右键 → 删除，或选中后点击清空        |
| 编辑间隔  | 双击表格中的间隔单元格直接修改         |
| 插入轮错  | 右键 → 插入轮错，配置备选坐标或按键     |
| 保存/加载 | 工具栏按钮保存为 JSON 文件或加载已有文件 |
| 保存为模板 | 将当前序列保存为模板，便于后续复用       |

### 全局快捷键

| 快捷键   | 功能          |
| ----- | ----------- |
| `F9`  | 切换录制（开始/停止） |
| `F10` | 切换回放（开始/停止） |
| `Esc` | 紧急停止（录制或回放） |

### 模板管理

右侧面板管理模板：

- **使用** — 加载模板中的操作序列到当前列表
- **删除** — 删除不需要的模板

## Build

### 打包为可执行文件

```bash
pip install pyinstaller
pyinstaller AutoTap.spec
```

输出在 `dist/AutoTap/` 目录。

### 构建安装包

需要安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)：

```bash
python build_installer.py
```

自动生成：

- `dist/AutoTap_x.x.x_Portable.zip` — 便携版
- `dist/AutoTap_x.x.x_Setup.exe` — 安装包

## Tech Stack

| 类别     | 技术                       |
| ------ | ------------------------ |
| 编程语言   | Python 3.10+             |
| GUI 框架 | PyQt6                    |
| 输入监听   | pynput                   |
| 鼠标模拟   | pyautogui                |
| 键盘模拟   | Win32 API (ctypes)       |
| 全局热键   | Win32 RegisterHotKey     |
| 数据存储   | JSON                     |
| 测试     | pytest                   |
| 打包     | PyInstaller + Inno Setup |

## Project Structure

```
AutoTap/
├── src/                    # 源代码
│   ├── main.py             # 程序入口
│   ├── main_window.py      # 主窗口 UI（PyQt6）
│   ├── data_models.py      # 数据模型（Operation / OperationSequence）
│   ├── recorder.py          # 操作录制管理器
│   ├── playback_engine.py  # 回放引擎
│   ├── input_listener.py   # 输入监听封装
│   ├── hotkey_manager.py   # 全局快捷键管理
│   ├── config_manager.py   # 配置管理
│   ├── template_manager.py # 模板管理
│   ├── logger.py           # 日志系统
│   └── system_tray.py      # 系统托盘
├── config/
│   └── settings.json       # 应用配置
├── tests/                  # 单元测试
├── requirements.txt        # Python 依赖
├── AutoTap.spec            # PyInstaller 配置
└── installer.iss           # Inno Setup 安装脚本
```

## License

本项目基于 [MIT License](LICENSE) 开源。

