param([string]$OutputDirectory = (Join-Path $PSScriptRoot '../assets/images'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$palette = @{ bg='#F5F7FA'; ink='#172B43'; muted='#56677B'; blue='#235DC0'; teal='#087F78'; line='#CDD7E2'; white='#FFFFFF'; light='#E8F0FD'; green='#E4F3EF' }
function Color($value) { [Drawing.ColorTranslator]::FromHtml($value) }
function Label($text, $x, $y, $width, $height, $size=24, $color=$palette.ink, $bold=$false) {
    $style = [Drawing.FontStyle]::Regular
    if ($bold) { $style = [Drawing.FontStyle]::Bold }
    $font = [Drawing.Font]::new('Microsoft YaHei UI', $size, $style, [Drawing.GraphicsUnit]::Pixel)
    $brush = [Drawing.SolidBrush]::new((Color $color))
    $format = [Drawing.StringFormat]::new()
    try {
        $measured = $script:graphics.MeasureString($text, $font, [int]$width, $format)
        if ($measured.Height -gt $height) { throw "Text does not fit: $text (needs $($measured.Height), has $height)" }
        $script:graphics.DrawString($text, $font, $brush, [Drawing.RectangleF]::new($x,$y,$width,$height), $format)
    } finally { $font.Dispose(); $brush.Dispose(); $format.Dispose() }
}
function Card($x,$y,$width,$height,$title,$body,$fill=$palette.white,$accent=$palette.blue) {
    $brush=[Drawing.SolidBrush]::new((Color $fill)); $pen=[Drawing.Pen]::new((Color $palette.line),2)
    try { $script:graphics.FillRectangle($brush,$x,$y,$width,$height); $script:graphics.DrawRectangle($pen,$x,$y,$width,$height) }
    finally { $brush.Dispose(); $pen.Dispose() }
    Label $title ($x+24) ($y+22) ($width-48) 46 27 $accent $true
    Label $body ($x+24) ($y+84) ($width-48) ($height-104) 23
}
function Arrow($x1,$y1,$x2,$y2,$color=$palette.blue) {
    $pen=[Drawing.Pen]::new((Color $color),3)
    $cap=[Drawing.Drawing2D.AdjustableArrowCap]::new(5,6)
    $pen.CustomEndCap=$cap
    try { $script:graphics.DrawLine($pen,$x1,$y1,$x2,$y2) } finally { $pen.Dispose(); $cap.Dispose() }
}
function Begin-Figure($number,$title,$subtitle) {
    $script:bitmap=[Drawing.Bitmap]::new(1440,900)
    $script:graphics=[Drawing.Graphics]::FromImage($script:bitmap)
    $script:graphics.Clear((Color $palette.bg))
    $script:graphics.SmoothingMode=[Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $script:graphics.TextRenderingHint=[Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    Label "MILVUS / $number" 60 30 1300 30 20 $palette.blue $true
    Label $title 60 78 1320 66 42 $palette.ink $true
    Label $subtitle 62 157 1310 60 23 $palette.muted
    Label '自制教学示意图 · 非软件截图 · 完整步骤见正文' 62 850 1310 30 19 $palette.muted
}
function Save-Figure($name) {
    try { $script:bitmap.Save((Join-Path $OutputDirectory $name),[Drawing.Imaging.ImageFormat]::Png) }
    finally { $script:graphics.Dispose(); $script:bitmap.Dispose() }
}

Begin-Figure '01' '一句话怎样变成可检索的数据' 'Embedding 模型负责编码；Milvus 负责存储、索引和检索。'
Card 60 255 390 230 '1. 原始资料' "差旅制度、产品手册、FAQ`n先清洗，再按内容切块`n保留来源与权限字段" $palette.white
Card 525 255 390 230 '2. Embedding 模型' "文本 → 一组浮点数`n例如输出 384 维向量`n文档与问题使用配套编码" $palette.light
Card 990 255 390 230 '3. Milvus 集合' "保存向量、文本、来源`n建立索引并加载集合`n按相似度返回候选记录" $palette.green $palette.teal
Arrow 460 370 515 370
Arrow 925 370 980 370
Card 60 575 1320 190 '查询时走同样的编码路线' '用户问“出差住酒店怎么报销？” → 编码查询 → 限定可访问文档 → 找到相关制度。模型不同，即使向量维度相同，也不能直接混用。' $palette.white $palette.teal
Save-Figure '01-vector-pipeline.png'

Begin-Figure '02' '本教程的本机部署与连接地址' '三个核心服务 + 可选 Attu；对外端口只绑定本机 127.0.0.1。'
Card 60 245 570 180 'Windows / Linux / macOS' "Python SDK → 127.0.0.1:19530`n浏览器管理界面 → 127.0.0.1:8000" $palette.light
Card 810 245 570 180 'Attu 容器（可选）' "容器内连接 → standalone:19530`n容器里的 localhost 是它自己" $palette.white
Arrow 345 435 345 485
Arrow 1095 435 1095 465
Arrow 1095 465 345 465
Card 60 500 390 235 'standalone' "Milvus 3.0.1`n处理写入、索引与检索`n嵌入式 Woodpecker 管理 WAL" $palette.green $palette.teal
Card 525 500 390 235 'etcd' "保存元数据和协调状态`n不是向量检索引擎`n数据放入独立命名卷" $palette.white
Card 990 500 390 235 'MinIO' "保存对象数据`n本部署也存放 WAL 数据`n不向宿主机发布端口" $palette.white
Arrow 460 610 515 610
Arrow 255 775 1185 775
Arrow 255 745 255 775
Arrow 1185 775 1185 745
Save-Figure '02-deployment.png'

Begin-Figure '03' '写入以后，为什么还要索引和加载' '示例显式定义 Schema、创建索引，并使用 Strong 一致性观察刚写入的数据。'
Card 60 255 390 210 '1. 定义 Schema' "主键 id、文本 text`n类别 category、向量 vector`n向量维度必须与模型一致" $palette.light
Card 525 255 390 210 '2. 创建集合与索引' "集合组织数据`n本例先用 FLAT 精确检索`n再学习 ANN 索引的取舍" $palette.white
Card 990 255 390 210 '3. 写入与加载' "批量 insert / upsert`nload_collection 使数据可搜索`n失败时先读错误和日志" $palette.green $palette.teal
Arrow 460 355 515 355
Arrow 925 355 980 355
Card 60 565 625 205 'search：找相似记录' "传入查询向量，返回 Top-K`n可以叠加类别、租户等过滤条件`n分数不是正确概率" $palette.white
Card 755 565 625 205 'query / get：按条件或 ID 取数据' "不需要查询向量`nquery 使用过滤表达式；get 使用主键`n更新用 upsert，删除前确认目标" $palette.white $palette.teal
Save-Figure '03-data-lifecycle.png'

Begin-Figure '04' '把语义检索接成一个 RAG 应用' '示例实现检索与评测；生成回答是下一层，需要单独接入大语言模型。'
Card 60 245 390 220 '1. 用户与问题' "后端确认用户身份`n确定租户及可访问文档`n使用模型编码问题" $palette.light
Card 525 245 390 220 '2. 检索候选' "Milvus 向量检索 + 过滤`n可结合 BM25 关键词召回`n按 source_id 去重" $palette.white
Card 990 245 390 220 '3. 重排与选材' "Reranker 重排候选片段`n控制长度与重复内容`n找不到证据时允许拒答" $palette.green $palette.teal
Arrow 460 350 515 350
Arrow 925 350 980 350
Card 60 575 625 195 '4. 生成带来源的答案' "把问题和证据交给 LLM`n返回文档标题、片段与引用链接`n检索内容不能覆盖系统指令" $palette.white
Card 755 575 625 195 '5. 用数据改进' "检索质量：Recall@K、MRR`n使用体验：端到端延迟、费用`n权限检查与无答案问题也要测试" $palette.white $palette.teal
Save-Figure '04-rag.png'

Begin-Figure '05' '调优先找到问题在哪一层' '先建立基线，再一次只改变一个变量；不要仅凭几条查询宣布检索效果好。'
Card 60 245 625 220 '结果不相关：先检查数据与模型' "切块是否完整？中文模型是否合适？`n查询与文档是否使用正确前缀？`n过滤条件是否排除了正确答案？" $palette.light
Card 755 245 625 220 '正确答案漏掉：再检查召回' "对照精确搜索，检查近似索引损失`n尝试调整 Top-K、HNSW ef`n模型召回不足时考虑混合检索" $palette.white
Card 60 550 625 230 '速度慢：区分测量范围' "编码耗时、网络耗时、Milvus 耗时分开记`n预热后再测多次，观察 P50 / P95`n确认 CPU、内存、磁盘和并发负载" $palette.white
Card 755 550 625 230 '上线前：验证可靠性' "权限过滤必须由可信后端注入`n准备备份、恢复演练与版本回滚`n保留原始文档、模型版本和评测集" $palette.green $palette.teal
Save-Figure '05-quality-and-operations.png'
Write-Output 'Rendered 5 figures; all text blocks passed size checks.'
