# Quality Failure Cases

This note summarizes representative low-quality and high-disagreement cases from the paper-track quality runs.

## E4 Selected Configuration

- Baseline merged faithfulness / relevance: `4.237` / `4.975`
- Optimized merged faithfulness / relevance: `4.275` / `4.875`
- Optimized judge agreement rate (gap <= 1 on both axes): `0.275`

### Lowest merged-faithfulness optimized cases

- `Q014` faith `0.0`, relevance `0.5`, gap_f `0.0`, gap_r `1.0`: TGI Completions 的端点路径是什么？
- `Q009` faith `0.5`, relevance `1.0`, gap_f `1.0`, gap_r `2.0`: vLLM Chat Completions 的端点路径是什么？
- `Q010` faith `0.5`, relevance `0.5`, gap_f `1.0`, gap_r `1.0`: vLLM Completions 的端点路径是什么？
- `Q011` faith `1.0`, relevance `1.0`, gap_f `2.0`, gap_r `2.0`: vLLM Embeddings 的端点路径是什么？
- `Q056` faith `1.0`, relevance `2.0`, gap_f `2.0`, gap_r `2.0`: 结合 vector_db_comparison 与 embedding_models，说明向量库选择对嵌入模型的影响。

### Highest judge-gap optimized cases

- `Q012` faith `5.0`, relevance `5.5`, gap_f `10.0`, gap_r `9.0`: vLLM Models 列表接口的端点路径是什么？
- `Q008` faith `6.5`, relevance `4.5`, gap_f `7.0`, gap_r `1.0`: docker_compose.md 中 API 服务的端口映射配置是什么？
- `Q059` faith `3.5`, relevance `3.0`, gap_f `7.0`, gap_r `6.0`: 结合 tgi_docker 与 docker_compose_llm_official，说明容器部署参数的一致性。
- `Q060` faith `5.5`, relevance `5.5`, gap_f `7.0`, gap_r `5.0`: 结合 ollama_api_official 与 ollama_models，说明模型管理与 API 使用的关系。
- `Q037` faith `7.0`, relevance `7.5`, gap_f `6.0`, gap_r `5.0`: 总结 CUDA 常见问题与解决思路。

---

## E2 TurboQuant On/Off

- FP32 off: Recall@10 `0.8`, merged faithfulness `4.812`, merged relevance `5.325`, error rate `0.5`
- TurboQuant on: Recall@10 `0.787`, merged faithfulness `4.612`, merged relevance `5.138`, error rate `0.55`

### Representative factual-drift cases under TurboQuant

- `Q008` recall `1.0`, faith `4.0`, rel `3.5`: docker_compose.md 中 API 服务的端口映射配置是什么？
  source docs: `E_config/docker_compose.md`
- `Q009` recall `1.0`, faith `2.0`, rel `2.5`: vLLM Chat Completions 的端点路径是什么？
  source docs: `A_api/vllm_chat_completions.md`
- `Q010` recall `1.0`, faith `3.0`, rel `4.5`: vLLM Completions 的端点路径是什么？
  source docs: `A_api/vllm_completions.md`
- `Q011` recall `1.0`, faith `0.0`, rel `0.0`: vLLM Embeddings 的端点路径是什么？
  source docs: `A_api/vllm_embeddings.md`
- `Q014` recall `1.0`, faith `0.0`, rel `0.0`: TGI Completions 的端点路径是什么？
  source docs: `A_api/tgi_completions.md`

### Representative retrieval-miss cases under TurboQuant

- `Q016` recall `0.0`, faith `4.5`, rel `8.0`: Ollama Chat 的端点路径是什么？
  retrieved docs: `C_troubleshoot/port_conflict.md; A_api/ollama_api_official.md; B_deploy/ollama_macos.md; B_deploy/ollama_linux.md; B_deploy/ollama_linux.md`
- `Q018` recall `0.0`, faith `3.0`, rel `4.5`: Ollama Models 列表端点路径是什么？
  retrieved docs: `B_deploy/ollama_linux.md; C_troubleshoot/model_load_fail.md; A_api/ollama_nodejs_sdk.md; E_config/env_variables.md; E_config/docker_compose_llm_official.md`
- `Q038` recall `0.0`, faith `6.5`, rel `5.5`: 总结推理性能优化的关键策略。
  retrieved docs: `C_troubleshoot/oom_solution.md; deploy_spec.md; D_design/rag_architecture_patterns.md; D_design/rag_architecture_patterns.md; B_deploy/vllm_quickstart_official.md`
- `Q039` recall `0.0`, faith `3.0`, rel `3.5`: 总结微服务架构的核心模块划分。
  retrieved docs: `D_design/llm_gateway.md; DATASET_DESCRIPTION.md; memory_spec.md; B_deploy/vllm_k8s_basic.md; A_api/ollama_nodejs_sdk.md`
- `Q057` recall `0.0`, faith `0.0`, rel `0.0`: 对比 api_security 与 env_variables 中关于鉴权配置的说明。
  retrieved docs: `skills_spec.md; E_config/k8s_yaml.md; A_api/vllm_nodejs_sdk.md; D_design/microservices.md; A_api/vllm_chat_completions.md`
