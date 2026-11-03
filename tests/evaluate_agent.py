"""Run the 20-case live Agent and RAG evaluation suite."""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from langchain.messages import AIMessage, ToolMessage

from agent.langchain_assitant import build_agent, search_dishes_by_flavor

CASES = [
    {"id": "T01", "query": "菜单里有宫保鸡丁吗？", "tools": ["search_dishes_by_name"]},
    {"id": "T02", "query": "麻婆豆腐多少钱？", "tools": ["search_dishes_by_name"]},
    {"id": "T03", "query": "店里有哪些特色菜？", "tools": ["search_main_dishes"]},
    {"id": "T04", "query": "我喜欢清淡不油腻的菜，有什么推荐？", "tools": ["search_dishes_by_flavor"]},
    {"id": "T05", "query": "推荐一道口味偏辣的菜。", "tools": ["search_dishes_by_flavor"]},
    {"id": "T06", "query": "有没有适合素食者的菜？", "tools": ["search_dishes_by_flavor"]},
    {"id": "T07", "query": "帮我找一道酸甜口的菜。", "tools": ["search_dishes_by_flavor"]},
    {"id": "T08", "query": "推荐一道海鲜类菜品。", "tools": ["search_dishes_by_flavor"]},
    {"id": "T09", "query": "请帮我订明天晚上七点，三个人。", "tools": []},
    {"id": "T10", "query": "帮我预订靠窗的位置，今晚六点，两个人。", "tools": []},
    {"id": "T11", "query": "我想了解宫保鸡丁的主要食材。", "tools": ["search_dishes_by_name"]},
    {"id": "T12", "query": "菜单里有没有清炒时蔬？", "tools": ["search_dishes_by_name"]},
    {"id": "T13", "query": "招牌菜都有什么？", "tools": ["search_main_dishes"]},
    {"id": "T14", "query": "推荐一款不辣的菜。", "tools": ["search_dishes_by_flavor"]},
    {"id": "T15", "query": "有什么适合喜欢浓郁口味的人吃的菜？", "tools": ["search_dishes_by_flavor"]},
    {"id": "T16", "query": "鱼类菜品有哪些？", "tools": ["search_dishes_by_flavor"]},
    {"id": "T17", "query": "我对花生过敏，宫保鸡丁能吃吗？", "tools": ["search_dishes_by_name"]},
    {"id": "T18", "query": "订周末中午的位子，四位成人和一个小孩。", "tools": []},
    {"id": "T19", "query": "查一下菜单有没有红烧鲈鱼。", "tools": ["search_dishes_by_name"]},
    {"id": "T20", "query": "想吃清爽、少油的菜，请推荐。", "tools": ["search_dishes_by_flavor"]},
]

RAG_CASES = [
    ("R01", "清淡不油腻", ["清炒时蔬"]),
    ("R02", "微辣口味", ["宫保鸡丁"]),
    ("R03", "素食菜品", ["清炒时蔬"]),
    ("R04", "海鲜鱼类", ["红烧鲈鱼"]),
    ("R05", "酸甜口味", ["宫保鸡丁"]),
    ("R06", "浓郁酱香", ["红烧鲈鱼"]),
    ("R07", "少油清爽", ["清炒时蔬"]),
    ("R08", "香辣下饭", ["宫保鸡丁"]),
    ("R09", "不吃肉的素菜", ["清炒时蔬"]),
    ("R10", "鱼肉鲜美", ["红烧鲈鱼"]),
]


def tool_names(messages):
    names = []
    for message in messages:
        if isinstance(message, AIMessage):
            names.extend(call.get("name") for call in message.tool_calls or [])
        elif isinstance(message, ToolMessage):
            names.append(message.name)
    return set(filter(None, names))


async def evaluate_tools():
    results = []
    for case in CASES:
        session_id = f"eval-{case['id']}-{datetime.now().timestamp()}"
        try:
            agent = await build_agent()
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": case["query"]}]},
                config={"configurable": {"thread_id": session_id}},
            )
            actual = tool_names(result["messages"])
            expected, actual_set = set(case["tools"]), set(actual)
            results.append({"id": case["id"], "expected": sorted(expected), "actual": sorted(actual_set), "pass": expected == actual_set})
        except Exception as error:
            results.append({"id": case["id"], "expected": case["tools"], "actual": [], "pass": False, "error": str(error)})
    return results


def evaluate_rag():
    rows = []
    for case_id, query, expected_terms in RAG_CASES:
        try:
            retrieved = search_dishes_by_flavor.invoke({"user_query": query})
            text = " ".join(retrieved) if isinstance(retrieved, list) else str(retrieved)
            hit = any(term in text for term in expected_terms)
            rows.append({"id": case_id, "query": query, "expected": expected_terms, "hit": hit})
        except Exception as error:
            rows.append({"id": case_id, "query": query, "expected": expected_terms, "hit": False, "error": str(error)})
    return rows


async def main():
    parser = argparse.ArgumentParser(description="Evaluate tool selection and Milvus RAG recall")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    tool_results = await evaluate_tools()
    rag_results = evaluate_rag()
    report = {
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tool_accuracy": sum(row["pass"] for row in tool_results) / len(tool_results),
        "rag_hit_rate": sum(row["hit"] for row in rag_results) / len(rag_results),
        "tool_results": tool_results,
        "rag_results": rag_results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
