"""把 FAQ 示例数据同步到 Redis。

每条 FAQ 存成独立 Hash，并用集合 ``faq:all_items`` 记录所有键名，
API 可以据此批量读取。
"""

import os

from dotenv import load_dotenv
from redis import Redis

load_dotenv()

FAQ_ITEMS = [
    {
        "id": "address",
        "question": "地址是什么",
        "answer": "北京市东城区东四十二条3号",
    },
    {
        "id": "phone",
        "question": "大堂电话是什么",
        "answer": "我们的电话是010-87621252，欢迎您联系",
    },
    {
        "id": "work_time",
        "question": "营业时间是什么时候",
        "answer": "我们的营业时间是：周日至周四：早10点至晚21点，周五周六：早10点至晚23点。欢迎您来哦",
    },
]


def sync_faq_items_to_redis() -> None:
    """写入所有 FAQ Hash，并更新保存键名的集合。"""
    client = Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
    )

    pipeline = client.pipeline()
    faq_keys = []
    for item in FAQ_ITEMS:
        key = f"faq:items:{item['id']}"
        pipeline.hset(
            name=key,
            mapping={
                "question": item["question"],
                "answer": item["answer"],
            },
        )
        faq_keys.append(key)

    pipeline.sadd("faq:all_items", *faq_keys)
    pipeline.execute()

    print(client.smembers("faq:all_items"))


if __name__ == "__main__":
    sync_faq_items_to_redis()
