# V2 SOTA Completion: Battle 4

## 背景判断

当前计划书已经明确了 Battle 4 的目标，即从 mock 与局部单测切换到一体化真实性能测量，但仍存在四个明显缺口：

1. 缺少分阶段执行策略。现有计划直接进入 `--full` 压测，容易在本地机器上一次性拉高显存、内存与推理时长，排障成本高。
2. 缺少可复核的产物定义。虽然提到输出 `v2_performance_final.json`，但未定义 JSON 结构、关键字段与基线对比维度，后续画图和论文引用会不稳定。
3. 缺少风险控制与降级路径。计划里默认并发、长上下文和自适应剪枝都能一次跑通，但没有说明失败后应该如何回退到 smoke 模式定位问题。
4. 缺少验收标准。现有描述偏“希望测出来”，但没有把“脚本能跑通”“产物可复用”“日志可追踪”拆成明确的完成条件。

因此，本次改进不只是保留原有目标，而是把 Battle 4 重构成“先冒烟、再基准、后压测”的可执行工程计划。

## 改进后的实施目标

Battle 4 的最终目标调整为以下三项：

- 构建一套可重复执行的 V2 Benchmark Orchestrator，支持 smoke / full 两种运行模式。
- 补齐 `AdaptiveKVCompressor` 与 `TurboQuantizer` 的可追踪性和边界处理，使其能稳定服务批量与并发测试。
- 产出可直接被后续图表脚本、论文与实验附录复用的结构化 JSON 结果。

## 实施范围

### 1. 编排脚本

文件：`scripts/v2_benchmark_orchestrator.py`

改进内容：

- 增加命令行参数，支持 `--smoke`、`--full`、`--output`、`--seed`。
- 增加统一的结果结构，至少包含：
  - `metadata`
  - `retrieval`
  - `scaling`
  - `concurrency`
  - `summary`
- 增加 smoke 模式，优先验证模型加载、TurboQuant 检索、短上下文生成和单并发流程。
- 将输出路径从硬编码改为可配置，并自动创建父目录。
- 固定随机种子，降低多次实验之间的随机抖动。

### 2. KV 压缩模块

文件：`src/kv_compressor.py`

改进内容：

- 强化批量场景下的边界处理，保证 `num_to_keep` 不为 0。
- 记录每次压缩事件的关键指标，包括：
  - `seq_len`
  - `ratio`
  - `retained_tokens`
  - `available_gb`
- 将“内存压力触发剪枝”从 `print` 提升为可结构化查询的事件日志。

### 3. TurboQuant 检索模块

文件：`src/turbo_quant.py`

改进内容：

- 保留当前向量化 ADC 主路径，但补齐输入形状校验与 dtype 规范化。
- 显式约束 `query_fp32`、`codes`、`qjl`、`scale_qjl` 的维度关系，避免 benchmark 阶段因为数据格式问题导致静默错误。
- 保持批量查询接口稳定，保证 orchestrator 可以直接测 batch query latency。

## 分阶段实施计划

### Phase A：Smoke 验证

目标：先确认链路可运行，而不是一次性压满机器。

执行内容：

- 加载本地模型与 tokenizer。
- 加载 TurboQuant 索引并执行 1 次检索。
- 运行一组短上下文生成测试。
- 运行 `N=1` 的单并发测试。
- 输出 `smoke` 结果 JSON。

完成标准：

- 脚本无异常退出。
- 结果文件存在且字段齐全。
- TTFT、TPS、RSS 均被记录。

### Phase B：Full Benchmark

目标：在 smoke 通过后再执行完整 Battle 4 数据采集。

执行内容：

- 上下文长度测试：`1024 / 2048 / 4096 / 8192`
- 并发测试：`N=1 / 2 / 4`
- 检索测试：TurboQuant 路径耗时统计
- 汇总生成 `v2_performance_final.json`

完成标准：

- `scaling`、`concurrency`、`retrieval` 三类结果均存在。
- 所有阶段有明确的成功、失败或跳过状态。
- 输出可直接供图表脚本消费。

### Phase C：故障回退

若 full 模式失败，应按以下顺序回退：

1. 先重跑 `--smoke`
2. 再只跑 `scaling`
3. 最后只跑 `concurrency`

这样可以快速判断问题究竟出在：

- 模型加载
- 长上下文
- 并发线程争用
- TurboQuant 数据格式

## 验收标准

Battle 4 完成需要同时满足以下条件：

1. `scripts/v2_benchmark_orchestrator.py` 支持 smoke/full 模式。
2. `src/kv_compressor.py` 能输出结构化压缩事件。
3. `src/turbo_quant.py` 能稳定处理单查询与批量查询。
4. 结果 JSON 可重复生成，并具有统一字段结构。
5. 后续图表脚本可以直接读取这些结果，而不需要手工改字段名。

## 本次实施项

本轮直接实施以下内容：

- 改造 orchestrator，加入 CLI、smoke/full、结构化输出与随机种子控制。
- 改造 KV compressor，加入事件记录与更稳的批量边界处理。
- 改造 TurboQuant，补齐输入校验和批量健壮性。

## 后续建议

本轮完成后，建议追加两个动作：

1. 为 `scripts/generate_waterfall_chart.py` 补一个读取新 JSON schema 的适配层。
2. 在 `experiments/results/` 下固定保存一份 smoke 结果和一份 full 结果，便于论文与答辩时分别展示“可运行性”和“峰值性能”。
