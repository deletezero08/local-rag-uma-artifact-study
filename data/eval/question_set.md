# Question Set Definition

Target: 60 questions total, balanced across types.

Types:
- Factual (20)
- Summarization (20)
- Cross-document reasoning (20)

Rules:
- Each question must reference content in the indexed docs.
- Keep questions concise; avoid multi-part prompts.
- Record source document IDs for each question.

Question Set:
| id | type | question | source_docs |
|----|------|----------|-------------|
| Q001 | factual | Ollama 的 REST API 中，生成补全请求的端点路径是什么？ | A_api/ollama_api_official.md |
| Q002 | factual | Ollama 模型名称的默认 tag 是什么？ | A_api/ollama_api_official.md |
| Q003 | factual | 使用 TGI Docker 单卡部署时，容器 80 端口默认映射到主机的哪个端口？ | B_deploy/tgi_docker.md |
| Q004 | factual | TGI Docker 多卡部署中指定 GPU 分片数量的参数名是什么？ | B_deploy/tgi_docker.md |
| Q005 | factual | vLLM 支持哪些量化方法？ | E_config/quantization.md |
| Q006 | factual | 7B 参数模型在 INT4 量化下大约需要多少显存？ | C_troubleshoot/oom_solution.md |
| Q007 | factual | 环境变量 OLLAMA_HOST 的默认值是什么？ | E_config/env_variables.md |
| Q008 | factual | docker_compose.md 中 API 服务的端口映射配置是什么？ | E_config/docker_compose.md |
| Q009 | factual | vLLM Chat Completions 的端点路径是什么？ | A_api/vllm_chat_completions.md |
| Q010 | factual | vLLM Completions 的端点路径是什么？ | A_api/vllm_completions.md |
| Q011 | factual | vLLM Embeddings 的端点路径是什么？ | A_api/vllm_embeddings.md |
| Q012 | factual | vLLM Models 列表接口的端点路径是什么？ | A_api/vllm_models.md |
| Q013 | factual | TGI Chat 的端点路径是什么？ | A_api/tgi_chat.md |
| Q014 | factual | TGI Completions 的端点路径是什么？ | A_api/tgi_completions.md |
| Q015 | factual | TGI 的 metrics/info 暴露端点路径是什么？ | A_api/tgi_info_metrics.md |
| Q016 | factual | Ollama Chat 的端点路径是什么？ | A_api/ollama_chat.md |
| Q017 | factual | Ollama Generate 的端点路径是什么？ | A_api/ollama_generate.md |
| Q018 | factual | Ollama Models 列表端点路径是什么？ | A_api/ollama_models.md |
| Q019 | factual | Ollama REST API 中列出本地模型的端点路径是什么？ | A_api/ollama_api_official.md |
| Q020 | factual | Ollama REST API 中生成嵌入向量的端点路径是什么？ | A_api/ollama_api_official.md |
| Q021 | summarization | 总结 RAG 系统的四个核心组件及其功能。 | D_design/rag_architecture_patterns.md |
| Q022 | summarization | 总结 RAG 系统的常见设计模式。 | D_design/rag_architecture_patterns.md |
| Q023 | summarization | 总结 CUDA OOM（显存不足）问题的主要解决方案。 | C_troubleshoot/oom_solution.md |
| Q024 | summarization | 总结 Ollama REST API 的主要端点功能。 | A_api/ollama_api_official.md |
| Q025 | summarization | 总结 FP16、INT8、INT4 三种量化方式的对比。 | E_config/quantization.md |
| Q026 | summarization | 总结 TGI Docker 支持的量化部署方式与参数。 | B_deploy/tgi_docker.md |
| Q027 | summarization | 总结 vLLM 单卡部署的关键步骤。 | B_deploy/vllm_single_gpu.md |
| Q028 | summarization | 总结 vLLM 多卡部署的关键参数与流程。 | B_deploy/vllm_multi_gpu.md |
| Q029 | summarization | 总结 vLLM Kubernetes 基础部署流程。 | B_deploy/vllm_k8s_basic.md |
| Q030 | summarization | 总结 vLLM Kubernetes 进阶部署的优化点。 | B_deploy/vllm_k8s_advanced.md |
| Q031 | summarization | 总结 CUDA 官方安装流程的关键步骤。 | B_deploy/cuda_install_official.md |
| Q032 | summarization | 总结 GPU 监控方案的关键组件与指标。 | E_config/gpu_monitoring.md |
| Q033 | summarization | 总结官方 LLM Docker Compose 部署配置中的主要服务。 | E_config/docker_compose_llm_official.md |
| Q034 | summarization | 总结 K8s YAML 配置中常见字段及用途。 | E_config/k8s_yaml.md |
| Q035 | summarization | 总结端口冲突排查的主要步骤。 | C_troubleshoot/port_conflict.md |
| Q036 | summarization | 总结模型加载失败的常见原因与处理方式。 | C_troubleshoot/model_load_fail.md |
| Q037 | summarization | 总结 CUDA 常见问题与解决思路。 | C_troubleshoot/cuda_issues.md |
| Q038 | summarization | 总结推理性能优化的关键策略。 | D_design/inference_performance.md |
| Q039 | summarization | 总结微服务架构的核心模块划分。 | D_design/microservices.md |
| Q040 | summarization | 总结 LLM 网关的职责与能力。 | D_design/llm_gateway.md |
| Q041 | cross-doc | 对比 Ollama Generate 与 Chat 接口的输入输出差异。 | A_api/ollama_generate.md, A_api/ollama_chat.md |
| Q042 | cross-doc | 对比 vLLM Chat Completions 与 Completions 接口的使用场景。 | A_api/vllm_chat_completions.md, A_api/vllm_completions.md |
| Q043 | cross-doc | 对比 Ollama Models 与 vLLM Models 列表接口在模型管理上的差异。 | A_api/ollama_models.md, A_api/vllm_models.md |
| Q044 | cross-doc | 结合 env_variables 与 docker_compose，说明服务地址与环境变量如何对齐。 | E_config/env_variables.md, E_config/docker_compose.md |
| Q045 | cross-doc | 对比 vLLM 单卡部署与多卡部署的关键差异。 | B_deploy/vllm_single_gpu.md, B_deploy/vllm_multi_gpu.md |
| Q046 | cross-doc | 对比 vLLM Kubernetes 基础版与进阶版部署的核心差异。 | B_deploy/vllm_k8s_basic.md, B_deploy/vllm_k8s_advanced.md |
| Q047 | cross-doc | 结合 oom_solution 与 quantization，说明降低显存占用的两类路径。 | C_troubleshoot/oom_solution.md, E_config/quantization.md |
| Q048 | cross-doc | 结合 oom_nccl_troubleshoot 与 cuda_issues，说明 NCCL/驱动问题的排查顺序。 | C_troubleshoot/oom_nccl_troubleshoot.md, C_troubleshoot/cuda_issues.md |
| Q049 | cross-doc | 对比 TGI Chat 与 TGI Completions 的请求结构差异。 | A_api/tgi_chat.md, A_api/tgi_completions.md |
| Q050 | cross-doc | 结合 api_security 与 llm_gateway，说明 API 安全控制应放在系统哪一层。 | E_config/api_security.md, D_design/llm_gateway.md |
| Q051 | cross-doc | 结合 gpu_monitoring 与 inference_performance，说明监控指标如何指导性能优化。 | E_config/gpu_monitoring.md, D_design/inference_performance.md |
| Q052 | cross-doc | 结合 rag_architecture_patterns 与 rag_system，说明架构设计如何映射到系统实现模块。 | D_design/rag_architecture_patterns.md, D_design/rag_system.md |
| Q053 | cross-doc | 结合 microservices 与 docker_compose_llm_official，说明服务拆分与编排关系。 | D_design/microservices.md, E_config/docker_compose_llm_official.md |
| Q054 | cross-doc | 对比 Ollama Python SDK 与 Node.js SDK 的基础调用方式。 | A_api/ollama_python_sdk.md, A_api/ollama_nodejs_sdk.md |
| Q055 | cross-doc | 对比 vLLM Python SDK 与 Node.js SDK 的基础调用方式。 | A_api/vllm_python_sdk.md, A_api/vllm_nodejs_sdk.md |
| Q056 | cross-doc | 结合 vector_db_comparison 与 embedding_models，说明向量库选择对嵌入模型的影响。 | A_api/vector_db_comparison.md, A_api/embedding_models.md |
| Q057 | cross-doc | 对比 api_security 与 env_variables 中关于鉴权配置的说明。 | E_config/api_security.md, E_config/env_variables.md |
| Q058 | cross-doc | 结合 k8s_yaml 与 vllm_k8s_basic，说明关键资源字段如何落地到部署。 | E_config/k8s_yaml.md, B_deploy/vllm_k8s_basic.md |
| Q059 | cross-doc | 结合 tgi_docker 与 docker_compose_llm_official，说明容器部署参数的一致性。 | B_deploy/tgi_docker.md, E_config/docker_compose_llm_official.md |
| Q060 | cross-doc | 结合 ollama_api_official 与 ollama_models，说明模型管理与 API 使用的关系。 | A_api/ollama_api_official.md, A_api/ollama_models.md |
