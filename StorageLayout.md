# OMX-27 存储布局与存档大小参考

> 基于 v1.13.8 / EEPROM_VERSION 37 代码实测分析。位域大小按 ARM GCC (Teensy) 打包规则计算。

## 1. 存储介质

| 介质 | 容量 | 检测方式 | 备注 |
|---|---:|---|---|
| FRAM (Fujitsu MB85RC256V) | 32,000 B 使用上限 | `fram.begin()`：地址 0x50 探测 + ID 校验 (Manuf `0x0A` / Prod `0x510`) | I2C 与 OLED 共线，时钟被 SSD1306 库设为 400kHz |
| Teensy 模拟 EEPROM（回退） | T3.x: 2048 B；T4.0: 1080 B 默认（core `E2END=0x437`） | FRAM 探测失败时静默启用 | T4.0 可通过 core `avr/eeprom.h` 扩至 3825 B（`E2END=0xEF0`，`tools/patch_e2end.py` 自动打补丁） |

## 2. 各模式存档单元大小

### 总览（FRAM 全量视角）

| 模式 | 存档单元 | 单条大小 | 条数 | 全量占用 |
|---|---|---:|---:|---:|
| header | 系统设置（整块） | 39 B | 1 | **39 B** |
| Seq | 1 条 pattern | 715 B | 16 | **11,440 B** |
| Grids | 1 个快照 | 28 B | 8 | **224 B** |
| Euclidean | 1 个存档槽（8 条节奏线） | 73 B | 16 + 1B 游标 | **1,169 B** |
| Chords | 1 个和弦键 | 20 B | 16 键 × 8 预设 | **2,560 B** |
| Drums | 1 套鼓组（26 键） | 130 B | 8 | **1,040 B** |
| MidiFX | 1 个 FX 槽 | 1–44 B（类型字节 + 各 FX payload，ARP=44） | 5 组 × 8 槽 | **40–1,760 B**（全空 40，挂满 ARP 约 1,760） |
| **合计** | | | | **≈16.5–18.2 KB / 32,000 B，余量 ≈14 KB** |

（Seq 在 EEPROM 模式使用精简版 332 B/条，无 EEPROM 精简版的模块：Grids/Euclid/Chords/Drums。）

### Seq（音序器）
| 单元 | 大小 | 说明 |
|---|---:|---|
| 1 条 pattern（FRAM 完整版） | **715 B** | `Pattern` 结构体裸拷 |
| 1 条 pattern（EEPROM 精简版） | **332 B** | `serializedPatternSize(true)` |

### Grids
| 单元 | 大小 | 构成 |
|---|---:|---|
| 1 个快照 | **28 B** | 4 通道 × InstSettings (6B: note/len/chan/density/x/y) + chaos + accent + resolution/swing 位域 |
| 全量 8 快照 | 224 B | |

### Euclidean
| 单元 | 大小 | 构成 |
|---|---:|---|
| 1 条节奏线 `EuclidSave` | **9 B** | 位域：rotation6/events6/steps6/note7/chan4/vel7/swing7/len4+midifx4/muted |
| 1 个存档槽 `EuclidPatternSave` | **73 B** | 8 线 × 9 + polyRhythmMode 1B |
| 全量（FRAM / 3825 布局） | **1169 B** | 游标 1B + 16 槽 × 73 |

### Chords
| 单元 | 大小 | 构成 |
|---|---:|---|
| 1 个和弦键 `ChordSettings` | **20 B** | color int(4) + 位域参数 + CustomChordNote[6] |
| 1 套预设（16 键） | **320 B** | |
| 全量 8 预设（FRAM） | 2560 B | |

### Drums
| 单元 | 大小 | 构成 |
|---|---:|---|
| 1 套鼓组 `DrumKit` | **130 B** | 26 键 × `DrumKeySettings` 5B (note/chan/vel/midifx/hue) |
| 全量 8 套（FRAM） | 1040 B | |

### MidiFX（5 组 × 8 槽）
| 单元 | 大小 | 说明 |
|---|---:|---|
| 空槽 | **1 B** | 仅类型字节（`MIDIFXTYPE` 0–10，1 字节全宽存储） |
| 基础 FX（Repeat/Randomizer/Transpose/Monophonic/Selector） | 1 B | 基类 payload 为 no-op，参数不存 |
| Chance 槽 | 2 B | 类型 + 百分比 |
| ChordFx / Harmonizer / Scaler 槽 | 数字节 | 各自小结构 |
| Arpeggiator 槽 | **44 B** | 类型字节 + `ArpSave` 43B（位域参数 + modPattern[16] + transpPattern[16]） |
| 全空一组 | 8 B | |
| 一组挂满 8 ARP | 8 + 8×43 = 352 B | |

### FX 类型字节值表
`0=NONE 1=CHANCE 2=TRANSPOSE 3=RANDOMIZER 4=SELECTOR 5=CHORD 6=HARMONIZER 7=SCALER 8=MONOPHONIC 9=REPEAT 10=ARP`（枚举兼作 UI 颜色索引，顺序不可变更）

## 3. FRAM 布局（32,000 B，未变更）

| 地址 | 项 | 大小 | 构成 |
|---:|---|---:|---|
| 0–38 | header | 39 | 版本号 / 模式 / 播放pattern / 通道 / 25电位器 / macro×2 / 音阶×4 / 力度 / 量化 / CV / bank |
| 39–63 | 留白 | 25 | `EEPROM_PATTERN_ADDRESS=64` 取整空洞 |
| 64–11,503 | Seq ×16 | 11,440 | 16 × 715B 完整版 pattern |
| 11,504–11,727 | Grids ×8 | 224 | 8 × 28B 快照（全量） |
| 11,728–12,896 | Euclidean | 1,169 | 游标 1B + 16 槽 × 73B（全量） |
| 12,897–15,456 | Chords ×8 预设 | 2,560 | 8 × 16 键 × 20B（全量） |
| 15,457–16,496 | Drums ×8 套 | 1,040 | 8 × 130B（全量） |
| 16,497–16,536 | MidiFX 骨架 | 40 | 5 组 × 8 槽 × 1B 类型字节 |
| 16,537–18,256 | MidiFX 参数载荷（**含全部 ArpSave**） | 0–1,720 | 变长：每个 ARP 槽 +43B（ArpSave）、Chance +1B 等，按"组类型表 → 该组各槽载荷（槽序）→ 下一组"顺序内嵌 |

- 只有 MidiFX 段是运行时变长：类型字节表之后紧跟该组各带参槽的载荷，槽的字节边界由用户挂载内容决定；40 槽全挂 ARP 时载荷 = 40×43 = 1,720B。
- 典型总用量 ≈ 16.6–18.3 KB，理论最坏 18,257B，余量 ≥ 13.7 KB。
- 链顺序：**Seq → Grids → Euclid → Chords → Drums → MidiFX×5**（EEPROM 新布局沿用同一顺序）。

EEPROM 模式跳过：Grids / Euclid / Chords / Drums / MidiFX（FRAM 专属，见 savePatterns 早退）。

## 4. EEPROM 布局（定稿，3825 B，E2END=0xEF0，v38）

FRAM 老链序 + 原版留白（Seq 起点 64 与 FRAM 同址），全部区段编译期定长，`EEPROM_VERSION = 38`。

| 地址 | 项 | 大小 | 构成 |
|---:|---|---:|---|
| 0–38 | header | 39 | 系统设置（与 FRAM 逐字节一致） |
| 39–63 | 留白 | 25 | 仿 FRAM 空洞，`EEPROM_PATTERN_ADDRESS=64` 双语义复用 |
| 64–2,055 | Seq ×6 | 1,992 | 6 × 332B 精简 pattern |
| 2,056–2,167 | Grids ×4 | 112 | 快照 0–3 × 28B |
| 2,168–2,459 | Euclid 槽 ×4 | 292 | 4 × 73B，无独立游标字节（工作槽打包进 3824） |
| 2,460–3,099 | Chords ×2 预设 | 640 | 预设 0–1 × 16 键 × 20B |
| 3,100–3,619 | Drums ×4 | 520 | Kit 0–3 × 130B |
| 3,620–3,651 | MidiFX 类型表 4×8 | 32 | 组 0–3 全部 32 槽骨架（1B/槽）；组 4 不进存档 |
| 3,652–3,823 | **FX 参数流（变长）** | 172 | 按 4×8 链序追加各 FX 原生载荷（ARP 43 / Harmonizer 9 / Scaler 4 / Transpose·Chord·Repeat·Random·Selector 按 sizeof / Chance·Mono 1）；放不下的槽丢弃（保类型字节，参数回默认），扫描继续（小载荷可填空隙） |
| 3,824 | **尾部字节（打包）** | 1 | 低 4 位 = 标记 `0xA`（保存最后写，开机校验）；高 4 位 = Euclid 工作槽 0–15（全量程还原，内容持久化仅链内 4 槽） |

```
校验: 39 + 25 + 1992 + 112 + 292 + 640 + 520 + 32 + 172 + 1 = 3,825 ✅ 顶格零浪费
```

### 尾部字节（3824）：`[高4位 Euclid槽][低4位 标记0xA]`

- **首次开机**（header 版本校验失败）→ 不进 loadPatterns，不查标记，全默认值；保存时链尾写打包字节。
- **之后每次开机**（header 有效 = 数据存在过）→ 低 nibble ≠ `0xA` 即报 `EEPROM LAYOUT ERROR` 并跳过图案载入（保默认值）。此时高位区写入已被 core 静默吞掉，载入只会读进 0xFF 垃圾；0xFF 的低 nibble 是 0xF，必然校验失败。
- 高 nibble 恢复 Euclid 工作槽的**完整 0–15 量程**（FRAM 游标语义回归，零成本）；内容持久化仅链内 4 槽，落 4–15 时该槽显示默认内容。
- 能捕获 capacity() 查不出的状态：**平台升级回滚 E2END 后烧旧固件**、T4.1 构建烧 T4.0、EEPROM 高位区磨损/撕裂。
- 代价：哨兵从 8 bit 缩到 4 bit（随机噪声误通过率 1/16 → 对"写入被吞返回 0xFF"这类系统性故障仍是必然检出）。

### 设计规则

- **无 var、无死区**：每个字节语义固定，`static_assert(EP_CHAIN_END <= E2END+1)` 编译期容量锁（仅 T4.0 检查）。
- **容量运行时闸**：`storage->capacity() < 3825` 时（T3.2 原生 2048B / 未打补丁 T4）跳过图案存取并串口告警，header 正常。T3.2 无 FRAM = 无图案持久化（有意取舍）。
- **非 ARP 的 FX 参数不存**（类型字节恢复挂载，参数回默认）；组 4（第 5 组 MidiFX）FRAM 专属。
- 磨损：3825B 摊满 15 扇区，单字节有效写寿命千万级；稳态保存只写变化字节（core 内按值去重），首次全量写 ≈ 1–3 s 停核。

覆盖面：**Seq 6 · Grids 4 · Euclid 4 槽(32 线) · Chords 2 屏 32 键 · Drums 4 套 · MidiFX 32 槽骨架 + 172B 变长 FX 参数流**（例：4 ARP + 若干小 FX；或 2 ARP + Scaler/Harmonizer/Chance 全家）。

## 6. 关键代码索引

| 逻辑 | 位置 |
|---|---|
| 存储抽象 / FRAM 探测 | `src/hardware/storage.cpp` |
| FRAM 布局链 | `OMX-27-firmware.ino` `savePatterns()/loadPatterns()` |
| EEPROM 紧凑布局常量 | `src/config.h` `EP_*`（含 `static_assert` 容量锁） |
| EEPROM MidiFX 配额读写 | `.ino` `saveMidiFxQuota()/loadMidiFxQuota()` |
| MidiFX 链式变长编码（FRAM）/ 配额原语 | `src/modes/submodes/submode_midifxgroup.cpp`（`saveTypesOnly`、`saveSlotPayload` 等） |
| T4 E2END 自动补丁 | `tools/patch_e2end.py`（`pio run -e teensy40` 前自动执行） |

## 7. 已知陷阱备忘

1. `MIDIFXTYPE` 枚举顺序不可变（盘上数据 + UI 颜色索引依赖）。
2. 位域废弃位为残值：勿对盘上数据做逐字节内容比对/去重（`EEPROM.update` 的按值去重不受影响）。
3. 结构体布局 = 编译器行为：任何字段改动必须 `EEPROM_VERSION` +1。
4. FRAM 地址固定 0x50：A0–A2 悬空/接高（芯片有内部下拉，接地最稳）不影响；非 Fujitsu 兼容芯片 ID 校验必败 → 静默降级 EEPROM。
5. `.ino` 无自动原型生成：函数依赖定义顺序，新函数需定义在使用点之前。
