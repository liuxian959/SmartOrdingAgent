"""餐厅 Agent 的组装入口：模型、工具、外部服务和流式输出。

工具函数本身是普通 Python 函数，``@tool`` 会把函数说明和参数 schema
转换成模型可以理解并调用的工具定义。
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pymilvus import MilvusClient
from pymysql.cursors import DictCursor
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

load_dotenv()

# 项目根目录，用来定位模型文件和 prompt 文件。
PROJECT_ROOT = Path(__file__).parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "agent" / "prompts" / "system_prompt.txt"
MENU_COLLECTION_NAME = "menu_items"

# 需要连接外部服务的对象都延迟初始化，首次使用时再创建。
_embeddings = None
_milvus_client = None
_mysql_engine = None
_agent = None
_agent_lock = asyncio.Lock()
logger = logging.getLogger(__name__)


def resolve_embedding_model_path() -> str:
    """解析 embedding 模型路径；相对路径按项目根目录计算。"""
    model_path = os.getenv("EMBEDDING_MODEL_PATH", "models/bge-m3")
    path = Path(model_path)
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


def get_embeddings() -> HuggingFaceEmbeddings:
    """加载并复用本地文本向量模型。"""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model=resolve_embedding_model_path())
    return _embeddings


def get_milvus_client() -> MilvusClient:
    """创建并复用 Milvus 客户端。"""
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient(
            uri=os.getenv("MILVUS_URI"),
            token=os.getenv("MILVUS_TOKEN"),
        )
    return _milvus_client


def get_mysql_engine():
    """创建并复用 SQLAlchemy Engine（连接池，不是单条连接）。"""
    global _mysql_engine
    if _mysql_engine is None:
        database_url = (
            f"mysql+pymysql://{os.getenv('MYSQL_USERNAME')}:"
            f"{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:"
            f"{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
        )
        _mysql_engine = create_engine(database_url, pool_size=15)
    return _mysql_engine


@tool(description="查询餐厅特色主打菜品")
def search_main_dishes() -> list[dict]:
    """从菜单表中读取标记为特色菜的菜品。"""
    with pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USERNAME"),
        password=os.getenv("MYSQL_PASSWORD"),
    ) as connection:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute(
                """
                SELECT dish_name, price, description, category, spice_level,
                       flavor, main_ingredients, cooking_method,
                       is_vegetarian, allergens
                FROM menu.menu_items
                WHERE is_featured = 1
                """
            )
            return cursor.fetchall()


@tool(description="按用户明确提到的菜名在当前可售菜单中精确或部分匹配查询；适用于询问某道菜是否有、菜品详情或已知菜名，不要用特色菜查询代替")
def search_dishes_by_name(dish_name: str) -> list[dict] | str:
    """按菜名查询 MySQL 可售菜单，避免向量检索漏掉具体菜名。"""
    sql = text("""
        SELECT id, dish_name, price, description, category, spice_level,
               flavor, main_ingredients, cooking_method, is_vegetarian,
               allergens, is_available
        FROM menu_items
        WHERE is_available = 1 AND dish_name LIKE :dish_name
        ORDER BY dish_name
        LIMIT 10
    """)
    with get_mysql_engine().connect() as connection:
        rows = connection.execute(
            sql,
            {"dish_name": f"%{dish_name.strip()}%"},
        ).mappings().all()

    if not rows:
        return f"可售菜单中没有找到名称匹配‘{dish_name}’的菜品。"

    return [dict(row) for row in rows]


@tool(description="根据用户的口味/菜品偏好在菜品知识库中进行向量检索，返回最匹配的菜品描述")
def search_dishes_by_flavor(user_query: str) -> list[str] | str:
    """把用户偏好转成向量，从 Milvus 取回最相近的菜品文本。"""
    client = get_milvus_client()
    if not client.has_collection(collection_name=MENU_COLLECTION_NAME):
        logger.warning(
            "Milvus collection '%s' is missing; flavor search is unavailable",
            MENU_COLLECTION_NAME,
        )
        return "菜品语义检索库尚未初始化，请先同步菜单数据。"

    query_vector = get_embeddings().embed_query(user_query)
    search_result = client.search(
        collection_name=MENU_COLLECTION_NAME,
        data=[query_vector],
        anns_field="vector",
        output_fields=["text"],
        limit=3,
    )

    if not search_result or not search_result[0]:
        return "当前库里没有找到和用户喜好相关的菜品"

    return [item["entity"]["text"] for item in search_result[0]]


class ReservationToolArgsInfo(BaseModel):
    """预约工具参数；Field 的说明会提供给模型。"""

    num_people: int = Field(description="预约的总人数")
    num_children: int = Field(description="预约的0-2岁儿童人数")
    arrival_time: str = Field(description="预约的到达时间,格式: YYYY-MM-DD HH:MM:SS")
    seat_preference: str = Field(
        description="预约的座位偏好，当用户没有特殊需求时，传递空字符串"
    )
    main_dish_preference: str = Field(
        description="预约的主菜偏好，当用户没有特殊需求时，传递空字符串即可"
    )
    comment: str = Field(
        description="预约的其他备注，当用户没有特殊需求时，传递空字符串即可"
    )


@tool(description="为用户创建餐厅预订订单", args_schema=ReservationToolArgsInfo)
def make_reservation(
    num_people: int,
    num_children: int,
    arrival_time: str,
    seat_preference: str,
    main_dish_preference: str,
    comment: str,
) -> str:
    """校验预约信息后写入订单表。"""
    if num_people <= 0:
        return "预约人数必须大于0。"
    if num_children < 0 or num_children > num_people:
        return "儿童人数必须在0到总人数之间。"

    try:
        parsed_arrival_time = datetime.strptime(arrival_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "到达时间格式不正确，请使用 YYYY-MM-DD HH:MM:SS。"

    if parsed_arrival_time <= datetime.now():
        return "到达时间必须晚于当前时间。"

    sql = text("""
        INSERT INTO reservation_order (
            num_people, num_children, arrival_time,
            seat_preference, main_dish_preference, other_comments
        )
        VALUES (
            :num_people, :num_children, :arrival_time,
            :seat_preference, :main_dish_preference, :comment
        )
    """)
    parameters = {
        "num_people": num_people,
        "num_children": num_children,
        "arrival_time": arrival_time,
        "seat_preference": seat_preference,
        "main_dish_preference": main_dish_preference,
        "comment": comment,
    }

    with get_mysql_engine().connect() as connection:
        connection.execute(sql, parameters)
        connection.commit()

    return "预订成功"


def _build_time_prompt() -> dict:
    """给每次请求补充当前日期，让模型能理解“今天/明天”等说法。"""
    today = datetime.now().strftime("%Y-%m-%d")
    return {"role": "system", "content": f"当前日期为：{today}"}


async def assistant_query(user_query: str, session_id: str):
    """生成 Agent 的流式回复，按 SSE 格式逐段 yield 给前端。"""
    agent = await build_agent()
    messages = {
        "messages": [
            _build_time_prompt(),
            {"role": "user", "content": user_query},
        ]
    }
    # 每个会话使用独立 thread_id，避免不同用户的对话历史混在一起。
    config = {"configurable": {"thread_id": session_id}}

    async for chunk in agent.astream(
        messages,
        config=config,
        stream_mode="messages",
    ):
        message = chunk[0]
        if isinstance(message, ToolMessage):
            continue

        payload = json.dumps(
            {"content": message.content, "type": "token"},
            ensure_ascii=False,
        )
        yield f"data: {payload}\n\n"


async def build_agent():
    """构建并缓存 Agent；地图 MCP 不可用时继续提供基础点餐能力。"""
    global _agent
    if _agent is not None:
        return _agent

    async with _agent_lock:
        if _agent is not None:
            return _agent

        mcp_tools = []
        try:
            mcp_client = MultiServerMCPClient(
                connections={
                    "amap-maps": {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "@amap/amap-maps-mcp-server"],
                        "env": {"AMAP_MAPS_API_KEY": os.getenv("AMAP_MAPS_API_KEY", "")},
                    }
                }
            )
            mcp_tools = await mcp_client.get_tools()
        except Exception:
            logger.exception("Failed to connect to Amap MCP; continuing without map tools")

        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL"),
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
        )
        system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

        _agent = create_agent(
            model=llm,
            system_prompt=system_prompt,
            tools=[
                search_main_dishes,
                search_dishes_by_name,
                search_dishes_by_flavor,
                make_reservation,
                *mcp_tools,
            ],
            checkpointer=InMemorySaver(),
        )
        return _agent


async def test_agent():
    """本地调试：向 Agent 发一条消息并打印回复。"""
    agent = await build_agent()
    config = {"configurable": {"thread_id": "local-test"}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "你能为我做什么"}]},
        config=config,
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_agent())
