import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from pathlib import Path

from fastagent.core.embeddings import create_embedding, EmbeddingConfig

# 使用本地Transformer模型
transformer_config = EmbeddingConfig(
    provider="transformer",
    model_name="Qwen/Qwen3-Embedding-0.6B",
    # model_name="bert-base-chinese",
    device="mps",
    model_cache_dir=Path("../hf_models")
)
transformer_emb = create_embedding(transformer_config)

# 使用Ollama
ollama_config = EmbeddingConfig(
    provider="ollama",
    model_name="qwen3-embedding:0.6B",
)
ollama_emb = create_embedding(ollama_config)

# 测试编码
test_texts = ["你好世界", "Hello World"]

print("Transformer embedding:")
print(transformer_emb.encode(test_texts[0]))

print("Ollama embedding:")
print(ollama_emb.encode(test_texts[0]))
