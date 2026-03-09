"""
BettaFish - 舆情分析服务
占位符版本 - 需要根据实际项目完善
"""

import os
from flask import Flask, request, jsonify
from loguru import logger

app = Flask(__name__)

# 配置
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

logger.info(f"BettaFish started - Model: {DEFAULT_MODEL}")


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "bettafish"})


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """舆情分析 API"""
    data = request.get_json() or {}
    topic = data.get("topic", "")
    depth = data.get("depth", "medium")

    logger.info(f"Analyze request: topic={topic}, depth={depth}")

    # TODO: 实现实际的舆情分析逻辑
    return jsonify({
        "status": "success",
        "topic": topic,
        "analysis": f"BettaFish 分析结果: {topic}",
        "sentiment": "positive",
        "keywords": ["AI", "技术", "发展"],
        "depth": depth
    })


@app.route("/api/search", methods=["GET"])
def search():
    """搜索 API"""
    query = request.args.get("q", "")
    logger.info(f"Search request: query={query}")

    # TODO: 实现实际的搜索逻辑
    return jsonify({
        "status": "success",
        "query": query,
        "results": []
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
