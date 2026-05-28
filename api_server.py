"""
Local HTTP API for YouTube Auto Pusher Electron UI.
Keeps the existing Python core intact and exposes a small localhost JSON API.
"""

from __future__ import annotations

# ── UTF-8 bootstrap: must run before ANY other import that may print ──
import io as _io
import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8:replace")
os.environ.setdefault("PYTHONUTF8", "1")

def _force_utf8_streams():
    for _attr in ("stdout", "stderr"):
        _stream = getattr(sys, _attr, None)
        if _stream is None:
            continue
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            try:
                _buf = getattr(_stream, "buffer", None)
                if _buf:
                    setattr(sys, _attr, _io.TextIOWrapper(
                        _buf, encoding="utf-8", errors="replace", line_buffering=True))
            except Exception:
                pass

_force_utf8_streams()
# ── end UTF-8 bootstrap ──

import argparse
import datetime as dt
import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytz

from core.cache_manager import CacheManager
from core.chrome_manager import ChromeManager
from core.database import (
    DatabaseManager,
    Profile,
    Task,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from core.oauth_helper import OAuthHelper
from core.scheduler import TaskScheduler
from core.youtube_worker import (
    YouTubeWorker,
    delete_cache_best_effort,
)

BASE_DIR = Path(os.environ.get("YTAP_DATA_DIR", Path(__file__).resolve().parent))
BASE_DIR.mkdir(parents=True, exist_ok=True)


def _json_default(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    return str(value)


def _task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "profileId": task.profile.id if hasattr(task.profile, "id") else task.profile_id,
        "title": task.title,
        "description": task.description,
        "tags": task.tags,
        "hashtags": task.hashtags,
        "madeForKids": bool(task.made_for_kids),
        "paidPromotion": bool(task.paid_promotion),
        "alteredContent": bool(task.altered_content),
        "cachedPath": task.cached_path,
        "thumbnailPath": task.thumbnail_path,
        "scheduleTime": task.schedule_time.isoformat() if task.schedule_time else None,
        "timezone": task.timezone,
        "status": task.status,
        "youtubeUrl": task.youtube_url,
        "errorMessage": task.error_message,
        "retryCount": task.retry_count or 0,
        "createdAt": task.created_at.isoformat() if task.created_at else None,
        "updatedAt": task.updated_at.isoformat() if task.updated_at else None,
    }


def _profile_stats(profile: Profile) -> dict:
    query = Task.select().where(Task.profile == profile.id)
    return {
        "total": query.count(),
        "waiting": query.where(Task.status == STATUS_PENDING).count(),
        "running": query.where(Task.status == STATUS_RUNNING).count(),
        "completed": query.where(Task.status == STATUS_COMPLETED).count(),
        "failed": query.where(Task.status == STATUS_FAILED).count(),
    }


def _profile_to_dict(profile: Profile) -> dict:
    channels = []
    try:
        import json as _json
        if profile.channels_json:
            channels = _json.loads(profile.channels_json)
    except Exception:
        pass
    return {
        "id": profile.id,
        "name": profile.name,
        "channelId": profile.channel_id,
        "channelTitle": profile.channel_title,
        "channelAvatar": profile.channel_avatar,
        "subscriberCount": profile.subscriber_count,
        "channels": channels,
        "jsonApiPath": profile.json_api_path,
        "tokenPath": profile.token_path,
        "isActive": bool(profile.is_active),
        "chromeProfileName": profile.chrome_profile_name,
        "chromeRunning": ChromeManager.is_running(profile.id),
        "stats": _profile_stats(profile),
        "cacheBytes": profile.get_cache_size_bytes(),
    }


def _parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return dt.datetime.strptime(value, fmt)
        except Exception:
            pass
    try:
        return dt.datetime.fromisoformat(value)
    except Exception as exc:
        raise ValueError("Invalid scheduleTime. Use YYYY-MM-DDTHH:MM or DD/MM/YYYY HH:MM") from exc


def _is_due(task: Task) -> bool:
    # Nếu chưa đặt lịch đăng đăng → không cho chạy
    if not task.schedule_time:
        return False
    tz = pytz.timezone(task.timezone or "Asia/Ho_Chi_Minh")
    run_time = tz.localize(task.schedule_time) if task.schedule_time.tzinfo is None else task.schedule_time
    return run_time.astimezone(pytz.utc) <= dt.datetime.now(pytz.utc)


def _schedule_if_needed(task: Task):
    if task.status == STATUS_PENDING and task.schedule_time:
        TaskScheduler.schedule_task(task)
    else:
        TaskScheduler.remove_task(task.id)


def cleanup_orphan_cache_files():
    """Remove temp cache files that are no longer referenced by any task."""
    referenced = {str(Path(t.cached_path).resolve()).lower() for t in Task.select() if t.cached_path}
    cache_root = BASE_DIR / "cache"
    if not cache_root.exists():
        return
    for file in cache_root.rglob("*"):
        if not file.is_file():
            continue
        if str(file.resolve()).lower() in referenced:
            continue
        try:
            file.unlink()
            print(f"[Cleanup] Đã xóa cache mồ côi: {file.name}")
        except Exception as exc:
            print(f"[Cleanup] Không xóa được cache mồ côi {file}: {exc}")


def cleanup_completed_tasks_on_start():
    """Repair old success-marked-as-failed tasks and clean up orphan cache files."""
    for task in list(Task.select().where(Task.youtube_url != "")):
        # If YouTube URL exists, the upload succeeded even if old cleanup code marked Failed.
        if task.status == STATUS_FAILED:
            task.status = STATUS_COMPLETED
            task.error_message = ""
            task.save()

        try:
            delete_cache_best_effort(task.profile.id, task.cached_path, retries=3, delay=0.2)
        except Exception as exc:
            print(f"[Cleanup] Cache cleanup warning for task {task.id}: {exc}")


def _run_due_tasks(profile_id: int) -> dict:
    profile = Profile.get_by_id(profile_id)
    candidates = list(
        Task.select()
        .where((Task.profile == profile.id) & (Task.status.in_([STATUS_PENDING, STATUS_FAILED])))
        .order_by(Task.schedule_time, Task.created_at)
    )
    # PRE-FLIGHT VALIDATION: kiểm tra dữ liệu bắt buộc
    print(f"[API] _run_due_tasks: {len(candidates)} candidates for profile {profile_id}", flush=True)
    invalid = []
    valid_due = []
    for task in candidates:
        if not _is_due(task):
            if not task.schedule_time:
                invalid.append(f"Task #{task.id}: chưa đặt lịch đăng đăng")
            continue
        issues = []
        if not (task.title or "").strip():
            issues.append("thiếu tiêu đề")
        if not (task.description or "").strip():
            issues.append("thiếu mô tả")
        if not (task.tags or "").strip():
            issues.append("thiếu tags")
        if not (task.cached_path or "").strip():
            issues.append("chưa chọn video")
        elif not Path(task.cached_path).exists():
            issues.append(f"file video không tồn tại")
        if not task.schedule_time:
            issues.append("chưa đặt lịch đăng đăng")
        if issues:
            invalid.append(f"Task #{task.id}: {', '.join(issues)}")
        else:
            valid_due.append(task)
    if invalid:
        print(f"[API] BLOCKED {len(invalid)} invalid tasks: " + "; ".join(invalid), flush=True)
        print(f"[API] Bỏ qua {len(invalid)} task thiếu dữ liệu: {'; '.join(invalid)}")
    due = valid_due
    skipped = len(candidates) - len(due)
    if due:
        print(f"[API] UPLOADING {len(due)} valid tasks", flush=True)
    for task in due:
        if task.status == STATUS_FAILED:
            task.status = STATUS_PENDING
            task.error_message = ""
            task.save()
        YouTubeWorker(task).start()
    return {"ok": len(due) > 0 or len(invalid) == 0, "started": len(due), "skippedFuture": skipped, "invalid": invalid, "error": ("; ".join(invalid) if invalid else None)}


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "YouTubeAutoPusherAPI/2.0"

    def log_message(self, fmt, *args):
        print("[API]", fmt % args)

    def _send(self, status=200, data=None):
        body = json.dumps(data if data is not None else {}, ensure_ascii=False, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def _error(self, status, message):
        self._send(status, {"ok": False, "error": str(message)})

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        try:
            path = urlparse(self.path).path.strip("/").split("/")
            if self.path.startswith("/api/health"):
                self._send(200, {"ok": True})
                return
            if path == ["api", "profiles"]:
                self._send(200, {"profiles": [_profile_to_dict(p) for p in DatabaseManager.get_all_profiles()]})
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "tasks":
                profile_id = int(path[2])
                tasks = list(Task.select().where(Task.profile == profile_id).order_by(Task.created_at))
                self._send(200, {"tasks": [_task_to_dict(t) for t in tasks]})
                return
            if path == ["api", "statistics"] or path == ["api", "stats"]:
                self._send(200, {"cacheBytes": DatabaseManager.get_cache_total_bytes()})
                return
            if len(path) == 3 and path[:2] == ["api", "statistics"] and path[2] == "daily":
                # Today + last 7 days breakdown
                today = dt.date.today()
                days = []
                for i in range(7):
                    d = today - dt.timedelta(days=i)
                    day_start = dt.datetime.combine(d, dt.time.min)
                    day_end = dt.datetime.combine(d, dt.time.max)
                    q = Task.select().where(
                        (Task.updated_at >= day_start) & (Task.updated_at <= day_end)
                    )
                    days.append({
                        "date": d.isoformat(),
                        "total": q.count(),
                        "completed": q.where(Task.status == STATUS_COMPLETED).count(),
                        "failed": q.where(Task.status == STATUS_FAILED).count(),
                    })
                # Latest 20 completed/failed tasks
                recent = list(
                    Task.select()
                    .where(Task.status.in_([STATUS_COMPLETED, STATUS_FAILED]))
                    .order_by(Task.updated_at.desc())
                    .limit(20)
                )
                # Upcoming scheduled
                upcoming = list(
                    Task.select()
                    .where(Task.status.in_([STATUS_PENDING, STATUS_RUNNING]))
                    .order_by(Task.schedule_time.asc(), Task.created_at.asc())
                    .limit(20)
                )
                self._send(200, {
                    "ok": True,
                    "today": days[0],
                    "days": days,
                    "recent": [_task_to_dict(t) for t in recent],
                    "upcoming": [_task_to_dict(t) for t in upcoming],
                })
                return
            if len(path) == 3 and path[:2] == ["api", "statistics"] and path[2] == "summary":
                total_tasks = Task.select().count()
                total_completed = Task.select().where(Task.status == STATUS_COMPLETED).count()
                total_failed = Task.select().where(Task.status == STATUS_FAILED).count()
                total_pending = Task.select().where(Task.status == STATUS_PENDING).count()
                total_running = Task.select().where(Task.status == STATUS_RUNNING).count()
                profile_count = Profile.select().count()
                active_profiles = Profile.select().where(Profile.is_active == True).count()
                cache_bytes = DatabaseManager.get_cache_total_bytes()
                self._send(200, {
                    "ok": True,
                    "totalTasks": total_tasks,
                    "totalCompleted": total_completed,
                    "totalFailed": total_failed,
                    "totalPending": total_pending,
                    "totalRunning": total_running,
                    "profileCount": profile_count,
                    "activeProfiles": active_profiles,
                    "cacheBytes": cache_bytes,
                })
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "analytics":
                print("ANALYTICS HANDLER REACHED!", flush=True)
                profile = Profile.get_by_id(int(path[2]))
                data = OAuthHelper.get_channel_analytics(profile)
                self._send(200, {"ok": True, "analytics": data})
                return
            if path == ["api", "settings"]:
                cache_root = BASE_DIR / "cache"
                cache_bytes = DatabaseManager.get_cache_total_bytes()
                cache_files = sum(1 for _ in cache_root.rglob("*")) if cache_root.exists() else 0
                profiles = DatabaseManager.get_all_profiles()
                self._send(200, {
                    "ok": True,
                    "cacheBytes": cache_bytes,
                    "cacheFiles": cache_files,
                    "cacheLimitGB": 5,
                    "profileCount": len(profiles),
                    "dataDir": str(BASE_DIR),
                    "apiPort": 8765,
                })
                return
            self._error(404, "Not found")
        except Exception as exc:
            try:
                traceback.print_exc()
            except Exception:
                pass
            self._error(500, exc)

    def do_POST(self):
        try:
            path = urlparse(self.path).path.strip("/").split("/")
            data = self._read_json()
            if path == ["api", "profiles"]:
                name = (data.get("name") or "").strip()
                if not name:
                    raise ValueError("Vui lòng nhập tên kênh")
                profile = DatabaseManager.create_profile(
                    name=name,
                    json_api_path=(data.get("jsonApiPath") or "").strip(),
                )
                self._send(200, {"ok": True, "profile": _profile_to_dict(profile)})
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "tasks":
                profile = Profile.get_by_id(int(path[2]))
                cache = CacheManager(profile.id, BASE_DIR)
                created = []
                schedule = _parse_dt(data.get("scheduleTime"))  # None nếu không có — ép user đặt lịch
                timezone = data.get("timezone") or "Asia/Ho_Chi_Minh"
                for source in data.get("paths", []):
                    cached = cache.copy_to_cache(source)
                    task = Task.create(
                        profile=profile,
                        title=data.get("title") or Path(source).stem[:100],
                        description=data.get("description") or "",
                        tags=data.get("tags") or "",
                        hashtags=data.get("hashtags") or "",
                        cached_path=str(cached),
                        schedule_time=schedule,
                        timezone=timezone,
                        made_for_kids=bool(data.get("madeForKids", False)),
                        paid_promotion=bool(data.get("paidPromotion", False)),
                        altered_content=bool(data.get("alteredContent", False)),
                    )
                    _schedule_if_needed(task)
                    created.append(_task_to_dict(task))
                self._send(200, {"ok": True, "tasks": created})
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "run-due":
                result = _run_due_tasks(int(path[2]))
                self._send(400 if result.get("invalid") else 200, {"ok": len(result.get("invalid", [])) == 0, **result})
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "check-api":
                profile = Profile.get_by_id(int(path[2]))
                if data.get("jsonApiPath") is not None:
                    profile.json_api_path = data.get("jsonApiPath") or ""
                    profile.save()
                info = OAuthHelper.quick_connect(profile)
                self._send(200, {"ok": True, "profile": _profile_to_dict(Profile.get_by_id(profile.id)), "info": info})
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "switch-channel":
                profile = Profile.get_by_id(int(path[2]))
                channel_id = (data.get("channelId") or "").strip()
                if not channel_id:
                    raise ValueError("Thiếu channelId")
                # Tim kenh trong danh sach
                import json as _json
                channels = _json.loads(profile.channels_json or "[]")
                selected = next((c for c in channels if c["id"] == channel_id), None)
                if not selected:
                    raise ValueError(f"Kênh {channel_id} không có trong danh sách")
                profile.channel_id = selected["id"]
                profile.channel_title = selected["title"]
                profile.channel_avatar = selected.get("thumbnail_url", "")
                profile.subscriber_count = selected.get("subscriber_count", 0)
                profile.save()
                self._send(200, {"ok": True, "profile": _profile_to_dict(profile)})
                return
            if path == ["api", "settings", "cache", "clear"]:
                removed = 0
                size_freed = 0
                cache_root = BASE_DIR / "cache"
                if cache_root.exists():
                    # Only clear files not referenced by any task
                    referenced = {str(Path(t.cached_path).resolve()).lower()
                                  for t in Task.select() if t.cached_path}
                    for file in list(cache_root.rglob("*")):
                        if not file.is_file():
                            continue
                        if str(file.resolve()).lower() in referenced:
                            continue
                        try:
                            size_freed += file.stat().st_size
                            file.unlink()
                            removed += 1
                        except Exception:
                            pass
                self._send(200, {"ok": True, "removed": removed, "freedBytes": size_freed})
                return
            if len(path) == 4 and path[:2] == ["api", "tasks"] and path[3] == "retry":
                task = Task.get_by_id(int(path[2]))
                if task.status == STATUS_FAILED:
                    task.status = STATUS_PENDING
                    task.error_message = f"[Manual retry] {task.error_message}"
                    task.retry_count = (task.retry_count or 0) + 1
                    task.updated_at = dt.datetime.now()
                    task.save()
                    _schedule_if_needed(task)
                    self._send(200, {"ok": True, "task": _task_to_dict(task)})
                else:
                    self._send(200, {"ok": True, "task": _task_to_dict(task), "message": "Task is not in Failed status"})
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "open-studio":
                profile = Profile.get_by_id(int(path[2]))
                opened = ChromeManager.open_url(profile, "https://studio.youtube.com")
                self._send(200, {"ok": True, "opened": opened})
                return
            if len(path) == 4 and path[:2] == ["api", "profiles"] and path[3] == "open-api-key":
                profile = Profile.get_by_id(int(path[2]))
                opened = ChromeManager.open_url(profile, "https://console.cloud.google.com/apis/credentials")
                self._send(200, {"ok": True, "opened": opened})
                return
            self._error(404, "Not found")
        except Exception as exc:
            try:
                traceback.print_exc()
            except Exception:
                pass
            self._error(500, exc)

    def do_PUT(self):
        try:
            path = urlparse(self.path).path.strip("/").split("/")
            data = self._read_json()
            if len(path) == 3 and path[:2] == ["api", "profiles"]:
                profile = Profile.get_by_id(int(path[2]))
                name = (data.get("name") or "").strip()
                if not name:
                    raise ValueError("Vui lòng nhập tên kênh")
                profile.name = name
                if "jsonApiPath" in data:
                    profile.json_api_path = (data.get("jsonApiPath") or "").strip()
                profile.save()
                profile.save_config()
                self._send(200, {"ok": True, "profile": _profile_to_dict(Profile.get_by_id(profile.id))})
                return
            if len(path) == 3 and path[:2] == ["api", "tasks"]:
                task = Task.get_by_id(int(path[2]))
                task.title = data.get("title", task.title).strip() or task.title
                task.description = data.get("description", task.description) or ""
                task.tags = data.get("tags", task.tags) or ""
                task.hashtags = data.get("hashtags", task.hashtags) or ""
                task.made_for_kids = bool(data.get("madeForKids", task.made_for_kids))
                task.paid_promotion = bool(data.get("paidPromotion", task.paid_promotion))
                task.altered_content = bool(data.get("alteredContent", task.altered_content))
                task.timezone = data.get("timezone", task.timezone) or "Asia/Ho_Chi_Minh"
                if "scheduleTime" in data:
                    task.schedule_time = _parse_dt(data.get("scheduleTime"))
                task.updated_at = dt.datetime.now()
                task.save()
                _schedule_if_needed(task)
                self._send(200, {"ok": True, "task": _task_to_dict(Task.get_by_id(task.id))})
                return
            self._error(404, "Not found")
        except Exception as exc:
            try:
                traceback.print_exc()
            except Exception:
                pass
            self._error(500, exc)

    def do_DELETE(self):
        try:
            path = urlparse(self.path).path.strip("/").split("/")
            if len(path) == 3 and path[:2] == ["api", "profiles"]:
                profile = Profile.get_by_id(int(path[2]))
                # Stop scheduled jobs for this profile before deleting files/records.
                for task in Task.select().where(Task.profile == profile.id):
                    TaskScheduler.remove_task(task.id)
                DatabaseManager.delete_profile(profile.id)
                self._send(200, {"ok": True})
                return
            if len(path) == 3 and path[:2] == ["api", "tasks"]:
                task = Task.get_by_id(int(path[2]))
                cached_path = task.cached_path
                profile_id = task.profile.id
                TaskScheduler.remove_task(task.id)
                task.delete_instance()
                if cached_path:
                    try:
                        CacheManager(profile_id, BASE_DIR).delete(cached_path)
                    except Exception as exc:
                        print(f"[API] Delete cache warning: {exc}")
                self._send(200, {"ok": True})
                return
            self._error(404, "Not found")
        except Exception as exc:
            try:
                traceback.print_exc()
            except Exception:
                pass
            self._error(500, exc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    DatabaseManager.initialize()
    cleanup_completed_tasks_on_start()
    cleanup_orphan_cache_files()
    TaskScheduler.start()
    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    print(f"[API] Listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    finally:
        TaskScheduler.shutdown()
        DatabaseManager.close()


if __name__ == "__main__":
    main()
