"""共享配置与校验：可离线导入，只有实际连接时才导入 PyMilvus。"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

DATA_DIR = Path(__file__).resolve().parent / "data"
TOY_COLLECTION = "milvus_tutorial_toy_v1"
SEMANTIC_COLLECTION = "milvus_tutorial_semantic_v1"
TOY_MODEL = "handwritten-teaching-vector-v1"
SEMANTIC_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SEMANTIC_DIMENSION = 384
OWNERSHIP_PREFIX = "milvus-zero-to-pro-guide:v1:"
TIMEOUT = 30
TOY_QUERY = [0.98, 0.08, 0.04]


def load_json(filename: str):
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def validate_vectors(vectors, dimension: int) -> None:
    """拒绝错维度、NaN、无穷大和无法计算 COSINE 的全零向量。"""
    if dimension < 1:
        raise ValueError("向量维度必须大于 0。")
    if not vectors:
        raise ValueError("向量列表不能为空。")
    for vector in vectors:
        if len(vector) != dimension:
            raise ValueError(f"向量必须是 {dimension} 维。")
        if any(isinstance(x, bool) or not isinstance(x, (float, int)) for x in vector):
            raise ValueError("向量元素必须是数值。")
        if any(not math.isfinite(x) for x in vector):
            raise ValueError("向量中不能包含 NaN 或无穷大。")
        if not any(x != 0 for x in vector):
            raise ValueError("COSINE 示例不接受全零向量。")


def cosine_similarity(left, right) -> float:
    """离线理解余弦相似度用；实际向量搜索由 Milvus 执行。"""
    validate_vectors([left, right], len(left))
    numerator = sum(a * b for a, b in zip(left, right))
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(
        sum(x * x for x in right)
    )
    return numerator / denominator


def build_filter(tenant: str, category: str | None = None) -> str:
    """教学标签限定字符集，避免把任意输入拼接成可执行过滤表达式。

    租户过滤只是演示。真实应用应由服务端从已认证身份推导 tenant，
    不能让浏览器传什么租户就信什么租户。
    """
    values = [tenant] if category is None else [tenant, category]
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) for value in values):
        raise ValueError("教学租户 / 分类只允许 1–64 位字母、数字、下划线或连字符。")
    expression = f'tenant == "{tenant}"'
    if category is not None:
        expression += f' and category == "{category}"'
    return expression


def connection_options() -> dict:
    uri = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
    parsed = urlsplit(uri)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("MILVUS_URI 必须是 http(s) 服务地址；本示例不使用 Lite 文件。")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("请把凭据放入 MILVUS_TOKEN，不要嵌入 URI。")
    return {"uri": uri, "token": os.getenv("MILVUS_TOKEN", ""), "timeout": TIMEOUT}


def connect():
    from pymilvus import MilvusClient

    return MilvusClient(**connection_options())


def collection_description(model: str, dimension: int) -> str:
    return f"{OWNERSHIP_PREFIX}{model}:{dimension}"


def verify_collection(client, collection: str, model: str, dimension: int) -> None:
    """相同维度不代表相同向量空间，同时核验创建标记、模型和维度。"""
    description = client.describe_collection(collection_name=collection, timeout=TIMEOUT)
    if description.get("description") != collection_description(model, dimension):
        raise ValueError("已有同名集合不属于当前教学配置；请勿覆盖，先检查其用途。")
    fields = {field["name"]: field for field in description["fields"]}
    expected_names = {"id", "vector", "text", "tenant", "category", "model"}
    if set(fields) != expected_names:
        raise ValueError("已有集合字段与教程不一致，请检查集合结构。")
    if int(fields["vector"].get("params", {}).get("dim", -1)) != dimension:
        raise ValueError("已有集合向量维度与当前模型不一致。")


def ensure_collection(client, collection: str, model: str, dimension: int) -> None:
    from pymilvus import DataType, MilvusClient

    if not collection.startswith("milvus_tutorial_"):
        raise ValueError("示例只操作 milvus_tutorial_ 前缀的集合。")
    if client.has_collection(collection_name=collection, timeout=TIMEOUT):
        verify_collection(client, collection, model, dimension)
    else:
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
            description=collection_description(model, dimension),
        )
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dimension)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4096)
        schema.add_field(field_name="tenant", datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="category", datatype=DataType.VARCHAR, max_length=64)
        schema.add_field(field_name="model", datatype=DataType.VARCHAR, max_length=256)
        # FLAT 精确扫描适合这个很小的教学数据集；海量数据需另选 ANN 索引。
        index = MilvusClient.prepare_index_params()
        index.add_index(field_name="vector", index_type="FLAT", metric_type="COSINE")
        client.create_collection(
            collection_name=collection,
            schema=schema,
            index_params=index,
            consistency_level="Strong",
            timeout=TIMEOUT,
        )
    client.load_collection(collection_name=collection, timeout=TIMEOUT)


def cleanup_collection(client, collection: str, model: str, dimension: int) -> None:
    """只在用户显式选择 --cleanup 时调用，而且再次核验集合所有权标记。"""
    if not collection.startswith("milvus_tutorial_"):
        raise ValueError("拒绝清理非教学集合。")
    if client.has_collection(collection_name=collection, timeout=TIMEOUT):
        verify_collection(client, collection, model, dimension)
        client.drop_collection(collection_name=collection, timeout=TIMEOUT)
        print(f"已删除教学集合 {collection}；其中的教学数据可以通过重跑示例生成。")
    else:
        print(f"教学集合 {collection} 不存在，无需清理。")


def search(client, collection: str, vector: list, tenant="tenant_a", k=3, category=None):
    if not 1 <= k <= 100:
        raise ValueError("本教程的 k 必须在 1–100 之间。")
    return client.search(
        collection_name=collection,
        data=[vector],  # 外层列表表示一个批次，这里只有一个查询向量。
        anns_field="vector",
        filter=build_filter(tenant, category),
        limit=k,
        output_fields=["text", "tenant", "category", "model"],
        search_params={"metric_type": "COSINE", "params": {}},
        consistency_level="Strong",
        timeout=TIMEOUT,
    )[0]


def print_hits(hits) -> None:
    for rank, hit in enumerate(hits, start=1):
        entity = hit["entity"]
        # API 键叫 distance，但 COSINE 下数值越大越相似；不是正确率或概率。
        print(f"{rank}. id={hit['id']}  COSINE={hit['distance']:.4f}  tenant={entity['tenant']}")
        print(f"   {entity['text']}")


def entrypoint(main) -> None:
    """不输出连接参数或原始异常字符串，避免日志意外带出凭据。"""
    try:
        main()
    except (ValueError, FileNotFoundError, ModuleNotFoundError) as error:
        print(f"示例未完成：{type(error).__name__}。请检查参数、依赖和 README 排错章节。", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"示例未完成：{type(error).__name__}。请检查服务健康、版本、认证和网络。", file=sys.stderr)
        sys.exit(1)
