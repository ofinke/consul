from enum import Enum


class OLLAMA_LLMS(Enum):
    DEEPSEEK = "deepseek-r1:14b"
    QWEN = "qwen2.5-coder:14b"
    GEMMA3 = "gemma3:12b"
