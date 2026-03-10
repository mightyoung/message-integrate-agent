#!/usr/bin/env python3
"""
Docker 容器内 LLM 验证脚本
用于测试 Docker 环境中 DeepSeek API 是否正常工作
"""
import os
import sys

def test_env_config():
    """测试环境变量配置"""
    print("=== 环境变量配置 ===")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "")
    model = os.environ.get("DEFAULT_MODEL", "")
    http_proxy = os.environ.get("HTTP_PROXY", "")
    https_proxy = os.environ.get("HTTPS_PROXY", "")
    no_proxy = os.environ.get("NO_PROXY", "")

    print(f"OPENAI_API_KEY: {api_key[:10]}..." if api_key else "OPENAI_API_KEY: NOT SET")
    print(f"OPENAI_BASE_URL: {base_url}")
    print(f"DEFAULT_MODEL: {model}")
    print(f"HTTP_PROXY: {http_proxy or 'NOT SET'}")
    print(f"HTTPS_PROXY: {https_proxy or 'NOT SET'}")
    print(f"NO_PROXY: {no_proxy or 'NOT SET'}")

    return bool(api_key and base_url)


async def test_llm():
    """测试 LLM 调用"""
    import httpx

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

    print(f"\n=== LLM API 测试 ===")
    print(f"URL: {base_url}/chat/completions")
    print(f"Model: {model}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "回复 '测试成功'"}],
                    "max_tokens": 50,
                }
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"响应: {content}")
                return True
            else:
                print(f"错误: {response.text[:200]}")
                return False

    except Exception as e:
        print(f"异常: {e}")
        return False


async def test_network():
    """测试网络连通性"""
    import socket
    import httpx

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    host = base_url.replace("https://", "").replace("http://", "").split("/")[0]

    print(f"\n=== 网络连通性测试 ===")

    # DNS 解析
    try:
        ip = socket.gethostbyname(host)
        print(f"DNS 解析: {host} -> {ip}")
    except Exception as e:
        print(f"DNS 解析失败: {e}")
        return False

    # HTTP 连接
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(base_url)
            print(f"HTTPS 连接: {response.status_code}")
            return True
    except Exception as e:
        print(f"HTTPS 连接失败: {e}")
        return False


async def main():
    print("=" * 50)
    print("Docker LLM 验证测试")
    print("=" * 50)

    # 1. 环境变量
    if not test_env_config():
        print("\n❌ 环境变量配置不完整")
        return 1

    # 2. 网络连通性
    if not await test_network():
        print("\n❌ 网络连通性测试失败")
        return 1

    # 3. LLM API
    if not await test_llm():
        print("\n❌ LLM API 测试失败")
        return 1

    print("\n" + "=" * 50)
    print("✅ 所有测试通过!")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
