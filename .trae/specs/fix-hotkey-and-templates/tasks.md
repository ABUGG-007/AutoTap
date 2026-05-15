# Tasks

- [x] Task 1: 重写 HotkeyManager，使用 Win32 RegisterHotKey/UnregisterHotKey API
  - [x] SubTask 1.1: 使用 ctypes 调用 RegisterHotKey 注册 F9(0x78)、F10(0x79)、Esc(0x1B)
  - [x] SubTask 1.2: 使用 QThread + MSG 消息循环监听 WM_HOTKEY 消息
  - [x] SubTask 1.3: 提供 start()/stop() 方法，在窗口显示时启动、关闭时停止
  - [x] SubTask 1.4: 提供回调注册接口：on_record_toggle、on_playback_toggle、on_stop

- [x] Task 2: 在 main.py 中集成 HotkeyManager
  - [x] SubTask 2.1: 创建 HotkeyManager 实例并传入主窗口引用
  - [x] SubTask 2.2: 连接快捷键回调到主窗口的录制/回放/停止方法

- [x] Task 3: 修改 Recorder 过滤快捷键
  - [x] SubTask 3.1: 在 _on_keyboard_press_wrapper 中过滤 F9/F10/Esc 按键，不录入操作序列

- [x] Task 4: 创建 TemplateManager 类
  - [x] SubTask 4.1: 定义模板数据结构（name, created_at, operation_sequence）
  - [x] SubTask 4.2: 实现 CRUD：create_template、delete_template、list_templates、get_template
  - [x] SubTask 4.3: 持久化到 templates/ 目录，每个模板一个 JSON 文件

- [x] Task 5: 修改主窗口 UI，新增模板管理区域
  - [x] SubTask 5.1: 在控制按钮组新增"创建模板"按钮
  - [x] SubTask 5.2: 新增模板管理 QGroupBox：QListWidget 显示模板列表 + "删除模板"/"使用模板"按钮
  - [x] SubTask 5.3: 创建模板流程：点击按钮 → QInputDialog 输入名称 → 开始录制 → 结束后自动保存模板
  - [x] SubTask 5.4: 使用模板流程：选中模板 → 点击"使用模板"或双击 → 加载序列并回放
  - [x] SubTask 5.5: 删除模板流程：选中模板 → 点击"删除模板" → 确认对话框 → 删除

- [x] Task 6: 修改快捷键回调逻辑，支持录制/回放切换
  - [x] SubTask 6.1: F9 切换录制（空闲→开始录制，录制中→停止录制并保存模板）
  - [x] SubTask 6.2: F10 切换回放（空闲→开始回放，回放中→停止回放）
  - [x] SubTask 6.3: Esc 紧急停止（停止录制或回放）

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 5] depends on [Task 4]
- [Task 6] depends on [Task 1, Task 2, Task 5]
