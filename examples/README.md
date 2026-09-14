# 示例怎么运行

以下命令都在**仓库根目录**运行。先按主教程启动 Milvus Server **3.0.1**；这些脚本连接独立服务器，不会为你安装 Docker，不会自动启动 Milvus，也不采用 Milvus Lite。

建议 Python 3.11 / 3.12。创建虚拟环境后安装基础依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:MILVUS_URI = "http://127.0.0.1:19530"
```

macOS / Linux 激活命令为 `source .venv/bin/activate`，设置地址用 `export MILVUS_URI=http://127.0.0.1:19530`。不要把 `PS C:\...>` 或 `$` 提示符一起复制。若 PowerShell 拒绝激活，可以直接用 `.\.venv\Scripts\python.exe` 替代下文的 `python`，不必修改系统执行策略。

服务器启用了认证时，在本机设置 `MILVUS_TOKEN`，格式通常为 `用户名:密码`；默认无认证的本地教学环境不用设置。不要把真实凭据写进代码、仓库或截图，不要把用户名密码嵌入 `MILVUS_URI`。HTTPS 托管服务还需使用其提供的真实端点和相应 Token。

## 1. 确认连接

```powershell
python examples/01_connect.py
```

成功会显示服务端版本和当前可见集合。本步只读，不创建集合。连接失败优先检查容器健康、19530 端口、地址、认证设置与客户端版本。

## 2. 先理解增删改查与向量检索

```powershell
python examples/02_crud_search.py
```

本示例使用 3 维**手写教学向量**，三个数可粗略想成“账号、报销、网络”的坐标，但它们不是模型真正算出的语义表示，也不能把任意中文问题直接变成这些数。

代码会显式定义字段、建立 `FLAT + COSINE` 索引、加载集合，然后展示：

1. `upsert` 写入固定主键的虚构数据，便于反复运行。
2. `search` 找相似向量，同时限定 `tenant_a`。
3. 搜索同时限定租户和分类。
4. `query` 按普通字段条件查询。
5. `get` 按主键读取。
6. 两次 `upsert` 同一个临时主键，展示更新。
7. `delete` 只删除本次教学临时 ID `199`，再读取验证。

预期：账号相关的 `101` 排在前面；`tenant_b` 的 `901` 与问题向量完全一样，却因租户条件被排除。API 返回字段名为 `distance`，但在 **COSINE** 度量下，数值越大越相似。该值不是概率，也不是答案正确率。

为了马上看到写入和删除结果，集合和读取请求都指定了 `Strong`。这只是本教程选定的一致性配置，不代表应在所有业务中无条件使用最强一致性。

集合 `milvus_tutorial_toy_v1` 会保留。只在确认不再需要其中的教学记录时执行：

```powershell
python examples/02_crud_search.py --cleanup
```

`--cleanup` 是**单独的清理动作**，不会先重跑一遍演示。它只操作固定教学集合，并核验教程所有权标记和向量维度；不会遍历删除其他集合。清理后可重跑示例恢复虚构教学数据。请不要往此专用集合放自己的业务数据。

## 3. 换成真正的中文语义检索

```powershell
python -m pip install -r requirements-semantic.txt
python examples/03_semantic_search.py
python examples/03_semantic_search.py --query "出差的钱怎样报销？"
```

使用 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，输出 **384 维**向量。模型同时用于文档和问题编码，使用相同的归一化配置；数据写入独立集合 `milvus_tutorial_semantic_v1`，不会混进 3 维教学集合。模型名存入每条记录，维度也在创建与重跑时校验。

本例在 CPU 上推理，不要求 GPU，也不调用大语言模型，不需要 LLM API Key。不过首次安装会下载 PyTorch 等依赖，可能消耗较多时间、带宽与磁盘；首次运行还会从 Hugging Face 下载模型，模型缓存位置由相关库配置决定。断网或无法访问模型站点时无法完成首次下载，**这不代表 Milvus 连接失败**。可在联网机器提前取得同一模型，再按照模型库的离线加载说明配置缓存。

这款小模型适合用来理解流程，不保证适合你的行业知识。它还有输入长度限制，因此这里故意使用简短 FAQ。真实长文档需要分块、记录来源和版本，再使用业务测试集评估模型。仓库固定 Python 依赖版本，但没有固定下载模型的具体 revision；需要严格复现时，记录 Hugging Face 的提交 revision、运行环境和模型校验信息，在重建集合时使用同一版本。

模型相同、维度相同只是避免明显不兼容的一部分。修改模型、模型 revision、文本预处理或编码设置时，应重建向量并评测，不能把不同向量空间的结果混用。

```powershell
python examples/03_semantic_search.py --cleanup
```

这条只清理语义示例专用集合，不加载或下载模型，不清理模型缓存。

## 4. 测试“是不是搜到了正确资料”

先完成第 3 步，确保 FAQ 已写入，再运行：

```powershell
python examples/04_evaluate.py --k 3
```

评测使用 `data/evaluation.json` 的 6 个虚构问题和人工参考 ID，打印每题返回的 ID，并计算：

- `Recall@k`：所有标准相关文档中，有多少出现在前 k 条结果里。先逐题算，再求平均。
- `MRR@k`：每题第一个相关结果的排名倒数，再求平均。第 1 条正确记 1，第 2 条正确记 0.5，前 k 条没有正确结果记 0。
- 编码耗时与检索往返耗时：分开计时；不包含启动模型和建库，包含本次请求的网络及处理耗时。

这里每题只有一个标准相关文档，所以这个数据集的 Recall@k 等于 Hit@k。它不是 ANN 与精确检索之间的召回率基准，也不是 RAG 最终回答正确率。6 个样本只能教学，不能用于声称达到企业生产准确率。真实项目应增加未见过的问题、困难负例、拒答题和跨租户测试，并固定数据版本。

## 5. 离线检查与真实集成检查是两件事

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python tests/integration_smoke.py
```

第一条只依赖 Python 标准库，检查向量数值合法性、已知余弦关系、过滤的实际意义、过滤输入约束、FAQ 标注与检索指标。不会联网、不会连接 Milvus、不会下载模型。

第二条默认仅提示如何启用集成检查。**启动真实的 Milvus 3.0.1 测试环境后**，才运行：

```powershell
python tests/integration_smoke.py --run
```

它实际调用 CRUD 示例，核验首条结果、其他租户排除与保留、临时记录删除以及原始记录保留。会写入固定教学集合，不会删除集合。不是压力测试，也没有覆盖集群故障、备份恢复或真实语义模型质量。

## 边界与常见问题

- **所有脚本 `--help` 都可离线运行**，不会因为查看帮助就连接数据库或下载大模型。
- 租户字段过滤只是演示数据隔离条件，不是完整鉴权。真实服务必须认证用户，由服务端添加租户条件，并对按 ID 查询、更新、删除等所有入口实施同样权限检查。
- `get` 和临时 ID 操作用于专用教学集合，不应照搬成接受任意外部 ID 的业务接口。
- `VARCHAR max_length` 按 UTF-8 字节计；中文通常不止一个字节。本例文本很短，测试也检查了实际字节长度。
- 同名集合配置不匹配时，脚本会拒绝覆盖；先检查是否误用了别的项目的服务器或集合。脚本不会替你删除冲突集合。
- 示例不会输出 Token；异常只打印异常类型和排错方向。通过容器日志排查时，也请先确认其中没有敏感凭据。
- **通过离线测试不等于已经通过真实 Milvus 或模型测试。** 是否完成集成运行，以实际运行输出为准。
