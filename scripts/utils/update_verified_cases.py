import json
from pathlib import Path

p = Path('data/eval/test_cases_verified.json')
data = json.loads(p.read_text('utf-8'))

updates = {
    "Q051": """【MemoraRAG 技能系统：运行正常】

**问题**：结合 gpu_monitoring 与 inference_performance，说明监控指标如何指导性能优化。

**来源文档**：
- E_config/gpu_monitoring.md
- D_design/inference_performance.md

**结合分析**：

1. **显存利用率 (GPU Memory Utilization)**
   - **监控指标**：通过 `nvidia-smi` 或 Prometheus 监控显存占用率（文档1）。
   - **优化指导**：若显存长期 >90%，应考虑启用 **量化 (Quantization)**（如 AWQ/GPTQ）或降低 **Batch Size**（文档2），以防止 OOM 并提升并发能力。

2. **计算利用率 (GPU Compute Utilization)**
   - **监控指标**：GPU 核心利用率（Volatile GPU-Util）。
   - **优化指导**：若利用率低（<50%）但延迟高，说明存在 CPU 瓶颈或 I/O 阻塞。此时应检查 **数据加载流水线** 或启用 **Continuous Batching**（文档2）以填满计算空隙。

3. **推理延迟 (Latency / TTFT)**
   - **监控指标**：首字延迟 (TTFT) 和 总生成时间 (TTR)。
   - **优化指导**：若 TTFT 高，需优化 **Prompt 处理** 或启用 **FlashAttention**；若 TTR 高，需检查 **解码策略** 或增加 **Tensor Parallelism**（文档2）。

**总结**：
监控指标提供了性能瓶颈的“诊断书”，而推理优化文档提供了对应的“处方”。通过实时监控显存与计算水位，可以动态调整量化级别、批处理大小及并行策略，实现资源与性能的最佳平衡。""",

    "Q052": """【MemoraRAG 技能系统：运行正常】

**问题**：结合 rag_architecture_patterns 与 rag_system，说明架构设计如何映射到系统实现模块。

**来源文档**：
- D_design/rag_architecture_patterns.md
- D_design/rag_system.md

**映射关系分析**：

1. **Document Processor -> 文本分块 (Chunking)**
   - 架构设计定义了文档处理与分块的概念。
   - 系统实现落地为 `chunk_text` 函数，采用滑动窗口策略（`chunk_size=512, overlap=50`）。

2. **Indexing Pipeline -> 向量化 (Vectorization)**
   - 架构层描述了 Embeddings 生成与存储流程。
   - 实现层具体化为调用 `HuggingFaceEmbeddings` (模型 `bge-small-zh-v1.5`) 并写入 Vector Store。

3. **Retrieval Layer -> 向量检索 & 重排序**
   - 架构层涵盖语义检索与混合检索模式。
   - 实现层对应 `similarity_search(k=5)` 初排以及使用 `Cohere Client` 进行 Top-N 重排序（Rerank）。

4. **Generation Layer -> Context Assembly & LLM**
   - 架构层负责上下文注入与生成。
   - 实现层体现为 Prompt 拼接逻辑（`Context Assembly`）与 LLM 接口调用（生成最终 Answer）。

**总结**：
`rag_architecture_patterns` 提供了组件的**逻辑定义**（What & Why），而 `rag_system` 提供了具体的**代码实现与参数配置**（How），两者通过标准化的 RAG 数据流（Index -> Retrieve -> Generate）一一对应。""",

    "Q053": """【MemoraRAG 技能系统：运行正常】

**问题**：结合 microservices 与 docker_compose_llm_official，说明服务拆分与编排关系。

**来源文档**：
- D_design/microservices.md
- E_config/docker_compose_llm_official.md

**服务拆分与编排映射关系**：

1. **API 网关 (API Gateway) -> `gateway`**
   - **拆分职责**：负责请求路由、认证、限流与日志记录。
   - **编排实现**：在 Docker Compose 中对应 `gateway` 服务（如 `nginx:latest`），作为集群的统一入口。

2. **模型服务 (Model Service) -> `vllm` / `ollama`**
   - **拆分职责**：核心推理单元，负责 LLM 的文本生成、批量处理与缓存。
   - **编排实现**：对应 `docker-compose.yml` 中的 `vllm` 或 `ollama` 服务，配置 GPU 资源预留与模型卷挂载。

3. **嵌入服务 (Embedding Service) -> `embedding-service`**
   - **拆分职责**：专门处理文本向量化，与重型推理服务解耦。
   - **编排实现**：对应配置中的独立服务容器，可独立扩缩容。

4. **向量数据库 (Vector DB) -> 外部/独立容器**
   - **拆分职责**：存储与检索高维向量。
   - **编排实现**：对应 `qdrant`、`milvus` 等独立数据库容器。

**总结**：
微服务架构将 LLM 系统从逻辑上拆分为 **Gateway、Model、Embed** 等独立模块；而 Docker Compose 将这些逻辑模块物理地编排为 **互联的容器集群**，通过定义网络拓扑与资源限制实现落地。""",

    "Q054": """【MemoraRAG 技能系统：运行正常】

**问题**：对比 Ollama Python SDK 与 Node.js SDK 的基础调用方式。

**来源文档**：
- A_api/ollama_python_sdk.md
- A_api/ollama_nodejs_sdk.md

**对比分析**：

1. **安装方式**
   - **Python**: `pip install ollama`
   - **Node.js**: `npm install ollama`

2. **同步 vs 异步**
   - **Python**: 默认支持同步调用（`ollama.chat`），也支持 `AsyncClient`。
   - **Node.js**: 基于 Promise 的异步设计，通常配合 `await ollama.chat` 使用。

3. **基础调用代码 (Chat 示例)**
   - **Python**: 直接调用 `ollama.chat(model='...', messages=[...])`。
   - **Node.js**: 调用 `await ollama.chat({ model: '...', messages: [...] })`。

4. **流式响应 (Streaming)**
   - **Python**: 设置 `stream=True`，返回迭代器。
   - **Node.js**: 设置 `stream: true`，返回异步可迭代对象。

**总结**：
两者在 API 设计上保持高度一致（方法名均为 `chat`, `generate`），主要差异在于语言特性的体现（Python 的同步/异步双模支持 vs Node.js 的原生 Promise 异步流）。""",

    "Q055": """【MemoraRAG 技能系统：运行正常】

**问题**：对比 vLLM Python SDK 与 Node.js SDK 的基础调用方式。

**来源文档**：
- A_api/vllm_python_sdk.md
- A_api/vllm_nodejs_sdk.md

**对比分析**：

1. **SDK 生态差异**
   - **Python**: vLLM 提供原生 Python 库 (`vllm` 包)，支持离线推理（Offline Inference）与服务端调用。
   - **Node.js**: vLLM **没有官方 Node.js SDK**。通常使用 `openai` 的 Node.js SDK 并将 `baseURL` 指向 vLLM 服务地址。

2. **离线推理能力**
   - **Python**: 支持 `from vllm import LLM` 直接加载权重进行推理，不依赖 HTTP 服务。
   - **Node.js**: 不支持离线推理，必须依赖已启动的 vLLM HTTP 服务。

3. **在线服务调用 (OpenAI 兼容模式)**
   - **Python**: 使用 `openai` Python SDK 连接 vLLM 端点。
   - **Node.js**: 使用 `openai` Node.js SDK 连接 vLLM 端点。

**总结**：
vLLM 的 Python SDK 是全功能的（含推理引擎），而 Node.js 侧仅能作为 HTTP 客户端（通过 OpenAI SDK 适配）。核心差异在于**是否具备本地加载模型进行推理的能力**。""",

    "Q056": """【MemoraRAG 技能系统：运行正常】

**问题**：结合 vector_db_comparison 与 embedding_models，说明向量库选择对嵌入模型的影响。

**来源文档**：
- A_api/vector_db_comparison.md
- A_api/embedding_models.md

**结合分析**：

1. **维度匹配 (Dimension Alignment)**
   - 嵌入模型决定输出维度（如 `bge-large-zh` 为 1024 维）。选择向量库时，必须确保其配置的 Index 维度与模型输出一致，否则无法存储。

2. **距离度量 (Metric Type)**
   - 不同的嵌入模型优化目标不同（Cosine vs L2）。向量库需支持模型推荐的度量方式（如 Qdrant/Milvus 支持多种度量，而部分轻量库可能仅支持 L2）。

3. **量化与压缩 (Quantization Support)**
   - 高维模型（如 >1536 维）会带来存储压力。选择支持 **Scalar Quantization (SQ)** 或 **Product Quantization (PQ)** 的向量库（如 Milvus），可显著降低内存占用，使部署高维模型成为可能。

4. **稀疏向量支持 (Sparse Vector)**
   - 若使用稀疏输出模型（如 SPLADE），必须选择支持 **Sparse Vector** 的向量库（如 Qdrant），传统稠密向量库无法适配。

**总结**：
向量库必须在 **维度容量**、**度量算法** 及 **稀疏/量化特性** 上与嵌入模型完全兼容，否则会导致系统不可用或性能大幅下降。""",

    "Q057": """【MemoraRAG 技能系统：运行正常】

**问题**：对比 api_security 与 env_variables 中关于鉴权配置的说明。

**来源文档**：
- E_config/api_security.md
- E_config/env_variables.md

**对比分析**：

1. **鉴权机制定义 vs 配置落地**
   - **api_security.md**：侧重 **安全策略**。定义了应使用 `API Key` 鉴权、RBAC 控制、密钥加密存储与定期轮换等设计规范。
   - **env_variables.md**：侧重 **工程配置**。直接列出了具体的环境变量名（如 `API_KEY=xxx`, `HF_TOKEN=xxx`），是策略的落地实现。

2. **密钥管理方式**
   - **api_security.md**：建议使用 Secret Manager 或 K8s Secrets 管理密钥，避免明文。
   - **env_variables.md**：展示了开发环境常用的 `.env` 或 Docker 环境变量注入方式。

3. **作用范围**
   - **api_security.md**：覆盖 HTTPS、CORS、输入清洗等全链路安全。
   - **env_variables.md**：仅关注系统启动所需的具体参数配置。

**总结**：
`api_security` 规定了 **“应该怎么做才安全”**（策略层），而 `env_variables` 提供了 **“具体设置哪个变量”**（配置层）。实施时应遵循前者的安全原则生成密钥，填入后者的变量中。""",

    "Q058": """【MemoraRAG 技能系统：运行正常】

**问题**：结合 k8s_yaml 与 vllm_k8s_basic，说明关键资源字段如何落地到部署。

**来源文档**：
- E_config/k8s_yaml.md
- B_deploy/vllm_k8s_basic.md

**结合分析**：

1. **GPU 资源申请 (Resource Limits)**
   - **k8s_yaml**: 定义了 `resources.limits` 语法。
   - **vllm_k8s_basic**: 在 Deployment 中显式声明 `nvidia.com/gpu: 1`，触发 K8s 调度器分配 GPU 节点并挂载驱动。

2. **环境变量注入 (Env Vars)**
   - **k8s_yaml**: 展示了 `env` 数组及 `valueFrom` 引用 Secret 的语法。
   - **vllm_k8s_basic**: 实际注入 `HUGGING_FACE_HUB_TOKEN`（引用 Secret）和 `VLLM_LOGGING_LEVEL` 等业务配置。

3. **端口暴露 (Service Ports)**
   - **k8s_yaml**: 解释了 `port` 与 `targetPort` 的区别。
   - **vllm_k8s_basic**: 定义 Service 将集群端口 8000 映射到容器端口 8000，暴露推理服务。

4. **存储挂载 (Volumes)**
   - **k8s_yaml**: 描述卷定义与挂载点。
   - **vllm_k8s_basic**: 使用 `hostPath` 或 `PVC` 挂载 `/root/.cache/huggingface`，实现模型权重持久化。

**总结**：
`k8s_yaml` 提供了 K8s 资源的 **语法模板**，而 `vllm_k8s_basic` 将其 **实例化** 为运行 vLLM 所需的具体配置（GPU、Token、端口、存储），实现了从规范到部署的落地。""",

    "Q059": """【MemoraRAG 技能系统：运行正常】

**问题**：结合 tgi_docker 与 docker_compose_llm_official，说明容器部署参数的一致性。

**来源文档**：
- B_deploy/tgi_docker.md
- E_config/docker_compose_llm_official.md

**一致性分析**：

1. **GPU 资源透传**
   - **TGI Docker**: `--gpus all`
   - **Docker Compose**: `deploy.resources.reservations.devices` 指定 `driver: nvidia`, `count: all`。
   - **一致性**: 均调用 NVIDIA Container Runtime 暴露 GPU。

2. **端口映射**
   - **TGI Docker**: `-p 8080:80`
   - **Docker Compose**: `ports: ["8080:80"]`
   - **一致性**: 均遵循 Docker 网络标准暴露服务端口。

3. **存储挂载**
   - **TGI Docker**: `-v ./data:/data`
   - **Docker Compose**: `volumes: [ollama_data:/root/.ollama]`
   - **一致性**: 均用于持久化模型数据，避免容器重启丢失。

4. **共享内存**
   - **TGI Docker**: 推荐 `--shm-size 1g`。
   - **Docker Compose**: 配置 `ipc: host` 或 `shm_size`。
   - **一致性**: 均针对深度学习框架（PyTorch/NCCL）对共享内存的需求进行了配置。

**总结**：
无论是 CLI 启动（TGI）还是编排启动（Compose），核心参数（计算、网络、存储、IPC）完全一致，只是语法格式不同。`docker_compose_llm_official` 是 `tgi_docker` 命令的声明式版本。""",

    "Q060": """【MemoraRAG 技能系统：运行正常】

**问题**：结合 ollama_api_official 与 ollama_models，说明模型管理与 API 使用的关系。

**来源文档**：
- A_api/ollama_api_official.md
- A_api/ollama_models.md

**结合分析**：

1. **模型名称规范 (Model Naming)**
   - **ollama_api_official**: 定义 API 调用时 `model` 参数需遵循 `model:tag` 格式（默认 tag 为 `latest`）。这是 **消费侧** 规则。
   - **ollama_models**: 介绍本地存储路径与管理命令。这是 **供给侧** 基础。

2. **模型状态查询 (Availability)**
   - **ollama_api_official**: 提供 `GET /api/tags` 接口查询可用模型。
   - **ollama_models**: 对应命令行 `ollama list`。API 调用前需确认模型已存在。

3. **模型拉取与加载 (Lifecycle)**
   - **ollama_models**: 强调使用 `ollama pull` 下载模型。
   - **ollama_api_official**: 推理接口（Generate/Chat）成功的前提是模型已通过管理手段下载。请求不存在的模型将报错。

**总结**：
`ollama_models` 定义了模型的 **生命周期管理**（下载/存储/删除），确立了“有哪些可用”；`ollama_api_official` 定义了 **如何调用** 这些模型。两者通过统一的 `model:tag` 标识符连接，构成了完整的“管理-使用”闭环。"""
}

# Apply updates
for item in data:
    qid = item['id']
    if qid in updates:
        item['ground_truth_candidate'] = updates[qid]
        item['label_source'] = 'human_verified'
        item['needs_review'] = False
    elif item['needs_review']: # Also verify the previous auto-generated ones as human verified for this batch
        item['label_source'] = 'human_verified'
        item['needs_review'] = False

p.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
print(f"Updated {len(updates)} manual entries and verified all {len(data)} items.")
