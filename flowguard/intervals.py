"""区间集合运算：合并与扣减。"""

from __future__ import annotations

from .types import Interval


def merge(intervals: list[Interval]) -> list[Interval]:
    """合并重叠或相接的区间，返回有序不重叠列表。"""
    ordered = sorted(intervals, key=lambda iv: (iv.start, iv.end))
    merged: list[Interval] = []
    for iv in ordered:
        if iv.length == 0:
            continue
        if merged and iv.start <= merged[-1].end:
            last = merged[-1]
            if iv.end > last.end:
                merged[-1] = Interval(last.start, iv.end)
        else:
            merged.append(iv)
    return merged


def subtract(base: Interval, cutters: list[Interval]) -> list[Interval]:
    """从 base 中扣除 cutters 的并集，返回剩余区间列表。"""
    remaining: list[Interval] = []
    cursor = base.start
    for cut in merge(cutters):
        if cut.end <= cursor:
            continue
        if cut.start >= base.end:
            break
        if cut.start > cursor:
            remaining.append(Interval(cursor, min(cut.start, base.end)))
        cursor = max(cursor, cut.end)
        if cursor >= base.end:
            return remaining
    if cursor < base.end:
        remaining.append(Interval(cursor, base.end))
    return remaining


def intersect(first: list[Interval], second: list[Interval]) -> list[Interval]:
    """两个有序不重叠区间列表的交集。"""
    out: list[Interval] = []
    i = j = 0
    while i < len(first) and j < len(second):
        lo = max(first[i].start, second[j].start)
        hi = min(first[i].end, second[j].end)
        if lo < hi:
            out.append(Interval(lo, hi))
        if first[i].end < second[j].end:
            i += 1
        else:
            j += 1
    return out
