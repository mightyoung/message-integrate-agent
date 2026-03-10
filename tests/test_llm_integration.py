"""
Tests for LLM API integration
"""
import os
import pytest
import asyncio

# 设置测试环境变量（如果存在）
def get_test_env():
    """获取测试用环境变量"""
    return {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
        "DEFAULT_MODEL": os.environ.get("DEFAULT_MODEL", "deepseek-chat"),
    }


class TestLLMIntegration:
    """LLM 集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.env = get_test_env()
        # 确保有 API key
        if not self.env["OPENAI_API_KEY"]:
            pytest.skip("OPENAI_API_KEY not set in environment")

    def test_env_config(self):
        """测试环境变量配置"""
        print(f"\n=== 环境配置 ===")
        print(f"OPENAI_API_KEY: {self.env['OPENAI_API_KEY'][:10]}..." if self.env['OPENAI_API_KEY'] else "OPENAI_API_KEY: NOT SET")
        print(f"OPENAI_BASE_URL: {self.env['OPENAI_BASE_URL']}")
        print(f"DEFAULT_MODEL: {self.env['DEFAULT_MODEL']}")

        assert self.env["OPENAI_API_KEY"], "OPENAI_API_KEY must be set"
        assert self.env["OPENAI_BASE_URL"], "OPENAI_BASE_URL must be set"

    @pytest.mark.asyncio
    async def test_chat_with_llm_direct(self):
        """直接测试 chat_with_llm 函数"""
        # 直接导入避免 mcp 模块依赖问题
        import sys
        import importlib.util

        # 动态加载 llm 模块
        spec = importlib.util.spec_from_file_location("llm", "src/mcp/tools/llm.py")
        llm_module = importlib.util.module_from_spec(spec)

        # 先设置环境变量
        import os
        os.environ["OPENAI_API_KEY"] = self.env["OPENAI_API_KEY"]
        os.environ["OPENAI_BASE_URL"] = self.env["OPENAI_BASE_URL"]

        spec.loader.exec_module(llm_module)
        chat_with_llm = llm_module.chat_with_llm

        response = await chat_with_llm(
            prompt="你好，请回复 '测试成功'",
            model=self.env["DEFAULT_MODEL"],
            max_tokens=100
        )

        print(f"\n=== 直接调用结果 ===")
        print(f"响应: {response}")

        # 检查是否有错误
        assert "Error:" not in response, f"API调用失败: {response}"
        assert response, "响应为空"

    @pytest.mark.asyncio
    async def test_chat_with_llm_via_proxy(self):
        """通过代理测试 chat_with_llm 函数"""
        # 直接导入避免 mcp 模块依赖问题
        import sys
        import importlib.util

        # 动态加载 llm 模块
        spec = importlib.util.spec_from_file_location("llm", "src/mcp/tools/llm.py")
        llm_module = importlib.util.module_from_spec(spec)

        # 先设置环境变量
        import os
        os.environ["OPENAI_API_KEY"] = self.env["OPENAI_API_KEY"]
        os.environ["OPENAI_BASE_URL"] = self.env["OPENAI_BASE_URL"]

        spec.loader.exec_module(llm_module)
        chat_with_llm = llm_module.chat_with_llm
        _get_proxies = llm_module._get_proxies

        # 获取代理配置
        proxies = _get_proxies()
        print(f"\n=== 代理配置 ===")
        print(f"代理: {proxies}")

        response = await chat_with_llm(
            prompt="你好，请回复 '代理测试成功'",
            model=self.env["DEFAULT_MODEL"],
            max_tokens=100
        )

        print(f"\n=== 通过代理调用结果 ===")
        print(f"响应: {response}")

        # 检查是否有错误
        assert "Error:" not in response, f"API调用失败: {response}"
        assert response, "响应为空"

    @pytest.mark.asyncio
    async def test_deepseek_model_list(self):
        """测试 DeepSeek 模型列表 API"""
        import httpx

        api_key = self.env["OPENAI_API_KEY"]
        base_url = self.env["OPENAI_BASE_URL"]

        print(f"\n=== 调用模型列表 API ===")
        print(f"URL: {base_url}/models")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )

                print(f"状态码: {response.status_code}")
                print(f"响应: {response.text[:500]}")

                assert response.status_code == 200, f"请求失败: {response.status_code}"

                data = response.json()
                models = data.get("data", [])

                print(f"\n可用模型:")
                for model in models:
                    print(f"  - {model.get('id')}")

                # 检查 deepseek-chat 是否存在
                model_ids = [m.get("id") for m in models]
                if "deepseek-chat" not in model_ids:
                    print(f"\n警告: deepseek-chat 不在模型列表中")
                    print(f"实际模型列表: {model_ids}")

        except Exception as e:
            pytest.fail(f"模型列表 API 调用失败: {e}")


if __name__ == "__main__":
    # 允许直接运行测试
    pytest.main([__file__, "-v", "-s"])


# ============================================================
# 扩展测试用例 - 排查 DeepSeek API 问题
# ============================================================

class TestDeepSeekDebugging:
    """DeepSeek API 调试测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """设置测试环境"""
        self.env = get_test_env()
        if not self.env["OPENAI_API_KEY"]:
            pytest.skip("OPENAI_API_KEY not set in environment")

    @pytest.mark.asyncio
    async def test_no_proxy(self):
        """测试不使用代理的情况"""
        import importlib.util

        # 临时清除代理环境变量
        old_http = os.environ.get("HTTP_PROXY")
        old_https = os.environ.get("HTTPS_PROXY")
        old_no_proxy = os.environ.get("NO_PROXY")

        try:
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)
            os.environ.pop("http_proxy", None)
            os.environ.pop("https_proxy", None)
            os.environ["OPENAI_API_KEY"] = self.env["OPENAI_API_KEY"]
            os.environ["OPENAI_BASE_URL"] = self.env["OPENAI_BASE_URL"]

            spec = importlib.util.spec_from_file_location("llm", "src/mcp/tools/llm.py")
            llm_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(llm_module)

            print(f"\n=== 无代理测试 ===")
            print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY', 'NOT SET')}")
            print(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY', 'NOT SET')}")

            response = await llm_module.chat_with_llm(
                prompt="回复 '无代理测试'",
                model=self.env["DEFAULT_MODEL"],
                max_tokens=50
            )

            print(f"响应: {response}")
            assert "Error:" not in response

        finally:
            # 恢复环境变量
            if old_http:
                os.environ["HTTP_PROXY"] = old_http
            if old_https:
                os.environ["HTTPS_PROXY"] = old_https
            if old_no_proxy:
                os.environ["NO_PROXY"] = old_no_proxy

    @pytest.mark.asyncio
    async def test_httpx_proxy_param(self):
        """测试 httpx 0.27+ 的 proxy 参数"""
        import httpx
        import importlib.util

        os.environ["OPENAI_API_KEY"] = self.env["OPENAI_API_KEY"]
        os.environ["OPENAI_BASE_URL"] = self.env["OPENAI_BASE_URL"]

        spec = importlib.util.spec_from_file_location("llm", "src/mcp/tools/llm.py")
        llm_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(llm_module)

        proxies = llm_module._get_proxies()
        print(f"\n=== httpx 代理参数测试 ===")
        print(f"httpx 版本: {httpx.__version__}")
        print(f"代理配置: {proxies}")

        # 测试直接使用 httpx
        api_key = self.env["OPENAI_API_KEY"]
        base_url = self.env["OPENAI_BASE_URL"]

        client_kwargs = {"timeout": 30.0}
        if proxies:
            if tuple(map(int, httpx.__version__.split('.')[:2])) >= (0, 27):
                client_kwargs["proxy"] = list(proxies.values())[0]
            else:
                client_kwargs["proxies"] = proxies

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.env["DEFAULT_MODEL"],
                    "messages": [{"role": "user", "content": "回复 'httpx测试'"}],
                    "max_tokens": 50,
                }
            )

            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:200]}")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_different_models(self):
        """测试不同的模型名称"""
        import importlib.util

        os.environ["OPENAI_API_KEY"] = self.env["OPENAI_API_KEY"]
        os.environ["OPENAI_BASE_URL"] = self.env["OPENAI_BASE_URL"]

        spec = importlib.util.spec_from_file_location("llm", "src/mcp/tools/llm.py")
        llm_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(llm_module)

        # 测试可用模型
        models_to_test = ["deepseek-chat", "deepseek-reasoner", "gpt-4", "gpt-3.5-turbo"]

        print(f"\n=== 模型名称测试 ===")

        for model in models_to_test:
            print(f"\n测试模型: {model}")
            response = await llm_module.chat_with_llm(
                prompt="回复模型名称",
                model=model,
                max_tokens=20
            )

            if "Error:" in response:
                print(f"  ❌ 失败: {response}")
            else:
                print(f"  ✅ 成功: {response[:50]}")

    @pytest.mark.asyncio
    async def test_network_connectivity(self):
        """测试网络连通性"""
        import httpx

        base_url = self.env["OPENAI_BASE_URL"]

        print(f"\n=== 网络连通性测试 ===")
        print(f"目标: {base_url}")

        # 测试 DNS 解析
        try:
            import socket
            host = base_url.replace("https://", "").replace("http://", "").split("/")[0]
            ip = socket.gethostbyname(host)
            print(f"DNS 解析: {host} -> {ip}")
        except Exception as e:
            print(f"DNS 解析失败: {e}")

        # 测试 HTTPS 连接
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(base_url)
                print(f"HTTPS 连接: {response.status_code}")
        except Exception as e:
            print(f"HTTPS 连接失败: {e}")

    @pytest.mark.asyncio
    async def test_docker_env_simulation(self):
        """模拟 Docker 环境配置测试"""
        import importlib.util

        # 模拟 Docker 环境变量
        docker_env = {
            "HTTP_PROXY": "http://mihomo:7890",
            "HTTPS_PROXY": "http://mihomo:7890",
            "NO_PROXY": "localhost,127.0.0.1,api.feishu.cn,open.feishu.cn,192.168.0.0/16,api.deepseek.com,api.openai.com",
            "OPENAI_API_KEY": self.env["OPENAI_API_KEY"],
            "OPENAI_BASE_URL": self.env["OPENAI_BASE_URL"],
        }

        print(f"\n=== Docker 环境模拟 ===")
        print(f"HTTP_PROXY: {docker_env['HTTP_PROXY']}")
        print(f"HTTPS_PROXY: {docker_env['HTTPS_PROXY']}")
        print(f"NO_PROXY: {docker_env['NO_PROXY']}")

        # 保存旧环境变量
        old_env = {k: os.environ.get(k) for k in docker_env}

        try:
            # 设置新环境变量
            for k, v in docker_env.items():
                os.environ[k] = v

            spec = importlib.util.spec_from_file_location("llm", "src/mcp/tools/llm.py")
            llm_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(llm_module)

            # 检查代理配置
            proxies = llm_module._get_proxies()
            print(f"获取的代理: {proxies}")

            # 测试调用
            response = await llm_module.chat_with_llm(
                prompt="回复 'Docker模拟测试'",
                model=self.env["DEFAULT_MODEL"],
                max_tokens=50
            )

            print(f"响应: {response}")

            if "Error:" in response:
                print("❌ Docker 环境模拟测试失败")
            else:
                print("✅ Docker 环境模拟测试成功")

        finally:
            # 恢复旧环境变量
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    @pytest.mark.asyncio
    async def test_direct_url_variations(self):
        """测试不同的 URL 格式"""
        import httpx

        api_key = self.env["OPENAI_API_KEY"]

        # 不同的 URL 格式
        url_variations = [
            "https://api.deepseek.com/v1/chat/completions",
            "https://api.deepseek.com/v1/chat/completions/",
        ]

        print(f"\n=== URL 格式测试 ===")

        for url in url_variations:
            print(f"\n测试 URL: {url}")
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [{"role": "user", "content": "hi"}],
                            "max_tokens": 10,
                        }
                    )

                    print(f"状态码: {response.status_code}")
                    if response.status_code != 200:
                        print(f"错误: {response.text[:200]}")

            except Exception as e:
                print(f"异常: {e}")
