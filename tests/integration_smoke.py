"""真实 Milvus 集成冒烟检查；必须显式 --run，默认不连接、不写数据。

使用 02_crud_search.py 的固定教学集合，会 upsert 演示数据和删除临时 ID 199，
不删除集合。只在测试环境运行，不用于生产数据。
"""

import argparse
import importlib.util
import re
import sys
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(EXAMPLES))

from tutorial_common import (  # noqa: E402
    TIMEOUT, TOY_COLLECTION, TOY_QUERY, connect, entrypoint, search,
)


def load_crud_module():
    spec = importlib.util.spec_from_file_location("crud_example", EXAMPLES / "02_crud_search.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="确认使用测试环境运行读写检查")
    args = parser.parse_args()
    if not args.run:
        print("未执行集成测试。启动 Milvus 后运行：python tests/integration_smoke.py --run")
        return
    client = connect()
    try:
        version = client.get_server_version(timeout=TIMEOUT)
        print(f"测试服务器标识：{version}")
        # The official v3.0.1 image reports a build identifier such as
        # 3.0-20260902-658cbd1689, not always its release tag. CI separately
        # checks the exact container image; here accept either documented form.
        if not re.fullmatch(r"v?3\.0(?:\.1(?:[-+][A-Za-z0-9.-]+)?|-\d{8}-[0-9a-f]+)", version):
            raise RuntimeError("服务端标识不属于本教程的 3.0 版本范围，请检查镜像。")
        hits, remaining = load_crud_module().run_demo(client)
        if not hits or int(hits[0]["id"]) != 101:
            raise AssertionError("精确 COSINE 检索的首条应为 101。")
        if remaining:
            raise AssertionError("Strong 读取下已删除的临时 ID 199 不应可见。")
        if any(hit["entity"]["tenant"] != "tenant_a" for hit in hits):
            raise AssertionError("过滤结果包含其他租户。")
        b_hits = search(client, TOY_COLLECTION, TOY_QUERY, tenant="tenant_b", k=1)
        if not b_hits or int(b_hits[0]["id"]) != 901:
            raise AssertionError("另一租户数据应仍存在，可由其自己的过滤条件检索。")
        persisted = client.get(
            collection_name=TOY_COLLECTION, ids=[101, 102, 103, 104, 901],
            output_fields=["id"], consistency_level="Strong", timeout=TIMEOUT,
        )
        if {row["id"] for row in persisted} != {101, 102, 103, 104, 901}:
            raise AssertionError("演示原始记录未完整保留。")
        print("PASS：实际完成建库、索引、加载、写入、过滤搜索、主键查询、更新、精确删除检查。")
    finally:
        client.close()


if __name__ == "__main__":
    entrypoint(main)
