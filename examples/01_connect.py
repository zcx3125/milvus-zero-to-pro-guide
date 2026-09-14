"""只连接并读版本，不创建或修改集合。"""

import argparse

from tutorial_common import TIMEOUT, connect, entrypoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    client = connect()
    try:
        print(f"连接成功，Milvus Server 版本：{client.get_server_version(timeout=TIMEOUT)}")
        print(f"当前数据库可见集合：{client.list_collections(timeout=TIMEOUT)}")
        print("本教程示例固定使用 Milvus Server 3.0.1 与 pymilvus 3.0.1。")
    finally:
        client.close()


if __name__ == "__main__":
    entrypoint(main)
