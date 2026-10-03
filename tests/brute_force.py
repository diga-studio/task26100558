"""独立的逐秒穷举参考实现，用于对照 choose_slot。

刻意采用与 flowguard.scheduler 不同的直白写法：
每天逐秒检查可行性，并对每个候选人重新完整计算容量。
"""
from __future__ import annotations

from flowguard.types import DAYS, MIN_FOCUS_SEGMENT, EventKind, Problem

_CUT = (EventKind.MEETING, EventKind.PERSONAL)


def _merge(intervals):
    merged = []
    for s, e in sorted(intervals):
        if e <= s:
            continue
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def _capacity(window, cut_events):
    """单人单日专注容量：工作时段扣除 cut_events 后，>=5400 的段贡献全长。"""
    if window is None:
        return 0
    lo, hi = window
    busy = _merge((max(s, lo), min(e, hi)) for s, e in cut_events if e > lo and s < hi)
    total = 0
    cursor = lo
    for s, e in busy:
        if s > cursor and s - cursor >= MIN_FOCUS_SEGMENT:
            total += s - cursor
        cursor = max(cursor, e)
    if hi - cursor >= MIN_FOCUS_SEGMENT:
        total += hi - cursor
    return total


def _losses(problem: Problem, day: int, start: int):
    """把 [start, start+duration) 当作 meeting 插入后，每个人的容量损失。"""
    losses = []
    for person in problem.participants:
        window = problem.work_hours[person][day]
        cut = [
            (e.start, e.end)
            for e in problem.events.get(person, [])
            if e.kind in _CUT
        ]
        before = _capacity(window, cut)
        after = _capacity(window, cut + [(start, start + problem.duration)])
        losses.append(before - after)
    return losses


def brute_force_slot(problem: Problem):
    """逐秒枚举所有可行整数起点，返回 (start, end) 或 None。"""
    duration = problem.duration
    best = None
    for day in range(DAYS):
        common = None
        for person in problem.participants:
            window = problem.work_hours[person][day]
            if window is None:
                common = None
                break
            common = window if common is None else (
                max(common[0], window[0]),
                min(common[1], window[1]),
            )
            if common is None or common[1] <= common[0]:
                common = None
                break
        if common is None:
            continue
        lo, hi = common
        forbidden = _merge(
            [(max(s, lo), min(e, hi)) for s, e in problem.blocked if e > lo and s < hi]
            + [
                (max(ev.start, lo), min(ev.end, hi))
                for person in problem.participants
                for ev in problem.events.get(person, [])
                if ev.end > lo and ev.start < hi
            ]
        )
        for start in range(lo, hi - duration + 1):
            end = start + duration
            if any(s < end and start < e for s, e in forbidden):
                continue
            losses = _losses(problem, day, start)
            key = (max(losses), sum(losses), start)
            if best is None or key < best:
                best = key
    if best is None:
        return None
    return (best[2], best[2] + duration)
