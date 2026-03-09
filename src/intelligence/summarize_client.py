# coding=utf-8
"""
Summarize CLI Wrapper - URL/文件/YouTube 摘要工具

集成 summarize CLI (https://summarize.sh)

功能:
- 总结 URLs
- 总结本地文件 (PDF, 图片, 音频)
- 总结 YouTube 视频
- 支持 Firecrawl (网站抓取)
- 支持 Apify (YouTube 抓取)

支持的 LLM 提供商:
- OpenAI
- Anthropic
- xAI
- Google Gemini
"""
import os
import subprocess
import json
import asyncio
from typing import Optional, Dict, Any, Literal
from pathlib import Path

from loguru import logger


SummarizeLength = Literal["short", "medium", "long", "xl", "xxl"]
FirecrawlMode = Literal["auto", "off", "always"]
YouTubeMode = Literal["auto", "off"]


class SummarizeClient:
    """Summarize CLI 客户端封装"""

    def __init__(
        self,
        model: str = "google/gemini-2.0-flash-exp",
        api_key: str = None,
        config_path: str = None,
        firecrawl_api_key: str = None,
        apify_api_token: str = None,
    ):
        """初始化

        Args:
            model: 使用的 LLM 模型
            api_key: API 密钥 (从环境变量读取或使用默认)
            config_path: 配置文件路径 (~/.summarize/config.json)
            firecrawl_api_key: Firecrawl API 密钥 (用于抓取被屏蔽的网站)
            apify_api_token: Apify API token (用于 YouTube 抓取 fallback)
        """
        self.model = model
        self.api_key = api_key
        self.firecrawl_api_key = firecrawl_api_key
        self.apify_api_token = apify_api_token
        self.config_path = config_path or os.path.expanduser("~/.summarize/config.json")

        # 加载配置文件
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
                    # 使用配置中的默认值
                    if not self.model and config.get("model"):
                        self.model = config["model"]
                    logger.info(f"Loaded config from {self.config_path}: model={self.model}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")

    def _get_api_key(self, provider: str) -> Optional[str]:
        """获取 API 密钥

        Args:
            provider: 提供商名称 (openai/anthropic/xai/google)

        Returns:
            API 密钥或 None
        """
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "xai": "XAI_API_KEY",
            "google": "GEMINI_API_KEY",
        }

        # 如果传入了 api_key，直接使用
        if self.api_key:
            return self.api_key

        # 否则从环境变量读取
        return os.environ.get(env_vars.get(provider, ""))

    def _check_installed(self) -> bool:
        """检查 summarize CLI 是否已安装"""
        try:
            result = subprocess.run(
                ["which", "summarize"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def summarize_url(
        self,
        url: str,
        length: SummarizeLength = "medium",
        extract_only: bool = False,
        firecrawl: FirecrawlMode = "auto",
        max_output_tokens: int = None,
    ) -> str:
        """总结 URL

        Args:
            url: 目标 URL
            length: 总结长度
            extract_only: 仅提取内容，不总结
            firecrawl: Firecrawl 模式 (auto/off/always)
            max_output_tokens: 最大输出 token 数

        Returns:
            总结文本
        """
        cmd = ["summarize", url]

        if self.model:
            cmd.extend(["--model", self.model])

        if length:
            cmd.extend(["--length", length])

        if extract_only:
            cmd.append("--extract-only")

        if firecrawl and firecrawl != "auto":
            cmd.extend(["--firecrawl", firecrawl])

        if max_output_tokens:
            cmd.extend(["--max-output-tokens", str(max_output_tokens)])

        return await self._run_command(cmd)

    async def summarize_file(
        self,
        file_path: str,
        length: SummarizeLength = "medium",
        max_output_tokens: int = None,
    ) -> str:
        """总结本地文件

        Args:
            file_path: 文件路径 (支持 PDF, 图片, 音频)
            length: 总结长度
            max_output_tokens: 最大输出 token 数

        Returns:
            总结文本
        """
        # 检查文件是否存在
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        cmd = ["summarize", file_path]

        if self.model:
            cmd.extend(["--model", self.model])

        if length:
            cmd.extend(["--length", length])

        if max_output_tokens:
            cmd.extend(["--max-output-tokens", str(max_output_tokens)])

        return await self._run_command(cmd)

    async def summarize_youtube(
        self,
        url: str,
        length: SummarizeLength = "medium",
        use_apify: bool = True,
        max_output_tokens: int = None,
    ) -> str:
        """总结 YouTube 视频

        Args:
            url: YouTube URL
            length: 总结长度
            use_apify: 是否使用 Apify fallback
            max_output_tokens: 最大输出 token 数

        Returns:
            总结文本
        """
        cmd = ["summarize", url, "--youtube", "auto" if use_apify else "off"]

        if self.model:
            cmd.extend(["--model", self.model])

        if length:
            cmd.extend(["--length", length])

        if max_output_tokens:
            cmd.extend(["--max-output-tokens", str(max_output_tokens)])

        return await self._run_command(cmd)

    async def summarize_json(
        self,
        url: str = None,
        file_path: str = None,
        youtube_url: str = None,
        length: SummarizeLength = "medium",
        max_output_tokens: int = None,
    ) -> Dict[str, Any]:
        """以 JSON 格式返回总结

        Args:
            url: URL (可选)
            file_path: 文件路径 (可选)
            youtube_url: YouTube URL (可选)
            length: 总结长度
            max_output_tokens: 最大输出 token 数

        Returns:
            JSON 格式的总结结果
        """
        cmd = ["summarize", "--json"]

        if url:
            cmd.append(url)
        elif file_path:
            cmd.append(file_path)
        elif youtube_url:
            cmd.extend([youtube_url, "--youtube", "auto"])
        else:
            raise ValueError("Must provide url, file_path, or youtube_url")

        if self.model:
            cmd.extend(["--model", self.model])

        if length:
            cmd.extend(["--length", length])

        if max_output_tokens:
            cmd.extend(["--max-output-tokens", str(max_output_tokens)])

        result = await self._run_command(cmd)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON: {result}")
            return {"raw": result}

    def _run_command(self, cmd: list) -> str:
        """运行 summarize 命令

        Args:
            cmd: 命令列表

        Returns:
            命令输出
        """
        # 检查是否安装
        if not self._check_installed():
            raise RuntimeError(
                "summarize CLI not installed. Install with:\n"
                "brew install steipete/tap/summarize"
            )

        # 设置环境变量
        env = os.environ.copy()
        if self.api_key:
            # 根据模型提供商设置 API key
            if "openai" in self.model:
                env["OPENAI_API_KEY"] = self.api_key
            elif "anthropic" in self.model:
                env["ANTHROPIC_API_KEY"] = self.api_key
            elif "xai" in self.model:
                env["XAI_API_KEY"] = self.api_key
            elif "gemini" in self.model or "google" in self.model:
                env["GEMINI_API_KEY"] = self.api_key

        # Firecrawl API key
        if self.firecrawl_api_key:
            env["FIRECRAWL_API_KEY"] = self.firecrawl_api_key

        # Apify API token
        if self.apify_api_token:
            env["APIFY_API_TOKEN"] = self.apify_api_token

        try:
            result = asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            async def run():
                proc = await result
                stdout, stderr = await proc.communicate()
                return proc.returncode, stdout, stderr

            returncode, stdout, stderr = asyncio.run(run())

            if returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"summarize failed: {error_msg}")
                raise RuntimeError(f"summarize failed: {error_msg}")

            return stdout.decode().strip()

        except FileNotFoundError:
            raise RuntimeError("summarize CLI not found. Please install it first.")
        except Exception as e:
            logger.error(f"Error running summarize: {e}")
            raise

    def get_installation_instructions(self) -> str:
        """获取安装说明

        Returns:
            安装说明文本
        """
        return """# 安装 summarize CLI

## macOS (Homebrew)
```bash
brew install steipete/tap/summarize
```

## 验证安装
```bash
summarize --version
```

## 配置 API Keys

根据使用的模型设置环境变量:

### Google Gemini (默认)
```bash
export GEMINI_API_KEY="your-api-key"
```

### OpenAI
```bash
export OPENAI_API_KEY="your-api-key"
```

### Anthropic
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### xAI
```bash
export XAI_API_KEY="your-api-key"
```

## 可选服务

### Firecrawl (用于抓取被屏蔽的网站)
```bash
export FIRECRAWL_API_KEY="your-api-key"
```

### Apify (用于 YouTube 抓取 fallback)
```bash
export APIFY_API_TOKEN="your-api-token"
```

## 配置文件 (可选)

创建 ~/.summarize/config.json:
```json
{
    "model": "google/gemini-2.0-flash-exp"
}
```
"""


# ==================== 便捷函数 ====================

def create_summarize_client(
    model: str = "google/gemini-2.0-flash-exp",
    api_key: str = None,
    firecrawl_api_key: str = None,
    apify_api_token: str = None,
) -> SummarizeClient:
    """创建 SummarizeClient 的便捷函数

    Args:
        model: LLM 模型
        api_key: API 密钥
        firecrawl_api_key: Firecrawl API 密钥
        apify_api_token: Apify API token

    Returns:
        SummarizeClient 实例
    """
    return SummarizeClient(
        model=model,
        api_key=api_key,
        firecrawl_api_key=firecrawl_api_key,
        apify_api_token=apify_api_token,
    )
