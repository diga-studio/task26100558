"""左闭右开整数区间的基础操作。"""
from __future__ import annotations

Interval = tuple[int, int]


def normalize(intervals: list[Interval]) -> list[Interval]:
    """排序并合并重叠/相接区间，丢弃空区间。"""
    cleaned = sorted((s, e) for s, e in intervals if e > s)
    merged: list[Interval] = []
    for start, end in cleaned:
        if merged and start <= merged[-1][1]:
            last = merged[-1]
            merged[-1] = (last[0], max(last[1], end))
        else:
            merged.append((start, end))
    return merged


def clip(intervals: list[Interval], lo: int, hi: int) -> list[Interval]:
    """把区间裁剪到 [lo, hi) 内。"""
    return normalize([
        (max(s, lo), min(e, hi)) for s, e in intervals if min(e, hi) > max(s, lo)
    ])


def subtract(base: Interval, removals: list[Interval]) -> list[Interval]:
    """从 base 中扣除 removals 的并集，返回剩余的有序区间。"""
    remaining: list[Interval] = []
    cursor = base[0]
    for start, end in normalize(removals):
        if end <= cursor:
            continue
        if start > cursor:
            remaining.append((cursor, min(start, base[1])))
        cursor = max(cursor, end)
        if cursor >= base[1]:
            return remaining
    if cursor < base[1]:
        remaining.append((cursor, base[1]))
    return remaining
