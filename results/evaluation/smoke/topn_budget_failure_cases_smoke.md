# Topn x Budget Failure Cases

## Baseline Reference
- Faithfulness / relevance: `4.237` / `4.975`
- Error-rate proxy: `0.625`

## Selected Point
- `t8_b1500`: `topn=8`, `budget=1500`, `TTFT=2423.151`, `faith=5.5`, `rel=5.5`, `error_rate=0.5`
- Note: within bounded operating region under current thresholds

## Candidate Points
- `t8_b1500`: `TTFT=2423.151`, `total=7852.666`, `faith=5.5`, `rel=5.5`, `error_rate=0.5`

## Representative Failures Under Selected Point
- `Q009` `factual_drift` faith `1.0` rel `1.0`: vLLM Chat Completions 的端点路径是什么？

## Fast But Rejected Points
- `t5_bnone`: `TTFT=726.037`, `faith=2.0`, `rel=3.25`, `error_rate=1.0`; note: faithfulness_drop=2.237>threshold; relevance_drop=1.725>threshold; error_rate_delta=0.375>threshold; judge_gap_f=4.000>threshold; judge_gap_r=3.500>threshold
- `t5_b1500`: `TTFT=1986.977`, `faith=1.5`, `rel=2.75`, `error_rate=1.0`; note: faithfulness_drop=2.737>threshold; relevance_drop=2.225>threshold; error_rate_delta=0.375>threshold
- `t8_bnone`: `TTFT=6911.868`, `faith=4.5`, `rel=4.5`, `error_rate=0.5`; note: relevance_drop=0.475>threshold
