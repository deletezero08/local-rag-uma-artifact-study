# Failure Casebook

This note consolidates representative failure and disagreement cases across the current paper-track experiments.

## E4 Expanded Dual-Judge

- Baseline merged faithfulness / relevance: `4.237` / `4.975`
- Optimized merged faithfulness / relevance: `4.275` / `4.875`

### Lowest-faithfulness optimized cases

- `Q014` faith `0.0`, rel `0.5`, gap_f `0.0`, gap_r `1.0`: TGI Completions 的端点路径是什么？
- `Q009` faith `0.5`, rel `1.0`, gap_f `1.0`, gap_r `2.0`: vLLM Chat Completions 的端点路径是什么？
- `Q010` faith `0.5`, rel `0.5`, gap_f `1.0`, gap_r `1.0`: vLLM Completions 的端点路径是什么？
- `Q011` faith `1.0`, rel `1.0`, gap_f `2.0`, gap_r `2.0`: vLLM Embeddings 的端点路径是什么？
- `Q056` faith `1.0`, rel `2.0`, gap_f `2.0`, gap_r `2.0`: 结合 vector_db_comparison 与 embedding_models，说明向量库选择对嵌入模型的影响。

### Highest judge-gap optimized cases

- `Q012` faith `5.0`, rel `5.5`, gap_f `10.0`, gap_r `9.0`: vLLM Models 列表接口的端点路径是什么？
- `Q008` faith `6.5`, rel `4.5`, gap_f `7.0`, gap_r `1.0`: docker_compose.md 中 API 服务的端口映射配置是什么？
- `Q059` faith `3.5`, rel `3.0`, gap_f `7.0`, gap_r `6.0`: 结合 tgi_docker 与 docker_compose_llm_official，说明容器部署参数的一致性。
- `Q060` faith `5.5`, rel `5.5`, gap_f `7.0`, gap_r `5.0`: 结合 ollama_api_official 与 ollama_models，说明模型管理与 API 使用的关系。
- `Q037` faith `7.0`, rel `7.5`, gap_f `6.0`, gap_r `5.0`: 总结 CUDA 常见问题与解决思路。

---

## E2 TurboQuant On/Off

- FP32 off: recall `0.8`, faith `4.812`, rel `5.325`, error `0.5`
- TurboQuant on: recall `0.787`, faith `4.612`, rel `5.138`, error `0.55`

### Representative factual-drift cases under TurboQuant

- `Q008` recall `1.0`, faith `4.0`, rel `3.5`: docker_compose.md 中 API 服务的端口映射配置是什么？
- `Q009` recall `1.0`, faith `2.0`, rel `2.5`: vLLM Chat Completions 的端点路径是什么？
- `Q010` recall `1.0`, faith `3.0`, rel `4.5`: vLLM Completions 的端点路径是什么？
- `Q011` recall `1.0`, faith `0.0`, rel `0.0`: vLLM Embeddings 的端点路径是什么？
- `Q014` recall `1.0`, faith `0.0`, rel `0.0`: TGI Completions 的端点路径是什么？

### Representative retrieval-miss cases under TurboQuant

- `Q016` recall `0.0`, faith `4.5`, rel `8.0`: Ollama Chat 的端点路径是什么？
- `Q018` recall `0.0`, faith `3.0`, rel `4.5`: Ollama Models 列表端点路径是什么？
- `Q038` recall `0.0`, faith `6.5`, rel `5.5`: 总结推理性能优化的关键策略。
- `Q039` recall `0.0`, faith `3.0`, rel `3.5`: 总结微服务架构的核心模块划分。
- `Q057` recall `0.0`, faith `0.0`, rel `0.0`: 对比 api_security 与 env_variables 中关于鉴权配置的说明。

---

## E7 Topn x Budget Grid

### Candidate operating points

- `t5_b1500` TTFT `1344.748`, faith `4.5`, rel `5.112`, note `within bounded operating region under current thresholds`
- `t10_b2000` TTFT `1983.836`, faith `4.95`, rel `4.938`, note `within bounded operating region under current thresholds`
- `t10_b2500` TTFT `2446.941`, faith `5.112`, rel `5.157`, note `within bounded operating region under current thresholds`

### Representative failures under selected point `t5_b1500`

- `Q008` `factual_drift` faith `1.0` rel `2.5`: docker_compose.md 中 API 服务的端口映射配置是什么？
- `Q009` `factual_drift` faith `1.5` rel `2.0`: vLLM Chat Completions 的端点路径是什么？
- `Q010` `factual_drift` faith `0.5` rel `1.5`: vLLM Completions 的端点路径是什么？
- `Q012` `retrieval_miss` faith `9.5` rel `9.0`: vLLM Models 列表接口的端点路径是什么？
- `Q013` `factual_drift` faith `2.0` rel `3.5`: TGI Chat 的端点路径是什么？

---

## E8 Pruning Policy Ablation

### Policy summaries

- `static_ratio_60` TTFT `1344.748`, faith `4.5`, rel `5.112`, error `0.65`
- `dynamic_cliff` TTFT `1073.589`, faith `4.138`, rel `4.069`, error `0.65`
- `random_middle_60` TTFT `1065.434`, faith `4.019`, rel `3.969`, error `0.65`
- `boundary_first_60` TTFT `1283.936`, faith `4.175`, rel `3.933`, error `0.625`
