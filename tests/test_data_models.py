import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_models import Operation, OperationSequence, AppSettings, MOUSE_LEFT_CLICK, MOUSE_RIGHT_CLICK


class TestOperation:
    def test_operation_creation(self):
        op = Operation(
            id=1,
            type=MOUSE_LEFT_CLICK,
            x=100,
            y=200,
            content=None,
            modifiers=[],
            timestamp=1000
        )
        assert op.id == 1
        assert op.type == MOUSE_LEFT_CLICK
        assert op.x == 100
        assert op.y == 200

    def test_operation_to_dict(self):
        op = Operation(
            id=1,
            type=MOUSE_LEFT_CLICK,
            x=100,
            y=200,
            content=None,
            modifiers=[],
            timestamp=1000
        )
        data = op.to_dict()
        assert data['id'] == 1
        assert data['type'] == MOUSE_LEFT_CLICK
        assert data['x'] == 100

    def test_operation_from_dict(self):
        data = {
            'id': 1,
            'type': MOUSE_RIGHT_CLICK,
            'x': 150,
            'y': 250,
            'content': None,
            'modifiers': ['ctrl'],
            'timestamp': 500
        }
        op = Operation.from_dict(data)
        assert op.id == 1
        assert op.type == MOUSE_RIGHT_CLICK
        assert op.modifiers == ['ctrl']


class TestOperationSequence:
    def test_sequence_creation(self):
        seq = OperationSequence()
        assert seq.get_operation_count() == 0
        assert len(seq.operations) == 0

    def test_add_operation(self):
        seq = OperationSequence()
        op = Operation(id=1, type=MOUSE_LEFT_CLICK, x=100, y=200, timestamp=0)
        seq.add_operation(op)
        assert seq.get_operation_count() == 1

    def test_remove_operation(self):
        seq = OperationSequence()
        op1 = Operation(id=1, type=MOUSE_LEFT_CLICK, x=100, y=200, timestamp=0)
        op2 = Operation(id=2, type=MOUSE_RIGHT_CLICK, x=150, y=250, timestamp=500)
        seq.add_operation(op1)
        seq.add_operation(op2)
        seq.remove_operation(1)
        assert seq.get_operation_count() == 1

    def test_clear(self):
        seq = OperationSequence()
        seq.add_operation(Operation(id=1, type=MOUSE_LEFT_CLICK, x=100, y=200, timestamp=0))
        seq.add_operation(Operation(id=2, type=MOUSE_RIGHT_CLICK, x=150, y=250, timestamp=500))
        seq.clear()
        assert seq.get_operation_count() == 0

    def test_save_and_load(self):
        seq = OperationSequence()
        seq.add_operation(Operation(id=1, type=MOUSE_LEFT_CLICK, x=100, y=200, timestamp=0))
        seq.add_operation(Operation(id=2, type=MOUSE_RIGHT_CLICK, x=150, y=250, timestamp=500))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
            seq.save_to_file(temp_path)

        loaded_seq = OperationSequence.load_from_file(temp_path)
        assert loaded_seq.get_operation_count() == 2
        os.unlink(temp_path)


class TestAppSettings:
    def test_default_settings(self):
        settings = AppSettings.get_default_settings()
        assert settings.playback_speed == 1.0
        assert settings.loop_count == 1
        assert settings.infinite_loop == False
        assert settings.auto_startup == False
        assert settings.show_notifications == True

    def test_settings_to_dict(self):
        settings = AppSettings.get_default_settings()
        data = settings.to_dict()
        assert 'playback_speed' in data
        assert 'loop_count' in data

    def test_settings_save_load(self):
        settings = AppSettings.get_default_settings()
        settings.playback_speed = 2.0
        settings.loop_count = 5

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
            settings.save_to_file(temp_path)

        loaded = AppSettings.load_from_file(temp_path)
        assert loaded.playback_speed == 2.0
        assert loaded.loop_count == 5
        os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
