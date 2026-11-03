# Smart Ordering Agent

基于大语言模型的餐厅智能点餐与预约助手。项目提供 Vue 前端、FastAPI 服务和 LangChain/LangGraph Agent。

## 解决什么问题

传统线上点餐需要用户在菜单页逐层翻找，预约要对着表单一项项填写。本项目把这两类操作收敛成一次自然语言对话：用户直接说"推荐一道清淡的菜"或"明晚订两个人的位子"，由 Agent 识别意图、调用对应工具查询或写入数据，信息不全时会在对话中逐步追问确认，回复以流式方式实时输出。

## 主要功能

- **菜品咨询**：按菜名精确查询（MySQL），按"清淡""不辣"等口味偏好语义推荐（BGE-M3 + Milvus）
- **多轮预约**：Agent 逐步收集人数、到店时间、座位偏好等信息，用户确认后写入 MySQL
- **FAQ 问答**：营业时间、地址、电话等常见问题按字符相似度排序推荐（Redis）
- **地图问答**：通过 MCP 协议调用高德地图 MCP Server；MCP 不可用时自动降级，不影响核心点餐能力
- **流式回复**：SSE Token 级输出，前端逐字渲染并联动菜品高亮

## 技术栈

- **Agent**：LangChain / LangGraph、OpenAI-compatible Chat Completions API、工具调用、会话 checkpoint。
- **检索**：MySQL 菜单精确查询；本地 BGE-M3 embedding + Milvus 菜品语义检索；Redis FAQ 存储与相似问题排序。
- **服务端**：FastAPI、SQLAlchemy、PyMySQL、SSE 流式聊天。
- **前端**：Vue 3、Vite、Element Plus、Axios。
- **外部工具**：通过 LangChain MCP Adapter 连接高德地图 MCP Server。

> 本项目为个人学习与演示项目。运行前需要自行准备模型 API、MySQL、Redis 和 Milvus 等外部服务；不包含生产部署、安全审计或真实餐厅可用性保证。

## 架构与请求流程

```text
Vue 页面
  └─ Vite /api 代理 → FastAPI
       ├─ POST /chat → LangGraph Agent → LLM
       │                         ├─ 菜名查询 → MySQL
       │                         ├─ 偏好检索 → BGE-M3 → Milvus
       │                         ├─ 创建预约 → MySQL
       │                         └─ 地图问题 → 高德地图 MCP Server
       ├─ GET /faq/suggest → Redis FAQ → 相似度排序
       ├─ GET /menu/list → MySQL
       └─ GET /reservation/list → MySQL
```

明确提到菜名时，Agent 按提示优先调用 MySQL 查询；描述口味或偏好时可调用 Milvus 语义检索。预约流程由 Agent 收集必要信息并在确认后调用写入工具。聊天接口以 SSE 事件流返回内容，前端使用 `session_id` 区分会话。

## 目录结构

```text
.
├── agent/
│   ├── langchain_assitant.py    # Agent、工具及服务连接
│   ├── milvus_data_sync.py      # MySQL 菜单同步到 Milvus
│   ├── redis_data_sync.py       # FAQ 示例数据同步到 Redis
│   └── prompts/system_prompt.txt
├── api/main.py                  # FastAPI 路由
├── menu.sql                     # MySQL 示例 schema 和菜单数据
├── .env.example                 # 环境变量模板
├── tests/                       # 单元测试及手工 Agent 用例
├── ui/                          # Vue 3 前端
├── run.py                       # 后端启动入口
└── pyproject.toml               # Python 项目依赖
```

## 环境要求

- Python 3.12 或更高版本；推荐使用 [uv](https://docs.astral.sh/uv/)。
- Node.js 与 npm（版本以本机 Vite/依赖兼容情况为准）。
- MySQL、Redis，以及可访问的 Milvus 实例（Milvus Lite / Standalone / Zilliz Cloud 均需按各自连接方式配置）。
- 一个兼容 OpenAI Chat Completions API 的模型服务及 API Key。
- Node.js / npm 命令可从终端调用，用于启动高德地图 MCP Server。
- 本地 BGE-M3 模型文件。代码默认读取 `models/bge-m3`；可通过 `EMBEDDING_MODEL_PATH` 覆盖。

## 配置环境变量

在项目根目录创建 `.env`，填写下列配置。**不要把含真实凭据的 `.env` 提交到版本控制。**

```dotenv
LLM_MODEL=your-chat-model
LLM_API_KEY=replace-with-your-api-key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USERNAME=your-user
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=menu

REDIS_URL=redis://127.0.0.1:6379/0
MILVUS_URI=http://127.0.0.1:19530
MILVUS_TOKEN=
AMAP_MAPS_API_KEY=replace-with-your-amap-key

# 可选；默认是项目目录下的 models/bge-m3
# EMBEDDING_MODEL_PATH=models/bge-m3
```

注意：`menu.sql` 创建并使用名为 `menu` 的数据库。菜单同步脚本和部分 API/工具 SQL 也直接引用 `menu.menu_items` 或 `menu.reservation_order`；建议将 `MYSQL_DATABASE` 配置为 `menu`。Milvus 的 URI 和 token 格式依所使用的 Milvus 服务而异。聊天模型需要兼容当前 `ChatOpenAI` 使用方式。地图 MCP 工具依赖有效的高德地图 Key 和可运行的 Node.js/npx 环境。

## 本地启动

以下命令从仓库根目录执行。Windows PowerShell 可直接使用这些命令。

### 1. 初始化 MySQL

确认 MySQL 服务可连接，然后使用 MySQL 客户端导入示例结构和数据：

```powershell
mysql -u root -p < menu.sql
```

脚本会创建 `menu` 数据库、菜单表、预约表并插入示例菜品。**仅在可丢弃的本地开发数据库执行**：SQL 文件包含 `DROP TABLE`，会删除同名表及其中数据。

### 2. 准备 Python 环境并安装依赖

```powershell
uv sync
```

如需不用 uv，可根据 `pyproject.toml` 手动创建 Python 3.12 虚拟环境并安装项目依赖。首次加载 embedding 模型可能需要较多内存与初始化时间；请确认 `models/bge-m3` 已存在且模型文件完整。

### 3. 启动 Redis 与 Milvus

启动本机或远程 Redis / Milvus，并确认 `.env` 中的地址、凭据可访问。此仓库没有附带它们的容器编排配置，因此服务安装、初始化及持久化目录需按所选服务版本单独配置。

写入示例 FAQ：

```powershell
uv run python -m agent.redis_data_sync
```

同步菜单向量：

```powershell
uv run python -m agent.milvus_data_sync
```

**重要：菜单同步脚本会删除并重建 Milvus 的 `menu_items` collection。** 只对确认可重建的开发 collection 运行；它会以 MySQL 当前菜单重建向量数据。若 MySQL、模型文件或 Milvus 未准备好，脚本会失败。

### 4. 启动后端

```powershell
uv run python run.py
```

默认监听 `0.0.0.0:8000`。API 文档可在服务启动后访问 `http://127.0.0.1:8000/docs`。注意当前代码未定义独立 `/health` 路由。

### 5. 启动前端

另开终端：

```powershell
cd ui
npm ci
npm run dev
```

打开 Vite 启动日志显示的本地地址（配置默认端口为 `3000`）。开发服务器会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

生产构建：

```powershell
cd ui
npm run build
```

当前仓库说明的是本地开发构建；生产环境的静态文件托管、反向代理、HTTPS、CORS、进程管理和密钥管理需要自行配置。不要将开发服务器直接作为公网生产服务。

## API 概览

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/chat` | Agent 对话，SSE 流式响应。请求体为 `{"query":"...","session_id":"UUID"}` |
| `GET` | `/faq/suggest?query=...&limit=1` | 返回按当前字符相似度排序的 FAQ 建议，`limit` 范围为 1–20 |
| `GET` | `/menu/list` | 返回可售菜单 |
| `GET` | `/reservation/list` | 返回预约记录，需 `X-Admin-Key` 请求头 |

### 输入输出示例

以下示例中的菜品与 FAQ 内容均来自仓库自带数据（`menu.sql`、`agent/redis_data_sync.py`）。

**POST /chat**（SSE 流式）

请求体：

```json
{ "query": "推荐一道清淡的菜", "session_id": "00000000-0000-0000-0000-000000000001" }
```

响应为 `text/event-stream`，每个事件携带一个文本片段，按顺序拼接即完整回答（Agent 会先调用口味检索工具，再基于结果生成）：

```text
data: {"content": "为", "type": "token"}

data: {"content": "您", "type": "token"}

data: {"content": "推荐", "type": "token"}

...（持续输出直至回答结束，连接关闭）
```

**GET /menu/list**

响应（`count` 为在售菜品总数，示例菜单为 5 道菜；此处仅展示 1 条）：

```json
{
  "success": true,
  "count": 5,
  "message": "success",
  "menu_items": [
    {
      "id": 3,
      "dish_name": "清炒时蔬",
      "price": 15.0,
      "formatted_price": "¥15.00",
      "description": "新鲜时令蔬菜清炒，营养健康，口感清爽",
      "category": "素食",
      "spice_level": 0,
      "spice_text": "不辣",
      "flavor": "清淡爽口",
      "main_ingredients": "时令蔬菜,蒜蓉",
      "cooking_method": "清炒",
      "is_vegetarian": true,
      "allergens": "",
      "is_available": true
    }
  ]
}
```

**GET /faq/suggest?query=店里几点关门&limit=1**

```json
{
  "success": true,
  "query": "店里几点关门",
  "suggestions": [
    {
      "question": "营业时间是什么时候",
      "answer": "我们的营业时间是：周日至周四：早10点至晚21点，周五周六：早10点至晚23点。欢迎您来哦"
    }
  ]
}
```

**GET /reservation/list**（请求头携带 `X-Admin-Key: <ADMIN_API_KEY>`）

`menu.sql` 未包含预约示例数据，初次查询返回空列表；通过对话完成一次预约后再查询即为：

```json
{
  "success": true,
  "count": 1,
  "message": "success",
  "reservations": [
    {
      "id": 1,
      "num_people": 4,
      "num_children": 0,
      "arrival_time": "2026-11-03 12:00:00",
      "seat_preference": "靠窗",
      "main_dish_preference": "红烧鲈鱼",
      "other_comments": null,
      "created_at": "2026-11-02 18:30:00"
    }
  ]
}
```

（`reservations` 中的字段值随实际对话内容而定。）

### Agent / RAG 评测

新增 20 题评测脚本，覆盖菜名精确查询、特色菜、偏好检索及预约意图。工具调用准确率按单题实际调用工具集合与预期集合完全一致计算；RAG 命中率为 10 条预设偏好查询中，预期菜品名称出现在 Milvus Top-3 结果的比例。评测会真实调用模型和外部服务，预约题只使用信息不完整的请求，不会触发预约写入。建议在独立开发环境运行：

```powershell
uv run python tests/evaluate_agent.py --output evaluation-results.json
```

运行需配置模型 API、MySQL、Redis、Milvus、embedding 模型，并同步菜单向量。报告中的 RAG 预期菜名对应当前示例菜单，应随菜单数据更新。模型输出有随机性，指标仅代表本次运行，不等价于生产环境的稳定准确率。成功运行后可将报告的运行日期、工具调用准确率和 RAG 命中率记录在本节，便于版本间对比；本仓库尚未在当前环境完成真实服务评测，因此不填入虚构结果。

聊天请求示例：

```powershell
$body = @{ query = '推荐一道清淡的菜'; session_id = '00000000-0000-0000-0000-000000000001' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/chat' -Method Post -ContentType 'application/json' -Body $body
```

SSE 客户端更适合使用浏览器前端或支持事件流的 HTTP 客户端。`/reservation/list` 需要管理员密钥（`X-Admin-Key` 请求头）访问，当前返回全部记录且未实现分页。注意：示例前端通过 `VITE_ADMIN_API_KEY` 携带该密钥，而前端环境变量会打包进浏览器可见的产物中，仅适合本地演示；真实部署应由服务端代理持有密钥。

## 测试

运行自动化测试：

```powershell
uv run python -m pytest -q
```

`tests/agent_cases.md` 记录了手工验证范围和已知缺口。自动化测试目前以 FAQ 相似度、菜名查询等单元测试为主；它不代表真实 LLM、Redis、MySQL、Milvus 或浏览器端到端均已通过验证。菜单同步和 Agent 真实调用需要相应服务、模型及凭据可用。

## 安全与已知限制

- `.env` 已在 `.gitignore` 中排除；提交前仍应检查 Git 暂存内容。曾经泄露的凭据需要在对应平台轮换。
- `InMemorySaver` 将会话检查点保存在进程内存中，进程重启后不保留；多 worker 之间也不共享。
- MySQL、Redis、Milvus、模型 API 和地图 MCP 都是外部依赖；需要真实配置才能完整运行。
- 向量检索效果取决于数据覆盖、embedding、索引和查询表达；小规模示例菜单不构成准确率保证。
- 预约写入工具会直接操作数据库，且没有独立于对话链路的认证、限流或幂等保护；`/reservation/list` 的管理员密钥若按示例配置在前端持有，则等同公开。仅用于本地/受控演示。
- 项目含有示例餐厅资料与菜单数据；上线或公开演示前应确认数据使用和品牌信息授权。
