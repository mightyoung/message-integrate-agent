# coding=utf-8
"""
测试学术论文标题/概要生成功能
"""
import asyncio
import os
import logging
import httpx

# 设置环境变量
env_file = ".env.prod"
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

os.environ.setdefault("ENVIRONMENT", "test")

# 设置日志
logging.basicConfig(level=logging.INFO)


async def fetch_arxiv_papers():
    """从 arXiv 获取热门论文（按相关性排序）"""
    print("=" * 60)
    print("从 arXiv 获取热门论文")
    print("=" * 60)

    try:
        proxy = os.environ.get("HTTP_PROXY")

        # arXiv API - 搜索 AI 相关论文，获取最新发表的论文
        query = "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.NE"
        # 使用 submittedDate 排序获取最新发表的论文
        url = f"http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"

        async with httpx.AsyncClient(proxy=proxy, timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)

            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                from datetime import datetime
                root = ET.fromstring(response.text)

                # 命名空间 - arXiv 使用 atom 命名空间
                ns = {'atom': 'http://www.w3.org/2005/Atom'}

                papers = []
                for entry in root.findall('atom:entry', ns):
                    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                    abstract = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
                    paper_id = entry.find('atom:id', ns).text.strip()
                    url_link = entry.find('atom:link[@title="pdf"]', ns)
                    pdf_url = url_link.get('href', '') if url_link is not None else paper_id

                    # 获取发表日期 - 尝试多种方式
                    pub_date_str = ""
                    try:
                        published = entry.find('atom:published', ns)
                        if published is not None and published.text:
                            pub_date_str = published.text.strip()[:10]
                        else:
                            # 从 arXiv ID 推断日期 (格式: YYMM.NNNNN)
                            arxiv_id = paper_id.split('/')[-1] if '/' in paper_id else paper_id
                            if '.' in arxiv_id:
                                yymm = arxiv_id.split('.')[0]
                                if len(yymm) >= 4:
                                    year = "20" + yymm[:2]
                                    month = yymm[2:4]
                                    pub_date_str = f"{year}-{month}-??"
                    except Exception as e:
                        print(f"解析日期错误: {e}")

                    papers.append({
                        "title": title,
                        "abstract": abstract,
                        "url": pdf_url,
                        "id": paper_id.split('/')[-1] if '/' in paper_id else paper_id,
                        "published": pub_date_str,
                        "source": "arXiv"
                    })

                print(f"✅ 获取到 {len(papers)} 篇 arXiv 论文")
                return papers
            else:
                print(f"❌ 获取失败: {response.status_code}")
                return []
    except Exception as e:
        print(f"❌ 获取异常: {e}")
        return []


async def fetch_huggingface_papers():
    """从 HuggingFace Papers 页面获取热门论文（动态渲染，需备用源）"""
    print("=" * 60)
    print("HuggingFace Papers 页面为 SPA 动态渲染，无法直接获取")
    print("使用 arXiv 作为主要来源")
    print("=" * 60)
    # HuggingFace Papers 是 SPA 动态渲染页面，没有公开 API
    # 回退到 arXiv
    return await fetch_arxiv_papers()


async def fetch_with_http():
    """使用 HTTP 直接获取多源论文（Nature）"""
    print("=" * 60)
    print("使用 HTTP 获取 Nature 论文")
    print("=" * 60)

    import re

    papers = []
    proxy = os.environ.get("HTTP_PROXY")

    async with httpx.AsyncClient(proxy=proxy, timeout=30.0, follow_redirects=True) as client:
        # 1. Nature
        print("\n--- 获取 Nature 论文 ---")
        try:
            response = await client.get("https://www.nature.com/search?q=AI+machine+learning&sort=date")
            if response.status_code == 200:
                text = response.text
                # 提取标题、链接和日期
                title_pattern = re.findall(r'<a[^>]+href="(/articles/[^"]+)"[^>]*>([^<]+)</a>', text)
                # 提取日期
                date_pattern = re.findall(r'(\d{1,2}\s+\w+\s+\d{4})', text)

                print(f"Nature 找到 {len(title_pattern)} 个标题, {len(date_pattern)} 个日期")

                for i, (href, title) in enumerate(title_pattern[:5]):
                    if title and len(title) > 5:
                        pub_date = date_pattern[i] if i < len(date_pattern) else ""
                        full_url = f"https://www.nature.com{href}"
                        print(f"Nature paper {i+1}: {title[:30]}... URL: {full_url}")
                        papers.append({
                            "title": title.strip(),
                            "abstract": f"Nature AI 论文: {title.strip()}",
                            "url": full_url,
                            "published": pub_date,
                            "source": "Nature"
                        })
                print(f"获取到 {len([p for p in papers if p['source'] == 'Nature'])} 篇 Nature 论文")
        except Exception as e:
            print(f"Nature 获取异常: {e}")

        # 3. Science
        print("\n--- 获取 Science 论文 ---")
        try:
            response = await client.get("https://www.science.org/collections")
            if response.status_code == 200:
                # 提取标题和链接
                title_pattern = re.findall(r'<a[^>]+href="(https://www\.science\.org/doi/[^"]+)"[^>]*>([^<]+)</a>', response.text)
                for url, title in title_pattern[:5]:
                    if title and len(title) > 5:
                        papers.append({
                            "title": title.strip(),
                            "abstract": f"Science AI 论文: {title.strip()}",
                            "url": url,
                            "published": "",
                            "source": "Science"
                        })
                print(f"获取到 {len([p for p in papers if p['source'] == 'Science'])} 篇 Science 论文")
        except Exception as e:
            print(f"Science 获取异常: {e}")

    # 如果 HTTP 获取失败，回退到 arXiv
    if len(papers) < 3:
        print("\n⚠️ HTTP 获取论文数量不足，回退到 arXiv")
        return []

    print(f"\n✅ 共获取 {len(papers)} 篇论文")
    return papers


async def main():
    """主函数"""
    # 1. 首先尝试使用 HuggingFace Papers API
    print("尝试使用 HuggingFace Papers API 获取论文...")
    hf_papers = await fetch_huggingface_papers()

    # 2. 如果 HuggingFace 失败，使用 HTTP 获取 Nature 论文
    if not hf_papers or len(hf_papers) < 3:
        print("\n回退到 Nature 获取论文...")
        http_papers = await fetch_with_http()
        if http_papers:
            hf_papers = http_papers
            print(f"\n使用 Nature 获取到 {len(hf_papers)} 篇论文")

    # 3. 如果还是失败，使用 arXiv
    if not hf_papers or len(hf_papers) < 3:
        print("\n回退到 arXiv 获取论文...")
        arxiv_papers = await fetch_arxiv_papers()
        if arxiv_papers:
            hf_papers = arxiv_papers
            print(f"\n使用 arXiv 获取到 {len(hf_papers)} 篇论文")

    # 如果获取失败，使用示例数据
    if not hf_papers:
        print("\n使用示例论文数据进行测试...")
        hf_papers = [
            {
                "title": "DeepSeek-V3",
                "abstract": "DeepSeek-V3 is a powerful Mixture-of-Experts language model with 671B total parameters with 37B activated for each token. It achieves superior performance across various benchmarks while maintaining efficient inference through innovative training techniques."
            },
            {
                "title": "Qwen2.5-VL",
                "abstract": "Qwen2.5-VL is a multimodal large language model that understands images, videos, and spatial locations. It achieves state-of-the-art performance on multiple vision benchmarks and supports native resolution input up to 4K."
            },
            {
                "title": "R1",
                "abstract": "We present DeepSeek-R1, a reasoning model that achieves performance comparable to OpenAI-o1 on reasoning tasks. It uses pure reinforcement learning without supervised fine-tuning, demonstrating the emergence of reasoning behaviors."
            }
        ]
    else:
        # 转换格式 - 处理不同字段名
        converted = []
        for p in hf_papers:
            # 尝试多种可能的字段名
            title = p.get("title") or p.get("paper_title", "")
            abstract = p.get("abstract") or p.get("paper_abstract", "")
            paper_id = p.get("id") or p.get("paper_id", "")
            # 优先使用已有的 URL，否则从 ID 构建
            url = p.get("url", "")
            if not url and paper_id:
                url = f"https://huggingface.co/papers/{paper_id}"
            # 保留发表日期和来源
            published = p.get("published", "")
            source = p.get("source", "")

            if title:
                converted.append({
                    "title": title,
                    "abstract": abstract,
                    "url": url,
                    "id": paper_id,
                    "published": published
                })
        hf_papers = converted

    print(f"\n共 {len(hf_papers)} 篇论文")

    # 打印论文信息
    for i, paper in enumerate(hf_papers):
        print(f"\n--- 论文 {i+1} ---")
        print(f"标题: {paper.get('title', 'N/A')}")
        print(f"摘要: {paper.get('abstract', 'N/A')[:150]}...")

    # 测试学术论文标题/概要生成
    print("\n" + "=" * 60)
    print("测试学术论文标题/概要生成")
    print("=" * 60)

    from src.intelligence.translator import get_translator
    translator = get_translator()

    results = []

    for i, paper in enumerate(hf_papers):
        abstract = paper.get('abstract', paper.get('title', ''))
        print(f"\n--- 处理论文 {i+1} ---")

        # 使用学术论文生成器
        title = await translator.generate_academic_title(abstract, max_length=30)
        summary = await translator.generate_academic_summary(abstract, max_length=150)
        print(f"📚 论文标题: {title}")
        print(f"📚 论文概要: {summary}")

        # 获取论文 URL
        paper_url = paper.get('url', '')
        # 获取论文发表日期
        pub_date = paper.get('published', '')

        results.append({
            "title": title,
            "summary": summary,
            "url": paper_url,
            "published": pub_date
        })

    # 生成飞书消息
    print("\n" + "=" * 60)
    print("生成飞书消息")
    print("=" * 60)

    # 构建消息内容
    message_parts = ["📚 热门学术论文\n\n"]

    for i, r in enumerate(results):
        message_parts.append(f"{i+1}. {r['title']}\n")
        message_parts.append(f"   📝 {r['summary']}\n")
        if r.get('published'):
            message_parts.append(f"   📅 {r['published']}\n")
        # 添加来源信息
        message_parts.append(f"   🔗 {r.get('url', 'N/A')}\n")
        message_parts.append("\n")

    message_content = "".join(message_parts)
    print(message_content)

    # 发送到飞书
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if webhook_url:
        print("\n" + "=" * 60)
        print("发送到飞书...")
        print("=" * 60)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json={"msg_type": "text", "content": {"text": message_content}}
            )
            if response.status_code == 200:
                print("✅ 发送成功!")
            else:
                print(f"❌ 发送失败: {response.status_code}")
                print(response.text)
    else:
        print("\n⚠️ 未配置 FEISHU_WEBHOOK_URL，跳过发送")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
