"""把 MySQL 菜单同步到 Milvus 向量库，供 Agent 做菜品语义检索。

注意：脚本会删除并重建 ``menu_items`` 集合，原有向量数据会被清空，
只应在初始化或手动重建索引时运行。
"""

import os
from decimal import Decimal
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymilvus import DataType, IndexType, MilvusClient
from pymysql.cursors import DictCursor

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
COLLECTION_NAME = "menu_items"

# 数据库字段 -> 中文标签，拼成文本后更适合模型阅读和语义检索。
FIELD_LABELS = {
    "dish_name": "主菜名称",
    "price": "价格",
    "description": "描述",
    "category": "分类",
    "spice_level": "辣度等级",
    "flavor": "口味",
    "main_ingredients": "主要食材",
    "cooking_method": "烹饪方法",
    "is_vegetarian": "是否为素食",
    "allergens": "过敏信息",
}


def fetch_menu_rows() -> list[dict]:
    """从 MySQL 读取菜单原始数据。"""
    with pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        user=os.getenv("MYSQL_USERNAME"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    ) as connection:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute(
                """
                SELECT dish_name, price, description, category, spice_level,
                       flavor, main_ingredients, cooking_method,
                       is_vegetarian, allergens
                FROM menu.menu_items
                """
            )
            return cursor.fetchall()


def build_search_texts(menu_rows: list[dict]) -> list[str]:
    """把每行菜单转成带中文标签的自然语言文本。"""
    texts = []
    for row in menu_rows:
        lines = []
        for field, value in row.items():
            if isinstance(value, Decimal):
                value = float(value)
            lines.append(f"{FIELD_LABELS[field]}: {value}")
        texts.append("\n".join(lines))
    return texts


def create_milvus_collection(client: MilvusClient) -> None:
    """重建 ``menu_items`` 集合：主键、1024 维向量和原文。"""
    client.drop_collection(collection_name=COLLECTION_NAME)

    schema = (
        MilvusClient.create_schema(auto_id=True)
        .add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        .add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1024)
        .add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            max_length=1500,
        )
    )
    index_params = MilvusClient.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type=IndexType.HNSW,
        metric_type="L2",
    )
    client.create_collection(
        collection_name=COLLECTION_NAME,
        schema=schema,
        index_params=index_params,
    )


def resolve_embedding_model_path() -> str:
    """支持用环境变量覆盖模型路径，相对路径按项目根目录解析。"""
    model_path = os.getenv("EMBEDDING_MODEL_PATH", "models/bge-m3")
    if os.path.isabs(model_path):
        return model_path
    return str(PROJECT_ROOT / model_path)


def sync_menu_embeddings() -> None:
    """读取菜单、生成向量并写入 Milvus。"""
    from langchain_huggingface import HuggingFaceEmbeddings

    menu_rows = fetch_menu_rows()
    search_texts = build_search_texts(menu_rows)

    embedding_model = HuggingFaceEmbeddings(model=resolve_embedding_model_path())
    vectors = embedding_model.embed_documents(search_texts)

    client = MilvusClient(
        uri=os.getenv("MILVUS_URI"),
        token=os.getenv("MILVUS_TOKEN"),
    )
    create_milvus_collection(client)

    records = [
        {"vector": vector, "text": text}
        for vector, text in zip(vectors, search_texts)
    ]
    insert_result = client.insert(data=records, collection_name=COLLECTION_NAME)
    print(insert_result)


if __name__ == "__main__":
    sync_menu_embeddings()
