import dspy
import json
import logging
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger("rag_core")

class RAGIntent(dspy.Signature):
    """
    分析用户的查询意图，并从知识库文件列表中识别目标。
    """
    question = dspy.InputField(desc="用户的原始询问内容")
    file_list = dspy.InputField(desc="当前知识库中所有可用文件的列表")
    history = dspy.InputField(desc="最近几轮对话的摘要或历史记录")
    
    target_file = dspy.OutputField(desc="识别到的目标文件名，若无则返回 null")
    intent_type = dspy.OutputField(desc="意图分类：factual (事实查询), summarization (总结), analysis (深度分析), smalltalk (闲聊)")
    reasoning = dspy.OutputField(desc="简要的推导逻辑")

class DSPyRouter(dspy.Module):
    """
    SOTA Agentic Router using DSPy.
    Replaces static regex and simple LLM calls with an optimized chain.
    """
    def __init__(self, model_name: str = "qwen3:8b"):
        super().__init__()
        # 预设模型（实际运行时会动态绑定）
        self.generate_intent = dspy.ChainOfThought(RAGIntent)
        print(f"🤖 DSPyRouter 初始化完成，已挂载 ChainOfThought 决策链。")

    def forward(self, question: str, all_files: List[str], history_text: str = "") -> Dict[str, Any]:
        result = self.generate_intent(
            question=question, 
            file_list=", ".join(all_files[:50]), # 限制列表长度防止 token 爆炸
            history=history_text
        )
        
        # 结果后处理
        target = result.target_file if result.target_file != "null" else None
        if target and target not in all_files:
            target = None
            
        return {
            "target_file": target,
            "intent": result.intent_type,
            "reasoning": result.reasoning,
            "state": "agentic_hit" if target else "agentic_miss"
        }

def get_router_v2(llm_model: str):
    """
    Factory method to bind DSPy to the global LLM config.
    """
    # 假设使用 Ollama 作为后端（也可以切换至 Transformers）
    lm = dspy.OllamaLocal(model=llm_model, base_url="http://127.0.0.1:11434")
    dspy.settings.configure(lm=lm)
    return DSPyRouter(model_name=llm_model)
