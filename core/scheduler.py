"""
core/scheduler.py
=================
TaskScheduler — quản lý lịch upload tự động bằng APScheduler.

Thiết kế:
  - BackgroundScheduler chạy hoàn toàn nền, không block UI.
  - Mỗi Task.schedule_time → tạo một Job riêng.
  - Khi job kích hoạt → khởi tạo YouTubeWorker và start().
"""

import datetime
import os
from pathlib import Path
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import pytz

from core.database import Task, DatabaseManager, STATUS_PENDING


BASE_DIR = Path(os.environ.get("YTAP_DATA_DIR", Path(__file__).resolve().parent.parent))


class TaskScheduler:
    """
    TaskScheduler — Singleton quản lý jobs APScheduler.

    Sử dụng:
        TaskScheduler.start()             # Gọi khi app khởi động
        TaskScheduler.schedule_task(task) # Thêm job cho 1 task
        TaskScheduler.shutdown()          # Gọi khi app tắt
    """

    _scheduler: Optional[BackgroundScheduler] = None

    @classmethod
    def start(cls):
        """Khởi động background scheduler."""
        if cls._scheduler is None:
            cls._scheduler = BackgroundScheduler(timezone="UTC")
            cls._scheduler.start()
            print("[Scheduler] Đã khởi động.")

        # Load lại tất cả pending tasks từ DB
        cls._reload_pending_tasks()

    @classmethod
    def shutdown(cls):
        """Tắt scheduler an toàn khi ứng dụng đóng."""
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown(wait=False)
            cls._scheduler = None
            print("[Scheduler] Đã tắt.")

    @classmethod
    def schedule_task(cls, task: Task) -> bool:
        """
        Đăng ký một Task vào scheduler.

        Args:
            task: Task cần lên lịch (phải có schedule_time)

        Returns:
            True nếu đăng ký thành công, False nếu thời gian đã qua.
        """
        if not cls._scheduler:
            return False

        if not task.schedule_time:
            print(f"[Scheduler] Task {task.id} không có schedule_time.")
            return False

        # Convert sang timezone UTC để so sánh
        tz       = pytz.timezone(task.timezone)
        run_time = tz.localize(task.schedule_time) if task.schedule_time.tzinfo is None else task.schedule_time
        run_utc  = run_time.astimezone(pytz.utc)

        if run_utc < datetime.datetime.now(pytz.utc):
            print(f"[Scheduler] Task {task.id} đã quá hạn, bỏ qua.")
            return False

        job_id = f"task_{task.id}"
        # Xóa job cũ nếu đã tồn tại (tránh duplicate)
        cls._remove_job(job_id)

        cls._scheduler.add_job(
            func=cls._execute_task,
            trigger=DateTrigger(run_date=run_utc),
            args=[task.id],
            id=job_id,
            name=f"Upload: {task.title[:30]}",
            misfire_grace_time=300,  # 5 phút grace period
        )
        print(f"[Scheduler] Đã lên lịch Task {task.id} vào {run_utc.strftime('%Y-%m-%d %H:%M UTC')}")
        return True

    @classmethod
    def remove_task(cls, task_id: int):
        """Hủy job của một Task."""
        cls._remove_job(f"task_{task_id}")

    @classmethod
    def get_scheduled_jobs(cls) -> list[dict]:
        """Trả về danh sách jobs đang chờ."""
        if not cls._scheduler:
            return []
        return [
            {
                "id":      job.id,
                "name":    job.name,
                "next_run": str(job.next_run_time),
            }
            for job in cls._scheduler.get_jobs()
        ]

    # ──────────────────────────────────────────
    # INTERNAL
    # ──────────────────────────────────────────

    @classmethod
    def _reload_pending_tasks(cls):
        """Load lại tất cả Pending Tasks có schedule_time từ DB."""
        pending = DatabaseManager.get_pending_tasks()
        for task in pending:
            if task.schedule_time:
                # Nếu đã quá giờ → chạy ngay, không đợi scheduler
                tz = pytz.timezone(task.timezone or 'Asia/Ho_Chi_Minh')
                run_time = tz.localize(task.schedule_time) if task.schedule_time.tzinfo is None else task.schedule_time
                if run_time.astimezone(pytz.utc) <= datetime.datetime.now(pytz.utc):
                    print(f"[Scheduler] Task {task.id} đã quá giờ, chạy ngay khi khởi động")
                    # Import muộn để tránh circular
                    from core.youtube_worker import YouTubeWorker
                    YouTubeWorker(task).start()
                    continue
                cls.schedule_task(task)
        print(f"[Scheduler] Đã nạp lại {len(pending)} pending tasks.")

    @classmethod
    def _execute_task(cls, task_id: int):
        """
        Hàm được APScheduler gọi khi đến giờ upload.
        Tạo YouTubeWorker và bắt đầu upload trong thread riêng.
        """
        # Import muộn để tránh circular
        from core.youtube_worker import YouTubeWorker

        try:
            task = Task.get_by_id(task_id)
            if task.status != STATUS_PENDING:
                print(f"[Scheduler] Task {task_id} không còn Pending, bỏ qua.")
                return

            worker = YouTubeWorker(task)
            worker.start()
            print(f"[Scheduler] Đã kích hoạt upload Task {task_id}.")
        except Task.DoesNotExist:
            print(f"[Scheduler] Task {task_id} không tồn tại trong DB.")
        except Exception as e:
            print(f"[Scheduler] Lỗi khi thực thi Task {task_id}: {e}")

    @classmethod
    def _remove_job(cls, job_id: str):
        """Xóa job theo ID nếu tồn tại."""
        if cls._scheduler:
            try:
                cls._scheduler.remove_job(job_id)
            except Exception:
                pass  # Job không tồn tại → bỏ qua
