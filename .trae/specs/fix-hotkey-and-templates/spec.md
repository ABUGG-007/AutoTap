# 修复快捷键 & 新增模板管理功能 Spec

## Why
1. F9/F10/Esc 全局快捷键完全无响应——`HotkeyManager` 从未被实例化，且 pynput 双监听器方案与录制监听器冲突
2. 缺少模板管理能力，用户无法保存、复用录制序列

## What Changes
- 使用 Windows `RegisterHotKey`/`UnregisterHotKey` API（ctypes）替换 pynput 实现全局快捷键，彻底避免与录制监听器的冲突
- 在主窗口新增模板管理区域：创建模板按钮、模板列表、删除模板、选择模板回放
- 新增 `TemplateManager` 类管理模板的 CRUD 和持久化存储
- 录制流程改造：创建模板 → 输入名称 → 开始录制 → 结束后自动保存为模板

## Impact
- Affected code: `hotkey_manager.py`（重写）、`main_window.py`（大幅修改）、`main.py`（集成快捷键）
- Affected data: 新增 `templates/` 目录存储模板 JSON 文件
- **BREAKING**: `HotkeyManager` 类接口完全变更，从 pynput 方案切换到 Win32 API

## ADDED Requirements

### Requirement: 全局快捷键（Win32 API）
系统 SHALL 使用 Windows `RegisterHotKey`/`UnregisterHotKey` API 注册全局快捷键，确保在任何应用前台时快捷键均可响应。

#### Scenario: F9 触发录制切换
- **WHEN** 用户按下 F9
- **THEN** 若当前空闲则开始录制，若当前录制中则停止录制

#### Scenario: F10 触发回放切换
- **WHEN** 用户按下 F10
- **THEN** 若当前空闲则开始回放，若当前回放中则停止回放

#### Scenario: Esc 紧急停止
- **WHEN** 用户按下 Esc
- **THEN** 立即停止当前录制或回放

#### Scenario: 快捷键不与录制冲突
- **WHEN** 录制进行中用户按下 F9/F10/Esc
- **THEN** 快捷键正常触发对应功能，且 F9/F10/Esc 按键不被录入操作序列

### Requirement: 模板管理
系统 SHALL 提供模板管理功能，支持创建、保存、删除和选择模板进行回放。

#### Scenario: 创建模板
- **WHEN** 用户点击"创建模板"按钮
- **THEN** 弹出输入框要求输入模板名称，确认后自动开始录制

#### Scenario: 保存模板
- **WHEN** 录制结束（用户点击结束录制或按 F9 停止）
- **THEN** 录制内容自动保存为以输入名称命名的模板，模板列表刷新

#### Scenario: 删除模板
- **WHEN** 用户在模板列表中选择一个模板并点击"删除模板"
- **THEN** 弹出确认对话框，确认后删除该模板，模板列表刷新

#### Scenario: 选择模板回放
- **WHEN** 用户在模板列表中选择一个模板并点击"使用模板"（或双击）
- **THEN** 加载该模板的操作序列并开始回放

#### Scenario: 模板持久化
- **WHEN** 模板被创建或删除
- **THEN** 变更持久化到 `templates/` 目录下的 JSON 文件

## MODIFIED Requirements

### Requirement: 主窗口布局
主窗口 SHALL 在控制按钮区域新增"创建模板"按钮，在操作列表下方新增模板管理区域（模板列表 + 删除/使用按钮）。

### Requirement: 录制流程
录制流程 SHALL 支持两种模式：
1. 普通录制（点击"开始录制"按钮，行为不变）
2. 模板录制（点击"创建模板"按钮，先输入名称再录制，结束后自动保存为模板）

### Requirement: 快捷键过滤
录制器 SHALL 过滤 F9、F10、Esc 按键，不将其录入操作序列。
