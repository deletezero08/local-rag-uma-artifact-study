# Topn x Budget Failure Cases

## Baseline Reference
- Faithfulness / relevance: `4.237` / `4.975`
- Error-rate proxy: `0.625`

## Selected Point
- `t5_b1500`: `topn=5`, `budget=1500`, `TTFT=1344.748`, `faith=4.5`, `rel=5.112`, `error_rate=0.65`
- Note: within bounded operating region under current thresholds

## Candidate Points
- `t5_b1500`: `TTFT=1344.748`, `total=7915.441`, `faith=4.5`, `rel=5.112`, `error_rate=0.65`
- `t10_b2000`: `TTFT=1983.836`, `total=8005.64`, `faith=4.95`, `rel=4.938`, `error_rate=0.5`
- `t10_b2500`: `TTFT=2446.941`, `total=8739.499`, `faith=5.112`, `rel=5.157`, `error_rate=0.5`

## Representative Failures Under Selected Point
- `Q008` `factual_drift` faith `1.0` rel `2.5`: docker_compose.md 中 API 服务的端口映射配置是什么？
- `Q009` `factual_drift` faith `1.5` rel `2.0`: vLLM Chat Completions 的端点路径是什么？
- `Q010` `factual_drift` faith `0.5` rel `1.5`: vLLM Completions 的端点路径是什么？
- `Q012` `retrieval_miss` faith `9.5` rel `9.0`: vLLM Models 列表接口的端点路径是什么？
- `Q013` `factual_drift` faith `2.0` rel `3.5`: TGI Chat 的端点路径是什么？

## Fast But Rejected Points
- `t5_bnone`: `TTFT=1091.709`, `faith=3.837`, `rel=4.6`, `error_rate=0.7`; note: faithfulness_drop=0.400>threshold; relevance_drop=0.375>threshold; judge_gap_r=3.250>threshold
- `t5_b2000`: `TTFT=1291.329`, `faith=3.925`, `rel=4.513`, `error_rate=0.65`; note: faithfulness_drop=0.312>threshold; relevance_drop=0.462>threshold
- `t5_b2500`: `TTFT=1410.468`, `faith=4.275`, `rel=4.476`, `error_rate=0.7`; note: relevance_drop=0.499>threshold
