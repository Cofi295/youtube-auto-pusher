"""
core/cache_manager.py
=====================
Quản lý vòng đời file cache theo từng Profile.

Nguyên tắc bất di bất dịch:
  - KHÔNG BAO GIỜ dùng file gốc của người dùng trực tiếp.
  - Mọi video kéo vào → copy sang ./cache/{profile_id}/{timestamp}_{filename}.
  - Sau khi upload thành công → xóa file cache ngay lập tức.
"""

import shutil
import os
import uuid
from pathlib import Path


class CacheManager:
    """
    CacheManager — quản lý thao tác file trong thư mục cache của từng profile.

    Mỗi instance gắn với một profile_id cụ thể.
    """

    # Giới hạn dung lượng cache (byte) — đọc từ .env hoặc mặc định 5GB
    CACHE_LIMIT_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB

    def __init__(self, profile_id: int, base_dir: Path):
        """
        Args:
            profile_id: ID của profile (dùng tên thư mục)
            base_dir  : Thư mục gốc của project (chứa ./cache)
        """
        self.profile_id = profile_id
        self.cache_dir  = base_dir / "cache" / str(profile_id)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────
    # COPY — Nhận file gốc, trả về đường dẫn cache
    # ──────────────────────────────────────────

    def copy_to_cache(self, source_path: str | Path) -> Path:
        """
        Copy file video từ nguồn vào thư mục cache của profile.

        Tên file cache = {unix_timestamp}_{original_filename}
        (tránh trùng tên nếu user kéo nhiều file cùng tên)

        Args:
            source_path: Đường dẫn gốc của file video người dùng kéo vào

        Returns:
            Path: Đường dẫn file trong cache

        Raises:
            FileNotFoundError: Nếu file nguồn không tồn tại
            ValueError       : Nếu vượt quá giới hạn cache
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"File không tồn tại: {source}")

        # Kiểm tra giới hạn cache trước khi copy
        file_size        = source.stat().st_size
        current_usage    = self.get_cache_size_bytes()
        if current_usage + file_size > self.CACHE_LIMIT_BYTES:
            raise ValueError(
                f"Cache đầy! Hiện tại: {self._fmt_bytes(current_usage)}, "
                f"file cần thêm: {self._fmt_bytes(file_size)}, "
                f"giới hạn: {self._fmt_bytes(self.CACHE_LIMIT_BYTES)}"
            )

        # Tạo tên file unique (uuid đảm bảo không trùng kể cả cùng timestamp + cùng tên)
        safe_filename  = f"{uuid.uuid4().hex[:12]}_{source.name}"
        dest_path      = self.cache_dir / safe_filename

        # shutil.copy2 giữ nguyên metadata (ngày tạo, sửa)
        shutil.copy2(str(source), str(dest_path))
        print(f"[Cache] Đã copy: {source.name} → {dest_path}")
        return dest_path

    # ──────────────────────────────────────────
    # DELETE — Xóa file cache sau khi upload xong
    # ──────────────────────────────────────────

    def delete(self, cached_path: str | Path) -> bool:
        """
        Xóa một file khỏi cache (gọi sau khi YouTube báo Success).

        Args:
            cached_path: Đường dẫn file trong cache cần xóa

        Returns:
            True nếu xóa thành công, False nếu file không tồn tại.
        """
        target = Path(cached_path)
        if target.exists() and target.is_file():
            target.unlink()
            print(f"[Cache] Đã xóa: {target.name}")
            return True
        print(f"[Cache] File không tồn tại, bỏ qua: {target}")
        return False

    # ──────────────────────────────────────────
    # STATS — Tính dung lượng cache
    # ──────────────────────────────────────────

    def get_cache_size_bytes(self) -> int:
        """Tổng dung lượng cache của profile này (bytes)."""
        if not self.cache_dir.exists():
            return 0
        return sum(f.stat().st_size for f in self.cache_dir.rglob("*") if f.is_file())

    def get_cache_size_gb(self) -> float:
        """Tổng dung lượng cache (GB), làm tròn 2 chữ số."""
        return round(self.get_cache_size_bytes() / (1024 ** 3), 2)

    def get_usage_ratio(self) -> float:
        """Tỉ lệ sử dụng cache (0.0 → 1.0)."""
        return min(self.get_cache_size_bytes() / self.CACHE_LIMIT_BYTES, 1.0)

    def list_files(self) -> list[Path]:
        """Liệt kê tất cả file trong cache của profile."""
        if not self.cache_dir.exists():
            return []
        return sorted(self.cache_dir.iterdir())

    # ──────────────────────────────────────────
    # GLOBAL STATS — Tổng cache toàn hệ thống
    # ──────────────────────────────────────────

    @staticmethod
    def get_global_cache_bytes(base_dir: Path) -> int:
        """Tính tổng dung lượng cache của TOÀN BỘ profiles."""
        cache_root = base_dir / "cache"
        if not cache_root.exists():
            return 0
        return sum(f.stat().st_size for f in cache_root.rglob("*") if f.is_file())

    @staticmethod
    def get_global_cache_gb(base_dir: Path) -> float:
        """Tổng cache toàn hệ thống (GB)."""
        return round(CacheManager.get_global_cache_bytes(base_dir) / (1024 ** 3), 2)

    # ──────────────────────────────────────────
    # UTILS
    # ──────────────────────────────────────────

    @staticmethod
    def _fmt_bytes(size: int) -> str:
        """Format bytes thành chuỗi dễ đọc."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
