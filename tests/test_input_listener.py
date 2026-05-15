import pytest
import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.input_listener import InputListener


class TestInputListener:
    def test_listener_creation(self):
        listener = InputListener()
        assert listener is not None
        assert listener.is_listening() == False

    def test_register_callback(self):
        listener = InputListener()
        callback_called = {'count': 0}

        def test_callback(x, y, button):
            callback_called['count'] += 1

        listener.register_callback("on_mouse_click", test_callback)
        assert "on_mouse_click" in listener._callbacks

    def test_start_stop(self):
        listener = InputListener()
        listener.start()
        time.sleep(0.1)
        assert listener.is_listening() == True
        listener.stop()
        time.sleep(0.1)
        assert listener.is_listening() == False

    def test_context_manager(self):
        with InputListener() as listener:
            listener.start()
            assert listener.is_listening() == True
        time.sleep(0.1)
        assert listener.is_listening() == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
