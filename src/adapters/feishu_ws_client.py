# coding=utf-8
"""
Feishu WebSocket Long Connection Client

飞书官方 SDK 提供了 WebSocket 长连接支持，用于实时接收消息事件。
参考: https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/

注意: 长连接模式只需要客户端能访问外网，不需要公网 IP 或域名。
"""
import os
import threading
from typing import Any, Callable, Dict, Optional

from loguru import logger


class FeishuWebSocketClient:
    """
    飞书 WebSocket 长连接客户端

    使用飞书官方 SDK 的 WebSocket 功能建立长连接，
    实时接收消息事件。

    使用方式:
        client = FeishuWebSocketClient(
            app_id="cli_xxx",
            app_secret="xxx",
            on_message=handle_message,
        )
        client.start()
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        """
        初始化飞书 WebSocket 客户端

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
            on_message: 消息回调函数
            on_connect: 连接成功回调
            on_disconnect: 断开连接回调
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self._running = False
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_client = None

    def _create_event_handler(self):
        """
        创建事件处理器，注册所有需要的事件类型

        飞书 SDK 需要为每个事件类型注册处理器，
        否则会返回 "processor not found" 错误
        """
        import lark_oapi
        from lark_oapi.event.dispatcher_handler import EventDispatcherHandlerBuilder

        builder = EventDispatcherHandler.builder(
            encrypt_key="",  # 如果启用了加密则填写
            verification_token="",  # 如果启用了验证则填写
        )

        # 注册消息接收事件 (im.message.receive_v1)
        builder.register_p2_im_message_receive_v1(
            lambda event: self._handle_p2_event("im.message.receive_v1", event)
        )

        # 注册机器人进入私聊事件 (im.chat.access_event.bot_p2p_chat_entered_v1)
        builder.register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(
            lambda event: self._handle_p2_event("im.chat.access_event.bot_p2p_chat_entered_v1", event)
        )

        # 注册菜单事件 (application.bot.menu_v6)
        builder.register_p2_application_bot_menu_v6(
            lambda event: self._handle_p2_event("application.bot.menu_v6", event)
        )

        return builder.build()

    def _handle_p2_event(self, event_type: str, event: Any):
        """处理 P2 事件"""
        logger.info(f"[Lark WS] 处理 P2 事件: {event_type}")
        if self.on_message:
            try:
                msg_dict = {
                    "type": f"p2.{event_type}",
                    "event": event,
                }
                self.on_message(msg_dict)
            except Exception as e:
                logger.error(f"处理飞书 P2 事件失败: {e}")
        return {"code": 0}

    def start(self):
        """
        启动长连接 (阻塞)
        """
        try:
            import lark_oapi
            from lark_oapi import ws
            from lark_oapi.core.enum import LogLevel

            # 创建事件处理器 - 使用 builder 注册所有需要的事件
            logger.info("[Lark WS] 创建事件处理器并注册事件类型...")
            event_handler = self._create_event_handler()
            logger.info("[Lark WS] 事件处理器创建成功")

            # 创建 WebSocket 客户端
            self._ws_client = ws.Client(
                app_id=self.app_id,
                app_secret=self.app_secret,
                log_level=LogLevel.INFO,
                event_handler=event_handler,
            )

            self._running = True
            logger.info("飞书 WebSocket 客户端已启动")

            if self.on_connect:
                self.on_connect()

            # 启动连接 (会阻塞)
            self._ws_client.start()

        except Exception as e:
            logger.error(f"飞书 WebSocket 客户端启动失败: {e}")
            if self.on_disconnect:
                self.on_disconnect()
            raise

    def start_async(self):
        """
        在后台线程中启动长连接
        """
        self._ws_thread = threading.Thread(target=self.start, daemon=True)
        self._ws_thread.start()
        logger.info("飞书 WebSocket 客户端已在后台线程启动")

    def stop(self):
        """
        停止长连接
        """
        self._running = False
        if self._ws_client:
            try:
                # 断开连接
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._ws_client._disconnect())
            except Exception as e:
                logger.error(f"停止飞书 WebSocket 客户端失败: {e}")
        logger.info("飞书 WebSocket 客户端已停止")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running


def create_feishu_ws_client(
    app_id: str,
    app_secret: str,
    on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> "FeishuWebSocketClient":
    """
    创建飞书 WebSocket 客户端的工厂函数

    Args:
        app_id: 飞书应用 ID
        app_secret: 飞书应用密钥
        on_message: 消息回调函数

    Returns:
        FeishuWebSocketClient 实例
    """
    return FeishuWebSocketClient(
        app_id=app_id,
        app_secret=app_secret,
        on_message=on_message,
    )
