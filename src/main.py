import sys
import os
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, qInstallMessageHandler
from PyQt6.QtGui import QIcon
from src.main_window import AutoTapWindow
from src.logger import init_logger, log_info, log_error


def _qt_message_handler(msg_type, context, msg):
    log_error(f"Qt消息: {msg}", "Qt")


def _global_exception_handler(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log_error(f"未捕获异常:\n{tb_text}", "GlobalExceptionHandler")


def main():
    sys.excepthook = _global_exception_handler
    qInstallMessageHandler(_qt_message_handler)

    init_logger(name="autotap", log_dir="logs")
    log_info("[app] AutoTap 启动中...")

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("AutoTap")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("AutoTap")
    
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(__file__))

    icon_path = os.path.join(base_path, 'icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    try:
        window = AutoTapWindow()
        window.show()
        log_info("[app] AutoTap 启动成功")
        sys.exit(app.exec())
    except Exception as e:
        log_error(f"[app] 启动失败: {e}")
        try:
            QMessageBox.critical(None, "启动错误", f"程序启动失败:\n{str(e)}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
