# FlowGuard

团队会议择时库：在插入会议后，尽量保住每个人的连续深度工作时间。

## 用法

```python
from flowguard import Event, EventKind, Problem, choose_slot

problem = Problem(
    participants=["a", "b"],
    work_hours={  # 每人 5 个工作日，每天一个工作时段（或 None）
        "a": [(0, 20000), None, None, None, None],
        "b": [(18000, 38000), None, None, None, None],
    },
    events={"a": [Event(3000, 3600, EventKind.MEETING)]},
    blocked=[(10000, 11000)],  # 团队禁会区间
    duration=900,              # 15~120 分钟的 15 分钟整数倍
)
slot = choose_slot(problem)  # Slot(start, end) 或 None（无解）
```

## 规则

- 所有时间为整数秒，区间左闭右开，边界相接不算重叠。
- 可行会议完整落在每位参与者同一天的工作时段内，不与任何已有事件
  （meeting / personal / focus_block）或禁会区间重叠。
- 潜在专注段 = 工作时段扣除 meeting ∪ personal 后的最大连续区间；
  focus_block 与禁会区间只禁止落会，不切断专注段。
- 长度 ≥ 5400 秒的专注段贡献全部长度，否则贡献零；各段之和为专注容量。
- 把新会议视为 meeting 重新计算容量，插入前后容量之差即个人损失。
- 最优解依次最小化：最大个人损失、全体损失之和、开始时间；
  在所有可行整数秒起点中全局最优。

## 测试

```sh
python3 -m unittest discover -s tests
```

包含给定样例（最优起点 18550、最大损失 1450、总损失 2900）、
定向场景（5400 阈值两侧、focus_block 保护、边界相接、无解），
以及小规模随机输入与逐秒穷举参考实现（`tests/brute_force.py`）的对照。
