# FlowGuard

团队会议择时库：在插入会议后，尽量保住每个人的连续深度工作时间。

## 用法

```python
from flowguard import Interval, Participant, choose_slot

p1 = Participant("A", (Interval(0, 20000),) + (Interval(0, 0),) * 4)
p2 = Participant("B", (Interval(18000, 38000),) + (Interval(0, 0),) * 4)
choice = choose_slot([p1, p2], blocked=[], duration=900)
# SlotChoice(start=18550, end=19450, max_loss=1450, total_loss=2900)
```

- `Participant`：姓名、五个工作日各一个工作时段（`Interval`，左闭右开整数秒），
  以及 `meetings` / `personal` / `focus_blocks` 事件区间。
- `choose_slot(participants, blocked, duration)`：`blocked` 为团队禁会区间，
  `duration` 为会议时长（15–120 分钟、15 分钟整数倍，单位秒）。
  返回最优 `SlotChoice`，无解返回 `None`。

## 规则

- 可行会议完整落在每位参与者同一天的工作时段内，不与任何已有事件或
  禁会区间重叠；边界相接不算重叠。
- 逐人逐日从工作时段扣除 meeting 与 personal 的并集，剩余最大连续区间为
  潜在专注段；focus_block 与禁会区间只禁止安排会议，不切断潜在专注段。
- 潜在专注段长度达到 5400 秒才贡献其全部长度，各段贡献之和为专注容量。
  插入会议（视为 meeting）前后的容量差即该人的损失。
- 最优解依次最小化：最大个人损失、全体损失之和、开始时间；结果为所有
  可行整数秒起点中的全局最优。

## 测试

```sh
python3 -m unittest discover -s tests
```

包含题目给定的固定用例、5400 秒阈值两侧 / 重叠事件 / focus_block 保护 /
无解等定向用例，以及小规模随机输入与逐秒穷举 oracle 的对照。
