# coding=utf-8
"""
发送 GitHub Trending 仓库信息
"""
import asyncio
import os
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


async def fetch_github_trending():
    """从 GitHub API 获取热门仓库"""
    print("=" * 60)
    print("获取 GitHub 热门仓库")
    print("=" * 60)

    proxy = os.environ.get("HTTP_PROXY")
    token = os.environ.get("GITHUB_TOKEN", "")

    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    async with httpx.AsyncClient(proxy=proxy, timeout=30.0) as client:
        # 搜索近期创建的热门仓库 (Python 相关)
        query = "stars:>1000 created:>2024-01-01"
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=5"

        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            repos = data.get("items", [])[:5]

            results = []
            for repo in repos:
                results.append({
                    "name": repo.get("full_name", ""),
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "language": repo.get("language", ""),
                    "url": repo.get("html_url", ""),
                    "created": repo.get("created_at", "")[:10],
                })

            print(f"✅ 获取到 {len(results)} 个热门仓库")
            return results
        else:
            print(f"❌ GitHub API 错误: {response.status_code}")
            return []


async def main():
    """主函数"""
    # 获取 GitHub 热门仓库
    repos = await fetch_github_trending()

    if not repos:
        # 使用示例数据
        repos = [
            {
                "name": "microsoft/Phi-4",
                "description": "Phi-4: Microsoft's latest language model",
                "stars": 15000,
                "forks": 1200,
                "language": "Python",
                "url": "https://github.com/microsoft/Phi-4",
                "created": "2024-12-01"
            },
            {
                "name": "deepseek-ai/DeepSeek-V3",
                "description": "DeepSeek V3 - Strong MoE model",
                "stars": 12000,
                "forks": 900,
                "language": "Python",
                "url": "https://github.com/deepseek-ai/DeepSeek-V3",
                "created": "2024-11-15"
            },
            {
                "name": "Qwen/Qwen2.5-VL",
                "description": "Multimodal AI model from Alibaba",
                "stars": 9800,
                "forks": 750,
                "language": "Python",
                "url": "https://github.com/Qwen/Qwen2.5-VL",
                "created": "2024-10-20"
            },
            {
                "name": "anthropic/claude-code",
                "description": "Claude Code - AI coding assistant",
                "stars": 8500,
                "forks": 600,
                "language": "TypeScript",
                "url": "https://github.com/anthropic/claude-code",
                "created": "2024-09-10"
            },
            {
                "name": "google/gemma.cpp",
                "description": "Google's efficient LLM inference",
                "stars": 7200,
                "forks": 450,
                "language": "C++",
                "url": "https://github.com/google/gemma.cpp",
                "created": "2024-08-05"
            }
        ]

    # 打印仓库信息
    print(f"\n共 {len(repos)} 个热门仓库:")
    for i, repo in enumerate(repos):
        print(f"\n--- 仓库 {i+1} ---")
        print(f"名称: {repo.get('name', 'N/A')}")
        print(f"描述: {repo.get('description', 'N/A')}")
        print(f"Stars: {repo.get('stars', 0):,}")
        print(f"语言: {repo.get('language', 'N/A')}")

    # 生成标题和概要
    print("\n" + "=" * 60)
    print("生成标题和概要")
    print("=" * 60)

    from src.intelligence.translator import get_translator
    translator = get_translator()

    results = []

    for repo in repos:
        desc = repo.get("description", "") or repo.get("name", "")

        # 使用 GitHub 仓库生成器
        title = await translator.generate_github_title(desc, max_length=30)
        summary = await translator.generate_github_summary(desc, max_length=150)

        results.append({
            "title": title,
            "summary": summary,
            "stars": repo.get("stars", 0),
            "language": repo.get("language", ""),
            "url": repo.get("url", ""),
        })

    # 生成飞书消息
    print("\n" + "=" * 60)
    print("生成飞书消息")
    print("=" * 60)

    message_parts = ["💻 GitHub 热门开源项目\n\n"]

    for i, r in enumerate(results):
        stars_str = f"{r['stars']:,}"
        message_parts.append(f"{i+1}. {r['title']}\n")
        message_parts.append(f"   📝 {r['summary']}\n")
        message_parts.append(f"   🗣️ {stars_str} ⭐ | 💻 {r['language']}\n")
        if r.get('url'):
            message_parts.append(f"   🔗 {r['url']}\n")
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
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
