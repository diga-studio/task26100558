"""FlowGuard 验证测试。"""
from __future__ import annotations

import random
import unittest

from flowguard import Event, EventKind, Problem, choose_slot
from tests.brute_force import brute_force_slot


def make_problem(**overrides) -> Problem:
    base = dict(
        participants=["a", "b"],
        work_hours={
            "a": [(0, 20000), None, None, None, None],
            "b": [(18000, 38000), None, None, None, None],
        },
        events={},
        blocked=[],
        duration=900,
    )
    base.update(overrides)
    return Problem(**base)


class GivenExampleTest(unittest.TestCase):
    def test_two_people_first_day(self):
        problem = make_problem()
        slot = choose_slot(problem)
        self.assertIsNotNone(slot)
        self.assertEqual(slot.start, 18550)
        self.assertEqual(slot.end, 18550 + 900)
        # 用参考实现复核损失：最大个人损失 1450，总损失 2900。
        from tests.brute_force import _losses

        losses = _losses(problem, 0, slot.start)
        self.assertEqual(max(losses), 1450)
        self.assertEqual(sum(losses), 2900)


class DirectedTest(unittest.TestCase):
    def test_threshold_both_sides(self):
        # 5400 恰好达标：容量 5400，插入后两段都 < 5400，损失恒为 5400，
        # 所有起点并列，取最早起点 0。
        problem = Problem(
            participants=["a"],
            work_hours={"a": [(0, 5400), None, None, None, None]},
            duration=900,
        )
        self.assertEqual(choose_slot(problem).start, 0)
        # 5399 不达标：插入前后容量都是 0，损失 0，同样取最早起点。
        problem.work_hours["a"] = [(0, 5399), None, None, None, None]
        self.assertEqual(choose_slot(problem).start, 0)

    def test_threshold_split(self):
        # 10800 的段：插在最左损失 900（右侧剩 9900 仍达标），
        # 插在中间会把两侧都打到阈值以下，损失 10800。
        problem = Problem(
            participants=["a"],
            work_hours={"a": [(0, 10800), None, None, None, None]},
            duration=900,
        )
        self.assertEqual(choose_slot(problem).start, 0)

    def test_focus_block_protects_but_contributes(self):
        # focus_block 禁止落会但不切断专注段：容量仍按完整 10000 计算，
        # 最优是把会议贴到最左端，损失 900。
        problem = Problem(
            participants=["a"],
            work_hours={"a": [(0, 10000), None, None, None, None]},
            events={"a": [Event(4000, 6000, EventKind.FOCUS_BLOCK)]},
            duration=900,
        )
        slot = choose_slot(problem)
        self.assertEqual(slot.start, 0)
        # 会议不得与 focus_block 重叠：把 focus_block 挪到最左端后，
        # 可行起点为 5000..9100；s>=5400 时左段达标，损失 10000-s，
        # 最优取最右端 9100（损失 900）。
        problem.events["a"] = [Event(0, 5000, EventKind.FOCUS_BLOCK)]
        self.assertEqual(choose_slot(problem).start, 9100)

    def test_no_solution(self):
        # 禁会区间覆盖全部共同工作时段。
        problem = make_problem(blocked=[(15000, 25000)])
        self.assertIsNone(choose_slot(problem))
        # 无共同工作时段。
        problem = make_problem(
            work_hours={
                "a": [(0, 10000), None, None, None, None],
                "b": [(20000, 30000), None, None, None, None],
            }
        )
        self.assertIsNone(choose_slot(problem))
        # 共同时段短于会议时长。
        problem = make_problem(
            work_hours={
                "a": [(0, 20000), None, None, None, None],
                "b": [(19500, 38000), None, None, None, None],
            }
        )
        self.assertIsNone(choose_slot(problem))

    def test_touching_boundaries_ok(self):
        # 边界相接不算重叠：会议可以紧贴已有事件。
        problem = Problem(
            participants=["a"],
            work_hours={"a": [(0, 2000), None, None, None, None]},
            events={"a": [Event(0, 500, EventKind.MEETING)]},
            duration=900,
        )
        self.assertEqual(choose_slot(problem).start, 500)


def random_problem(rng: random.Random) -> Problem:
    participants = ["a", "b", "c"][: rng.randint(1, 3)]
    work_hours = {}
    events = {}
    for person in participants:
        windows = []
        for _ in range(5):
            if rng.random() < 0.6:
                start = rng.randint(0, 3000)
                windows.append((start, start + rng.randint(1500, 12000)))
            else:
                windows.append(None)
        work_hours[person] = windows
        person_events = []
        for _ in range(rng.randint(0, 6)):
            start = rng.randint(-1000, 9000)  # 允许跨越工作时段边界
            kind = rng.choice(list(EventKind))
            person_events.append(
                Event(start, start + rng.randint(300, 3000), kind)
            )
        if person_events and rng.random() < 0.5:
            person_events.append(person_events[-1])  # 重复事件
        events[person] = person_events
    blocked = []
    for _ in range(rng.randint(0, 3)):
        start = rng.randint(-500, 9000)
        blocked.append((start, start + rng.randint(300, 4000)))
    return Problem(
        participants=participants,
        work_hours=work_hours,
        events=events,
        blocked=blocked,
        duration=rng.choice([900, 1800, 3600, 7200]),
    )


class RandomizedTest(unittest.TestCase):
    def test_matches_brute_force(self):
        for seed in range(120):
            rng = random.Random(seed)
            problem = random_problem(rng)
            expected = brute_force_slot(problem)
            slot = choose_slot(problem)
            actual = None if slot is None else (slot.start, slot.end)
            self.assertEqual(actual, expected, f"seed={seed}")


if __name__ == "__main__":
    unittest.main()
