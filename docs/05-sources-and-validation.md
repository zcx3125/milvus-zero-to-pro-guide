# 第五章：资料来源、配置差异与验证范围

[返回首页](../README.md) · [安装教程](02-installation.md) · [实战教程](03-practice.md)

核对日期：**2026-09-14**。本教程区分官方说明、仓库示例、实际测试和后续练习，不把建议参数或示意数字写成实测结果。

## 1. 固定版本及依据

- **Milvus Server 3.0.1**：[官方发布记录](https://github.com/milvus-io/milvus/releases/tag/v3.0.1)，发布时间 2026-09-09；编写时通过官方 GitHub API 核对为最新正式发布。
- **PyMilvus 3.0.1**：[PyPI 包版本](https://pypi.org/project/pymilvus/3.0.1/)；与该 Milvus 发布说明的 Python SDK 配套版本一致。
- **Attu 3.0.0**：[官方发布记录](https://github.com/zilliztech/attu/releases/tag/v3.0.0)及[固定版本 README](https://github.com/zilliztech/attu/blob/v3.0.0/README.md)。3.x 的端口、登录方式、兼容范围与旧版教程可能不同。
- **sentence-transformers 6.0.1**：[PyPI 包版本](https://pypi.org/project/sentence-transformers/6.0.1/)。使用可选依赖文件安装，基础向量例子不需要它。
- **中文多语言模型**：[paraphrase-multilingual-MiniLM-L12-v2 模型卡](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)。模型文件不包含在本仓库中，首次使用时由模型库下载。

模型名不等于固定模型快照。本仓库尚未固定 Hugging Face revision；要严格复现实验，请记录并锁定模型 revision、预处理配置、实际依赖版本和数据版本。固定顶层 Python 包版本也不代表所有传递依赖已经完全锁定。

## 2. Compose 文件从哪里来

参考的原文件是 [Milvus 3.0.1 发布附件](https://github.com/milvus-io/milvus/releases/download/v3.0.1/milvus-standalone-docker-compose.yml)。

编写时实际读取了该发布附件，而不只依赖 `master` 分支的安装脚本。官方仓库 tag 下的源码 Compose 与发布附件可能仍有不同的镜像或依赖标签，复现时以明确记录的文件为准。

本仓库使用的核心镜像与该发布附件一致：

```text
milvusdb/milvus:v3.0.1
quay.io/coreos/etcd:v3.5.25
minio/minio:RELEASE.2024-12-18T13-15-44Z
```

为了让本机学习更容易管理，做了以下调整：

1. 去掉旧版 `version` 字段，使用 Compose 项目名 `milvus-tutorial`。
2. 去掉固定容器名和固定外部网络名，让 Compose 管理项目内资源。
3. 原来的目录绑定挂载改为声明式命名卷。这不表示数据跟随源码目录移动。
4. 19530 和 9091 只绑定宿主机回环地址，etcd、MinIO 不向宿主机发布端口。
5. 依赖启动改为等待 etcd、MinIO 健康，调整健康检查等待时间。
6. 增加容器日志大小与文件数限制，避免教学环境无限积累日志。
7. MinIO 使用 `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`，教学值与 Milvus 默认对象存储凭据保持一致。
8. 显式沿用发布附件的 `MQ_TYPE: woodpecker`，由 Milvus 嵌入式运行，无单独消息队列容器。
9. 增加可选 Attu 3.0.0，宿主机端口为 8000，容器端口为 3000，连接使用 `standalone:19530`。

本地教学保留官方示例的 `seccomp:unconfined`，没有开启 Milvus 认证。它不等于经过加固的生产模板。更换 MinIO 凭据时必须同时更新 Milvus 访问它所使用的凭据，不能只改一端。

Attu 不是 Milvus 运行的必选组件。Attu v2.6.0 起的许可已变化；请核对其[版本许可说明](https://github.com/zilliztech/attu/blob/v3.0.0/README.md#license)，不要因为旧文章称其开源就忽略当前使用条款。本仓库只引用镜像，不分发 Attu 源码或二进制。

## 3. 官方概念与 API 资料

- [Milvus v3.0.x 文档源码](https://github.com/milvus-io/milvus-docs/tree/v3.0.x/site/en)：编写时用于核验版本相关语义。
- [Standalone 安装要求](https://milvus.io/docs/prerequisite-docker.md)：内存、CPU、SSD 和平台前提。
- [Windows 安装](https://milvus.io/docs/install_standalone-windows.md)与[Docker Compose 安装](https://milvus.io/docs/install_standalone-docker-compose.md)。
- [主要组件](https://milvus.io/docs/main_components.md)与[Milvus Lite](https://milvus.io/docs/milvus_lite.md)：部署方式及其边界。
- [PyMilvus 3.0.1 客户端源码](https://github.com/milvus-io/pymilvus/blob/v3.0.1/pymilvus/milvus_client/milvus_client.py)：核对调用签名与参数传递。
- [HNSW](https://milvus.io/docs/hnsw.md)、[IVF_FLAT](https://milvus.io/docs/ivf-flat.md)、[度量](https://milvus.io/docs/metric.md)、[一致性](https://milvus.io/docs/tune_consistency.md)。
- [全文搜索](https://milvus.io/docs/full-text-search.md)、[混合搜索](https://milvus.io/docs/multi-vector-search.md)。
- [Milvus Backup](https://milvus.io/docs/milvus_backup_overview.md)：工具版本兼容性需另外确认，不能把旧矩阵直接外推到 3.0.1。

官网默认文档会随新版本变化。遇到与本文不一致的地方，先核对页面版本、服务器版本和 SDK 版本，再参考对应版本发布说明。

## 4. 本地验证

编写机器是 Windows，使用隔离虚拟环境中的 Python 3.13.9 和 PyMilvus 3.0.1 完成 SDK 导入、Schema/索引对象构建与离线检查。教程读者建议使用 Python 3.11/3.12，尤其需要安装语义模型依赖时。

已经检查的范围：

- Python 文件语法、JSON 可解析性、Markdown 围栏与本地文件链接。
- 五张 PNG 的生成与视觉检查，正文没有错位、溢出或字面量换行符。
- Compose YAML、核心镜像版本、命名卷关联、回环端口和 Attu 容器连接地址的静态一致性。
- 12 个离线测试：向量数值合法性、余弦排序、租户过滤、过滤输入约束、标注关联、Recall/MRR 计算。
- 四个例子查看帮助时不连接数据库、不下载模型；基础依赖和可选模型依赖分开。

本机未安装 Docker，未在这台 Windows 电脑上实际启动容器。静态 YAML 检查不能代替 Docker Compose 的解析和数据库集成测试。

复查命令：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools/check_docs.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

配图重建工具为 `tools/render-figures.ps1`，使用 Windows 字体和绘图组件，不是运行数据库所必需的脚本。

## 5. GitHub 上的真实服务验证

仓库提供 [Verify tutorial 工作流](../.github/workflows/verify.yml)，可在 [Actions 页面](https://github.com/zcx3125/milvus-zero-to-pro-guide/actions/workflows/verify.yml)查看每次提交的实际结果。

普通推送触发的检查包括：

1. Ubuntu / Python 3.12 上的离线测试与文档检查。
2. Docker Compose 解析完整配置，包括可选 UI profile。
3. 拉取固定镜像并真实启动 etcd、MinIO、Milvus，等待健康检查。
4. 实际连接服务器、读版本、执行 CRUD、向量搜索、过滤和删除后验证。
5. 再次执行同一组例子，验证已存在集合的重跑行为。

手动运行工作流并勾选 `semantic` 时，还会安装 CPU 模型依赖，下载中文多语言模型，运行语义检索和六题评测。这会额外消耗下载时间与临时 runner 资源；不调用收费 LLM API。

是否通过以对应提交的绿色检查及日志为准。仅存在工作流文件不能证明执行成功。可选语义检查与普通 CRUD 检查也不是同一个覆盖范围。

## 6. 还没有承诺的能力

- 不承诺任意 Windows、macOS、CPU 架构和 Docker Desktop 版本均已实测。
- 不把 Attu 初始化页面或 Windows 安装示意描述为实际操作截图。
- 不包含多节点高可用、故障注入、百万级性能或备份恢复的实际验证。
- 不宣称六题 FAQ 分数代表真实企业准确率。
- 不包含完整登录系统、业务 ACL、混合检索、Reranker、文档上传或 LLM 生成服务；这些在第四章作为后续练习解释。
- 没有把 Milvus Standalone 原地升级到 Cluster，也没有用旧版 Backup 兼容表证明 3.0.1 的恢复能力。

企业落地时，需要用真实规模与访问模式验证性能、成本、权限和恢复目标。学习项目最有价值的部分之一，是清楚写出这些边界，并逐步用可重复的实验缩小它们。
