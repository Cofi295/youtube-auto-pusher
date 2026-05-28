"""
core/database.py
================
Định nghĩa toàn bộ Schema cơ sở dữ liệu SQLite thông qua Peewee ORM.

Nguyên tắc thiết kế:
  - Single-file SQLite để dễ deploy, không cần server.
  - Cascade delete: Xóa Profile → tự động xóa Task liên quan.
  - Enum-style trạng thái Task qua STATUS_* constants.
"""
import os
import sys
import json
import shutil
import datetime
from pathlib import Path
from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    TextField,
    DateTimeField,
    IntegerField,
    BooleanField,
    ForeignKeyField,
    AutoField,
)

# ──────────────────────────────────────────
# 1. DATABASE CONNECTION
# ──────────────────────────────────────────

# Data directory. In dev, use project root.
# In packaged PyInstaller builds, use the EXE's own directory.
# The YTAP_DATA_DIR env var can always override both.
if getattr(sys, 'frozen', False):
    _default_dir = Path(sys.executable).resolve().parent
else:
    _default_dir = Path(__file__).resolve().parent.parent
BASE_DIR = Path(os.environ.get("YTAP_DATA_DIR", _default_dir))
BASE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH  = BASE_DIR / "openclaw_bridge.db"

db = SqliteDatabase(
    str(DB_PATH),
    pragmas={
        "journal_mode": "wal",   # Write-Ahead Logging: tránh lock khi đọc/ghi đồng thời
        "cache_size":   -64 * 1024,  # 64 MB cache
        "foreign_keys": 1,       # Bắt buộc FK constraints
    },
)

# ──────────────────────────────────────────
# 2. BASE MODEL (chia sẻ chung database)
# ──────────────────────────────────────────

class BaseModel(Model):
    """BaseModel: tất cả model kế thừa class này để dùng chung `db`."""
    class Meta:
        database = db


# ──────────────────────────────────────────
# 3. PROFILE MODEL — Lưu thông tin kênh YouTube
# ──────────────────────────────────────────

class Profile(BaseModel):
    """
    Bang `profiles` -- luu thong tin mot kenh YouTube.

    Fields:
        id                : Primary key tu tang
        name              : Ten hien thi cua kenh (vi du: "Kenh Game 1")
        channel_id        : YouTube Channel ID (UC...)
        channel_title     : Ten kenh chinh thuc tu YouTube API
        channel_avatar    : URL avatar kenh tu YouTube API
        subscriber_count  : So nguoi theo doi kenh
        last_auth_at      : Thoi diem xac thuc OAuth gan nhat
        json_api_path     : Duong dan tuyet doi den file client_secret.json
        token_path        : Duong dan den file token OAuth credentials
        chrome_profile_name: Ten Chrome profile (vi du: "Profile_1")
        is_active         : True neu ket noi API dang hoat dong
        chrome_active     : True neu Chrome profile dang mo
        created_at        : Thoi diem tao profile
    """
    id                  = AutoField()
    name                = CharField(max_length=120, unique=True)
    channel_id          = CharField(max_length=64, default="")
    channel_title       = CharField(max_length=200, default="")   # Ten kenh tu YouTube API
    channel_avatar      = CharField(max_length=512, default="")   # URL avatar kenh
    subscriber_count    = IntegerField(default=0)                  # So nguoi theo doi
    last_auth_at        = DateTimeField(null=True)                 # Lan auth gan nhat
    json_api_path       = CharField(max_length=512, default="")
    token_path          = CharField(max_length=512, default="")
    chrome_profile_name = CharField(max_length=64, default="")   # "Profile_1", "Profile_2"...
    is_active           = BooleanField(default=False)
    chrome_active       = BooleanField(default=False)             # Chrome dang chay khong
    channels_json       = TextField(default="")                   # JSON list cac kenh YouTube
    created_at          = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "profiles"

    # ── Directory Paths ──

    @property
    def cache_dir(self) -> Path:
        """Thu muc video cache rieng cua profile."""
        return BASE_DIR / "cache" / str(self.id)

    @property
    def chrome_data_dir(self) -> Path:
        """
        Thu muc Chrome User Data rieng cua profile.
        Chrome dung thu muc nay de luu: cookie, session, localStorage, history...
        Moi profile = mot thu muc doc lap = hoan toan tach biet.
        """
        return BASE_DIR / "profiles" / str(self.id) / "chrome_data"

    @property
    def cookies_export_path(self) -> Path:
        """File JSON backup cookie thu cong."""
        return BASE_DIR / "profiles" / str(self.id) / "cookies.json"

    @property
    def profile_config_path(self) -> Path:
        """File config meta cua profile."""
        return BASE_DIR / "profiles" / str(self.id) / "config.json"

    # ── Cleanup ──

    def delete_cache_folder(self):
        """Xoa sach folder cache VIDEO cua profile truoc khi xoa record."""
        folder = self.cache_dir
        if folder.exists():
            shutil.rmtree(folder)

    def delete_chrome_profile(self):
        """Xoa sach thu muc Chrome (cookie, session) khi xoa profile."""
        folder = BASE_DIR / "profiles" / str(self.id)
        if folder.exists():
            shutil.rmtree(folder)

    # ── Stats ──

    def get_cache_size_bytes(self) -> int:
        """Tinh tong dung luong file VIDEO trong cache (bytes)."""
        folder = self.cache_dir
        if not folder.exists():
            return 0
        return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())

    def get_chrome_data_size_bytes(self) -> int:
        """Tinh dung luong thu muc Chrome (cookie + cache browser) (bytes)."""
        folder = self.chrome_data_dir
        if not folder.exists():
            return 0
        return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())

    def save_config(self, extra: dict = None):
        """Luu file config.json kem metadata profile."""
        import json as _json
        data = {
            "profile_id":          self.id,
            "name":                self.name,
            "chrome_profile_name": self.chrome_profile_name,
            "chrome_data_dir":     str(self.chrome_data_dir),
            "created_at":          str(self.created_at),
        }
        if extra:
            data.update(extra)
        self.profile_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile_config_path.write_text(_json.dumps(data, indent=2, ensure_ascii=False))

    def __str__(self):
        return f"Profile(id={self.id}, name={self.name})"


# ──────────────────────────────────────────
# 4. TASK MODEL — Metadata video cần upload
# ──────────────────────────────────────────

# Trạng thái hợp lệ cho một Task
STATUS_PENDING   = "Pending"
STATUS_RUNNING   = "Running"
STATUS_COMPLETED = "Completed"
STATUS_FAILED    = "Failed"

VALID_STATUSES = [STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED]


class Task(BaseModel):
    """
    Bảng `tasks` — lưu metadata video và trạng thái upload.

    Fields:
        id            : Primary key tự tăng
        profile       : FK → Profile (cascade delete)
        title         : Tiêu đề video
        description   : Mô tả video
        tags          : Danh sách tags (JSON string)
        hashtags      : Danh sách hashtag
        cached_path   : Đường dẫn video trong ./cache/{profile_id}/
        thumbnail_path: (Optional) đường dẫn ảnh thumbnail
        schedule_time : Thời điểm lên lịch đăng (UTC)
        timezone      : Múi giờ gốc người dùng chọn (ví dụ: "Asia/Ho_Chi_Minh")
        status        : Pending | Running | Completed | Failed
        youtube_url   : URL video sau khi upload thành công
        error_message : Ghi log lỗi nếu upload thất bại
        created_at    : Thời điểm tạo task
        updated_at    : Thời điểm cập nhật gần nhất
    """
    id             = AutoField()
    profile        = ForeignKeyField(Profile, backref="tasks", on_delete="CASCADE")
    title          = CharField(max_length=256)
    description    = TextField(default="")
    tags           = TextField(default="")      # JSON: ["tag1", "tag2"]
    hashtags       = TextField(default="")      # "#game #vlog"
    made_for_kids  = BooleanField(default=False) # YouTube audience: made for kids
    paid_promotion = BooleanField(default=False) # Contains paid promotion/product placement
    altered_content = BooleanField(default=False) # Altered/synthetic content disclosure
    retry_count    = IntegerField(default=0)        # Auto-retry count (max 3)
    cached_path    = CharField(max_length=512, default="")
    thumbnail_path = CharField(max_length=512, default="")
    schedule_time  = DateTimeField(null=True)
    timezone       = CharField(max_length=64, default="Asia/Ho_Chi_Minh")
    status         = CharField(max_length=20, default=STATUS_PENDING)
    youtube_url    = CharField(max_length=256, default="")
    error_message  = TextField(default="")
    created_at     = DateTimeField(default=datetime.datetime.now)
    updated_at     = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = "tasks"

    def mark_running(self):
        """Đổi trạng thái → Running và lưu vào DB."""
        self.status     = STATUS_RUNNING
        self.updated_at = datetime.datetime.now()
        self.save()

    def mark_completed(self, youtube_url: str):
        """Đổi trạng thái → Completed, lưu URL video."""
        self.status      = STATUS_COMPLETED
        self.youtube_url = youtube_url
        self.updated_at  = datetime.datetime.now()
        self.save()

    def mark_failed(self, error: str):
        """Đổi trạng thái → Failed, ghi lại lỗi."""
        self.status        = STATUS_FAILED
        self.error_message = error
        self.updated_at    = datetime.datetime.now()
        self.save()

    def __str__(self):
        return f"Task(id={self.id}, title={self.title[:30]}, status={self.status})"


# ──────────────────────────────────────────
# 5. DATABASE MANAGER — Khởi tạo & Helpers
# ──────────────────────────────────────────

class DatabaseManager:
    """
    DatabaseManager — lớp singleton quản lý vòng đời kết nối DB.

    Sử dụng:
        DatabaseManager.initialize()  # Gọi 1 lần khi app khởi động
        DatabaseManager.close()       # Gọi khi app tắt
    """

    _initialized = False

    @classmethod
    def initialize(cls):
        """Mo ket noi, tao bang neu chua ton tai, va migrate schema."""
        if cls._initialized:
            return
        db.connect(reuse_if_open=True)
        db.create_tables([Profile, Task], safe=True)
        cls._migrate_schema()   # <-- them cot moi cho DB cu
        cls._initialized = True
        print(f"[DB] Initialized at: {DB_PATH}")

    @classmethod
    def _migrate_schema(cls):
        """
        Schema migration an toan: ADD COLUMN neu chua ton tai.
        Chay moi lan khoi dong. SQLite bao loi neu cot da co -> ignore.

        Cac buoc migration:
          v1 -> v2: profiles.chrome_profile_name, profiles.chrome_active
          v2 -> v3: profiles.channel_title, channel_avatar, subscriber_count, last_auth_at
          v3 -> v4: tasks.made_for_kids, paid_promotion, altered_content
        """
        migrations = [
            "ALTER TABLE profiles ADD COLUMN chrome_profile_name VARCHAR(64) DEFAULT ''",
            "ALTER TABLE profiles ADD COLUMN chrome_active INTEGER DEFAULT 0",
            # v2 -> v3: OAuth channel info fields
            "ALTER TABLE profiles ADD COLUMN channel_title VARCHAR(200) DEFAULT ''",
            "ALTER TABLE profiles ADD COLUMN channel_avatar VARCHAR(512) DEFAULT ''",
            "ALTER TABLE profiles ADD COLUMN subscriber_count INTEGER DEFAULT 0",
            "ALTER TABLE profiles ADD COLUMN last_auth_at DATETIME",
            # v3 -> v4: YouTube video disclosure fields
            "ALTER TABLE tasks ADD COLUMN made_for_kids INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN paid_promotion INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN altered_content INTEGER DEFAULT 0",
            # v4 -> v5: multi-channel support
            "ALTER TABLE profiles ADD COLUMN channels_json TEXT DEFAULT ''",
            # v5 -> v6: auto-retry on upload failure
            "ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0",
        ]
        for sql in migrations:
            try:
                db.execute_sql(sql)
                print(f"[DB] Migration OK: {sql.split('ADD COLUMN')[1].strip().split()[0]}")
            except Exception:
                pass  # Cot da ton tai -> bo qua

    @classmethod
    def close(cls):
        """Đóng kết nối DB an toàn."""
        if not db.is_closed():
            db.close()
        cls._initialized = False

    # ──── PROFILE HELPERS ────

    @staticmethod
    def get_all_profiles() -> list[Profile]:
        """Trả về toàn bộ profiles, sắp xếp theo thời gian tạo (cũ nhất trước)."""
        return list(Profile.select().order_by(Profile.created_at))

    @staticmethod
    def create_profile(name: str, json_api_path: str = "", token_path: str = "") -> Profile:
        """
        Tao moi mot profile:
          1. Tao record trong DB
          2. Tao thu muc video cache
          3. Tao thu muc Chrome User Data (cookie isolation)
          4. Luu config.json
        """
        # Tao ten Chrome Profile unique: "Profile_{id}"
        profile = Profile.create(
            name=name,
            json_api_path=json_api_path,
            token_path=token_path,
        )
        # Dat ten Chrome profile sau khi co ID
        profile.chrome_profile_name = f"Profile_{profile.id}"
        profile.save()

        # Tao cac thu muc can thiet
        profile.cache_dir.mkdir(parents=True, exist_ok=True)
        profile.chrome_data_dir.mkdir(parents=True, exist_ok=True)

        # Luu config meta
        profile.save_config()
        return profile

    @staticmethod
    def delete_profile(profile_id: int):
        """
        Xoa Profile:
          0. Revoke OAuth token tren Google (de add lai chon duoc kenh moi)
          1. Đóng Chrome profile (tránh lock file)
          2. Xóa folder cache VIDEO (dữ liệu vật lý)
          3. Xóa thư mục Chrome (cookie, session)
          4. Peewee cascade-delete các Task liên quan
          5. Xóa record Profile
        """
        try:
            profile = Profile.get_by_id(profile_id)
            # Revoke token de Google khong nho session cu
            if profile.token_path:
                try:
                    import json as _json, urllib.request
                    tp = Path(profile.token_path)
                    if tp.exists():
                        token_data = _json.loads(tp.read_text())
                        refresh_token = token_data.get("refresh_token", "")
                        if refresh_token:
                            data = urllib.parse.urlencode({"token": refresh_token}).encode()
                            urllib.request.urlopen(
                                urllib.request.Request("https://oauth2.googleapis.com/revoke", data=data),
                                timeout=5
                            )
                            print(f"[DB] Đã revoke OAuth token cho profile {profile_id}")
                except Exception as e:
                    print(f"[DB] Revoke token warning: {e}")
            # Đóng Chrome trước để tránh PermissionError
            try:
                from core.chrome_manager import ChromeManager
                ChromeManager.close(profile.id)
                import time as _time
                _time.sleep(0.5)  # Cho Chrome dong hoan toan
            except Exception:
                pass
            # Xóa cache + chrome data (bỏ qua file bị khóa)
            import shutil as _shutil
            def _onerror(func, path, exc_info):
                print(f"[DB] Bỏ qua file bị khóa khi xóa: {path}")
            if hasattr(_shutil, 'onexc'):
                _shutil.rmtree(str(profile.cache_dir), onexc=_onerror) if profile.cache_dir.exists() else None
                _shutil.rmtree(str(profile.chrome_data_dir), onexc=_onerror) if profile.chrome_data_dir.exists() else None
            else:
                _shutil.rmtree(str(profile.cache_dir), onerror=_onerror) if profile.cache_dir.exists() else None
                _shutil.rmtree(str(profile.chrome_data_dir), onerror=_onerror) if profile.chrome_data_dir.exists() else None
            # Xóa luôn thư mục cha profiles/{id}/ (config.json, cookies.json, ...)
            profile_root = BASE_DIR / "profiles" / str(profile_id)
            if profile_root.exists():
                if hasattr(_shutil, 'onexc'):
                    _shutil.rmtree(str(profile_root), onexc=_onerror)
                else:
                    _shutil.rmtree(str(profile_root), onerror=_onerror)
                print(f"[DB] Đã xóa thư mục profile: {profile_root}")
            profile.delete_instance(recursive=True)
        except Profile.DoesNotExist:
            print(f"[DB] Profile {profile_id} không tồn tại.")

    # ──── TASK HELPERS ────

    @staticmethod
    def get_tasks_by_profile(profile_id: int) -> list[Task]:
        """Lấy tất cả tasks của một profile."""
        return list(Task.select().where(Task.profile == profile_id).order_by(Task.created_at.desc()))

    @staticmethod
    def get_pending_tasks() -> list[Task]:
        """Lấy tất cả tasks đang ở trạng thái Pending."""
        return list(Task.select().where(Task.status == STATUS_PENDING))

    @staticmethod
    def get_running_tasks() -> list[Task]:
        """Lấy tất cả tasks đang ở trạng thái Running."""
        return list(Task.select().where(Task.status == STATUS_RUNNING))

    @staticmethod
    def get_cache_total_bytes() -> int:
        """Tính tổng dung lượng toàn bộ cache của tất cả profiles."""
        total = 0
        cache_root = BASE_DIR / "cache"
        if cache_root.exists():
            total = sum(f.stat().st_size for f in cache_root.rglob("*") if f.is_file())
        return total
