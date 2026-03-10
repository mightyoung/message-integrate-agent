# coding=utf-8
"""
使用 Firecrawl 抓取 Science.org 和 SciRobotics 热点新闻，并发送到飞书
"""
import asyncio
import os
import re

# 设置环境变量
env_file = ".env.prod"
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

from src.intelligence.firecrawl_adapter import get_firecrawl_adapter


def extract_articles_from_content(content: str, source_name: str, limit: int = 5):
    """从抓取的内容中提取热点文章"""
    articles = []

    # 匹配文章链接模式: ### [文章标题](URL)
    # 或 [文章标题](URL)
    pattern = r'###\s*\[([^\]]+)\]\(([^)]+)\)'

    matches = re.findall(pattern, content)

    for i, (title, url) in enumerate(matches[:limit]):
        title = title.strip()
        url = url.strip()

        # 跳过非文章链接
        if not url.startswith('http'):
            continue
        if 'doi.org' not in url and 'science.org/doi' not in url:
            # 只保留 DOI 链接
            continue

        # 清理标题（移除多余描述）
        title = re.sub(r'\s*"[^"]*"$', '', title)

        articles.append({
            "title": title,
            "url": url,
            "source": source_name
        })

    return articles


async def scrape_and_process_science():
    """抓取并处理 Science.org 文章"""
    print("=" * 60)
    print("抓取 Science.org 热点新闻")
    print("=" * 60)

    adapter = get_firecrawl_adapter()
    if not adapter:
        print("❌ Firecrawl 适配器初始化失败")
        return []

    result = await adapter.scrape_url(
        "https://www.science.org/",
        formats=["markdown"]
    )

    if result and result.success:
        articles = extract_articles_from_content(result.content, "Science", limit=5)
        print(f"✅ 提取到 {len(articles)} 篇文章")
        for i, a in enumerate(articles):
            print(f"  {i+1}. {a['title'][:50]}...")
        return articles
    else:
        print(f"❌ 抓取失败")
        return []


async def scrape_and_process_robotics():
    """抓取并处理 SciRobotics 文章"""
    print("=" * 60)
    print("抓取 SciRobotics 热点新闻")
    print("=" * 60)

    adapter = get_firecrawl_adapter()
    if not adapter:
        print("❌ Firecrawl 适配器初始化失败")
        return []

    result = await adapter.scrape_url(
        "https://www.science.org/journal/scirobotics",
        formats=["markdown"]
    )

    if result and result.success:
        articles = extract_articles_from_content(result.content, "Science Robotics", limit=5)
        print(f"✅ 提取到 {len(articles)} 篇文章")
        for i, a in enumerate(articles):
            print(f"  {i+1}. {a['title'][:50]}...")
        return articles
    else:
        print(f"❌ 抓取失败")
        return []


async def generate_chinese_content(articles: list, source_name: str):
    """使用 LLM 生成中文标题和概要"""
    from src.intelligence.translator import get_translator

    translator = get_translator()
    results = []

    for article in articles:
        # 生成中文标题和概要
        title = await translator.generate_academic_title(article['title'], max_length=30)
        summary = await translator.generate_academic_summary(article['title'], max_length=150)

        results.append({
            "title": title,
            "summary": summary,
            "url": article['url'],
            "source": source_name
        })

    return results


async def send_to_feishu(articles: list, source_name: str):
    """发送到飞书"""
    import httpx

    # 构建消息
    emoji = "🔬" if source_name == "Science" else "🤖"
    message_parts = [f"{emoji} {source_name} 热点研究\n\n"]

    for i, a in enumerate(articles):
        message_parts.append(f"{i+1}. {a['title']}\n")
        message_parts.append(f"   📝 {a['summary']}\n")
        # 清理 URL（去除引号和额外描述）
        clean_url = a['url'].split('"')[0] if '"' in a['url'] else a['url']
        message_parts.append(f"   🔗 {clean_url}\n\n")

    message_content = "".join(message_parts)
    print(f"\n--- {source_name} 消息 ---\n{message_content}")

    # 发送
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if webhook_url:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json={"msg_type": "text", "content": {"text": message_content}}
            )
            if response.status_code == 200:
                print(f"✅ {source_name} 发送成功!")
            else:
                print(f"❌ {source_name} 发送失败: {response.status_code}")
    else:
        print(f"⚠️ 未配置 FEISHU_WEBHOOK_URL")


async def main():
    """主函数"""
    # 1. 抓取 Science.org
    science_articles = await scrape_and_process_science()

    # 2. 抓取 SciRobotics
    robotics_articles = await scrape_and_process_robotics()

    # 3. 生成中文内容
    if science_articles:
        print("\n" + "=" * 60)
        print("生成 Science 中文内容")
        print("=" * 60)
        science_results = await generate_chinese_content(science_articles, "Science")

        # 发送到飞书
        await send_to_feishu(science_results, "Science")

    if robotics_articles:
        print("\n" + "=" * 60)
        print("生成 SciRobotics 中文内容")
        print("=" * 60)
        robotics_results = await generate_chinese_content(robotics_articles, "Science Robotics")

        # 发送到飞书
        await send_to_feishu(robotics_results, "Science Robotics")

    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
