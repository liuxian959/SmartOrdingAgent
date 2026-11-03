"""Redis 基础命令练习：字符串、Hash 和 Pipeline 的用法。"""

from redis import Redis

REDIS_URL = "redis://localhost:6379"


def connect_redis() -> Redis:
    """创建字符串解码的 Redis 客户端，方便直接打印结果。"""
    return Redis.from_url(REDIS_URL, decode_responses=True)


def demo_string_and_hash() -> None:
    """写入并读取一个字符串键和一个 Hash 键。"""
    client = connect_redis()

    client.set("name", "张三")
    print(client.get("name"))

    client.hset(
        "faq:items:address",
        mapping={
            "question": "地址是多少？",
            "answer": "北京市海淀区",
        },
    )
    print(client.hgetall("faq:items:address"))


def demo_pipeline() -> None:
    """用 Pipeline 一次提交多条命令，减少网络往返。"""
    client = connect_redis()
    pipeline = client.pipeline()

    pipeline.set("name2", "张三")
    pipeline.get("name2")
    pipeline.hset(
        "faq:items:phone:test",
        mapping={
            "question": "手机号是多少？",
            "answer": "13800000000",
        },
    )

    # execute() 会按顺序返回每条命令的结果。
    results = pipeline.execute()
    print(results)


if __name__ == "__main__":
    demo_string_and_hash()
    demo_pipeline()
