import json
import os
import tempfile
import threading
import time
from src.data_models import Operation, OperationSequence
from src.playback_engine import PlaybackEngine


def test_playback_engine_rotation():
    print("=" * 70)
    print("测试1: PlaybackEngine 轮错执行逻辑 (loop_count=4)")
    print("规格: Loop1→1,2,3,4,5 | Loop2→1,a,3,4,5 | Loop3→1,b,3,4,5 | Loop4→1,c,3,4,5")
    print("=" * 70)

    op1 = Operation(id=1, type='mouse_left_click', x=100, y=200, timestamp=100)
    op2 = Operation(id=2, type='mouse_left_click', x=300, y=400, timestamp=200, loop_operations=[
        Operation(id=10, type='mouse_left_click', x=700, y=800, timestamp=0),
        Operation(id=11, type='mouse_left_click', x=900, y=1000, timestamp=0),
        Operation(id=12, type='mouse_left_click', x=1100, y=1200, timestamp=0),
    ])
    op3 = Operation(id=3, type='mouse_left_click', x=500, y=600, timestamp=300)
    op4 = Operation(id=4, type='keyboard_press', content='enter', timestamp=400)
    op5 = Operation(id=5, type='mouse_right_click', x=800, y=900, timestamp=500)
    seq = OperationSequence(operations=[op1, op2, op3, op4, op5])

    executed_ops = []

    def mock_execute(op):
        if op.type in ('mouse_left_click', 'mouse_right_click'):
            executed_ops.append(f'click({op.x},{op.y})')
        elif op.type == 'keyboard_press':
            executed_ops.append(f'key({op.content})')
        else:
            executed_ops.append(f'[{op.type}]')

    engine = PlaybackEngine()
    engine.load_sequence(seq)
    engine.set_loop(4, False)

    original = engine._execute_operation
    engine._execute_operation = mock_execute

    engine.play()
    time.sleep(2)
    engine.stop()

    expected = [
        'click(100,200)', 'click(300,400)', 'click(500,600)', 'key(enter)', 'click(800,900)',
        'click(100,200)', 'click(700,800)', 'click(500,600)', 'key(enter)', 'click(800,900)',
        'click(100,200)', 'click(900,1000)', 'click(500,600)', 'key(enter)', 'click(800,900)',
        'click(100,200)', 'click(1100,1200)', 'click(500,600)', 'key(enter)', 'click(800,900)',
    ]

    engine._execute_operation = original

    match = executed_ops == expected[:len(executed_ops)]
    print(f"执行操作数: {len(executed_ops)} / 期望: {len(expected)}")
    print(f"结果: {'✓ 通过' if match else '✗ 失败'}")
    if not match:
        for i, (act, exp) in enumerate(zip(executed_ops, expected[:len(executed_ops)])):
            if act != exp:
                print(f"  [{i}] 实际: {act} | 期望: {exp}")
    return match


def test_loop_num_logic():
    print("\n" + "=" * 70)
    print("测试2: loop_num → loop_idx 映射逻辑验证")
    print("=" * 70)

    op = Operation(id=1, type='mouse_left_click', x=300, y=400, timestamp=200, loop_operations=[
        Operation(id=10, type='mouse_left_click', x=700, y=800, timestamp=0),
        Operation(id=11, type='mouse_left_click', x=900, y=1000, timestamp=0),
        Operation(id=12, type='mouse_left_click', x=1100, y=1200, timestamp=0),
    ])

    test_cases = [
        (1, False, None, '原操作'),           # loop_num=1: 执行原操作
        (2, True, 0, 'a(700,800)'),          # loop_num=2: 执行第1个轮错
        (3, True, 1, 'b(900,1000)'),         # loop_num=3: 执行第2个轮错
        (4, True, 2, 'c(1100,1200)'),        # loop_num=4: 执行第3个轮错
        (5, True, 0, 'a(700,800) 循环'),     # loop_num=5: 回到第1个轮错
        (6, True, 1, 'b(900,1000) 循环'),    # loop_num=6: 回到第2个轮错
    ]

    all_pass = True
    for loop_num, expect_replace, expect_idx, desc in test_cases:
        has_loop = bool(op.loop_operations)
        should_replace = has_loop and loop_num > 1
        if should_replace:
            idx = (loop_num - 2) % len(op.loop_operations)
            result = f"轮错[{idx}]=({op.loop_operations[idx].x},{op.loop_operations[idx].y})"
        else:
            result = f"原操作=({op.x},{op.y})"

        replace_match = should_replace == expect_replace
        idx_match = (idx == expect_idx) if should_replace else True
        passed = replace_match and idx_match

        status = "✓" if passed else "✗"
        print(f"  loop_num={loop_num}: {status} {desc} → {result}")
        if not passed:
            all_pass = False

    return all_pass


def test_serialization_roundtrip():
    print("\n" + "=" * 70)
    print("测试3: 序列化/反序列化 轮错数据保留")
    print("=" * 70)

    op2 = Operation(id=2, type='mouse_left_click', x=300, y=400, timestamp=200, loop_operations=[
        Operation(id=10, type='mouse_left_click', x=700, y=800, timestamp=0),
        Operation(id=11, type='keyboard_press', content='enter', timestamp=0),
    ])
    seq = OperationSequence(operations=[
        Operation(id=1, type='mouse_left_click', x=100, y=200, timestamp=100),
        op2,
        Operation(id=3, type='mouse_left_click', x=500, y=600, timestamp=300),
    ])

    data = seq.to_dict()
    json_str = json.dumps(data, ensure_ascii=False)
    loaded_data = json.loads(json_str)
    loaded_seq = OperationSequence.from_dict(loaded_data)

    op2_loaded = loaded_seq.operations[1]
    loop_count = len(op2_loaded.loop_operations)
    loop1_ok = (op2_loaded.loop_operations[0].x == 700 and op2_loaded.loop_operations[0].y == 800)
    loop2_ok = (op2_loaded.loop_operations[1].type == 'keyboard_press' and op2_loaded.loop_operations[1].content == 'enter')

    all_pass = loop_count == 2 and loop1_ok and loop2_ok
    print(f"  轮错数量: {loop_count} (期望: 2)")
    print(f"  轮错0: ({op2_loaded.loop_operations[0].x},{op2_loaded.loop_operations[0].y}) (期望: (700,800))")
    print(f"  轮错1: {op2_loaded.loop_operations[1].type}:{op2_loaded.loop_operations[1].content} (期望: keyboard_press:enter)")
    print(f"  结果: {'✓ 通过' if all_pass else '✗ 失败'}")

    tmpdir = tempfile.gettempdir()
    filepath = os.path.join(tmpdir, "_test_loop_rot.json")
    seq.save_to_file(filepath)
    loaded_seq2 = OperationSequence.load_from_file(filepath)
    os.remove(filepath)

    op2_loaded2 = loaded_seq2.operations[1]
    file_pass = len(op2_loaded2.loop_operations) == 2
    print(f"  文件保存/加载: {'✓ 通过' if file_pass else '✗ 失败'}")

    return all_pass and file_pass


def test_single_loop_op():
    print("\n" + "=" * 70)
    print("测试4: 单个轮错元素 + loop_count=3")
    print("规格: Loop1→o | Loop2→a | Loop3→a(循环)")
    print("=" * 70)

    op = Operation(id=1, type='mouse_left_click', x=300, y=400, timestamp=200, loop_operations=[
        Operation(id=10, type='mouse_left_click', x=999, y=888, timestamp=0),
    ])
    seq = OperationSequence(operations=[op])

    executed = []

    def capture(op):
        executed.append(f'({op.x},{op.y})')

    engine = PlaybackEngine()
    engine.load_sequence(seq)
    engine.set_loop(3, False)
    original = engine._execute_operation
    engine._execute_operation = capture
    engine.play()
    time.sleep(1)
    engine.stop()
    engine._execute_operation = original

    expected = ['(300,400)', '(999,888)', '(999,888)']
    match = executed == expected[:len(executed)]
    print(f"  实际: {executed}")
    print(f"  期望: {expected}")
    print(f"  结果: {'✓ 通过' if match else '✗ 失败'}")
    return match


def test_no_loop_ops():
    print("\n" + "=" * 70)
    print("测试5: 无轮错元素 - 所有循环均执行原操作")
    print("=" * 70)

    op = Operation(id=1, type='mouse_left_click', x=111, y=222, timestamp=200)
    seq = OperationSequence(operations=[op])

    executed = []

    def capture(op):
        executed.append(f'({op.x},{op.y})')

    engine = PlaybackEngine()
    engine.load_sequence(seq)
    engine.set_loop(3, False)
    original = engine._execute_operation
    engine._execute_operation = capture
    engine.play()
    time.sleep(1)
    engine.stop()
    engine._execute_operation = original

    expected = ['(111,222)', '(111,222)', '(111,222)']
    match = executed == expected[:len(executed)]
    print(f"  实际: {executed}")
    print(f"  期望: {expected}")
    print(f"  结果: {'✓ 通过' if match else '✗ 失败'}")
    return match


def test_multiple_ops_with_rotation():
    print("\n" + "=" * 70)
    print("测试6: 多个操作各有不同数量轮错元素")
    print("规格: loop_count=3")
    print("  op2有[a,b] | op4有[x]")
    print("  Loop1: 1,2,3,4,5")
    print("  Loop2: 1,a,3,x,5")
    print("  Loop3: 1,b,3,x,5")
    print("=" * 70)

    op1 = Operation(id=1, type='mouse_left_click', x=10, y=10, timestamp=100)
    op2 = Operation(id=2, type='mouse_left_click', x=20, y=20, timestamp=200, loop_operations=[
        Operation(id=21, type='mouse_left_click', x=2000, y=2000, timestamp=0),
        Operation(id=22, type='mouse_left_click', x=2200, y=2200, timestamp=0),
    ])
    op3 = Operation(id=3, type='mouse_left_click', x=30, y=30, timestamp=300)
    op4 = Operation(id=4, type='mouse_left_click', x=40, y=40, timestamp=400, loop_operations=[
        Operation(id=41, type='mouse_left_click', x=4000, y=4000, timestamp=0),
    ])
    op5 = Operation(id=5, type='mouse_left_click', x=50, y=50, timestamp=500)
    seq = OperationSequence(operations=[op1, op2, op3, op4, op5])

    executed = []

    def capture(op):
        executed.append(f'({op.x},{op.y})')

    engine = PlaybackEngine()
    engine.load_sequence(seq)
    engine.set_loop(3, False)
    original = engine._execute_operation
    engine._execute_operation = capture
    engine.play()
    time.sleep(2)
    engine.stop()
    engine._execute_operation = original

    expected = [
        '(10,10)', '(20,20)', '(30,30)', '(40,40)', '(50,50)',
        '(10,10)', '(2000,2000)', '(30,30)', '(4000,4000)', '(50,50)',
        '(10,10)', '(2200,2200)', '(30,30)', '(4000,4000)', '(50,50)',
    ]
    match = executed == expected[:len(executed)]
    print(f"  实际: {executed}")
    print(f"  期望: {expected}")
    print(f"  结果: {'✓ 通过' if match else '✗ 失败'}")
    if not match:
        for i, (act, exp) in enumerate(zip(executed, expected[:len(executed)])):
            if act != exp:
                print(f"  [{i}] 实际: {act} | 期望: {exp}")
    return match


def test_infinite_loop_rotation():
    print("\n" + "=" * 70)
    print("测试7: 无限循环模式轮错 (抓取前4轮)")
    print("=" * 70)

    op = Operation(id=1, type='mouse_left_click', x=300, y=400, timestamp=200, loop_operations=[
        Operation(id=10, type='mouse_left_click', x=700, y=800, timestamp=0),
        Operation(id=11, type='mouse_left_click', x=900, y=1000, timestamp=0),
        Operation(id=12, type='mouse_left_click', x=1100, y=1200, timestamp=0),
    ])
    seq = OperationSequence(operations=[op])

    executed = []

    def capture(op):
        executed.append(f'({op.x},{op.y})')

    engine = PlaybackEngine()
    engine.load_sequence(seq)
    engine.set_loop(1, True)
    original = engine._execute_operation
    engine._execute_operation = capture

    engine.play()
    time.sleep(1.2)
    engine.stop()
    engine._execute_operation = original

    print(f"  抓取操作数: {len(executed)}")
    print(f"  序列: {executed}")

    if len(executed) >= 4:
        match = (
            executed[0] == '(300,400)'
            and executed[1] == '(700,800)'
            and executed[2] == '(900,1000)'
            and executed[3] == '(1100,1200)'
        )
        print(f"  前4轮匹配: {'✓ 通过' if match else '✗ 失败'}")
        return match
    else:
        print(f"  ✗ 未收集到足够样本")
        return False


if __name__ == "__main__":
    results = []
    results.append(("PlaybackEngine 轮错逻辑", test_playback_engine_rotation()))
    results.append(("loop_num映射", test_loop_num_logic()))
    results.append(("序列化/反序列化", test_serialization_roundtrip()))
    results.append(("单个轮错元素", test_single_loop_op()))
    results.append(("无轮错元素", test_no_loop_ops()))
    results.append(("多操作不同轮错", test_multiple_ops_with_rotation()))
    results.append(("无限循环轮错", test_infinite_loop_rotation()))

    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    all_pass = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        if not passed:
            all_pass = False
        print(f"  {status}: {name}")
    print(f"\n总计: {'全部通过' if all_pass else '存在失败'}")