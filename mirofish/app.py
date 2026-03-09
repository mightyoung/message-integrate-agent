"""
MiroFish - 预测分析服务
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

logger.info(f"MiroFish started - Model: {DEFAULT_MODEL}")


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "mirofish"})


@app.route("/api/simulate", methods=["POST"])
def simulate():
    """预测仿真 API"""
    data = request.get_json() or {}
    scenario = data.get("scenario", "")
    steps = data.get("steps", 10)

    logger.info(f"Simulate request: scenario={scenario}, steps={steps}")

    # TODO: 实现实际的预测仿真逻辑
    return jsonify({
        "status": "success",
        "scenario": scenario,
        "prediction": f"MiroFish 预测结果: {scenario}",
        "confidence": 0.85,
        "steps": steps,
        "trends": [
            {"step": 1, "value": "增长"},
            {"step": 2, "value": "稳定"},
            {"step": 3, "value": "波动"}
        ]
    })


@app.route("/api/prediction/<task_id>", methods=["GET"])
def get_prediction(task_id):
    """获取预测结果"""
    logger.info(f"Get prediction: task_id={task_id}")

    # TODO: 实现实际的预测结果获取
    return jsonify({
        "status": "success",
        "task_id": task_id,
        "result": "预测进行中...",
        "progress": 0.5
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
