"""
core/oauth_helper.py
====================
OAuthHelper — quan ly OAuth flow don gian hoa cho user.

Nguyen tac:
  - Dung bundled client_secret.json (trong config/) lam mac dinh.
  - User chi can bấm "Kết nối" → login Gmail → xong.
  - Tu dong luu token, tu dong refresh.
  - Lay thong tin kênh sau khi auth (ten, avatar, subscriber).
"""

import json
import os
import wsgiref.simple_server
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import (
    InstalledAppFlow,
    WSGITimeoutError,
    _RedirectWSGIApp,
    _WSGIRequestHandler,
)
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",  # dùng để check API/lấy thông tin kênh
]
AUTH_TIMEOUT_SECONDS = 75
BASE_DIR = Path(os.environ.get("YTAP_DATA_DIR", Path(__file__).resolve().parent.parent))
BUNDLED_JSON_PATH = BASE_DIR / "config" / "client_secret.json"


class OAuthHelper:
    """Quan ly OAuth flow — 1 class cho tat ca profile."""

    @classmethod
    def get_default_json_path(cls) -> Path:
        """Tra ve duong dan bundled client_secret.json."""
        return BUNDLED_JSON_PATH

    @classmethod
    def is_bundled_available(cls) -> bool:
        """Check bundled JSON file co ton tai khong."""
        return BUNDLED_JSON_PATH.exists()

    @classmethod
    def resolve_json_path(cls, custom_path: str = "") -> Path:
        """
        Tra ve duong dan JSON se dung.
        Uu tien: custom_path > bundled path.
        """
        if custom_path and Path(custom_path).exists():
            return Path(custom_path)
        return BUNDLED_JSON_PATH

    @classmethod
    def get_valid_credentials(cls, token_path: Path, json_path: Optional[Path] = None) -> Optional[Credentials]:
        """
        Lay credentials hop le (load tu file hoac refresh).

        Args:
            token_path: Duong dan file token da luu
            json_path:  Duong dan client_secret.json (mac dinh: bundled)

        Returns:
            Credentials object hoac None neu can auth lai
        """
        creds = None
        if token_path and token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            except Exception:
                pass

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                token_path.write_text(creds.to_json(), encoding="utf-8")
                return creds
            except Exception:
                pass

        return None

    @classmethod
    def authenticate(cls, json_path: Path, token_path: Path, profile=None) -> Credentials:
        """
        Chay OAuth flow day du → tra ve Credentials.

        Mo browser → user login Gmail → auto dong → tra ve creds.
        Luu token vao token_path ngay lap tuc.

        Args:
            json_path:  Duong dan client_secret.json
            token_path: Duong dan se luu token

        Returns:
            Credentials da xac thuc

        Raises:
            FileNotFoundError: Neu json_path khong ton tai
        """
        if not json_path.exists():
            raise FileNotFoundError(
                f"Khong tim thay client_secret.json tai: {json_path}\n"
                f"Hay dat file vao: {BUNDLED_JSON_PATH}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(str(json_path), SCOPES)
        try:
            creds = cls._run_oauth_in_profile_chrome(flow, profile)
        except WSGITimeoutError as ex:
            raise TimeoutError(
                f"Hết thời gian chờ xác thực ({AUTH_TIMEOUT_SECONDS}s). "
                "Hãy kiểm tra tab xác thực trong đúng Chrome/Chromium của boxcard."
            ) from ex

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

        print(f"[OAuth] Auth thanh cong! Token luu tai: {token_path}")
        return creds

    @classmethod
    def _run_oauth_in_profile_chrome(cls, flow: InstalledAppFlow, profile=None) -> Credentials:
        """Run OAuth local-server flow, opening auth URL via ChromeManager for this profile."""
        success_message = "Đã xác thực YouTube API thành công. Có thể đóng tab này."
        wsgi_app = _RedirectWSGIApp(success_message)
        wsgiref.simple_server.WSGIServer.allow_reuse_address = False
        local_server = wsgiref.simple_server.make_server(
            "localhost", 0, wsgi_app, handler_class=_WSGIRequestHandler
        )
        try:
            flow.redirect_uri = f"http://localhost:{local_server.server_port}/"
            auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent select_account")

            opened = False
            if profile is not None:
                try:
                    from core.chrome_manager import ChromeManager
                    opened = ChromeManager.open_url(profile, auth_url)
                except Exception as ex:
                    print(f"[OAuth] Khong mo duoc URL bang Chrome profile: {ex}")
            if not opened:
                raise RuntimeError("Không mở được URL xác thực bằng Chrome profile của boxcard.")

            local_server.timeout = AUTH_TIMEOUT_SECONDS
            local_server.handle_request()
            if not wsgi_app.last_request_uri:
                raise WSGITimeoutError("Timed out waiting for OAuth response")

            authorization_response = wsgi_app.last_request_uri.replace("http", "https")
            flow.fetch_token(authorization_response=authorization_response)
        finally:
            local_server.server_close()
        return flow.credentials

    @classmethod
    def _get_client_id_from_json(cls, json_path: Path) -> str:
        """Extract client_id from a client_secret.json file."""
        try:
            if json_path.exists():
                data = json.loads(json_path.read_text(encoding="utf-8"))
                installed = data.get("installed", {}) or data.get("web", {})
                return installed.get("client_id", "")
        except Exception:
            pass
        return ""

    @classmethod
    def authenticate_profile(cls, profile) -> Credentials:
        """
        Convenience: auth cho 1 Profile instance.
        Auto-resolve JSON path + token path.
        """
        json_path = cls.resolve_json_path(profile.json_api_path)
        token_dir = BASE_DIR / "tokens"
        token_path = (
            Path(profile.token_path) if profile.token_path and Path(profile.token_path).exists()
            else token_dir / f"token_{profile.id}.json"
        )

        # Validate JSON path: neu file khong phai client_secret hop le → force re-auth
        if token_path.exists():
            new_client_id = cls._get_client_id_from_json(json_path) if json_path.exists() else ""
            if not new_client_id:
                # File khong phai OAuth client secret (vd: .srt, .txt, json rong...) → xoa token cu
                token_path.unlink()
                print(f"[OAuth] '{json_path.name}' khong phai OAuth client_secret hop le. Force re-auth.")
            else:
                try:
                    token_data = json.loads(token_path.read_text(encoding="utf-8"))
                    old_client_id = token_data.get("client_id", "")
                    if old_client_id and old_client_id != new_client_id:
                        token_path.unlink()
                        print(f"[OAuth] Token client_id mismatch ({old_client_id[:20]}... != {new_client_id[:20]}...). Force re-auth.")
                except Exception:
                    pass

        creds = cls.get_valid_credentials(token_path, json_path)
        if not creds:
            creds = cls.authenticate(json_path, token_path, profile=profile)

        profile.token_path = str(token_path)
        profile.save()
        return creds

    @classmethod
    def get_channel_info(cls, creds: Credentials) -> dict:
        """
        Lay thong tin kênh YouTube cua user da auth.
        Returns: dict voi keys: id, title, description, thumbnail_url, subscriber_count
        """
        channels = cls.get_all_channels(creds)
        return channels[0] if channels else {}

    @classmethod
    def get_all_channels(cls, creds: Credentials) -> list:
        """
        Lay TAT CA kênh YouTube tren tai khoan Google da auth.
        Returns: list cac dict channel info
        """
        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(
            part="snippet,statistics",
            mine=True,
            maxResults=50
        ).execute()

        channels = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            default_thumb = thumbnails.get("default", {})
            channels.append({
                "id": item["id"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "thumbnail_url": default_thumb.get("url", ""),
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "view_count": int(stats.get("viewCount", 0)),
            })
        return channels

    @classmethod
    def get_channel_analytics(cls, profile) -> dict:
        """Get analytics data for a profile's selected channel."""
        from pathlib import Path as _Path
        json_path = cls.resolve_json_path(profile.json_api_path)
        token_path = _Path(profile.token_path) if profile.token_path and _Path(profile.token_path).exists() else (BASE_DIR / "tokens" / f"token_{profile.id}.json")
        creds = cls.get_valid_credentials(token_path, json_path)
        if not creds:
            return {}

        youtube = build("youtube", "v3", credentials=creds)

        ch = youtube.channels().list(part="snippet,statistics,contentDetails", id=profile.channel_id).execute()
        channel_info = {}
        if ch.get("items"):
            item = ch["items"][0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            thumbs = snippet.get("thumbnails", {})
            channel_info = {
                "id": item["id"],
                "title": snippet.get("title", ""),
                "thumbnail": (thumbs.get("default", {}) or {}).get("url", ""),
                "subscriberCount": int(stats.get("subscriberCount", 0)),
                "videoCount": int(stats.get("videoCount", 0)),
                "viewCount": int(stats.get("viewCount", 0)),
            }

        videos = []
        if ch.get("items"):
            uploads_id = ch["items"][0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
            if uploads_id:
                playlist = youtube.playlistItems().list(part="snippet", playlistId=uploads_id, maxResults=20).execute()
                video_ids = [item["snippet"]["resourceId"]["videoId"] for item in playlist.get("items", [])]
                if video_ids:
                    vids = youtube.videos().list(part="snippet,statistics", id=",".join(video_ids)).execute()
                    for v in vids.get("items", []):
                        vs = v.get("snippet", {})
                        vst = v.get("statistics", {})
                        vth = vs.get("thumbnails", {})
                        videos.append({
                            "id": v["id"],
                            "title": vs.get("title", ""),
                            "thumbnail": (vth.get("default", {}) or {}).get("url", ""),
                            "publishedAt": vs.get("publishedAt", ""),
                            "viewCount": int(vst.get("viewCount", 0)),
                            "likeCount": int(vst.get("likeCount", 0)),
                            "commentCount": int(vst.get("commentCount", 0)),
                        })

        return {"channel": channel_info, "videos": videos}

    @classmethod
    def quick_connect(cls, profile) -> dict:
        """
        Toan bo quy trinh: auth + lay channel info.
        Tra ve dict channel info de hien thi tren UI.
        """
        creds = cls.authenticate_profile(profile)
        channels = cls.get_all_channels(creds)
        info = channels[0] if channels else {}

        if info:
            profile.channel_id = info["id"]
            profile.channel_title = info["title"]
            profile.channel_avatar = info.get("thumbnail_url", "")
            profile.subscriber_count = info.get("subscriber_count", 0)
            profile.is_active = True
            from datetime import datetime
            import json as _json
            profile.last_auth_at = datetime.now()
            # Luu danh sach tat ca kênh (de chuyen doi)
            profile.channels_json = _json.dumps(channels, ensure_ascii=False)
            profile.save()

        return info
