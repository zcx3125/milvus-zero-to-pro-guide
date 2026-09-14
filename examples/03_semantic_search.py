"""真实中文语义检索：首次下载公开多语言模型，无需 LLM API Key。"""

import argparse

from tutorial_common import (
    SEMANTIC_COLLECTION, SEMANTIC_DIMENSION, SEMANTIC_MODEL, TIMEOUT,
    cleanup_collection, connect, ensure_collection, entrypoint,
    load_json, print_hits, search, validate_vectors,
)


def load_model():
    # 延迟导入：运行 --help / 离线测试不下载模型，不要求 torch。
    from sentence_transformers import SentenceTransformer

    print("加载多语言 Embedding 模型。首次会下载模型文件，需要可访问模型托管站点。")
    model = SentenceTransformer(SEMANTIC_MODEL, device="cpu")
    if model.get_sentence_embedding_dimension() != SEMANTIC_DIMENSION:
        raise ValueError("模型输出维度发生变化，请勿写入现有集合。")
    return model


def encode(model, texts: list[str]) -> list[list[float]]:
    vectors = model.encode(
        texts, normalize_embeddings=True, convert_to_numpy=True,
        show_progress_bar=False,
    ).tolist()
    validate_vectors(vectors, SEMANTIC_DIMENSION)
    return vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="我忘记了登录公司的密码，怎么办？", help="要检索的问题")
    parser.add_argument("--cleanup", action="store_true", help="只删除语义示例集合，不下载模型")
    args = parser.parse_args()
    client = connect()
    try:
        if args.cleanup:
            cleanup_collection(client, SEMANTIC_COLLECTION, SEMANTIC_MODEL, SEMANTIC_DIMENSION)
            return
        model = load_model()
        documents = load_json("faq.json")
        # 文档和问题必须使用同一个模型及相同编码方式。
        vectors = encode(model, [row["text"] for row in documents])
        rows = [
            {**document, "vector": vector, "model": SEMANTIC_MODEL}
            for document, vector in zip(documents, vectors)
        ]
        ensure_collection(client, SEMANTIC_COLLECTION, SEMANTIC_MODEL, SEMANTIC_DIMENSION)
        client.upsert(collection_name=SEMANTIC_COLLECTION, data=rows, timeout=TIMEOUT)
        query_vector = encode(model, [args.query])[0]
        print(f"\n模型：{SEMANTIC_MODEL}\n维度：{SEMANTIC_DIMENSION}\n问题：{args.query}")
        print_hits(search(client, SEMANTIC_COLLECTION, query_vector, tenant="tenant_a", k=3))
        print("\n这里返回的是相似原文，没有调用大语言模型生成回答。相似度不是正确率。")
    finally:
        client.close()


if __name__ == "__main__":
    entrypoint(main)
