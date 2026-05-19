"""
main.py
=======
Entry point cua OpenClaw-Bridge Desktop App.

FIX:
  FloatingChatWidget khong con duoc them vao ft.Stack (se chan click).
  Thay vao do: dung chat_widget.mount_to_page() sau khi page.add() chay xong.
  => page.overlay approach: widget float len tren MA KHONG chan click phia duoi.
"""

import sys
import io
import asyncio
import atexit
import flet as ft
from dotenv import load_dotenv
from pathlib import Path

# Flet 0.85 bỏ helper ft.padding.symmetric/all/only; project cũ dùng API này nhiều.
# Patch tương thích để app chạy được trên Flet mới mà không phải sửa hàng chục chỗ UI.
if not hasattr(ft.padding, "symmetric"):
    ft.padding.symmetric = lambda horizontal=0, vertical=0: ft.Padding(horizontal, vertical, horizontal, vertical)
if not hasattr(ft.padding, "all"):
    ft.padding.all = lambda value=0: ft.Padding(value, value, value, value)
if not hasattr(ft.padding, "only"):
    ft.padding.only = lambda left=0, top=0, right=0, bottom=0: ft.Padding(left, top, right, bottom)
if not hasattr(ft.border, "all"):
    ft.border.all = lambda width=1, color=None: ft.Border(
        ft.BorderSide(width, color), ft.BorderSide(width, color),
        ft.BorderSide(width, color), ft.BorderSide(width, color)
    )
if not hasattr(ft.border, "only"):
    ft.border.only = lambda left=None, top=None, right=None, bottom=None: ft.Border(
        top or ft.BorderSide(0, "transparent"),
        right or ft.BorderSide(0, "transparent"),
        bottom or ft.BorderSide(0, "transparent"),
        left or ft.BorderSide(0, "transparent"),
    )
if not hasattr(ft.border_radius, "only"):
    ft.border_radius.only = lambda top_left=0, top_right=0, bottom_left=0, bottom_right=0: ft.BorderRadius(
        top_left, top_right, bottom_left, bottom_right
    )
if not hasattr(ft.border_radius, "all"):
    ft.border_radius.all = lambda value=0: ft.BorderRadius(value, value, value, value)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv()

from core.database import DatabaseManager
from core.cache_manager import CacheManager
from core.oauth_helper import OAuthHelper
from ui.components import CacheSidebar, FloatingChatWidget
from ui.components import (
    COLOR_BG_DARK, COLOR_BORDER, COLOR_ACCENT, CACHE_LIMIT_GB,
    COLOR_TEXT_MAIN, COLOR_TEXT_SUB,
)
from ui.views import DashboardView

BASE_DIR = Path(__file__).resolve().parent


def main(page: ft.Page):
    # ── 1. Page config ──
    page.title             = "YouTube Auto Pusher"
    page.theme_mode        = ft.ThemeMode.DARK
    page.bgcolor           = COLOR_BG_DARK
    page.padding           = 0
    page.fonts             = {
        "Inter": (
            "https://fonts.gstatic.com/s/inter/v13/"
            "UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiJ-Ek-_EeA.woff2"
        )
    }
    page.theme             = ft.Theme(font_family="Inter")
    page.window.width      = 1340
    page.window.height     = 820
    page.window.min_width  = 1000
    page.window.min_height = 680
    page.window.prevent_close = True  # minimize to tray, khong dong app

    # ── 2. Show splash screen (co logo + loading) ──
    splash_icon = ft.Icon(ft.Icons.VIDEO_LIBRARY, size=64, color=COLOR_ACCENT)
    splash_title = ft.Text("YouTube Auto Pusher", size=22, weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN)
    splash_ver = ft.Text("V1.0 by OCIF", size=12, color=COLOR_TEXT_SUB)
    spinner = ft.ProgressRing(width=32, height=32, color=COLOR_ACCENT)
    load_status = ft.Text("Dang khoi dong...", size=13, color=COLOR_TEXT_SUB)
    loading_view = ft.Container(
        content=ft.Column([splash_icon, ft.Container(height=8), splash_title, splash_ver,
                           ft.Container(height=20), spinner, ft.Container(height=10), load_status],
                          horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        alignment=ft.Alignment(0, 0), expand=True, bgcolor=COLOR_BG_DARK,
    )

    # ── 3. Build UI ngay lap tuc + init background ──
    dashboard = DashboardView(
        page=page,
        on_cache_change=None,
        on_chrome_count_change=None,
    )
    content_slot = ft.Container(content=loading_view, expand=True)

    def _make_placeholder(title: str, icon) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [ft.Icon(icon, size=64, color=f"{COLOR_ACCENT}66"),
                 ft.Text(title, size=24, weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN),
                 ft.Text("Tinh nang dang phat trien...", size=14, color=COLOR_TEXT_SUB)],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16,
            ), expand=True, bgcolor=COLOR_BG_DARK, alignment=ft.Alignment(0, 0),
        )

    VIEW_MAP = {"/dashboard": dashboard, "/channels": dashboard,
        "/schedule": _make_placeholder("Lich Dang", ft.Icons.CALENDAR_MONTH),
        "/telegram": _make_placeholder("Cai Dat Telegram", ft.Icons.SEND),
        "/settings": _make_placeholder("Cai Dat He Thong", ft.Icons.SETTINGS)}

    def on_navigate(route: str):
        sidebar.active_route = route
        content_slot.content = VIEW_MAP.get(route, dashboard)
        try: page.update()
        except: pass

    sidebar = CacheSidebar(active_route="/channels", on_navigate=on_navigate)
    chat_widget = FloatingChatWidget(page)

    page.add(ft.Row([sidebar, ft.VerticalDivider(width=1, color=COLOR_BORDER), content_slot], expand=True, spacing=0))
    chat_widget.mount_to_page()
    try: page.update()
    except: pass

    # ── 4. Init backend + first-run trong background ──
    async def _init_all():
        import asyncio
        try: load_status.value = "Dang ket noi database..."; page.update()
        except: pass
        DatabaseManager.initialize()

        try: load_status.value = "Dang kiem tra Chrome..."; page.update()
        except: pass
        await asyncio.sleep(0.05)
        try:
            from core.chrome_manager import migrate_existing_profiles
            migrate_existing_profiles(BASE_DIR)
        except Exception as ex:
            print(f"[App] Chrome migrate warning: {ex}")

        try: load_status.value = "Dang khoi dong scheduler..."; page.update()
        except: pass
        await asyncio.sleep(0.05)
        try:
            from core.scheduler import TaskScheduler
            TaskScheduler.start()
        except Exception as ex:
            print(f"[App] Scheduler warning: {ex}")

        # Wire callbacks
        def refresh_cache():
            try: sidebar.refresh_cache(CacheManager.get_global_cache_gb(BASE_DIR), CACHE_LIMIT_GB)
            except: pass
        def refresh_chrome_count(count: int):
            try: sidebar.refresh_chrome_count(count)
            except: pass

        dashboard.on_cache_change = refresh_cache
        dashboard.on_chrome_count_change = refresh_chrome_count
        refresh_cache()

        # Show dashboard
        content_slot.content = dashboard
        try: page.update()
        except: pass

        # First-run check
        try:
            profiles = DatabaseManager.get_all_profiles()
            if not profiles:
                from ui.setup_wizard import SetupWizard
                def on_wizard_done():
                    dashboard.refresh()
                    refresh_cache()
                wizard = SetupWizard(page, on_complete=on_wizard_done)
                wizard.show()
        except Exception as ex:
            print(f"[App] First-run check warning: {ex}")

    page.run_task(_init_all)

    # ── 9. Graceful shutdown (atexit) + minimize-to-tray ──
    def _shutdown():
        """Cleanup khi app thuc su thoat (kill process)."""
        try:
            from core.chrome_manager import ChromeManager
            ChromeManager.close_all()
        except Exception:
            pass
        try:
            from core.scheduler import TaskScheduler
            TaskScheduler.shutdown()
        except Exception:
            pass
        try:
            DatabaseManager.close()
        except Exception:
            pass

    atexit.register(_shutdown)

    def on_window_event(e):
        if e.data == "close":
            # Minimize xuong taskbar thay vi dong app
            page.window.minimized = True

    page.window.on_event = on_window_event


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
