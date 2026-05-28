"""
core/chrome_manager.py
======================
ChromeManager -- quan ly Chrome profile doc lap cho tung kenh YouTube.

Nguyen tac thiet ke:
  - Moi Profile co 1 thu muc `chrome_data/` rieng biet.
  - Chrome duoc launch voi `--user-data-dir` tro vao thu muc do.
  - Cookie, Session, LocalStorage hoan toan TACH BIET giua cac profile.
  - Ho tro: mo Chrome, kiem tra Chrome dang chay, dong Chrome, export/import cookie.

Cach hoat dong:
  - Dung subprocess.Popen de launch Chrome (non-blocking).
  - Giu process handle de kiem tra / dong sau nay.
  - Windows: tu dong tim duong dan Chrome qua registry hoac cac vi tri mac dinh.
"""

import os
import json
import shutil
import subprocess
import threading
import winreg
from pathlib import Path
from typing import Optional, Callable


# ──────────────────────────────────────────
# CHROME PATH DETECTION — Tim Chrome tren Windows
# ──────────────────────────────────────────

CHROME_REGISTRY_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
]

CHROME_DEFAULT_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
]


def find_chrome_path() -> Optional[str]:
    """
    Tim duong dan Chrome tren Windows.
    Thu tu uu tien:
      1. Bien moi truong CHROME_PATH (cho phep user override)
      2. Windows Registry
      3. Duong dan mac dinh pho bien

    Returns:
        Duong dan tuyet doi den chrome.exe, hoac None neu khong tim thay.
    """
    # 1. Environment variable override
    env_path = os.getenv("CHROME_PATH", "")
    if env_path and Path(env_path).exists():
        return env_path

    # 2. Registry
    for key_path in CHROME_REGISTRY_KEYS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                path, _ = winreg.QueryValueEx(key, "")
                if path and Path(path).exists():
                    return path
        except (FileNotFoundError, OSError):
            continue

    # 3. Default paths
    for path in CHROME_DEFAULT_PATHS:
        if Path(path).exists():
            return path

    return None


# ──────────────────────────────────────────
# CHROME INSTANCE — Quan ly 1 phien Chrome
# ──────────────────────────────────────────

class ChromeInstance:
    """
    Dai dien cho mot phien Chrome dang chay cua mot Profile.
    Luu giu process handle de kiem tra / dong.
    """

    def __init__(self, profile_id: int, process: subprocess.Popen, user_data_dir: Path):
        self.profile_id   = profile_id
        self.process      = process
        self.user_data_dir = user_data_dir

    @property
    def is_running(self) -> bool:
        """Kiem tra Chrome process con dang chay khong."""
        return self.process.poll() is None

    def close(self):
        """Dong Chrome an toan (SIGTERM -> SIGKILL)."""
        if self.is_running:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

    def __repr__(self):
        status = "RUNNING" if self.is_running else "CLOSED"
        return f"ChromeInstance(profile_id={self.profile_id}, status={status})"


# ──────────────────────────────────────────
# CHROME MANAGER — Orchestrator chinh
# ──────────────────────────────────────────

class ChromeManager:
    """
    ChromeManager -- singleton quan ly tat ca phien Chrome cua cac Profile.

    Moi Profile co the mo Chrome rieng cung luc, hoan toan doc lap.
    ChromeManager theo doi toan bo va dam bao dong sach khi tat app.

    Thread-safe: dung Lock de bao ve _instances dict.
    """

    _instances: dict[int, ChromeInstance] = {}
    _lock = threading.Lock()

    # ──────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────

    @classmethod
    def launch(
        cls,
        profile,                          # Profile model instance
        start_url: str = "https://studio.youtube.com",
        on_close: Optional[Callable] = None,
        extra_args: list[str] = None,
    ) -> ChromeInstance:
        """
        Mo Chrome voi user-data-dir rieng cua profile.

        Args:
            profile   : Profile model instance (co .chrome_data_dir)
            start_url : URL mo khi khoi dong (mac dinh: YouTube Studio)
            on_close  : Callback khi Chrome dong (chay trong daemon thread)
            extra_args: Tham so Chrome bo sung

        Returns:
            ChromeInstance dang chay

        Raises:
            FileNotFoundError: Neu khong tim thay Chrome
            RuntimeError     : Neu profile da co Chrome dang chay
        """
        # Kiem tra Chrome path
        chrome_path = find_chrome_path()
        if not chrome_path:
            raise FileNotFoundError(
                "Khong tim thay Chrome! Hay cai dat Chrome hoac dat bien moi truong CHROME_PATH."
            )

        with cls._lock:
            # Neu Chrome cua profile nay da chay -> khong mo them
            existing = cls._instances.get(profile.id)
            if existing and existing.is_running:
                raise RuntimeError(
                    f"Chrome cua '{profile.name}' da dang mo. "
                    "Hay dong phien cu truoc khi mo lai."
                )

        # Dam bao thu muc ton tai
        profile.chrome_data_dir.mkdir(parents=True, exist_ok=True)

        # Xay dung tham so Chrome
        args = cls._build_chrome_args(
            chrome_path=chrome_path,
            user_data_dir=profile.chrome_data_dir,
            profile_name=profile.chrome_profile_name or f"Profile_{profile.id}",
            start_url=start_url,
            extra_args=extra_args or [],
        )

        print(f"[Chrome] Mo profile '{profile.name}' -> {profile.chrome_data_dir}")
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        instance = ChromeInstance(
            profile_id=profile.id,
            process=process,
            user_data_dir=profile.chrome_data_dir,
        )

        with cls._lock:
            cls._instances[profile.id] = instance

        # Kiem tra vong doi process trong daemon thread
        if on_close:
            threading.Thread(
                target=cls._watch_process,
                args=(instance, on_close),
                daemon=True,
                name=f"chrome_watch_{profile.id}",
            ).start()

        return instance

    @classmethod
    def close(cls, profile_id: int) -> bool:
        """
        Dong Chrome cua mot profile cu the.

        Returns:
            True neu dong thanh cong, False neu khong co phien nao chay.
        """
        with cls._lock:
            instance = cls._instances.get(profile_id)

        if instance and instance.is_running:
            instance.close()
            print(f"[Chrome] Da dong profile_id={profile_id}")
            with cls._lock:
                cls._instances.pop(profile_id, None)
            return True
        return False

    @classmethod
    def is_running(cls, profile_id: int) -> bool:
        """Kiem tra Chrome cua profile co dang chay khong."""
        with cls._lock:
            instance = cls._instances.get(profile_id)
        return bool(instance and instance.is_running)

    @classmethod
    def close_all(cls):
        """Dong TAT CA phien Chrome (goi khi tat app)."""
        with cls._lock:
            ids = list(cls._instances.keys())
        for profile_id in ids:
            cls.close(profile_id)
        print("[Chrome] Da dong tat ca phien Chrome.")

    @classmethod
    def get_status(cls) -> dict[int, bool]:
        """Tra ve dict {profile_id: is_running} cho tat ca instances."""
        with cls._lock:
            return {pid: inst.is_running for pid, inst in cls._instances.items()}

    @classmethod
    def open_url(cls, profile, url: str) -> bool:
        """
        Mo URL bang dung Chrome user-data-dir cua profile.
        Neu Chrome profile dang mo, Chrome se reuse session/profile hien tai va mo tab moi.
        """
        try:
            chrome_path = find_chrome_path()
            if not chrome_path:
                return False
            profile.chrome_data_dir.mkdir(parents=True, exist_ok=True)
            args = cls._build_chrome_args(
                chrome_path=chrome_path,
                user_data_dir=profile.chrome_data_dir,
                profile_name=profile.chrome_profile_name or f"Profile_{profile.id}",
                start_url=url,
                extra_args=[],
            )
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[Chrome] open_url error: {e}")
            return False

    # ──────────────────────────────────────────
    # COOKIE MANAGEMENT
    # ──────────────────────────────────────────

    @classmethod
    def export_cookies_note(cls, profile) -> str:
        """
        Ghi chu huong dan export cookie thu cong.

        Chrome ma hoa cookie bang DPAPI nen khong the doc truc tiep.
        Cach chinh xac nhat: dung extension "Cookie-Editor" de export JSON.

        Returns:
            Duong dan file cookies.json se luu vao.
        """
        note = {
            "huong_dan": (
                "Chrome ma hoa cookie bang Windows DPAPI. "
                "De export cookie, hay dung extension 'Cookie-Editor' (https://cookie-editor.com/), "
                "sau do export JSON va luu vao file nay."
            ),
            "profile_id":        profile.id,
            "profile_name":      profile.name,
            "chrome_data_dir":   str(profile.chrome_data_dir),
            "cookies_file":      str(profile.cookies_export_path),
        }
        profile.cookies_export_path.parent.mkdir(parents=True, exist_ok=True)
        profile.cookies_export_path.write_text(
            json.dumps(note, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return str(profile.cookies_export_path)

    @classmethod
    def get_chrome_data_size_mb(cls, profile) -> float:
        """Tinh dung luong thu muc chrome_data (MB)."""
        return round(profile.get_chrome_data_size_bytes() / (1024 * 1024), 2)

    @classmethod
    def reset_chrome_data(cls, profile) -> bool:
        """
        Xoa sach du lieu Chrome cua profile (cookie, cache, session...).
        CANH BAO: Hanh dong nay xoa toan bo phien dang nhap!

        Returns:
            True neu xoa thanh cong.
        """
        if cls.is_running(profile.id):
            cls.close(profile.id)

        folder = profile.chrome_data_dir
        if folder.exists():
            shutil.rmtree(folder)
            folder.mkdir(parents=True, exist_ok=True)
            print(f"[Chrome] Da reset data cho profile '{profile.name}'")
            return True
        return False

    # ──────────────────────────────────────────
    # INTERNAL
    # ──────────────────────────────────────────

    @staticmethod
    def _build_chrome_args(
        chrome_path: str,
        user_data_dir: Path,
        profile_name: str,
        start_url: str,
        extra_args: list[str],
    ) -> list[str]:
        """
        Xay dung danh sach tham so launch Chrome.

        Tham so quan trong:
          --user-data-dir : Thu muc rieng chua toan bo du lieu Chrome
          --profile-directory: Ten sub-profile trong user-data-dir
          --no-first-run  : Bo qua man hinh chao dau tien
          --no-default-browser-check: Khong hoi dat lam trinh duyet mac dinh
        """
        args = [
            chrome_path,
            f"--user-data-dir={user_data_dir}",
            f"--profile-directory={profile_name}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",              # Tat dong bo Google Account (tranh lo du lieu)
            "--disable-background-networking",  # Giam tai nguyen
            *extra_args,
            start_url,
        ]
        return args

    @staticmethod
    def _watch_process(instance: ChromeInstance, on_close: Callable):
        """Watch Chrome process va goi callback khi dong."""
        instance.process.wait()
        print(f"[Chrome] Profile {instance.profile_id} da dong.")
        on_close(instance.profile_id)


# ──────────────────────────────────────────
# MIGRATION HELPER — Cap nhat Profile cu (khong co Chrome)
# ──────────────────────────────────────────

def migrate_existing_profiles(base_dir: Path):
    """
    Quet Profile cu chua co chrome_data_dir -> tao thu muc cho chung.
    Goi 1 lan khi khoi dong app.
    """
    from core.database import Profile
    profiles = list(Profile.select())
    migrated = 0
    for p in profiles:
        if not p.chrome_data_dir.exists():
            p.chrome_data_dir.mkdir(parents=True, exist_ok=True)
            if not p.chrome_profile_name:
                p.chrome_profile_name = f"Profile_{p.id}"
                p.save()
            migrated += 1

    if migrated:
        print(f"[Chrome] Da migrate {migrated} profile cu -> tao chrome_data/")
