"""FastAPI 接口层：处理聊天、FAQ、菜单和预约查询。"""

import os
from difflib import SequenceMatcher
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from pydantic import BaseModel
from sqlalchemy import text
from starlette.responses import StreamingResponse

from agent.langchain_assitant import assistant_query, build_agent, get_embeddings, get_mysql_engine

load_dotenv()
logger = logging.getLogger(__name__)
redis_client = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """启动时预热 Agent 和向量模型，避免首次聊天承担初始化耗时。"""
    try:
        await build_agent()
    except Exception:
        logger.exception("Agent prewarm failed; it will be retried on the first chat request")

    try:
        await asyncio.to_thread(get_embeddings)
    except Exception:
        logger.exception("Embedding model prewarm failed; semantic search may be unavailable")

    yield


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    query: str
    session_id: UUID


class FaqItem(BaseModel):
    question: str
    answer: str


class FaqResponse(BaseModel):
    success: bool
    query: str
    suggestions: list[FaqItem]


class ReservationItem(BaseModel):
    id: int
    num_people: int
    num_children: int
    arrival_time: Optional[str] = None
    seat_preference: Optional[str] = None
    main_dish_preference: Optional[str] = None
    other_comments: Optional[str] = None
    created_at: Optional[str] = None


class ReservationListResponse(BaseModel):
    success: bool
    reservations: list[ReservationItem]
    count: int
    message: str


class MenuItem(BaseModel):
    id: int
    dish_name: str
    price: float
    formatted_price: str
    description: Optional[str] = None
    category: str
    spice_level: Optional[int] = 0
    spice_text: str
    flavor: Optional[str] = None
    main_ingredients: Optional[str] = None
    cooking_method: Optional[str] = None
    is_vegetarian: bool = False
    allergens: Optional[str] = None
    is_available: bool = True


class MenuListResponse(BaseModel):
    success: bool
    menu_items: list[MenuItem]
    count: int
    message: str


def get_redis_client():
    """首次需要读取 FAQ 时连接 Redis，并复用客户端。"""
    global redis_client
    if redis_client is None:
        from redis.asyncio import Redis

        redis_client = Redis.from_url(
            os.getenv("REDIS_URL"),
            decode_responses=True,
        )
    return redis_client


async def load_faq_items() -> list[FaqItem]:
    """从 Redis 批量读取 FAQ，减少逐条请求的网络开销。"""
    client = get_redis_client()
    faq_keys = await client.smembers("faq:all_items")
    if not faq_keys:
        return []

    pipeline = client.pipeline()
    for faq_key in faq_keys:
        pipeline.hgetall(faq_key)

    faq_records = await pipeline.execute()
    return [
        FaqItem(question=record["question"], answer=record["answer"])
        for record in faq_records
        if "question" in record and "answer" in record
    ]


def get_similarity_score(query: str, faq_question: str) -> float:
    """用字符顺序相似度和字符集合相似度给 FAQ 问题打分。"""
    if not query or not faq_question:
        return 0.0

    sequence_score = SequenceMatcher(None, query, faq_question).ratio()
    query_chars = set(query)
    question_chars = set(faq_question)
    all_chars = query_chars | question_chars
    jaccard_score = len(query_chars & question_chars) / len(all_chars) if all_chars else 0
    return 0.6 * sequence_score + 0.4 * jaccard_score


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """把用户消息交给 Agent，并以 SSE 形式返回生成内容。"""
    return StreamingResponse(
        assistant_query(request.query, str(request.session_id)),
        media_type="text/event-stream",
    )


@app.get("/faq/suggest", response_model=FaqResponse)
async def faq_endpoint(
    query: str,
    limit: int = Query(default=1, ge=1, le=20),
):
    """按相似度返回最相关的 FAQ 问题。"""
    faq_items = await load_faq_items()
    ranked_items = sorted(
        faq_items,
        key=lambda item: get_similarity_score(query, item.question),
        reverse=True,
    )
    return FaqResponse(
        success=True,
        query=query,
        suggestions=ranked_items[:limit],
    )


@app.get("/reservation/list", response_model=ReservationListResponse)
async def reservation_list():
    """查询预约记录并转换为前端使用的响应格式。"""
    sql = text("""
        SELECT id, num_people, num_children, arrival_time, seat_preference,
               main_dish_preference, other_comments, created_at
        FROM menu.reservation_order
    """)
    with get_mysql_engine().connect() as connection:
        rows = connection.execute(sql).mappings().all()

    reservations = [
        ReservationItem(
            id=row["id"],
            num_people=row["num_people"],
            num_children=row["num_children"],
            arrival_time=str(row["arrival_time"]) if row["arrival_time"] else None,
            seat_preference=row["seat_preference"],
            main_dish_preference=row["main_dish_preference"],
            other_comments=row["other_comments"],
            created_at=str(row["created_at"]) if row["created_at"] else None,
        )
        for row in rows
    ]
    return ReservationListResponse(
        success=True,
        reservations=reservations,
        count=len(reservations),
        message="success",
    )


@app.get("/menu/list", response_model=MenuListResponse)
async def menu_list():
    """查询可售菜品，并补充前端展示用的价格和辣度文本。"""
    sql = text("""
        SELECT id, dish_name, price, description, category, spice_level,
               flavor, main_ingredients, cooking_method, is_vegetarian,
               allergens, is_available
        FROM menu_items
        WHERE is_available = 1
        ORDER BY category, dish_name
    """)
    spice_labels = {0: "不辣", 1: "微辣", 2: "中辣", 3: "重辣"}

    with get_mysql_engine().connect() as connection:
        rows = connection.execute(sql).mappings().all()

    menu_items = [
        MenuItem(
            id=row["id"],
            dish_name=row["dish_name"],
            price=row["price"],
            formatted_price=f"¥{row['price']:.2f}",
            description=row["description"],
            category=row["category"],
            spice_level=row["spice_level"],
            spice_text=spice_labels.get(row["spice_level"], "未知"),
            flavor=row["flavor"],
            main_ingredients=row["main_ingredients"],
            cooking_method=row["cooking_method"],
            is_vegetarian=row["is_vegetarian"],
            allergens=row["allergens"],
            is_available=row["is_available"],
        )
        for row in rows
    ]
    return MenuListResponse(
        success=True,
        menu_items=menu_items,
        count=len(menu_items),
        message="success",
    )
