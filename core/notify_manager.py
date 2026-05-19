"""
core/notify_manager.py
======================
NotifyManager — gửi thông báo kết quả upload lên Telegram.

Thiết kế:
  - Non-blocking: dùng asyncio + python-telegram-bot v21+.
  - Fallback graceful: nếu Token/Admin ID chưa cấu hình, chỉ log ra console.
  - Không raise exception lên caller — thất bại thông báo không được làm crash worker.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Đọc credentials từ .env
_TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "")
_TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")


class NotifyManager:
    """
    NotifyManager — Singleton-style class gửi notification qua Telegram Bot.

    Sử dụng:
        from core.notify_manager import NotifyManager
        await NotifyManager.notify_success("Kênh Game 1", "Tên video", "https://youtu.be/xxx")
        await NotifyManager.notify_failure("Kênh Game 1", "Tên video", "Lỗi: quota exceeded")
    """

    # ──────────────────────────────────────────
    # INTERNAL — Gửi tin nhắn thô
    # ──────────────────────────────────────────

    @staticmethod
    async def _send(message: str):
        """
        Gửi text message đến Admin ID.
        Nếu token hoặc admin_id chưa cấu hình → chỉ print ra console.
        """
        if not _TELEGRAM_TOKEN or not _TELEGRAM_ADMIN_ID:
            print(f"[Telegram] (Chưa cấu hình) {message}")
            return

        try:
            # Import lazy để tránh lỗi khi thư viện chưa cài
            from telegram import Bot
            bot = Bot(token=_TELEGRAM_TOKEN)
            async with bot:
                await bot.send_message(
                    chat_id=_TELEGRAM_ADMIN_ID,
                    text=message,
                    parse_mode="HTML",
                )
            print(f"[Telegram] Đã gửi notification.")
        except Exception as e:
            # Không re-raise: lỗi Telegram không được làm hỏng logic chính
            print(f"[Telegram] Lỗi gửi tin: {e}")

    # ──────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────

    @classmethod
    async def notify_success(cls, channel_name: str, video_title: str, youtube_url: str):
        """
        Gửi thông báo upload THÀNH CÔNG.

        Args:
            channel_name : Tên kênh (Profile.name)
            video_title  : Tiêu đề video đã upload
            youtube_url  : Link video YouTube
        """
        message = (
            "✅ <b>Upload Thành Công!</b>\n\n"
            f"📺 <b>Kênh:</b> {channel_name}\n"
            f"🎬 <b>Video:</b> {video_title}\n"
            f"🔗 <b>Link:</b> <a href='{youtube_url}'>{youtube_url}</a>"
        )
        await cls._send(message)

    @classmethod
    async def notify_failure(cls, channel_name: str, video_title: str, error: str):
        """
        Gửi thông báo upload THẤT BẠI.

        Args:
            channel_name: Tên kênh
            video_title : Tiêu đề video bị lỗi
            error       : Thông tin lỗi
        """
        message = (
            "❌ <b>Upload Thất Bại!</b>\n\n"
            f"📺 <b>Kênh:</b> {channel_name}\n"
            f"🎬 <b>Video:</b> {video_title}\n"
            f"⚠️ <b>Lỗi:</b> <code>{error[:300]}</code>"
        )
        await cls._send(message)

    @classmethod
    async def notify_status(cls, running_count: int, pending_count: int):
        """Gửi báo cáo trạng thái hệ thống theo yêu cầu."""
        message = (
            "📊 <b>Trạng thái hệ thống</b>\n\n"
            f"🔄 <b>Đang chạy:</b> {running_count} task\n"
            f"⏳ <b>Chờ xử lý:</b> {pending_count} task"
        )
        await cls._send(message)

    @classmethod
    def fire_and_forget(cls, coro):
        """
        Utility: chạy coroutine notification mà không cần await.
        Dùng trong Worker thread không có event loop sẵn.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(coro)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            # Nếu không có loop → tạo loop mới
            asyncio.run(coro)
