# coding=utf-8
"""
学术论文功能测试脚本
测试 pipeline 对学术论文的标题和概要生成
"""
import asyncio
import os
import sys

# 设置环境变量
env_file = ".env.prod"
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

from src.intelligence.translator import get_translator


async def test_academic_prompts():
    """测试学术论文标题和概要生成"""
    print("=" * 60)
    print("测试学术论文标题和概要生成")
    print("=" * 60)

    # 示例学术论文内容（来自 arXiv）
    sample_papers = [
        {
            "title": "Attention Is All You Need",
            "abstract": """We propose a new network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including the Ensemble, by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.0 after training for 3.5 days on eight GPUs."""
        },
        {
            "title": "GPT-4 Technical Report",
            "abstract": """We report the development of GPT-4, a large-scale, multimodal model which can accept image and text inputs and produce text outputs. While in many cases - especially when the task is constrained to parsing a short text - GPT-4's outputs are similar to human-level performance, GPT-4 can be flawed in more complex situations. To measure GPT-4's capabilities relative to prior models, we tested it on a diverse set of exams originally designed for humans. On the majority of these exams, GPT-4 achieves a score in the top 10% of test takers."""
        },
        {
            "title": "Deep Residual Learning for Image Recognition",
            "abstract": """We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions. We provide comprehensive empirical evidence showing that these residual networks are easier to optimize, and can gain accuracy from considerably increased depth."""
        }
    ]

    translator = get_translator()

    for i, paper in enumerate(sample_papers):
        print(f"\n--- 论文 {i+1}: {paper['title']} ---")

        # 生成标题
        title = await translator.generate_academic_title(paper['abstract'], max_length=30)
        print(f"标题: {title}")

        # 生成概要
        summary = await translator.generate_academic_summary(paper['abstract'], max_length=150)
        print(f"概要: {summary}")


async def test_news_prompts():
    """测试新闻标题和概要生成"""
    print("\n" + "=" * 60)
    print("测试新闻标题和概要生成")
    print("=" * 60)

    sample_news = [
        {
            "title": "Apple releases new MacBook Pro with M4 chip",
            "content": "Apple today announced the new MacBook Pro powered by the M4 chip, featuring improved performance and battery life. The new model starts at $1,999 and will be available next month. The M4 chip offers 20% faster CPU performance and 30% faster GPU performance compared to M3."
        },
        {
            "title": "Tesla recalls 1 million vehicles due to software bug",
            "content": "Tesla is recalling approximately 1 million vehicles worldwide due to a software bug that could affect rearview camera functionality. The recall affects Model S, Model X, Model Y, and Model 3 vehicles produced between 2020 and 2023. Tesla will deploy an over-the-air software update to fix the issue."
        }
    ]

    translator = get_translator()

    for i, news in enumerate(sample_news):
        print(f"\n--- 新闻 {i+1}: {news['title']} ---")

        # 生成标题
        title = await translator.generate_news_title(news['content'], max_length=30)
        print(f"标题: {title}")

        # 生成概要
        summary = await translator.generate_news_summary(news['content'], max_length=150)
        print(f"概要: {summary}")


async def main():
    """主函数"""
    await test_academic_prompts()
    await test_news_prompts()
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
