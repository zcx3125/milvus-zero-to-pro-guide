"""先运行 03_semantic_search.py，再对虚构 FAQ 执行小规模检索评测。"""

import argparse
import importlib.util
from pathlib import Path
from statistics import mean
from time import perf_counter

from evaluation_metrics import recall_at_k, reciprocal_rank_at_k
from tutorial_common import (
    SEMANTIC_COLLECTION, SEMANTIC_DIMENSION, SEMANTIC_MODEL, TIMEOUT,
    connect, entrypoint, load_json, search, verify_collection,
)


def load_semantic_module():
    # 文件名以数字开头，使用 importlib 加载；main guard 保证不会执行演示。
    spec = importlib.util.spec_from_file_location(
        "semantic_example", Path(__file__).with_name("03_semantic_search.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.k <= 100:
        raise ValueError("k 必须在 1–100 之间。")
    client = connect()
    try:
        if not client.has_collection(collection_name=SEMANTIC_COLLECTION, timeout=TIMEOUT):
            raise ValueError("请先运行 03_semantic_search.py 创建语义集合。")
        verify_collection(client, SEMANTIC_COLLECTION, SEMANTIC_MODEL, SEMANTIC_DIMENSION)
        client.load_collection(collection_name=SEMANTIC_COLLECTION, timeout=TIMEOUT)
        semantic = load_semantic_module()
        model = semantic.load_model()
        recalls, reciprocal_ranks, embedding_ms, search_ms = [], [], [], []
        for case in load_json("evaluation.json"):
            started = perf_counter()
            vector = semantic.encode(model, [case["query"]])[0]
            encoded = perf_counter()
            hits = search(client, SEMANTIC_COLLECTION, vector, tenant=case["tenant"], k=args.k)
            finished = perf_counter()
            ids = [int(hit["id"]) for hit in hits]
            if any(hit["entity"]["tenant"] != case["tenant"] for hit in hits):
                raise ValueError("结果中出现其他租户数据，评测中止。")
            recall = recall_at_k(ids, case["relevant_ids"], args.k)
            reciprocal = reciprocal_rank_at_k(ids, case["relevant_ids"], args.k)
            recalls.append(recall)
            reciprocal_ranks.append(reciprocal)
            embedding_ms.append((encoded - started) * 1000)
            search_ms.append((finished - encoded) * 1000)
            print(f"问题：{case['query']}\n  返回 ID={ids}  Recall@{args.k}={recall:.3f}  RR@{args.k}={reciprocal:.3f}")
        print(f"\n样本数：{len(recalls)}")
        print(f"平均 Recall@{args.k}：{mean(recalls):.3f}")
        print(f"MRR@{args.k}：{mean(reciprocal_ranks):.3f}")
        print(f"平均问题编码耗时：{mean(embedding_ms):.1f} ms")
        print(f"平均检索往返耗时：{mean(search_ms):.1f} ms")
        print("这是 6 条人工编写问题的教学测量，不是 Milvus 性能基准或生产正确率。")
        print("每题只有 1 个标准相关文档，因此这里的 Recall@k 数值也等于 Hit@k。")
        print("耗时不含模型加载 / 建库，含首次推理或检索的冷启动影响；不可直接比较不同机器。")
    finally:
        client.close()


if __name__ == "__main__":
    entrypoint(main)
