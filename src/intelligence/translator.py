# coding=utf-8
"""
Translation utilities using LLM for translating intelligence content
"""
import asyncio
import os
from typing import Optional, List, Dict, Any

import httpx
from loguru import logger


class Translator:
    """Translation utility using LLM - 顶级新闻编辑思维"""

    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        self._translation_cache: Dict[str, str] = {}

    def _get_proxies(self) -> dict:
        """Get proxy configuration from environment."""
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

        proxies = {}
        if http_proxy:
            proxies["http://"] = http_proxy
        if https_proxy:
            proxies["https://"] = https_proxy

        return proxies if proxies else {}

    def _get_proxy_url(self) -> str:
        """Get proxy URL for httpx."""
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        return https_proxy or http_proxy or ""

    async def generate_news_title(
        self,
        text: str,
        max_length: int = 30,
    ) -> str:
        """生成新闻标题（顶级新闻编辑风格）

        原则：
        - 简洁有力，15-30字
        - 核心事件（What）+ 关键人物/机构（Who）
        - 吸引眼球，引发好奇
        - 不包含背景信息

        Args:
            text: 原始新闻内容
            max_length: 最大长度

        Returns:
            中文新闻标题
        """
        if not text or not text.strip():
            return text

        cache_key = f"title_{text[:50]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            if not api_key:
                return text[:max_length]

            # 顶级新闻标题生成提示词
            prompt = f"""你是一位顶级新闻标题编辑（来自路透社、华尔街日报）。

请根据以下新闻内容，生成一个吸引眼球的新闻标题。

要求：
1. 简洁有力，15-{max_length}个中文字符
2. 包含核心事件（What）和关键人物/机构（Who）
3. 去掉所有修饰词、背景信息
4. 直接陈述事实，不要评论
5. 只输出标题，不要任何解释

新闻内容：
{text[:300]}"""

            proxy_url = self._get_proxy_url()
            async with httpx.AsyncClient(proxy=proxy_url if proxy_url else None, timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.5,
                        "max_tokens": max_length,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    title = result["choices"][0]["message"]["content"].strip()
                    self._translation_cache[cache_key] = title
                    return title
                else:
                    return text[:max_length]

        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            return text[:max_length]

    async def generate_news_summary(
        self,
        text: str,
        max_length: int = 150,
    ) -> str:
        """生成新闻概要（顶级新闻编辑风格）

        原则：
        - 50-150字
        - 包含5W1H：Who, What, When, Where, Why, How
        - 交代背景和影响
        - 是标题的补充，不是重复

        Args:
            text: 原始新闻内容
            max_length: 最大长度

        Returns:
            中文新闻概要
        """
        if not text or not text.strip():
            return text

        cache_key = f"summary_{text[:50]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            if not api_key:
                return text[:max_length]

            # 顶级新闻概要生成提示词
            prompt = f"""你是一位顶级新闻编辑（来自路透社、华尔街日报）。

请根据以下新闻内容，生成一个新闻概要。

要求：
1. 50-{max_length}个中文字符
2. 必须包含标题中没有的信息：时间、地点、原因、背景、影响
3. 使用倒金字塔结构：最重要的信息放最前面
4. 是标题的补充，不是重复标题内容
5. 只输出概要，不要任何解释

新闻内容：
{text[:500]}"""

            proxy_url = self._get_proxy_url()
            async with httpx.AsyncClient(proxy=proxy_url if proxy_url else None, timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": max_length,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result["choices"][0]["message"]["content"].strip()
                    self._translation_cache[cache_key] = summary
                    return summary
                else:
                    return text[:max_length]

        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return text[:max_length]

    def _get_proxies(self) -> dict:
        """Get proxy configuration from environment."""
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

        proxies = {}
        if http_proxy:
            proxies["http://"] = http_proxy
        if https_proxy:
            proxies["https://"] = https_proxy

        return proxies if proxies else {}

    async def translate_to_chinese(
        self,
        text: str,
        max_length: int = 200,
    ) -> str:
        """Translate text to Chinese

        Args:
            text: English text to translate
            max_length: Maximum length of translated text

        Returns:
            Chinese translation
        """
        if not text or not text.strip():
            return text

        # Check cache
        cache_key = text[:100]  # Use first 100 chars as cache key
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            # Use DeepSeek API directly
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            if not api_key:
                logger.warning("No API key found, returning original text")
                return text

            prompt = f"""你是一位顶级新闻编辑（来自路透社、华尔街日报或彭博社）。请按照新闻写作的"倒金字塔"原则，将以下英文新闻翻译为中文新闻摘要。

"倒金字塔"原则要求：
1. 首句必须是新闻的核心要点（最重要的事实）
2. 包含关键要素：谁(who)、什么(what)、何时(when)、何地(where)、为何(why)、如何(how)
3. 交代新闻来源和背景
4. 如有商业/科技影响，请一并说明
5. 信息要完整全面，不需要精简

请直接输出中文新闻摘要，不要添加任何解释或开场白：

原文: {text[:500]}"""

            proxy_url = self._get_proxy_url()
            async with httpx.AsyncClient(proxy=proxy_url if proxy_url else None, timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": max_length,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    translation = result["choices"][0]["message"]["content"].strip()
                    # Cache the result
                    self._translation_cache[cache_key] = translation
                    return translation
                else:
                    logger.warning(f"Translation API error: {response.status_code}")
                    return text

        except Exception as e:
            logger.warning(f"Translation failed: {e}, returning original text")
            return text

    async def translate_batch(
        self,
        texts: List[str],
        max_length: int = 200,
    ) -> List[str]:
        """Translate multiple texts to Chinese

        Args:
            texts: List of English texts
            max_length: Maximum length per translation

        Returns:
            List of Chinese translations
        """
        tasks = [self.translate_to_chinese(text, max_length) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        translated = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Translation error for text {i}: {result}")
                translated.append(texts[i])
            else:
                translated.append(result)

        return translated

    # ==================== 学术论文标题和概要生成 ====================
    # 顶级科学家思维：精准、简洁、包含核心发现

    async def generate_academic_title(
        self,
        text: str,
        max_length: int = 30,
    ) -> str:
        """生成学术论文标题（顶级科学家风格）

        原则：
        - 简洁精准，15-30字
        - 包含：研究问题/方法 + 核心发现
        - 使用领域术语
        - 不包含背景、动机描述

        Args:
            text: 论文内容
            max_length: 最大长度

        Returns:
            中文论文标题
        """
        if not text or not text.strip():
            return text

        cache_key = f"academic_title_{text[:50]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            if not api_key:
                return text[:max_length]

            # 顶级科学家风格论文标题提示词
            prompt = f"""你是一位顶级科学家（来自MIT、斯坦福、Google DeepMind等顶尖机构）。

请根据以下学术论文内容，生成一个精准的论文标题。

要求：
1. 简洁精准，15-{max_length}个中文字符
2. 格式："[领域]研究问题：核心发现" 或 "方法/模型 + 关键结果"
3. 使用领域专业术语
4. 只描述事实发现，不包含研究动机或背景
5. 只输出标题，不要任何解释

论文内容：
{text[:400]}"""

            proxy_url = self._get_proxy_url()
            async with httpx.AsyncClient(proxy=proxy_url if proxy_url else None, timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": max_length,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    title = result["choices"][0]["message"]["content"].strip()
                    self._translation_cache[cache_key] = title
                    return title
                else:
                    return text[:max_length]

        except Exception as e:
            logger.warning(f"Academic title generation failed: {e}")
            return text[:max_length]

    async def generate_academic_summary(
        self,
        text: str,
        max_length: int = 150,
    ) -> str:
        """生成学术论文概要（顶级科学家风格）

        原则：
        - 50-150字
        - 包含：研究问题、方法、关键发现、意义
        - 使用专业术语
        - 是标题的补充，不是重复

        Args:
            text: 论文内容
            max_length: 最大长度

        Returns:
            中文论文概要
        """
        if not text or not text.strip():
            return text

        cache_key = f"academic_summary_{text[:50]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            if not api_key:
                return text[:max_length]

            # 顶级科学家风格论文概要提示词
            prompt = f"""你是一位顶级科学家（来自MIT、斯坦福、Google DeepMind等顶尖机构）。

请根据以下学术论文内容，生成一个论文概要。

要求：
1. 50-{max_length}个中文字符
2. 必须包含：研究问题（Gap）、使用的方法、关键发现、学术/应用意义
3. 使用专业术语和领域词汇
4. 是标题的补充，包含标题中没有的信息
5. 只输出概要，不要任何解释

论文内容：
{text[:600]}"""

            proxy_url = self._get_proxy_url()
            async with httpx.AsyncClient(proxy=proxy_url if proxy_url else None, timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": max_length,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result["choices"][0]["message"]["content"].strip()
                    self._translation_cache[cache_key] = summary
                    return summary
                else:
                    return text[:max_length]

        except Exception as e:
            logger.warning(f"Academic summary generation failed: {e}")
            return text[:max_length]

    # ==================== GitHub 仓库标题和概要生成 ====================
    # 顶级工程师/开源贡献者思维：实用、创新、可扩展

    async def generate_github_title(
        self,
        text: str,
        max_length: int = 30,
    ) -> str:
        """生成 GitHub 仓库标题（顶级开源工程师风格）

        原则：
        - 简洁有力，15-30字
        - 包含：项目核心功能 + 技术标签
        - 使用技术术语
        - 突出创新点或实用性

        Args:
            text: 仓库 README 内容
            max_length: 最大长度

        Returns:
            中文仓库标题
        """
        if not text or not text.strip():
            return text

        cache_key = f"github_title_{text[:50]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            if not api_key:
                return text[:max_length]

            # 顶级开源工程师风格仓库标题提示词
            prompt = f"""你是一位顶级开源工程师（来自 Google、Meta、DeepMind 等顶尖科技公司，拥有大量开源项目经验）。

请根据以下 GitHub 仓库的 README 内容，生成一个精准的仓库标题。

要求：
1. 简洁有力，15-{max_length}个中文字符
2. 格式："[技术领域]核心功能描述" 或 "项目名称：核心功能"
3. 使用领域专业术语（LLM、CV、RL、MoE、Transformer 等）
4. 突出项目创新点或实用价值
5. 只输出标题，不要任何解释

README 内容：
{text[:500]}"""

            proxy_url = self._get_proxy_url()
            async with httpx.AsyncClient(proxy=proxy_url if proxy_url else None, timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": max_length,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    title = result["choices"][0]["message"]["content"].strip()
                    self._translation_cache[cache_key] = title
                    return title
                else:
                    return text[:max_length]

        except Exception as e:
            logger.warning(f"GitHub title generation failed: {e}")
            return text[:max_length]

    async def generate_github_summary(
        self,
        text: str,
        max_length: int = 150,
    ) -> str:
        """生成 GitHub 仓库概要（顶级开源工程师风格）

        原则：
        - 50-150字
        - 包含：解决的问题、技术方案、适用场景、Stars 意义
        - 使用技术术语
        - 是标题的补充，不是重复

        Args:
            text: 仓库 README 内容
            max_length: 最大长度

        Returns:
            中文仓库概要
        """
        if not text or not text.strip():
            return text

        cache_key = f"github_summary_{text[:50]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        try:
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

            if not api_key:
                return text[:max_length]

            # 顶级开源工程师风格仓库概要提示词
            prompt = f"""你是一位顶级开源工程师（来自 Google、Meta、DeepMind 等顶尖科技公司，拥有大量开源项目经验）。

请根据以下 GitHub 仓库的 README 内容，生成一个仓库概要。

要求：
1. 50-{max_length}个中文字符
2. 必须包含：解决的问题（Why）、使用的技术方案（How）、适用场景（Where）
3. 使用专业术语和领域词汇
4. 是标题的补充，包含标题中没有的信息
5. 只输出概要，不要任何解释

README 内容：
{text[:800]}"""

            proxy_url = self._get_proxy_url()
            async with httpx.AsyncClient(proxy=proxy_url if proxy_url else None, timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": max_length,
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    summary = result["choices"][0]["message"]["content"].strip()
                    self._translation_cache[cache_key] = summary
                    return summary
                else:
                    return text[:max_length]

        except Exception as e:
            logger.warning(f"GitHub summary generation failed: {e}")
            return text[:max_length]


# Global translator instance
_translator: Optional[Translator] = None


def get_translator(model: str = "deepseek-chat") -> Translator:
    """Get or create translator instance"""
    global _translator
    if _translator is None:
        _translator = Translator(model=model)
    return _translator
