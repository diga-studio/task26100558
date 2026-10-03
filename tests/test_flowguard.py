"""FlowGuard 验证：固定用例、定向边界用例、随机输入对照逐秒穷举。"""

from __future__ import annotations

import random
import unittest

from flowguard import Interval, Participant, choose_slot
from flowguard.capacity import FOCUS_THRESHOLD


def brute_force(participants, blocked, duration):
    """独立实现的逐秒穷举 oracle：返回 (start, max_loss, total_loss) 或 None。"""
    best = None
    for day in range(5):
        windows = [p.work_windows[day] for p in participants]
        lo = max(w.start for w in windows)
        hi = min(w.end for w in windows)
        for start in range(lo, hi - duration + 1):
            end = start + duration
            feasible = True
            for person in participants:
                events = person.meetings + person.personal + person.focus_blocks
                for ev in events + blocked:
                    if start < ev.end and ev.start < end:
                        feasible = False
                        break
                if not feasible:
                    break
            if not feasible:
                continue
            losses = []
            for person in participants:
                work = person.work_windows[day]
                blockers = person.meetings + person.personal
                before = _capacity_scan(work, blockers)
                after = _capacity_scan(work, blockers + [Interval(start, end)])
                losses.append(before - after)
            key = (max(losses), sum(losses), start)
            if best is None or key < best:
                best = key
    if best is None:
        return None
    max_loss, total_loss, start = best
    return start, max_loss, total_loss


def _capacity_scan(work, blockers):
    """独立容量实现：扫描基本区间，累加连续空闲段，达阈值才计入。"""
    points = {work.start, work.end}
    clips = []
    for ev in blockers:
        lo = max(ev.start, work.start)
        hi = min(ev.end, work.end)
        if lo < hi:
            clips.append((lo, hi))
            points.add(lo)
            points.add(hi)
    ordered = sorted(points)
    total = 0
    run = 0
    for left, right in zip(ordered, ordered[1:]):
        covered = any(lo <= left and right <= hi for lo, hi in clips)
        if covered:
            if run >= FOCUS_THRESHOLD:
                total += run
            run = 0
        else:
            run += right - left
    if run >= FOCUS_THRESHOLD:
        total += run
    return total


def empty_windows():
    return (Interval(0, 0),) * 5


class FixedCaseTest(unittest.TestCase):
    def test_required_example(self):
        p1 = Participant("A", (Interval(0, 20000),) + (Interval(0, 0),) * 4)
        p2 = Participant("B", (Interval(18000, 38000),) + (Interval(0, 0),) * 4)
        choice = choose_slot([p1, p2], [], 900)
        self.assertIsNotNone(choice)
        self.assertEqual(choice.start, 18550)
        self.assertEqual(choice.end, 19450)
        self.assertEqual(choice.max_loss, 1450)
        self.assertEqual(choice.total_loss, 2900)


class DirectedTest(unittest.TestCase):
    def test_threshold_below(self):
        # 工作时段 5399 < 5400：容量恒为 0，损失为 0，取最早起点
        person = Participant("A", (Interval(0, 5399),) + (Interval(0, 0),) * 4)
        choice = choose_slot([person], [], 900)
        self.assertIsNotNone(choice)
        self.assertEqual((choice.start, choice.max_loss, choice.total_loss), (0, 0, 0))

    def test_threshold_exact(self):
        # 工作时段恰好 5400：会前容量 5400，插入后两段都低于阈值，损失 5400
        person = Participant("A", (Interval(0, 5400),) + (Interval(0, 0),) * 4)
        choice = choose_slot([person], [], 900)
        self.assertIsNotNone(choice)
        self.assertEqual((choice.start, choice.max_loss), (0, 5400))

    def test_focus_block_protects_but_keeps_capacity(self):
        # focus_block 禁止安排会议但不切断潜在专注段
        person = Participant(
            "A",
            (Interval(0, 20000),) + (Interval(0, 0),) * 4,
            focus_blocks=[Interval(9000, 10000)],
        )
        choice = choose_slot([person], [], 900)
        self.assertIsNotNone(choice)
        # 容量按 20000 整段计算：s=0 时右段 19100 仍达阈值，损失即最小的 900
        self.assertEqual((choice.start, choice.max_loss), (0, 900))
        # 且会议不得与 focus_block 重叠
        self.assertFalse(choice.start < 10000 and 9000 < choice.end)

    def test_blocked_intervals_avoided(self):
        person = Participant("A", (Interval(0, 10000),) + (Interval(0, 0),) * 4)
        choice = choose_slot([person], [Interval(0, 9000)], 900)
        self.assertIsNotNone(choice)
        # 禁会区间不切断容量：会前容量 10000，s=9100 时左段 9100 达标，损失 900
        self.assertEqual((choice.start, choice.max_loss), (9100, 900))

    def test_no_solution_when_window_too_short(self):
        person = Participant("A", (Interval(0, 800),) + (Interval(0, 0),) * 4)
        self.assertIsNone(choose_slot([person], [], 900))

    def test_no_solution_when_fully_blocked(self):
        person = Participant("A", (Interval(0, 10000),) + (Interval(0, 0),) * 4)
        self.assertIsNone(choose_slot([person], [Interval(-100, 20000)], 900))

    def test_overlapping_and_duplicate_events(self):
        # 重叠、重复且跨越工作时段边界的事件按并集处理
        person = Participant(
            "A",
            (Interval(1000, 20000),) + (Interval(0, 0),) * 4,
            meetings=[Interval(-500, 3000), Interval(2000, 4000), Interval(2000, 4000)],
            personal=[Interval(19000, 25000)],
        )
        choice = choose_slot([person], [], 900)
        self.assertIsNotNone(choice)
        self.assertGreaterEqual(choice.start, 4000)
        self.assertLessEqual(choice.end, 19000)

    def test_duration_validation(self):
        person = Participant("A", (Interval(0, 20000),) + (Interval(0, 0),) * 4)
        for bad in (0, 899, 901, 7201, 1000):
            with self.assertRaises(ValueError):
                choose_slot([person], [], bad)
        for good in (900, 1800, 2700, 7200):
            self.assertIsNotNone(choose_slot([person], [], good))


class RandomizedTest(unittest.TestCase):
    def test_against_brute_force(self):
        rng = random.Random(20261005)
        trials = 60
        solved = 0
        for _ in range(trials):
            participants = []
            for idx in range(rng.randint(1, 3)):
                windows = []
                for _day in range(5):
                    if rng.random() < 0.15:
                        windows.append(Interval(0, 0))
                    else:
                        start = rng.randint(0, 1200)
                        windows.append(Interval(start, start + rng.randint(2500, 6000)))
                def events(count):
                    out = []
                    for _ in range(count):
                        start = rng.randint(-500, 9000)
                        out.append(Interval(start, start + rng.randint(0, 1800)))
                    return out
                participants.append(Participant(
                    f"P{idx}",
                    tuple(windows),
                    meetings=events(rng.randint(0, 2)),
                    personal=events(rng.randint(0, 2)),
                    focus_blocks=events(rng.randint(0, 1)),
                ))
            blocked = []
            for _ in range(rng.randint(0, 1)):
                start = rng.randint(-500, 9000)
                blocked.append(Interval(start, start + rng.randint(0, 1500)))
            duration = rng.choice([900, 900, 1800, 2700])
            expected = brute_force(participants, blocked, duration)
            choice = choose_slot(participants, blocked, duration)
            actual = None if choice is None else (
                choice.start, choice.max_loss, choice.total_loss)
            self.assertEqual(actual, expected,
                             msg=f"participants={participants} blocked={blocked} "
                                 f"duration={duration}")
            if expected is not None:
                solved += 1
        self.assertGreater(solved, trials // 2)  # 确保多数用例有解，覆盖有效比较


if __name__ == "__main__":
    unittest.main()
