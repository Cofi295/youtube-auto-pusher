"""
core/youtube_worker.py
======================
YouTubeWorker — xử lý logic upload video lên YouTube Data API v3.
"""

import json
import os
import threading
import re
import time
import datetime
import pytz
from pathlib import Path
from typing import Callable, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from core.database import Task, Profile, STATUS_PENDING
from core.cache_manager import CacheManager
from core.notify_manager import NotifyManager
from core.oauth_helper import OAuthHelper

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE = "youtube"
API_VERSION = "v3"
BASE_DIR = Path(os.environ.get("YTAP_DATA_DIR", Path(__file__).resolve().parent.parent))
COMPLETED_TASK_TTL_SECONDS = 30 * 60


def delete_cache_best_effort(profile_id: int, cached_path: str, retries: int = 20, delay: float = 0.5) -> bool:
    """Delete cache after upload without ever marking the upload as failed."""
    if not cached_path:
        return True
    for attempt in range(retries):
        try:
            return CacheManager(profile_id, BASE_DIR).delete(cached_path)
        except PermissionError as exc:
            if attempt == retries - 1:
                print(f"[Cache] Không xóa được cache sau upload, bỏ qua để không báo fail: {exc}")
                return False
            time.sleep(delay)
        except Exception as exc:
            print(f"[Cache] Lỗi xóa cache sau upload, bỏ qua để không báo fail: {exc}")
            return False
    return False


def schedule_completed_task_delete(task_id: int, delay_seconds: int = COMPLETED_TASK_TTL_SECONDS):
    """Keep completed task visible for a short time, then remove it from DB/list."""
    def _delete_later():
        try:
            task = Task.get_by_id(task_id)
            if task.status == "Completed":
                try:
                    delete_cache_best_effort(task.profile.id, task.cached_path, retries=3, delay=0.2)
                except Exception:
                    pass
                task.delete_instance()
                print(f"[DB] Đã tự xóa task đã đăng sau {delay_seconds}s: {task_id}")
        except Task.DoesNotExist:
            pass
        except Exception as exc:
            print(f"[DB] Không xóa được task completed {task_id}: {exc}")

    timer = threading.Timer(delay_seconds, _delete_later)
    timer.daemon = True
    timer.start()


def parse_youtube_tags(value: str) -> list[str]:
    """Nhận tags kiểu YouTube Studio: tag1, tag2 / #tag1 #tag2 / mỗi dòng 1 tag / JSON list."""
    raw = (value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x).strip().lstrip("#") for x in parsed if str(x).strip()]
    except Exception:
        pass

    parts = []
    if "," in raw or "\n" in raw or ";" in raw:
        parts = re.split(r"[,;\n]+", raw)
    else:
        # Nếu người dùng nhập '#tag1 #tag2' thì tách theo khoảng trắng.
        # Nếu là cụm từ không có # thì giữ nguyên làm 1 tag.
        parts = raw.split() if "#" in raw else [raw]
    result = []
    seen = set()
    for p in parts:
        tag = p.strip().strip(",;").lstrip("#").strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            result.append(tag[:500])
    return result


def normalize_cached_path(path_text: str) -> str:
    """Tự sửa path cache cũ khi project bị chuyển ổ/thư mục."""
    p = Path(path_text or "")
    if p.exists():
        return str(p)
    try:
        marker = f"cache{Path(path_text).anchor and ''}"
        parts = p.parts
        if "cache" in parts:
            idx = parts.index("cache")
            candidate = BASE_DIR.joinpath(*parts[idx:])
            if candidate.exists():
                return str(candidate)
    except Exception:
        pass
    return path_text


class YouTubeWorker:
    def __init__(self, task: Task, on_progress: Optional[Callable[[int], None]] = None, on_done: Optional[Callable[[str], None]] = None, on_error: Optional[Callable[[str], None]] = None):
        self.task = task
        self.on_progress = on_progress
        self.on_done = on_done
        self.on_error = on_error
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"yt_worker_{task.id}")

    def start(self):
        self._thread.start()

    def _get_youtube_service(self, profile: Profile):
        json_path = OAuthHelper.resolve_json_path(profile.json_api_path)
        token_dir = BASE_DIR / "tokens"
        token_file = Path(profile.token_path) if profile.token_path else token_dir / f"token_{profile.id}.json"
        creds = OAuthHelper.get_valid_credentials(token_file, json_path)
        if not creds:
            creds = OAuthHelper.authenticate(json_path, token_file)
        return build(API_SERVICE, API_VERSION, credentials=creds)

    def _run(self):
        task = self.task
        profile = task.profile
        try:
            print(f"[Worker] Task {task.id}: title={repr(task.title[:40] if task.title else None)} sched={task.schedule_time} desc_len={len(task.description or '')} tags_len={len(task.tags or '')} hashtags_len={len(task.hashtags or '')}")
            # === VALIDATION: kiểm tra DỮ LIỆU BẮT BUỘc trước khi upload ===
            issues = []
            if not (task.title or "").strip():
                issues.append("Tiêu đề trống")
            if not (task.description or "").strip():
                issues.append("Mô tả trống")
            if not (task.tags or "").strip():
                issues.append("Tags trống")
            if not (task.hashtags or "").strip():
                issues.append("Hashtags trống")
            if not (task.cached_path or "").strip():
                issues.append("Chưa chọn file video")
            if issues:
                print(f"[Worker] Task {task.id}: REJECTED - {'; '.join(issues)}")
                raise ValueError("Dữ liệu không hợp lệ: " + "; ".join(issues))
            video_path = normalize_cached_path(task.cached_path)
            if not video_path or not Path(video_path).exists():
                raise FileNotFoundError(f"Không tìm thấy video: {task.cached_path}")
            task.mark_running()
            if video_path != task.cached_path:
                task.cached_path = video_path
                task.save()

            body = {
                "snippet": {
                    "title": task.title,
                    "description": task.description + ("\n" + task.hashtags if task.hashtags else ""),
                    "tags": parse_youtube_tags(task.tags),
                    "categoryId": "22",
                },
                "status": {
                    "privacyStatus": "public",
                    # Required audience declaration in YouTube Studio.
                    "selfDeclaredMadeForKids": bool(task.made_for_kids),
                    # YouTube altered/synthetic content disclosure.
                    "containsSyntheticMedia": bool(task.altered_content),
                },
                "paidProductPlacementDetails": {
                    "hasPaidProductPlacement": bool(task.paid_promotion),
                },
            }

            media = MediaFileUpload(video_path, mimetype="video/*", resumable=True, chunksize=10 * 1024 * 1024)
            youtube = self._get_youtube_service(profile)
            request = youtube.videos().insert(part="snippet,status,paidProductPlacementDetails", body=body, media_body=media)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and self.on_progress:
                    self.on_progress(int(status.progress() * 100))

            video_id = response["id"]
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            cached_path = task.cached_path
            task_title = task.title
            profile_id = profile.id
            profile_name = profile.name

            # YouTube has accepted the upload. From this point on, cleanup errors must
            # not turn a successfully posted video into a Failed task.
            task.mark_completed(youtube_url)

            try:
                fd = getattr(media, "_fd", None)
                if fd:
                    fd.close()
            except Exception:
                pass

            # Delete cached video immediately after successful upload.
            delete_cache_best_effort(profile_id, cached_path)

            NotifyManager.fire_and_forget(NotifyManager.notify_success(profile_name, task_title, youtube_url))

            if self.on_done:
                self.on_done(youtube_url)

        except HttpError as e:
            content = e.content.decode(errors="replace") if hasattr(e.content, "decode") else str(e.content)
            self._handle_failure(f"YouTube API lỗi: {e.resp.status} — {content[:400]}")
        except Exception as e:
            self._handle_failure(str(e))

    def _handle_failure(self, error_msg: str):
        MAX_RETRIES = 3
        RETRY_DELAY_SECONDS = 5 * 60  # 5 minutes
        print(f"[Worker] LỖI: {error_msg}")
        if self.task.youtube_url:
            # Upload was already accepted by YouTube; cleanup/notify errors must not
            # turn it into Failed.
            self.task.mark_completed(self.task.youtube_url)
            if self.on_done:
                self.on_done(self.task.youtube_url)
            return

        retry_count = self.task.retry_count or 0
        if retry_count < MAX_RETRIES:
            # Increment retry count and schedule retry
            self.task.retry_count = retry_count + 1
            self.task.status = STATUS_PENDING
            self.task.error_message = f"[Retry {retry_count + 1}/{MAX_RETRIES}] {error_msg}"
            self.task.updated_at = datetime.datetime.now()
            self.task.save()
            print(f"[Worker] Retry {retry_count + 1}/{MAX_RETRIES} for task {self.task.id} in 5 min")
            # Schedule retry after 5 minutes
            task_id = self.task.id
            timer = threading.Timer(RETRY_DELAY_SECONDS, self._retry_upload, args=(task_id,))
            timer.daemon = True
            timer.start()
            if self.on_error:
                self.on_error(f"Retry {retry_count + 1}/{MAX_RETRIES} scheduled")
        else:
            # Permanently failed after max retries
            self.task.mark_failed(f"[Failed after {MAX_RETRIES} retries] {error_msg}")
            NotifyManager.fire_and_forget(NotifyManager.notify_failure(self.task.profile.name, self.task.title, error_msg))
            if self.on_error:
                self.on_error(error_msg)

    @staticmethod
    def _retry_upload(task_id: int):
        """Retry upload after delay."""
        try:
            task = Task.get_by_id(task_id)
            if task.status != STATUS_PENDING:
                return  # Already handled by another retry
            worker = YouTubeWorker(task)
            worker.start()
        except Task.DoesNotExist:
            print(f"[Worker] Task {task_id} not found for retry")
        except Exception as e:
            print(f"[Worker] Retry failed for task {task_id}: {e}")
