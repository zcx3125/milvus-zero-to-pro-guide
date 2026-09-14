"""检索指标纯函数，不依赖数据库或模型。"""


def recall_at_k(retrieved_ids, relevant_ids, k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant or k < 1:
        raise ValueError("评测需至少一个标准相关 ID，且 k >= 1。")
    return len(set(retrieved_ids[:k]) & relevant) / len(relevant)


def reciprocal_rank_at_k(retrieved_ids, relevant_ids, k: int) -> float:
    relevant = set(relevant_ids)
    if not relevant or k < 1:
        raise ValueError("评测需至少一个标准相关 ID，且 k >= 1。")
    for rank, identifier in enumerate(retrieved_ids[:k], start=1):
        if identifier in relevant:
            return 1.0 / rank
    return 0.0
