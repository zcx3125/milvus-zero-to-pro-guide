"""三维手写向量演示 CRUD 与过滤；这些数字不是真实 Embedding 模型的输出。"""

import argparse
import json

from tutorial_common import (
    TIMEOUT, TOY_COLLECTION, TOY_MODEL, TOY_QUERY, build_filter,
    cleanup_collection, connect, ensure_collection, entrypoint,
    load_json, print_hits, search, validate_vectors,
)


def run_demo(client):
    rows = [{**row, "model": TOY_MODEL} for row in load_json("toy_vectors.json")]
    validate_vectors([row["vector"] for row in rows] + [TOY_QUERY], 3)
    ensure_collection(client, TOY_COLLECTION, TOY_MODEL, 3)
    result = client.upsert(collection_name=TOY_COLLECTION, data=rows, timeout=TIMEOUT)
    print(f"1. upsert 完成：{result}；同一主键重跑时更新，不另外生成主键。")

    print("\n2. 在 tenant_a 中搜索与密码问题相似的向量：")
    hits = search(client, TOY_COLLECTION, TOY_QUERY, tenant="tenant_a", k=3)
    print_hits(hits)
    print("tenant_b 的 901 与查询向量完全相同，但被过滤，所以不会出现在结果中。")

    print("\n3. 限定 tenant_a 且分类为 account：")
    print_hits(search(client, TOY_COLLECTION, TOY_QUERY, category="account"))

    print("\n4. query 根据标量条件找记录；没有向量相似度排名：")
    queried = client.query(
        collection_name=TOY_COLLECTION,
        filter=build_filter("tenant_a", "account"),
        output_fields=["id", "text", "tenant"],
        limit=10,
        consistency_level="Strong",
        timeout=TIMEOUT,
    )
    print(json.dumps(queried, ensure_ascii=False, indent=2))

    print("\n5. get 按主键读取 101（仅为教程；业务服务仍须检查调用者权限）：")
    print(client.get(
        collection_name=TOY_COLLECTION, ids=[101], output_fields=["text", "tenant"],
        consistency_level="Strong", timeout=TIMEOUT,
    ))

    # 199 是本演示专用临时主键；不对其他记录执行 delete。
    temporary = {**rows[0], "id": 199, "text": "临时教学记录：原始文字。"}
    client.upsert(collection_name=TOY_COLLECTION, data=[temporary], timeout=TIMEOUT)
    temporary["text"] = "临时教学记录：已使用相同主键更新文字。"
    client.upsert(collection_name=TOY_COLLECTION, data=[temporary], timeout=TIMEOUT)
    print("\n6. 相同主键 upsert 后的内容：")
    print(client.get(
        collection_name=TOY_COLLECTION, ids=[199], output_fields=["text"],
        consistency_level="Strong", timeout=TIMEOUT,
    ))
    client.delete(collection_name=TOY_COLLECTION, ids=[199], timeout=TIMEOUT)
    print("7. 已删除临时记录 199。确认查询结果应为空列表：")
    remaining = client.get(
        collection_name=TOY_COLLECTION, ids=[199],
        consistency_level="Strong", timeout=TIMEOUT,
    )
    print(remaining)
    print(f"集合 {TOY_COLLECTION} 和原始教学数据保留，可在界面继续查看。")
    return hits, remaining


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup", action="store_true", help="只删除本示例专用集合，不运行演示")
    args = parser.parse_args()
    client = connect()
    try:
        if args.cleanup:
            cleanup_collection(client, TOY_COLLECTION, TOY_MODEL, 3)
        else:
            run_demo(client)
    finally:
        client.close()


if __name__ == "__main__":
    entrypoint(main)
