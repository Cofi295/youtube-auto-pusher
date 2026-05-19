"""
ui/components.py
================
Cac UI component tai su dung cua OpenClaw-Bridge:
  - BoxCard           : The hien thi Profile co Chrome controls
  - ChromeBadge       : Badge Chrome dang chay / tat
  - CacheSidebar      : Sidebar voi progress bar cache
  - FloatingChatWidget: Cua so chat float (dung page.overlay, KHONG chan click)

BUG FIX:
  FloatingChatWidget truoc day la ft.Stack(expand=True) → chặn toan bo click.
  Nay chuyen sang ft.Container kich thuoc co dinh + mount vao page.overlay.
"""

import flet as ft
from typing import Callable, Optional
import threading
import tkinter as tk
from tkinter import filedialog
from ui.dialog_helper import open_dialog, close_dialog
from core.database import Profile, DatabaseManager, Task


# ══════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════

COLOR_PRIMARY    = "#4A90E2"
COLOR_SUCCESS    = "#27AE60"
COLOR_DANGER     = "#E74C3C"
COLOR_WARNING    = "#F39C12"
COLOR_CHROME     = "#4285F4"
COLOR_BG_DARK    = "#1A1D2E"
COLOR_BG_CARD    = "#252840"
COLOR_BG_SIDEBAR = "#1E2130"
COLOR_TEXT_MAIN  = "#ECEFF4"
COLOR_TEXT_SUB   = "#8892A4"
COLOR_ACCENT     = "#7C6FF7"
COLOR_BORDER     = "#2E3250"

CACHE_LIMIT_GB = 5.0

TIMEZONES = [
    "Pacific/Honolulu", "America/Anchorage", "America/Los_Angeles",
    "America/Denver", "America/Chicago", "America/New_York",
    "America/Sao_Paulo", "Atlantic/Azores", "UTC",
    "Europe/London", "Europe/Paris", "Europe/Berlin",
    "Africa/Cairo", "Europe/Moscow", "Asia/Dubai",
    "Asia/Karachi", "Asia/Kolkata", "Asia/Dhaka",
    "Asia/Bangkok", "Asia/Ho_Chi_Minh", "Asia/Shanghai",
    "Asia/Tokyo", "Asia/Seoul", "Australia/Sydney",
    "Pacific/Auckland",
]


# ══════════════════════════════════════════
# 1. STATUS BADGES
# ══════════════════════════════════════════

def StatusBadge(is_online: bool) -> ft.Container:
    """Badge API Online / Offline."""
    color = COLOR_SUCCESS if is_online else COLOR_DANGER
    label = "● API On" if is_online else "● API Off"
    return ft.Container(
        content=ft.Text(label, size=10, color=color, weight=ft.FontWeight.W_600),
        bgcolor=f"{color}22",
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )


def ChromeBadge(is_running: bool) -> ft.Container:
    """Badge Chrome dang mo / da dong."""
    color = COLOR_CHROME if is_running else COLOR_TEXT_SUB
    label = "● Chrome On" if is_running else "○ Chrome Off"
    return ft.Container(
        content=ft.Text(label, size=10, color=color, weight=ft.FontWeight.W_600),
        bgcolor=f"{color}22",
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
    )



# ══════════════════════════════════════════
# 2. BOX CARD
# ══════════════════════════════════════════

def BoxCard(
    profile: Profile,
    on_detail: Callable[[int], None],
    on_delete: Callable[[int], None],
    on_chrome_studio: Callable[[int], None],
    on_chrome_api_key: Callable[[int], None],
    on_chrome_close: Callable[[int], None],
    on_run_now: Callable[[int], None],
    page: ft.Page,
    on_refresh: Callable[[], None] | None = None,
) -> ft.Container:
    """
    BoxCard -- The hien thi 1 kenh YouTube.

    Layout:
      [Header]   Avatar | Ten kenh | Badge API | Badge Chrome
      [API Row]  icon path.json | [Chinh sua API]
      [Stats]    Chrome profile | X pending
      [Chrome]   [Dong Chrome?] | [Mo Studio] [Tao API Key]
      [Actions]  [Tasks] [Chay ngay] [Xoa kenh]
    """
    from core.chrome_manager import ChromeManager
    from pathlib import Path as _Path

    # ── Counters ──
    total_count = Task.select().where(Task.profile == profile.id).count()
    waiting_count = Task.select().where(
        (Task.profile == profile.id) & (Task.status == "Pending")
    ).count()
    completed_count = Task.select().where(
        (Task.profile == profile.id) & (Task.status == "Completed")
    ).count()
    failed_count = Task.select().where(
        (Task.profile == profile.id) & (Task.status == "Failed")
    ).count()
    running_count = Task.select().where(
        (Task.profile == profile.id) & (Task.status == "Running")
    ).count()
    runnable_count = waiting_count + failed_count

    chrome_running = ChromeManager.is_running(profile.id)
    chrome_name    = profile.chrome_profile_name or f"Profile_{profile.id}"

    # ── API path status ──
    from core.oauth_helper import OAuthHelper as _OAuthHelper

    api_path      = profile.json_api_path or ""
    api_exists    = bool(api_path) and _Path(api_path).exists()
    bundled_ok    = _OAuthHelper.is_bundled_available()
    using_bundled = not api_path and bundled_ok  # Dang dung bundled JSON

    if api_exists:
        api_display = _Path(api_path).name
        api_color   = COLOR_SUCCESS
        api_icon    = ft.Icons.CHECK_CIRCLE_OUTLINE
    elif using_bundled:
        api_display = "Bundled API (san sang ket noi)"
        api_color   = COLOR_PRIMARY
        api_icon    = ft.Icons.CLOUD_DONE_OUTLINED
    else:
        api_display = "Chua cau hinh JSON API"
        api_color   = COLOR_DANGER
        api_icon    = ft.Icons.WARNING_AMBER

    # ──── HEADER ────
    avatar = ft.Container(
        content=ft.Icon(ft.Icons.SMART_DISPLAY, color="#FF4444", size=30),
        bgcolor="#FF000022",
        border_radius=10, width=48, height=48,
        alignment=ft.Alignment(0, 0),
    )
    header = ft.Row([
        avatar,
        ft.Column([
            ft.Text(
                profile.name, size=14, weight=ft.FontWeight.W_700,
                color=COLOR_TEXT_MAIN, max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS, expand=True,
            ),
            ft.Row([StatusBadge(profile.is_active), ChromeBadge(chrome_running)], spacing=6),
        ], spacing=4, expand=True),
    ], spacing=10)

    # ──── API ROW ────
    api_row = ft.Container(
        content=ft.Row([
            ft.Icon(api_icon, color=api_color, size=13),
            ft.Text(
                api_display, size=10, color=COLOR_TEXT_SUB,
                expand=True, overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.IconButton(
                ft.Icons.EDIT_NOTE,
                icon_color=COLOR_ACCENT, icon_size=16,
                tooltip="Cấu hình / Lưu & Check API",
                on_click=lambda _: _update_api_dialog(page, profile, on_done=on_refresh),
            ),
        ], spacing=4),
        bgcolor=f"{api_color}11",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        border=ft.border.all(1, f"{api_color}33"),
    )

    # ════ STATS ROW ════
    def _mini_stat(label: str, value: int, color: str):
        return ft.Container(
            content=ft.Text(f"{label}: {value}", size=10, color=color, weight=ft.FontWeight.W_600),
            bgcolor=f"{color}18",
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=6, vertical=3),
        )

    stats_items = [
        ft.Icon(ft.Icons.MANAGE_ACCOUNTS, color=COLOR_CHROME, size=13),
        ft.Text(chrome_name, size=10, color=COLOR_TEXT_SUB, expand=True),
    ]

    stats_row = ft.Container(
        content=ft.Row(stats_items, spacing=6),
        bgcolor=COLOR_BG_DARK, border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=5),
    )

    video_status_row = ft.Container(
        content=ft.Row(
            [
                _mini_stat("Tong", total_count, COLOR_TEXT_SUB),
                _mini_stat("Dang doi", waiting_count, COLOR_WARNING),
                _mini_stat("Dang dang", running_count, COLOR_PRIMARY),
                _mini_stat("Da dang", completed_count, COLOR_SUCCESS),
                _mini_stat("Loi", failed_count, COLOR_DANGER),
            ],
            spacing=5,
            wrap=True,
        ),
        bgcolor=COLOR_BG_DARK,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
    )

    # ════ CHROME BUTTONS ════
    btn_studio = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.VIDEO_CAMERA_BACK_OUTLINED, size=13),
            ft.Text("YouTube Studio", size=11),
        ], spacing=5),
        style=ft.ButtonStyle(
            bgcolor=COLOR_CHROME, color=COLOR_TEXT_MAIN,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
        ),
        on_click=lambda _: on_chrome_studio(profile.id),
        expand=True,
        tooltip="Mo Chrome → studio.youtube.com (xem/quan ly kenh, dang thu cong)",
    )

    btn_api_key = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.VPN_KEY_OUTLINED, size=13),
            ft.Text("Tao API Key", size=11),
        ], spacing=5),
        style=ft.ButtonStyle(
            bgcolor="#E37400", color=COLOR_TEXT_MAIN,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
        ),
        on_click=lambda _: on_chrome_api_key(profile.id),
        expand=True,
        tooltip="Mo Chrome → console.cloud.google.com/apis/credentials",
    )

    chrome_section = ft.Column([], spacing=6)
    if chrome_running:
        btn_close = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=13),
                ft.Text("Dong Chrome", size=11),
            ], spacing=5),
            style=ft.ButtonStyle(
                bgcolor="#D35400", color=COLOR_TEXT_MAIN,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.padding.symmetric(horizontal=8, vertical=8),
            ),
            on_click=lambda _: on_chrome_close(profile.id),
            expand=True,
        )
        chrome_section.controls.append(ft.Row([btn_close]))
    chrome_section.controls.append(ft.Row([btn_studio, btn_api_key], spacing=6))

    # ════ BOTTOM ACTIONS ════
    btn_detail = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.LIST_ALT, size=13),
            ft.Text("Tasks", size=11),
        ], spacing=4),
        style=ft.ButtonStyle(
            bgcolor=COLOR_PRIMARY, color=COLOR_TEXT_MAIN,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
        ),
        on_click=lambda _: on_detail(profile.id),
        expand=True,
        tooltip="Xem & chinh sua danh sach video",
    )

    can_run = runnable_count > 0 or running_count == 0
    btn_run = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, size=13),
            ft.Text("Chay task toi gio", size=11),
        ], spacing=4),
        style=ft.ButtonStyle(
            bgcolor=COLOR_SUCCESS if runnable_count > 0 else f"{COLOR_SUCCESS}33",
            color=COLOR_TEXT_MAIN,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
        ),
        on_click=lambda _: on_run_now(profile.id),
        disabled=(runnable_count == 0),
        expand=True,
        tooltip=f"Chỉ chạy task đã tới giờ; task hẹn tương lai sẽ giữ nguyên" if runnable_count > 0 else "Không có task nào chờ",
    )

    btn_del = ft.IconButton(
        icon=ft.Icons.DELETE_OUTLINE,
        icon_color=COLOR_DANGER, icon_size=20,
        tooltip="Xoa kenh nay",
        on_click=lambda _: _confirm_delete(page, profile, on_delete),
    )

    action_row = ft.Row([btn_detail, btn_run, btn_del], spacing=4)

    # ════ ASSEMBLE ════
    card_content = ft.Column([
        header,
        ft.Divider(height=1, color=COLOR_BORDER),
        api_row,
        stats_row,
        video_status_row,
        chrome_section,
        ft.Divider(height=1, color=COLOR_BORDER),
        action_row,
    ], spacing=8)

    def on_hover(e: ft.HoverEvent):
        card.scale = 1.02 if e.data == "true" else 1.0
        card.shadow = (
            ft.BoxShadow(
                spread_radius=3, blur_radius=24,
                color=f"{COLOR_CHROME}55" if chrome_running else f"{COLOR_ACCENT}33",
                offset=ft.Offset(0, 8),
            )
            if e.data == "true"
            else ft.BoxShadow(spread_radius=1, blur_radius=8, color="#00000044", offset=ft.Offset(0, 4))
        )
        card.update()

    border_color = (
        f"{COLOR_CHROME}88" if chrome_running
        else (f"{COLOR_DANGER}66" if not api_exists else COLOR_BORDER)
    )

    card = ft.Container(
        content=card_content,
        bgcolor=COLOR_BG_CARD,
        border_radius=16,
        padding=ft.padding.all(14),
        border=ft.border.all(1, border_color),
        shadow=ft.BoxShadow(
            spread_radius=1, blur_radius=8, color="#00000044", offset=ft.Offset(0, 4),
        ),
        animate_scale=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_hover=on_hover,
        width=290,
    )
    return card


def _confirm_delete(page: ft.Page, profile: Profile, on_delete: Callable[[int], None]):
    """Hop thoai xac nhan xoa Profile."""

    def do_delete(_):
        on_delete(profile.id)
        close_dialog(page, dialog)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Xac nhan xoa kenh", color=COLOR_TEXT_MAIN, weight=ft.FontWeight.W_700),
        content=ft.Column(
            [
                ft.Text(f"Ban co chac muon xoa kenh '{profile.name}'?", color=COLOR_TEXT_MAIN, size=14),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([
                                ft.Icon(ft.Icons.WARNING_AMBER, color=COLOR_WARNING, size=16),
                                ft.Text("Du lieu bi xoa:", color=COLOR_WARNING, size=12),
                            ]),
                            ft.Text("  - Thu muc Chrome (cookie, session)", color=COLOR_TEXT_SUB, size=12),
                            ft.Text("  - Thu muc video cache", color=COLOR_TEXT_SUB, size=12),
                            ft.Text("  - Tat ca task lien quan", color=COLOR_TEXT_SUB, size=12),
                        ],
                        spacing=4,
                    ),
                    bgcolor=f"{COLOR_WARNING}11",
                    border_radius=8,
                    padding=ft.padding.all(10),
                    border=ft.border.all(1, f"{COLOR_WARNING}44"),
                ),
            ],
            spacing=0, tight=True,
        ),
        bgcolor=COLOR_BG_CARD,
        actions=[
            ft.TextButton("Huy", on_click=lambda _: close_dialog(page, dialog),
                          style=ft.ButtonStyle(color=COLOR_TEXT_SUB)),
            ft.ElevatedButton(
                "Xoa vinh vien",
                style=ft.ButtonStyle(
                    bgcolor=COLOR_DANGER, color=COLOR_TEXT_MAIN,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=do_delete,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    open_dialog(page, dialog)


def _update_api_dialog(page: ft.Page, profile: Profile, on_done: Callable[[], None] | None = None):
    """
    Dialog cap nhat duong dan client_secret.json cho profile.
    Hien thi ghi chu cach tai file tu Google Cloud Console.
    """
    from pathlib import Path as _Path

    json_field = ft.TextField(
        value=profile.json_api_path or "",
        label="Đường dẫn OAuth client JSON (client_secret.json)",
        label_style=ft.TextStyle(color=COLOR_TEXT_SUB),
        text_style=ft.TextStyle(color=COLOR_TEXT_MAIN),
        bgcolor=COLOR_BG_DARK,
        border_color=COLOR_BORDER,
        focused_border_color=COLOR_ACCENT,
        border_radius=10,
        hint_text="Chọn hoặc dán đường dẫn file JSON tải từ Google Cloud",
        hint_style=ft.TextStyle(color="#4A4F70"),
        width=420,
    )
    error_text = ft.Text("", color=COLOR_DANGER, size=12)
    status_text = ft.Text(
        "Chọn JSON xong bấm 'Lưu & Check API' để đăng nhập Google và bật API On.",
        color=COLOR_TEXT_SUB,
        size=12,
    )

    guide = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=COLOR_ACCENT, size=14),
                ft.Text("Cach lay file JSON:", size=12, color=COLOR_TEXT_SUB, weight=ft.FontWeight.W_600),
            ], spacing=6),
            ft.Text("1. Vào Google Cloud Console → APIs & Services → Credentials", size=11, color=COLOR_TEXT_SUB),
            ft.Text("2. Tạo OAuth 2.0 Client ID → Application type: Desktop app", size=11, color=COLOR_TEXT_SUB),
            ft.Text("3. Download JSON → bấm Chọn JSON hoặc dán đường dẫn vào ô trên", size=11, color=COLOR_TEXT_SUB),
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, color=COLOR_SUCCESS, size=13),
                ft.Text("Bấm 'Lưu & Check API' trong popup này để kết nối YouTube", size=11, color=COLOR_SUCCESS),
            ], spacing=6),
        ], spacing=4),
        bgcolor=f"{COLOR_ACCENT}11",
        border_radius=8,
        padding=ft.padding.all(10),
        border=ft.border.all(1, f"{COLOR_ACCENT}33"),
    )

    def choose_json(_):
        def _pick():
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            path = filedialog.askopenfilename(title="Chọn OAuth client JSON", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
            root.destroy()
            if path:
                json_field.value = path
                try: json_field.update()
                except Exception: pass
        threading.Thread(target=_pick, daemon=True).start()

    def _save_path_only() -> bool:
        path = json_field.value.strip()
        if path and not _Path(path).exists():
            error_text.value = f"File không tồn tại: {path}"
            try: error_text.update()
            except Exception: pass
            return False
        old_path = profile.json_api_path or ""
        profile.json_api_path = path
        if path != old_path:
            profile.is_active = False  # reset connection khi đổi đường dẫn
            profile.token_path = ""     # token cũ có thể thuộc OAuth client khác
        profile.save()
        return True

    def do_save(_):
        if not _save_path_only():
            return
        close_dialog(page, dlg)
        _box_snack(page, f"Đã lưu JSON API cho '{profile.name}'", COLOR_SUCCESS)

    def do_save_and_check(_):
        if not _save_path_only():
            return
        check_btn.disabled = True
        save_btn.disabled = True
        status_text.value = "Đang xác thực Google... Nếu chưa có token, trình duyệt sẽ mở. Tối đa 75 giây rồi báo lỗi."
        status_text.color = COLOR_WARNING
        error_text.value = ""
        try: page.update()
        except Exception: pass

        from core.oauth_helper import OAuthHelper as _OAuthHelper
        def _run():
            try:
                info = _OAuthHelper.quick_connect(profile)
                title = info.get("title") or profile.name
                status_text.value = f"Kết nối thành công: {title}"
                status_text.color = COLOR_SUCCESS
                _box_snack(page, f"API On: {title}", COLOR_SUCCESS)
                close_dialog(page, dlg)
                if on_done:
                    on_done()
            except Exception as ex:
                profile.is_active = False
                profile.save()
                error_text.value = f"Lỗi check API: {ex}"
                status_text.value = "Chưa kết nối được. Kiểm tra JSON, OAuth consent, YouTube Data API v3."
                status_text.color = COLOR_DANGER
            finally:
                check_btn.disabled = False
                save_btn.disabled = False
                try: page.update()
                except Exception: pass
        threading.Thread(target=_run, daemon=True).start()

    save_btn = ft.ElevatedButton(
        "Lưu",
        style=ft.ButtonStyle(
            bgcolor=COLOR_BG_DARK, color=COLOR_TEXT_MAIN,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=do_save,
    )
    check_btn = ft.ElevatedButton(
        "Lưu & Check API",
        icon=ft.Icons.VERIFIED,
        style=ft.ButtonStyle(
            bgcolor=COLOR_SUCCESS, color=COLOR_TEXT_MAIN,
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=do_save_and_check,
    )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.API, color=COLOR_ACCENT),
            ft.Text("Cau hinh YouTube API", color=COLOR_TEXT_MAIN, weight=ft.FontWeight.W_700),
        ], spacing=10),
        bgcolor=COLOR_BG_CARD,
        content=ft.Column([
            json_field,
            ft.Row([
                ft.ElevatedButton("Chọn JSON auth...", icon=ft.Icons.UPLOAD_FILE, on_click=choose_json, style=ft.ButtonStyle(bgcolor=COLOR_PRIMARY, color=COLOR_TEXT_MAIN)),
            ]),
            guide,
            status_text,
            error_text,
        ], spacing=12, tight=True, width=470),
        actions=[
            ft.TextButton("Hủy", on_click=lambda _: close_dialog(page, dlg),
                          style=ft.ButtonStyle(color=COLOR_TEXT_SUB)),
            save_btn,
            check_btn,
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    open_dialog(page, dlg)


def _box_snack(page: ft.Page, msg: str, color: str = COLOR_SUCCESS):
    """SnackBar nhanh dung trong components.py."""
    try:
        snack = ft.SnackBar(
            content=ft.Text(msg, color=COLOR_TEXT_MAIN),
            bgcolor=color, duration=2500, open=True,
        )
        page.overlay.append(snack)
        page.update()
    except Exception:
        pass









# ══════════════════════════════════════════
# 3. CACHE SIDEBAR
# ══════════════════════════════════════════

class CacheSidebar(ft.Container):
    """
    Sidebar trai: Logo, Navigation, Cache progress, Chrome count.
    """

    def __init__(self, active_route: str = "/dashboard", on_navigate: Optional[Callable] = None):
        self.active_route = active_route
        self.on_navigate  = on_navigate

        self._progress_bar = ft.ProgressBar(
            value=0,
            bgcolor=COLOR_BORDER,
            color=COLOR_ACCENT,
            border_radius=4,
        )
        self._cache_text  = ft.Text("0.0 GB / 5 GB", size=11, color=COLOR_TEXT_SUB)
        self._chrome_text = ft.Text("0 Chrome dang chay", size=11, color=COLOR_TEXT_SUB)

        nav_items = [
            ("/dashboard", ft.Icons.DASHBOARD_OUTLINED,      "Dashboard"),
            ("/channels",  ft.Icons.VIDEO_LIBRARY_OUTLINED,  "Quan ly Kenh"),
            ("/schedule",  ft.Icons.CALENDAR_MONTH_OUTLINED, "Lich Dang"),
            ("/telegram",  ft.Icons.SEND_OUTLINED,           "Cai dat Telegram"),
            ("/settings",  ft.Icons.SETTINGS_OUTLINED,       "Cai dat He thong"),
        ]
        nav_controls = [self._nav_item(r, i, l) for r, i, l in nav_items]

        logo = ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.BOLT, color=COLOR_ACCENT, size=26),
                    bgcolor=f"{COLOR_ACCENT}22",
                    border_radius=10,
                    width=42, height=42,
                    alignment=ft.Alignment(0, 0),
                ),
                ft.Column(
                    [
                        ft.Text("YouTube Auto", size=15, weight=ft.FontWeight.W_800, color=COLOR_TEXT_MAIN),
                        ft.Text("Pusher v1.0", size=10, color=COLOR_TEXT_SUB),
                    ],
                    spacing=0,
                ),
            ],
            spacing=10,
        )

        cache_block = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Icon(ft.Icons.STORAGE, color=COLOR_TEXT_SUB, size=13),
                         ft.Text("Local Cache", size=12, color=COLOR_TEXT_SUB)],
                        spacing=6,
                    ),
                    self._progress_bar,
                    self._cache_text,
                    ft.Divider(height=1, color=COLOR_BORDER),
                    ft.Row(
                        [ft.Icon(ft.Icons.OPEN_IN_BROWSER, color=COLOR_CHROME, size=13),
                         self._chrome_text],
                        spacing=6,
                    ),
                ],
                spacing=6,
            ),
            bgcolor=f"{COLOR_ACCENT}11",
            border_radius=12,
            padding=ft.padding.all(12),
            border=ft.border.all(1, COLOR_BORDER),
        )

        super().__init__(
            content=ft.Column(
                [logo, ft.Divider(height=20, color=COLOR_BORDER),
                 *nav_controls,
                 ft.Container(expand=True),
                 cache_block],
                spacing=4,
            ),
            bgcolor=COLOR_BG_SIDEBAR,
            width=210,
            padding=ft.padding.all(18),
            border=ft.border.only(right=ft.BorderSide(1, COLOR_BORDER)),
        )

    def _nav_item(self, route: str, icon, label: str) -> ft.Container:
        is_active = self.active_route == route
        bg = f"{COLOR_ACCENT}22" if is_active else "transparent"
        tc = COLOR_ACCENT if is_active else COLOR_TEXT_SUB
        ic = COLOR_ACCENT if is_active else COLOR_TEXT_SUB

        def clicked(_):
            if self.on_navigate:
                self.on_navigate(route)

        return ft.Container(
            content=ft.Row(
                [ft.Icon(icon, color=ic, size=17), ft.Text(label, size=12, color=tc)],
                spacing=10,
            ),
            bgcolor=bg,
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=9),
            on_click=clicked,
        )

    def refresh_cache(self, used_gb: float, limit_gb: float = CACHE_LIMIT_GB):
        """Cap nhat progress bar cache."""
        ratio = min(used_gb / limit_gb, 1.0)
        self._progress_bar.value = ratio
        self._progress_bar.color = COLOR_DANGER if ratio > 0.85 else COLOR_ACCENT
        self._cache_text.value   = f"{used_gb:.1f} GB / {limit_gb:.0f} GB"
        try:
            self.update()
        except Exception:
            pass

    def refresh_chrome_count(self, count: int):
        """Cap nhat so Chrome dang chay."""
        self._chrome_text.value = f"{count} Chrome dang chay"
        self._chrome_text.color = COLOR_CHROME if count > 0 else COLOR_TEXT_SUB
        try:
            self.update()
        except Exception:
            pass


# ══════════════════════════════════════════
# 4. FLOATING CHAT WIDGET
# ══════════════════════════════════════════

class FloatingChatWidget(ft.Container):
    """
    FloatingChatWidget -- cua so chat thu nho goc duoi phai.

    FIX CLICK-BLOCKING BUG:
      Truoc day: ft.Stack(expand=True) → phu toan man hinh → chan het click.
      Nay: ft.Container kich thuoc co dinh (340x440).
      Duoc them vao page.overlay qua mount_to_page() → KHONG chan click phia duoi.

    Commands: help / status / pending / chrome / cache / clear
    """

    def __init__(self, page: ft.Page):
        self._page     = page
        self._expanded = False

        self._input = ft.TextField(
            hint_text="Nhap lenh... ('help')",
            hint_style=ft.TextStyle(color=COLOR_TEXT_SUB, size=12),
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=13),
            bgcolor="transparent",
            border=ft.InputBorder.NONE,
            expand=True,
            on_submit=self._handle_submit,
            color=COLOR_TEXT_MAIN,
        )

        self._chat_list = ft.ListView(
            expand=True,
            spacing=8,
            auto_scroll=True,
        )

        # FAB — wrap trong Container để đặt vị trí góc dưới-phải khi trong overlay
        self.fab = ft.Container(
            content=ft.FloatingActionButton(
                content=ft.Icon(ft.Icons.SMART_TOY_OUTLINED, color=COLOR_TEXT_MAIN),
                bgcolor=COLOR_ACCENT,
                on_click=self._toggle,
                tooltip="AI Assistant",
            ),
            width=56,
            height=56,
            right=16,
            bottom=16,
        )

        super().__init__(
            content=ft.Column(
                [
                    # Header bar
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(ft.Icons.SMART_TOY, color=COLOR_ACCENT, size=16),
                                        ft.Text("Auto Pusher AI", size=13,
                                                weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN),
                                    ],
                                    spacing=8,
                                ),
                                ft.IconButton(
                                    ft.Icons.CLOSE,
                                    icon_color=COLOR_TEXT_SUB,
                                    icon_size=18,
                                    on_click=self._toggle,
                                    tooltip="Thu nho",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        bgcolor=COLOR_BG_DARK,
                        padding=ft.padding.symmetric(horizontal=14, vertical=10),
                        border_radius=ft.border_radius.only(top_left=16, top_right=16),
                    ),
                    # Messages
                    ft.Container(
                        content=self._chat_list,
                        expand=True,
                        padding=ft.padding.all(12),
                    ),
                    # Input bar
                    ft.Container(
                        content=ft.Row(
                            [
                                self._input,
                                ft.IconButton(
                                    ft.Icons.SEND_ROUNDED,
                                    icon_color=COLOR_ACCENT,
                                    on_click=self._handle_submit,
                                    tooltip="Gui",
                                ),
                            ],
                            spacing=4,
                        ),
                        bgcolor=COLOR_BG_DARK,
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        border_radius=ft.border_radius.only(bottom_left=16, bottom_right=16),
                        border=ft.border.only(top=ft.BorderSide(1, COLOR_BORDER)),
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            bgcolor=COLOR_BG_CARD,
            border_radius=16,
            border=ft.border.all(1, COLOR_BORDER),
            shadow=ft.BoxShadow(
                spread_radius=4, blur_radius=24,
                color="#00000088",
                offset=ft.Offset(0, 8),
            ),
            width=340,
            height=440,
            visible=False,  # An ban dau
            right=80,       # Vi tri khi trong overlay
            bottom=80,
        )

        self._add_bot_message("Xin chao! Toi la Auto Pusher AI. Go 'help' de xem lenh.")

    def mount_to_page(self):
        """
        Them widget vao page.overlay sau khi page da san sang.
        Dung overlay: widget float TREN cung nhung KHONG chan click phia duoi.
        """
        self._page.overlay.extend([self, self.fab])
        self._page.update()

    def _toggle(self, _=None):
        self._expanded  = not self._expanded
        self.visible    = self._expanded
        # self.fab la Container boc ngoai FAB — cập nhật icon bên trong
        inner_fab = self.fab.content  # ft.FloatingActionButton
        inner_fab.content = ft.Icon(
            ft.Icons.CLOSE if self._expanded else ft.Icons.SMART_TOY_OUTLINED,
            color=COLOR_TEXT_MAIN,
        )
        try:
            self._page.update()
        except Exception:
            pass

    def _handle_submit(self, _=None):
        text = self._input.value.strip()
        if not text:
            return
        self._input.value = ""
        self._add_user_message(text)
        response = self._process_command(text.lower())
        self._add_bot_message(response)
        try:
            self._page.update()
        except Exception:
            pass

    def _process_command(self, cmd: str) -> str:
        if cmd == "help":
            return (
                "Lenh co san:\n"
                "  status  - task dang chay\n"
                "  pending - task cho xu ly\n"
                "  chrome  - trang thai Chrome\n"
                "  cache   - dung luong cache\n"
                "  clear   - xoa chat"
            )
        elif cmd == "status":
            running = DatabaseManager.get_running_tasks()
            if not running:
                return "Khong co task nao dang chay."
            return "Dang chay:\n" + "\n".join(f"  [{t.id}] {t.title[:35]}" for t in running)
        elif cmd == "pending":
            pending = DatabaseManager.get_pending_tasks()
            if not pending:
                return "Khong co task cho xu ly."
            return f"{len(pending)} task:\n" + "\n".join(
                f"  [{t.id}] {t.title[:35]}" for t in pending[:8]
            )
        elif cmd == "chrome":
            from core.chrome_manager import ChromeManager
            status = ChromeManager.get_status()
            if not status:
                return "Khong co phien Chrome nao."
            return "Chrome:\n" + "\n".join(
                f"  Profile_{pid}: {'ON' if ok else 'OFF'}"
                for pid, ok in status.items()
            )
        elif cmd == "cache":
            from pathlib import Path
            from core.cache_manager import CacheManager
            base = Path(__file__).resolve().parent.parent
            gb = CacheManager.get_global_cache_gb(base)
            return f"Cache: {gb:.2f} GB / 5 GB"
        elif cmd == "clear":
            self._chat_list.controls.clear()
            return "Da xoa."
        else:
            return f"'{cmd}' khong hop le. Go 'help'."

    def _add_user_message(self, text: str):
        self._chat_list.controls.append(
            ft.Row([
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text(text, size=13, color=COLOR_TEXT_MAIN, selectable=True),
                    bgcolor=COLOR_ACCENT + "33",
                    border_radius=ft.border_radius.only(top_left=12, top_right=12, bottom_left=12),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                ),
            ])
        )

    def _add_bot_message(self, text: str):
        self._chat_list.controls.append(
            ft.Row([
                ft.Container(
                    content=ft.Text(text, size=13, color=COLOR_TEXT_MAIN, selectable=True),
                    bgcolor=COLOR_BG_DARK,
                    border_radius=ft.border_radius.only(top_left=12, top_right=12, bottom_right=12),
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    border=ft.border.all(1, COLOR_BORDER),
                ),
                ft.Container(expand=True),
            ])
        )

