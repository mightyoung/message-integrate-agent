# coding=utf-8
"""
Simple Feishu Webhook Server for Testing

This is a minimal server that exposes a webhook endpoint for Feishu to call.
It can be used to verify the webhook configuration in Feishu developer console.
"""
import os
import asyncio
from fastapi import FastAPI, Request
from loguru import logger
import uvicorn

# Configure logging
logger.add("logs/webhook.log", rotation="10 MB", level="INFO")

app = FastAPI(title="Feishu Webhook Server")


@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"status": "ok", "message": "Feishu Webhook Server is running"}


@app.get("/webhook/feishu")
async def verify_webhook_get(request: Request):
    """Handle webhook verification (GET request)"""
    params = dict(request.query_params)
    logger.info(f"Verification request: {params}")

    # Return challenge if present
    challenge = params.get("challenge")
    if challenge:
        return {"challenge": challenge}

    return {"status": "verification_ok"}


@app.post("/webhook/feishu")
async def handle_webhook(request: Request):
    """Handle incoming Feishu webhook events"""
    try:
        body = await request.json()
        logger.info(f"Received webhook event: {body.get('type')}")

        event_type = body.get("type")

        # Handle menu events
        if event_type == "im.menu":
            menu_event = body.get("event", {}).get("menu_event", {})
            menu_event_id = menu_event.get("menu_event_id", "")
            user_id = menu_event.get("user_id", "")

            logger.info(f"Menu clicked: {menu_event_id} by user {user_id}")

            return {
                "status": "ok",
                "message": f"Menu event received: {menu_event_id}"
            }

        # Handle message events
        if event_type == "callback":
            logger.info(f"Callback event received")
            return {"status": "ok", "message": "Callback received"}

        # Handle challenge for verification
        challenge = body.get("challenge")
        if challenge:
            return {"challenge": challenge}

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting webhook server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
