"""
ui/views.py
===========
Cac View chinh cua OpenClaw-Bridge:
  - DashboardView   : Grid BoxCard + Chrome controls per profile
  - ProfilePopup    : Chi tiet kenh + inline task editing
  - AddProfileDialog: Tao Profile moi
"""

import json
import calendar
import datetime as dt
import threading
import time
import pytz
import flet as ft
from pathlib import Path
from typing import Callable, Optional
from ui.dialog_helper import open_dialog, close_dialog

from core.database import (
    Profile, Task, DatabaseManager,
    STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED
)
from core.cache_manager import CacheManager
from ui.components import (
    BoxCard, StatusBadge, TIMEZONES,
    COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING,
    COLOR_BG_DARK, COLOR_BG_CARD, COLOR_TEXT_MAIN, COLOR_TEXT_SUB,
    COLOR_ACCENT, COLOR_BORDER, CACHE_LIMIT_GB, COLOR_BG_SIDEBAR,
    COLOR_CHROME,
)

BASE_DIR = Path(__file__).resolve().parent.parent


# ══════════════════════════════════════════
# STATUS CHIP
# ══════════════════════════════════════════

STATUS_COLORS = {
    STATUS_PENDING:   COLOR_WARNING,
    STATUS_RUNNING:   COLOR_PRIMARY,
    STATUS_COMPLETED: COLOR_SUCCESS,
    STATUS_FAILED:    COLOR_DANGER,
}

STATUS_ICONS = {
    STATUS_PENDING:   ft.Icons.HOURGLASS_EMPTY,
    STATUS_RUNNING:   ft.Icons.SYNC,
    STATUS_COMPLETED: ft.Icons.CHECK_CIRCLE_OUTLINE,
    STATUS_FAILED:    ft.Icons.ERROR_OUTLINE,
}


def status_chip(status: str) -> ft.Container:
    color = STATUS_COLORS.get(status, COLOR_TEXT_SUB)
    icon  = STATUS_ICONS.get(status, ft.Icons.HELP_OUTLINE)
    return ft.Container(
        content=ft.Row(
            [ft.Icon(icon, color=color, size=12), ft.Text(status, size=11, color=color)],
            spacing=4,
        ),
        bgcolor=f"{color}22",
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
    )


# ══════════════════════════════════════════
# ADD PROFILE DIALOG
# ══════════════════════════════════════════

def AddProfileDialog(page: ft.Page, on_created: Callable[[Profile], None]):
    """
    Hop thoai tao moi Profile.
    Tu dong tao: thu muc Chrome profile + cache folder.
    """
    name_field = ft.TextField(
        label="Ten kenh *",
        label_style=ft.TextStyle(color=COLOR_TEXT_SUB),
        text_style=ft.TextStyle(color=COLOR_TEXT_MAIN),
        bgcolor=COLOR_BG_DARK,
        border_color=COLOR_BORDER,
        focused_border_color=COLOR_ACCENT,
        border_radius=10,
    )
    json_field = ft.TextField(
        label="Đường dẫn OAuth client JSON (client_secret.json)",
        label_style=ft.TextStyle(color=COLOR_TEXT_SUB),
        text_style=ft.TextStyle(color=COLOR_TEXT_MAIN),
        bgcolor=COLOR_BG_DARK,
        border_color=COLOR_BORDER,
        focused_border_color=COLOR_ACCENT,
        border_radius=10,
        hint_text="Chọn/nhập đường dẫn file JSON tải từ Google Cloud",
        hint_style=ft.TextStyle(color="#4A4F70"),
    )
    error_text = ft.Text("", color=COLOR_DANGER, size=12)

    # Note ve Chrome profile isolation
    chrome_note = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.INFO_OUTLINE, color=COLOR_CHROME, size=15),
                ft.Text(
                    "Moi kenh se co Chrome profile rieng (cookie tach biet)",
                    size=12, color=COLOR_CHROME,
                ),
            ],
            spacing=8,
        ),
        bgcolor=f"{COLOR_CHROME}11",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=8),
        border=ft.border.all(1, f"{COLOR_CHROME}33"),
    )

    def do_create(_):
        name = name_field.value.strip()
        if not name:
            error_text.value = "Ten kenh khong duoc de trong!"
            error_text.update()
            return
        try:
            profile = DatabaseManager.create_profile(
                name=name,
                json_api_path=json_field.value.strip(),
            )
            close_dialog(page, dialog)
            on_created(profile)
        except Exception as e:
            error_text.value = f"Loi: {e}"
            error_text.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.ADD_CIRCLE, color=COLOR_ACCENT),
                ft.Text("Them Kenh Moi", color=COLOR_TEXT_MAIN, weight=ft.FontWeight.W_700),
            ],
            spacing=10,
        ),
        bgcolor=COLOR_BG_CARD,
        content=ft.Column(
            [name_field, json_field, chrome_note, error_text],
            spacing=12,
            tight=True,
            width=420,
        ),
        actions=[
            ft.TextButton("Huy", on_click=lambda _: close_dialog(page, dialog),
                          style=ft.ButtonStyle(color=COLOR_TEXT_SUB)),
            ft.ElevatedButton(
                "Tao Kenh",
                style=ft.ButtonStyle(
                    bgcolor=COLOR_ACCENT, color=COLOR_TEXT_MAIN,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=do_create,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    open_dialog(page, dialog)


# ══════════════════════════════════════════
# DATETIME PICKER DIALOG
# ══════════════════════════════════════════

def DateTimePickerDialog(
    page: ft.Page,
    initial_dt,
    on_confirm: Callable,
):
    """
    Drum-roll style date/time picker.
    Mỗi cột hỗ trợ: cuộn chuột + nút mũi tên lên/xuống.
    Hỗ trợ chọn bằng nút/cuộn và nhập tay chính xác từng phút.
    """
    MONTHS_VI = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4",
        "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8",
        "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
    ]

    now = initial_dt if initial_dt else dt.datetime.now()
    state = {
        "year":   now.year,
        "month":  now.month,
        "day":    now.day,
        "hour":   now.hour,
        "minute": now.minute,
    }

    texts = {
        "day":    ft.Text(f"{state['day']:02d}",            size=22, weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN, text_align=ft.TextAlign.CENTER),
        "month":  ft.Text(MONTHS_VI[state["month"] - 1],  size=16, weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN, text_align=ft.TextAlign.CENTER),
        "year":   ft.Text(str(state["year"]),              size=20, weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN, text_align=ft.TextAlign.CENTER),
        "hour":   ft.Text(f"{state['hour']:02d}",          size=26, weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN, text_align=ft.TextAlign.CENTER),
        "minute": ft.Text(f"{state['minute']:02d}",        size=26, weight=ft.FontWeight.W_700, color=COLOR_TEXT_MAIN, text_align=ft.TextAlign.CENTER),
    }

    def _get_values(key):
        if key == "day":    return list(range(1, calendar.monthrange(state["year"], state["month"])[1] + 1))
        if key == "month":  return list(range(1, 13))
        if key == "year":   y = dt.datetime.now().year; return list(range(y, y + 10))
        if key == "hour":   return list(range(0, 24))
        if key == "minute": return list(range(0, 60))
        return []

    def _fmt(key, val):
        if key == "month": return MONTHS_VI[val - 1]
        if key == "year":  return str(val)
        return f"{val:02d}"

    def scroll(key, delta):
        vals = _get_values(key)
        curr = state[key]
        try:
            idx = vals.index(curr)
        except ValueError:
            idx = 0
        state[key] = vals[(idx + delta) % len(vals)]
        # Kẹp ngày khi tháng/năm thay đổi
        if key in ("month", "year"):
            md = calendar.monthrange(state["year"], state["month"])[1]
            if state["day"] > md:
                state["day"] = md
                texts["day"].value = _fmt("day", state["day"])
        texts[key].value = _fmt(key, state[key])
        try:
            manual_field.value = _manual_value()
        except Exception:
            pass
        try:
            page.update()
        except Exception:
            pass

    def make_col(key, width, label):
        up_btn = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_UP,
            icon_color=COLOR_ACCENT, icon_size=22,
            on_click=lambda _, k=key: scroll(k, -1),
            style=ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT, padding=ft.padding.all(0)),
        )
        dn_btn = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_DOWN,
            icon_color=COLOR_ACCENT, icon_size=22,
            on_click=lambda _, k=key: scroll(k, 1),
            style=ft.ButtonStyle(bgcolor=ft.Colors.TRANSPARENT, padding=ft.padding.all(0)),
        )
        display = ft.Container(
            content=texts[key],
            width=width, height=52,
            alignment=ft.Alignment(0, 0),
            bgcolor=f"{COLOR_ACCENT}22",
            border_radius=10,
            border=ft.border.all(1.5, COLOR_ACCENT),
        )
        col = ft.Column(
            [
                ft.Text(label, size=10, color=COLOR_TEXT_SUB, text_align=ft.TextAlign.CENTER),
                up_btn, display, dn_btn,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        )
        return ft.GestureDetector(
            content=ft.Container(content=col, width=width + 10, alignment=ft.Alignment(0, 0)),
            on_scroll=lambda e, k=key: scroll(
                k, 1 if (getattr(e, "delta_y", None) or getattr(e, "scroll_delta_y", 0)) > 0 else -1
            ),
            mouse_cursor=ft.MouseCursor.RESIZE_UP_DOWN,
        )

    def _manual_value():
        return f"{state['day']:02d}/{state['month']:02d}/{state['year']} {state['hour']:02d}:{state['minute']:02d}"

    manual_field = ft.TextField(
        label="Nhập tay thời gian",
        value=_manual_value(),
        hint_text="VD: 10/05/2026 16:37",
        text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=13),
        bgcolor=COLOR_BG_DARK,
        border_color=COLOR_BORDER,
        focused_border_color=COLOR_ACCENT,
        border_radius=8,
        width=260,
        height=46,
        content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
    )
    manual_error = ft.Text("", size=10, color=COLOR_DANGER)

    def do_confirm(_):
        raw = (manual_field.value or "").strip()
        try:
            if raw:
                result = dt.datetime.strptime(raw, "%d/%m/%Y %H:%M")
            else:
                result = dt.datetime(
                    state["year"], state["month"], state["day"],
                    state["hour"], state["minute"],
                )
        except Exception:
            manual_error.value = "Sai định dạng. Nhập kiểu: 10/05/2026 16:37"
            try: page.update()
            except Exception: pass
            return
        close_dialog(page, dialog)
        on_confirm(result)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.CALENDAR_MONTH, color=COLOR_ACCENT, size=20),
            ft.Text("Đặt Lịch Đăng", color=COLOR_TEXT_MAIN,
                    weight=ft.FontWeight.W_700, size=16),
        ], spacing=10),
        bgcolor=COLOR_BG_CARD,
        content=ft.Container(
            content=ft.Column([
                ft.Text("📅  Chọn ngày đăng", size=12, color=COLOR_TEXT_SUB),
                ft.Row(
                    [make_col("day", 56, "Ngày"), make_col("month", 94, "Tháng"), make_col("year", 72, "Năm")],
                    spacing=10, alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Divider(height=16, color=COLOR_BORDER),
                ft.Text("⏰  Chọn giờ đăng", size=12, color=COLOR_TEXT_SUB),
                ft.Row([
                    make_col("hour", 62, "Giờ"),
                    ft.Container(
                        content=ft.Text(":", size=32, color=COLOR_ACCENT, weight=ft.FontWeight.W_700),
                        padding=ft.padding.only(top=26),
                    ),
                    make_col("minute", 62, "Phút")
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                manual_field,
                manual_error,
                ft.Text(
                    "💡 Có thể cuộn/bấm mũi tên hoặc nhập tay chính xác từng phút",
                    size=10, color=f"{COLOR_TEXT_SUB}77",
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.symmetric(vertical=8, horizontal=12),
            width=360,
        ),
        actions=[
            ft.TextButton(
                "Hủy",
                on_click=lambda _: close_dialog(page, dialog),
                style=ft.ButtonStyle(color=COLOR_TEXT_SUB),
            ),
            ft.ElevatedButton(
                "✓  Xác nhận",
                style=ft.ButtonStyle(
                    bgcolor=COLOR_ACCENT, color=COLOR_TEXT_MAIN,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=do_confirm,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    open_dialog(page, dialog)


# ══════════════════════════════════════════
# PROFILE POPUP — Chi tiet kenh + Task inline editing
# ══════════════════════════════════════════

def ProfilePopup(
    page: ft.Page,
    profile: Profile,
    on_saved: Callable[[], None],
):
    """
    Hop thoai chi tiet kenh:
      - Thong tin API + Cache + Chrome profile
      - Danh sach Task inline editable
      - File picker them video (file_picker truyen vao, da mount san)
    """
    from core.chrome_manager import ChromeManager

    tasks       = DatabaseManager.get_tasks_by_profile(profile.id)
    cache_mgr   = CacheManager(profile.id, BASE_DIR)
    cache_gb    = cache_mgr.get_cache_size_gb()
    cache_ratio = cache_mgr.get_usage_ratio()
    chrome_running = ChromeManager.is_running(profile.id)
    chrome_name    = profile.chrome_profile_name or f"Profile_{profile.id}"


    # ── Info header ──
    api_widget = ft.Row([
        ft.Text("API: ", size=12, color=COLOR_TEXT_SUB),
        ft.Text(
            "Connected" if profile.is_active else "Disconnected",
            size=12,
            color=COLOR_SUCCESS if profile.is_active else COLOR_DANGER,
            weight=ft.FontWeight.W_600,
        ),
    ], spacing=0)

    cache_widget = ft.Row([
        ft.Text("Cache: ", size=12, color=COLOR_TEXT_SUB),
        ft.Text(f"{cache_gb:.1f}GB / 5GB", size=12, color=COLOR_ACCENT, weight=ft.FontWeight.W_600),
    ], spacing=0)

    chrome_color = COLOR_CHROME if chrome_running else COLOR_TEXT_SUB
    chrome_widget = ft.Row([
        ft.Icon(ft.Icons.OPEN_IN_BROWSER, size=14, color=chrome_color),
        ft.Text(
            f"{chrome_name} - {'Running' if chrome_running else 'Closed'}",
            size=12, color=chrome_color, weight=ft.FontWeight.W_600,
        ),
    ], spacing=6)

    info_bar = ft.Container(
        content=ft.Row(
            [api_widget, cache_widget, ft.Container(expand=True), chrome_widget],
            spacing=20,
        ),
        bgcolor=COLOR_BG_DARK,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=14, vertical=10),
    )

    # ── Chrome data folder info ──
    chrome_data_size = round(profile.get_chrome_data_size_bytes() / (1024*1024), 1)
    chrome_folder_bar = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.FOLDER, color=COLOR_CHROME, size=14),
                ft.Text("Chrome Data:", size=11, color=COLOR_TEXT_SUB),
                ft.Text(str(profile.chrome_data_dir), size=10, color=COLOR_TEXT_SUB,
                        expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"{chrome_data_size} MB", size=11, color=COLOR_CHROME),
                ft.IconButton(
                    ft.Icons.FOLDER_OPEN,
                    icon_color=COLOR_CHROME,
                    icon_size=16,
                    tooltip="Mo thu muc Chrome",
                    on_click=lambda _: _open_folder(profile.chrome_data_dir),
                ),
                ft.IconButton(
                    ft.Icons.DELETE_SWEEP,
                    icon_color=COLOR_DANGER,
                    icon_size=16,
                    tooltip="Xoa du lieu Chrome (xoa cookie!)",
                    on_click=lambda _: _confirm_reset_chrome(page, profile),
                ),
            ],
            spacing=8,
        ),
        bgcolor=f"{COLOR_CHROME}11",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        border=ft.border.all(1, f"{COLOR_CHROME}33"),
    )

    # ── Task rows ──
    task_rows_ref = []
    task_list_col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def _field_label(text: str, icon=None):
        items = []
        if icon:
            items.append(ft.Icon(icon, color=COLOR_ACCENT, size=13))
        items.append(ft.Text(text, size=11, color=COLOR_TEXT_SUB, weight=ft.FontWeight.W_600))
        return ft.Row(items, spacing=5)

    def _task_status_chip(status: str):
        color_map = {
            STATUS_PENDING: COLOR_WARNING,
            STATUS_RUNNING: COLOR_PRIMARY,
            STATUS_COMPLETED: COLOR_SUCCESS,
            STATUS_FAILED: COLOR_DANGER,
        }
        label_map = {
            STATUS_PENDING: "Đang đợi",
            STATUS_RUNNING: "Đang đăng",
            STATUS_COMPLETED: "Đã đăng",
            STATUS_FAILED: "Lỗi",
        }
        color = color_map.get(status, COLOR_TEXT_SUB)
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(STATUS_ICONS.get(status, ft.Icons.INFO_OUTLINE), color=color, size=13),
                    ft.Text(label_map.get(status, status), size=11, color=color, weight=ft.FontWeight.W_700),
                ],
                spacing=5,
                tight=True,
            ),
            bgcolor=f"{color}18",
            border=ft.border.all(1, f"{color}44"),
            border_radius=999,
            padding=ft.padding.symmetric(horizontal=9, vertical=4),
        )

    def build_task_row(task: Task) -> ft.Container:
        thumb = ft.Container(
            content=ft.Icon(ft.Icons.VIDEO_FILE, color=COLOR_ACCENT, size=24),
            bgcolor=f"{COLOR_ACCENT}22",
            border_radius=10,
            width=50, height=46,
            alignment=ft.Alignment(0, 0),
        )
        title_f = ft.TextField(
            label="Tiêu đề video",
            value=task.title,
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=13),
            bgcolor=COLOR_BG_DARK, border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT, border_radius=8,
            height=46,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        )
        desc_f = ft.TextField(
            label="Mô tả",
            value=task.description,
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=12),
            bgcolor=COLOR_BG_DARK, border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT, border_radius=8,
            min_lines=2, max_lines=4,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        )
        tags_f = ft.TextField(
            label="Tags",
            value=task.tags,
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=12),
            bgcolor=COLOR_BG_DARK, border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT, border_radius=8,
            hint_text="tag1, tag2 hoặc #tag1 #tag2",
            hint_style=ft.TextStyle(color="#4A4F70", size=10),
            height=44,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        )
        hash_f = ft.TextField(
            label="Hashtags",
            value=task.hashtags,
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=12),
            bgcolor=COLOR_BG_DARK, border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT, border_radius=8,
            hint_text="#shorts #viral",
            hint_style=ft.TextStyle(color="#4A4F70", size=10),
            height=44,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
        )

        sched_ref = [task.schedule_time]  # None nếu chưa đặt

        def _fmt_dt(d):
            if d is None:
                return "Chưa đặt lịch"
            return d.strftime("%d/%m/%Y  %H:%M")

        _dt_label = ft.Text(_fmt_dt(sched_ref[0]), color=COLOR_TEXT_MAIN, size=13, weight=ft.FontWeight.W_600)

        def _on_dt_confirmed(new_dt, _s=sched_ref, _l=_dt_label):
            _s[0] = new_dt
            _l.value = _fmt_dt(new_dt)
            try:
                _l.update()
            except Exception:
                pass

        def _open_dt_picker(_, _s=sched_ref):
            DateTimePickerDialog(page, _s[0], on_confirm=_on_dt_confirmed)

        dt_btn = ft.Container(
            content=ft.Row(
                [ft.Icon(ft.Icons.SCHEDULE, color=COLOR_ACCENT, size=16), _dt_label],
                spacing=8, tight=True,
            ),
            bgcolor=COLOR_BG_DARK,
            border_radius=8,
            border=ft.border.all(1, COLOR_BORDER),
            padding=ft.padding.symmetric(horizontal=10, vertical=9),
            on_click=_open_dt_picker,
            ink=True,
            height=42,
            alignment=ft.Alignment(-1, 0),
            tooltip="Bấm để đặt lịch đăng",
        )
        tz_dd = ft.Dropdown(
            label="Múi giờ",
            value=task.timezone,
            options=[ft.dropdown.Option(tz) for tz in TIMEZONES],
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=12),
            bgcolor=COLOR_BG_DARK, border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT, border_radius=8,
            width=190,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

        kids_dd = ft.Dropdown(
            label="Audience / trẻ em",
            value="yes" if task.made_for_kids else "no",
            options=[
                ft.dropdown.Option("no", "Không, không dành cho trẻ em"),
                ft.dropdown.Option("yes", "Có, dành cho trẻ em"),
            ],
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=12),
            bgcolor=COLOR_BG_DARK, border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT, border_radius=8,
            width=270,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )
        paid_cb = ft.Checkbox(
            label="Có paid promotion / tài trợ / product placement",
            value=bool(task.paid_promotion),
            label_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=12),
            fill_color=COLOR_ACCENT,
            check_color=COLOR_BG_DARK,
        )
        altered_dd = ft.Dropdown(
            label="Altered content / nội dung AI, giả lập",
            value="yes" if task.altered_content else "no",
            options=[
                ft.dropdown.Option("no", "Không"),
                ft.dropdown.Option("yes", "Có"),
            ],
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, size=12),
            bgcolor=COLOR_BG_DARK, border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT, border_radius=8,
            width=250,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=4),
        )

        row_ref = [None]
        details_ref = [None]
        toggle_icon = ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN, color=COLOR_ACCENT, size=18)
        toggle_text = ft.Text("Mở setting", size=11, color=COLOR_ACCENT, weight=ft.FontWeight.W_700)

        def delete_task(_):
            try:
                task.delete_instance()
                if row_ref[0] in task_list_col.controls:
                    task_list_col.controls.remove(row_ref[0])
                task_list_col.update()
            except Exception as ex:
                print(f"[UI] Lỗi xoá task: {ex}")

        def toggle_details(_):
            details_ref[0].visible = not details_ref[0].visible
            toggle_icon.name = ft.Icons.KEYBOARD_ARROW_UP if details_ref[0].visible else ft.Icons.KEYBOARD_ARROW_DOWN
            toggle_text.value = "Thu gọn" if details_ref[0].visible else "Mở setting"
            try:
                row_ref[0].update()
            except Exception:
                pass

        task_rows_ref.append({
            "task_id": task.id,
            "title": title_f, "desc": desc_f,
            "tags": tags_f, "hashtags": hash_f,
            "sched": sched_ref,
            "tz": tz_dd,
            "kids": kids_dd,
            "paid": paid_cb,
            "altered": altered_dd,
        })

        schedule_text = ft.Text(_fmt_dt(sched_ref[0]), size=11, color=COLOR_TEXT_SUB)
        details = ft.Container(
            visible=False,
            content=ft.Column(
                [
                    title_f,
                    desc_f,
                    ft.Row([ft.Container(content=tags_f, expand=True), ft.Container(content=hash_f, expand=True)], spacing=10),
                    ft.Row(
                        [
                            ft.Container(content=ft.Column([_field_label("Lịch đăng", ft.Icons.EVENT), dt_btn], spacing=5), expand=True),
                            tz_dd,
                        ],
                        spacing=10,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                _field_label("Khai báo bắt buộc của YouTube", ft.Icons.POLICY_OUTLINED),
                                ft.Text(
                                    "Chọn đúng 3 mục dưới đây để tránh YouTube báo thiếu thông tin khi upload.",
                                    size=11, color=COLOR_TEXT_SUB,
                                ),
                                ft.Row([kids_dd, altered_dd, paid_cb], spacing=10, wrap=True),
                            ],
                            spacing=6,
                        ),
                        bgcolor=f"{COLOR_WARNING}0F",
                        border=ft.border.all(1, f"{COLOR_WARNING}33"),
                        border_radius=10,
                        padding=ft.padding.all(10),
                    ),
                ],
                spacing=10,
            ),
            padding=ft.padding.only(top=10),
        )
        details_ref[0] = details

        card = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            thumb,
                            ft.Column(
                                [
                                    ft.Text(task.title or "Video mới", size=14, color=COLOR_TEXT_MAIN, weight=ft.FontWeight.W_700, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Row(
                                        [
                                            ft.Text(f"Task #{task.id}", size=11, color=COLOR_TEXT_SUB),
                                            ft.Text("•", size=11, color=COLOR_TEXT_SUB),
                                            ft.Icon(ft.Icons.SCHEDULE, color=COLOR_TEXT_SUB, size=12),
                                            schedule_text,
                                        ],
                                        spacing=5,
                                    ),
                                ],
                                spacing=3,
                                expand=True,
                            ),
                            _task_status_chip(task.status),
                            ft.Container(
                                content=ft.Row([toggle_text, toggle_icon], spacing=3, tight=True),
                                bgcolor=f"{COLOR_ACCENT}16",
                                border=ft.border.all(1, f"{COLOR_ACCENT}44"),
                                border_radius=8,
                                padding=ft.padding.symmetric(horizontal=10, vertical=7),
                                on_click=toggle_details,
                                ink=True,
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE, icon_color=COLOR_DANGER,
                                icon_size=20, on_click=delete_task, tooltip="Xóa video này khỏi danh sách",
                            ),
                        ],
                        spacing=10,
                    ),
                    details,
                ],
                spacing=0,
            ),
            bgcolor=COLOR_BG_DARK,
            border_radius=12,
            border=ft.border.all(1, COLOR_BORDER),
            padding=ft.padding.all(10),
        )
        row_ref[0] = card
        return card

    task_widgets = [build_task_row(t) for t in tasks]
    task_list_col.controls = task_widgets
    popup_alive = {"value": True}

    def _task_signature():
        return tuple(
            (t.id, t.status, str(t.schedule_time), t.title, t.youtube_url, t.error_message)
            for t in Task.select().where(Task.profile == profile.id).order_by(Task.id)
        )

    popup_signature = {"value": _task_signature()}

    def _rebuild_task_list_if_changed():
        sig = _task_signature()
        if sig == popup_signature["value"]:
            return
        popup_signature["value"] = sig
        task_rows_ref.clear()
        latest_tasks = list(Task.select().where(Task.profile == profile.id).order_by(Task.created_at))
        task_list_col.controls = [build_task_row(t) for t in latest_tasks]
        try:
            task_list_col.update()
        except Exception:
            try: page.update()
            except Exception: pass

    def _popup_refresh_loop():
        while popup_alive["value"]:
            time.sleep(2)
            try:
                _rebuild_task_list_if_changed()
            except Exception:
                pass

    threading.Thread(target=_popup_refresh_loop, daemon=True, name=f"profile_popup_refresh_{profile.id}").start()

    def handle_add_video(_):
        """Mo file dialog dung tkinter (native Windows, khong can Flet FilePicker)."""
        import threading
        import tkinter as tk
        from tkinter import filedialog

        def _pick_and_add():
            # Tao cua so tkinter an de lam host cho file dialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)  # Hien tren AlertDialog
            paths = filedialog.askopenfilenames(
                title="Chon video",
                filetypes=[
                    ("Video files", "*.mp4 *.mov *.avi *.mkv"),
                    ("All files", "*.*"),
                ],
            )
            root.destroy()

            if not paths:
                return
            for path in paths:
                try:
                    cached = cache_mgr.copy_to_cache(path)
                    new_task = Task.create(
                        profile=profile,
                        title=Path(path).stem[:80],
                        description="",
                        cached_path=str(cached),
                        schedule_time=None,  # Ép user đặt lịch thủ công
                    )
                    widget = build_task_row(new_task)
                    task_list_col.controls.append(widget)
                    popup_signature["value"] = _task_signature()
                except Exception as ex:
                    _show_snack(page, f"Loi copy: {ex}", COLOR_DANGER)
            try:
                page.update()
            except Exception:
                pass

        # Chay trong daemon thread de khong block UI
        threading.Thread(target=_pick_and_add, daemon=True).start()


    def handle_save(_):
        errors = []
        scheduled_count = 0
        validation_errors = []
        for row in task_rows_ref:
            try:
                task = Task.get_by_id(row["task_id"])
                new_title = row["title"].value.strip() or task.title
                new_schedule = row["sched"][0]

                # VALIDATION: tieu de + mo ta + tags + hashtags + lich
                task_issues = []
                if not new_title:
                    task_issues.append("thiếu tiêu đề")
                if not row["desc"].value.strip():
                    task_issues.append("thiếu mô tả")
                if not row["tags"].value.strip():
                    task_issues.append("thiếu tags")
                if not new_schedule:
                    task_issues.append("chưa đặt lịch đăng đăng")
                else:
                    tz = pytz.timezone(row["tz"].value or "Asia/Ho_Chi_Minh")
                    st = tz.localize(new_schedule) if new_schedule.tzinfo is None else new_schedule
                    if st.astimezone(pytz.utc) < dt.datetime.now(pytz.utc):
                        task_issues.append(f"lịch đã qua ({new_schedule.strftime('%d/%m/%Y %H:%M')})")
                if task_issues:
                    validation_errors.append(f"Task #{task.id}: {', '.join(task_issues)}")
                    continue

                task.title         = new_title
                task.description   = row["desc"].value.strip()
                task.tags          = row["tags"].value.strip()
                task.hashtags      = row["hashtags"].value.strip()
                task.made_for_kids = (row["kids"].value == "yes")
                task.paid_promotion = bool(row["paid"].value)
                task.altered_content = (row["altered"].value == "yes")
                task.timezone      = row["tz"].value or "UTC"
                task.schedule_time = new_schedule
                task.save()

                # Register/update scheduler immediately after saving.
                # Before this, newly edited tasks were only scheduled after app restart.
                from core.scheduler import TaskScheduler
                if task.status == STATUS_PENDING and task.schedule_time:
                    if TaskScheduler.schedule_task(task):
                        scheduled_count += 1
                else:
                    TaskScheduler.remove_task(task.id)
            except Task.DoesNotExist:
                pass
            except Exception as ex:
                errors.append(str(ex))

        popup_alive["value"] = False
        close_dialog(page, dialog)
        on_saved()
        show_errors = errors + validation_errors
        if show_errors:
            _show_snack(page, "Lỗi lưu: " + "; ".join(show_errors)[:300], COLOR_DANGER)
        elif scheduled_count:
            _show_snack(page, f"Đã lưu và hẹn giờ {scheduled_count} task.", COLOR_SUCCESS)

    # ── Assemble popup content ──
    total_count = Task.select().where(Task.profile == profile.id).count()
    waiting_count = Task.select().where((Task.profile == profile.id) & (Task.status == STATUS_PENDING)).count()
    running_count = Task.select().where((Task.profile == profile.id) & (Task.status == STATUS_RUNNING)).count()
    completed_count = Task.select().where((Task.profile == profile.id) & (Task.status == STATUS_COMPLETED)).count()
    failed_count = Task.select().where((Task.profile == profile.id) & (Task.status == STATUS_FAILED)).count()

    def _summary_chip(label: str, value: int, color: str, icon):
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, color=color, size=14),
                    ft.Text(f"{label}: {value}", size=12, color=color, weight=ft.FontWeight.W_700),
                ],
                spacing=6,
                tight=True,
            ),
            bgcolor=f"{color}18",
            border=ft.border.all(1, f"{color}44"),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=10, vertical=7),
        )

    summary_bar = ft.Container(
        content=ft.Row(
            [
                _summary_chip("Tổng", total_count, COLOR_TEXT_SUB, ft.Icons.VIDEO_LIBRARY_OUTLINED),
                _summary_chip("Đang đợi", waiting_count, COLOR_WARNING, ft.Icons.SCHEDULE),
                _summary_chip("Đang đăng", running_count, COLOR_PRIMARY, ft.Icons.SYNC),
                _summary_chip("Đã đăng", completed_count, COLOR_SUCCESS, ft.Icons.CHECK_CIRCLE_OUTLINE),
                _summary_chip("Lỗi", failed_count, COLOR_DANGER, ft.Icons.ERROR_OUTLINE),
            ],
            spacing=8,
            wrap=True,
        ),
        bgcolor=COLOR_BG_SIDEBAR,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )

    helper_bar = ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.TIPS_AND_UPDATES_OUTLINED, color=COLOR_ACCENT, size=16),
                ft.Text(
                    "Mỗi video là một thẻ riêng: nhập thông tin, đặt lịch, rồi chọn 3 khai báo bắt buộc của YouTube.",
                    size=12, color=COLOR_TEXT_SUB, expand=True,
                ),
            ],
            spacing=8,
        ),
        bgcolor=COLOR_BG_SIDEBAR,
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=12, vertical=9),
    )

    popup_content = ft.Column(
        [
            info_bar,
            summary_bar,
            chrome_folder_bar,
            ft.ElevatedButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=15),
                     ft.Text("CHỌN FILE VIDEO TỪ MÁY ĐỂ ĐĂNG...", size=13, weight=ft.FontWeight.W_600)],
                    spacing=8,
                ),
                style=ft.ButtonStyle(
                    bgcolor=COLOR_SUCCESS, color=COLOR_TEXT_MAIN,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.padding.symmetric(horizontal=20, vertical=12),
                ),
                on_click=handle_add_video,
                width=float("inf"),
            ),
            helper_bar,
            ft.Container(
                content=task_list_col,
                height=min(640, max(260, len(task_widgets) * 86 + 40)),
            ),
        ],
        spacing=10,
        width=1220,
    )

    def _close_popup(_=None):
        """Dong popup (FilePicker la global, khong xoa)."""
        popup_alive["value"] = False
        close_dialog(page, dialog)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.VIDEO_CAMERA_BACK, color=COLOR_ACCENT),
                ft.Text(f"HO SO KENH: {profile.name.upper()}", color=COLOR_TEXT_MAIN,
                        weight=ft.FontWeight.W_700),
            ],
            spacing=10,
        ),
        bgcolor=COLOR_BG_CARD,
        content=ft.Container(content=popup_content, padding=ft.padding.only(top=4)),
        actions=[
            ft.TextButton("Huy Bo", on_click=_close_popup,
                          style=ft.ButtonStyle(color=COLOR_TEXT_SUB)),
            ft.ElevatedButton(
                "Luu Thay Doi",
                style=ft.ButtonStyle(
                    bgcolor=COLOR_PRIMARY, color=COLOR_TEXT_MAIN,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
                on_click=handle_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    open_dialog(page, dialog)


def _open_folder(path: Path):
    """Mo thu muc trong Windows Explorer."""
    import subprocess
    try:
        subprocess.Popen(["explorer", str(path)])
    except Exception:
        pass


def _confirm_reset_chrome(page: ft.Page, profile: Profile):
    """Xac nhan reset Chrome data (xoa cookie)."""
    from core.chrome_manager import ChromeManager

    def do_reset(_):
        ChromeManager.reset_chrome_data(profile)
        close_dialog(page, dlg)
        _show_snack(page, f"Da reset Chrome data cho '{profile.name}'", COLOR_SUCCESS)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Reset Chrome Data?", color=COLOR_DANGER, weight=ft.FontWeight.W_700),
        content=ft.Text(
            f"Xoa toan bo cookie, session, lich su cua '{profile.name}'?\n"
            "Ban se phai dang nhap lai Google.",
            color=COLOR_TEXT_SUB,
        ),
        bgcolor=COLOR_BG_CARD,
        actions=[
            ft.TextButton("Huy", on_click=lambda _: close_dialog(page, dlg),
                          style=ft.ButtonStyle(color=COLOR_TEXT_SUB)),
            ft.ElevatedButton(
                "Xoa het",
                style=ft.ButtonStyle(bgcolor=COLOR_DANGER, color=COLOR_TEXT_MAIN,
                                     shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=do_reset,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    open_dialog(page, dlg)


def _show_snack(page: ft.Page, msg: str, color: str = COLOR_SUCCESS):
    """Hiển thị SnackBar thông báo. Flet 0.84: thêm vào overlay + open=True."""
    snack = ft.SnackBar(
        content=ft.Text(msg, color=COLOR_TEXT_MAIN),
        bgcolor=color,
        duration=3000,
        open=True,
    )
    page.overlay.append(snack)
    try:
        page.update()
    except Exception:
        pass


# ══════════════════════════════════════════
# DASHBOARD VIEW
# ══════════════════════════════════════════

class DashboardView(ft.Container):
    """
    DashboardView -- Grid hien thi tat ca Profile.

    Features:
      - Wrap grid responsive
      - Nut Them kenh moi + Chrome profile tu dong tao
      - Chrome launch/close per card (Thread rieng, khong block UI)
      - Refresh sau moi hanh dong
    """

    def __init__(
        self,
        page: ft.Page,
        on_cache_change: Optional[Callable] = None,
        on_chrome_count_change: Optional[Callable[[int], None]] = None,
    ):
        self._page                  = page
        self.on_cache_change        = on_cache_change
        self.on_chrome_count_change = on_chrome_count_change
        self._auto_refresh_running  = True

        self._cards_row = ft.Row(wrap=True, spacing=16, run_spacing=16)

        add_btn = ft.ElevatedButton(
            content=ft.Row(
                [ft.Icon(ft.Icons.ADD, size=18), ft.Text("Them kenh moi", size=13)],
                spacing=8,
            ),
            style=ft.ButtonStyle(
                bgcolor=COLOR_ACCENT, color=COLOR_TEXT_MAIN,
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.padding.symmetric(horizontal=18, vertical=12),
            ),
            on_click=self._handle_add,
        )

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Quan ly Kenh", size=22, weight=ft.FontWeight.W_800, color=COLOR_TEXT_MAIN),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.OPEN_IN_BROWSER, color=COLOR_CHROME, size=14),
                                ft.Text("Moi kenh co Chrome profile cookie rieng biet", size=12, color=COLOR_TEXT_SUB),
                            ],
                            spacing=6,
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(expand=True),
                add_btn,
            ],
        )

        super().__init__(
            content=ft.Column(
                [
                    header,
                    ft.Divider(height=1, color=COLOR_BORDER),
                    ft.Container(
                        content=ft.Column([self._cards_row], scroll=ft.ScrollMode.AUTO),
                        expand=True,
                    ),
                ],
                spacing=20,
            ),
            expand=True,
            padding=ft.padding.all(24),
        )

        self.refresh()
        self._start_auto_refresh()

    # ──────────────────────────────────────────

    def _start_auto_refresh(self):
        """Keep cards/status counters fresh while uploads run in background."""
        def _loop():
            while self._auto_refresh_running:
                time.sleep(3)
                try:
                    self.refresh()
                except Exception:
                    pass
        threading.Thread(target=_loop, daemon=True, name="dashboard_auto_refresh").start()

    # ──────────────────────────────────────────

    def refresh(self):
        profiles = DatabaseManager.get_all_profiles()
        self._cards_row.controls = [
            BoxCard(
                profile=p,
                on_detail=self._handle_detail,
                on_delete=self._handle_delete,
                on_chrome_studio=self._handle_chrome_studio,
                on_chrome_api_key=self._handle_chrome_api_key,
                on_chrome_close=self._handle_chrome_close,
                on_run_now=self._handle_run_now,
                page=self._page,
                on_refresh=self.refresh,
            )
            for p in profiles
        ]
        # Luôn gọi page.update() để đảm bảo UI được refresh
        # (hoạt động từ cả main thread lẫn daemon thread)
        try:
            self._page.update()
        except Exception:
            pass

        if self.on_cache_change:
            try:
                self.on_cache_change()
            except Exception:
                pass
        self._update_chrome_count()

    def _handle_add(self, _):
        AddProfileDialog(self._page, on_created=lambda p: self.refresh())

    def _handle_detail(self, profile_id: int):
        try:
            profile = Profile.get_by_id(profile_id)
            ProfilePopup(
                self._page, profile,
                on_saved=self.refresh,
            )
        except Profile.DoesNotExist:
            pass

    def _handle_delete(self, profile_id: int):
        from core.chrome_manager import ChromeManager
        ChromeManager.close(profile_id)
        DatabaseManager.delete_profile(profile_id)
        self.refresh()

    def _handle_chrome_studio(self, profile_id: int):
        self._launch_chrome(profile_id, "https://studio.youtube.com")

    def _handle_chrome_api_key(self, profile_id: int):
        self._launch_chrome(profile_id, "https://console.cloud.google.com/apis/credentials")

    def _launch_chrome(self, profile_id: int, start_url: str):
        """Mo Chrome trong daemon thread — khong block UI."""
        import threading
        from core.chrome_manager import ChromeManager

        def _launch():
            try:
                profile = Profile.get_by_id(profile_id)
                ChromeManager.launch(
                    profile=profile,
                    start_url=start_url,
                    on_close=self._on_chrome_closed,
                )
                self.refresh()
            except FileNotFoundError as ex:
                _show_snack(self._page, str(ex), COLOR_DANGER)
                self.refresh()
            except RuntimeError as ex:
                _show_snack(self._page, str(ex), COLOR_WARNING)
            except Exception as ex:
                _show_snack(self._page, f"Loi mo Chrome: {ex}", COLOR_DANGER)
                self.refresh()

        threading.Thread(target=_launch, daemon=True, name=f"chrome_{profile_id}").start()

    def _handle_run_now(self, profile_id: int):
        """Run only due tasks; keep future scheduled tasks waiting for their schedule_time."""
        import threading
        from core.youtube_worker import YouTubeWorker

        def _is_due(task: Task) -> bool:
            # Nếu chưa đặt lịch đăng đăng → không cho chạy, ép user phải đặt giờ
            if not task.schedule_time:
                return False
            tz = pytz.timezone(task.timezone or "Asia/Ho_Chi_Minh")
            run_time = tz.localize(task.schedule_time) if task.schedule_time.tzinfo is None else task.schedule_time
            return run_time.astimezone(pytz.utc) <= dt.datetime.now(pytz.utc)

        def _run():
            try:
                profile = Profile.get_by_id(profile_id)
                candidates = list(Task.select().where(
                    (Task.profile == profile.id) &
                    (Task.status.in_(["Pending", "Failed"]))
                ).order_by(Task.schedule_time, Task.created_at))

                # ── PRE-FLIGHT VALIDATION ──
                invalid_tasks = []
                for t in candidates:
                    issues = []
                    if not (t.title or "").strip():
                        issues.append("thiếu tiêu đề")
                    if not (t.description or "").strip():
                        issues.append("thiếu mô tả")
                    if not (t.tags or "").strip():
                        issues.append("thiếu tags")
                    if not (t.hashtags or "").strip():
                    if not (t.cached_path or "").strip():
                        issues.append("chưa chọn video")
                    elif not Path(t.cached_path).exists():
                        issues.append(f"file video không tồn tại: {Path(t.cached_path).name}")
                    if not t.schedule_time:
                        issues.append("chưa đặt lịch đăng đăng")
                    else:
                        tz = pytz.timezone(t.timezone or "Asia/Ho_Chi_Minh")
                        st = tz.localize(t.schedule_time) if t.schedule_time.tzinfo is None else t.schedule_time
                        if st.astimezone(pytz.utc) < dt.datetime.now(pytz.utc):
                            issues.append(f"lịch đã qua ({t.schedule_time.strftime('%d/%m/%Y %H:%M')})")
                    if issues:
                        invalid_tasks.append((t, issues))

                if invalid_tasks:
                    lines = [f"  Task #{t.id} '{t.title or 'Chưa đặt tên'}' - {', '.join(iss)}" for t, iss in invalid_tasks]
                    _show_snack(self._page, "Task thiếu dữ liệu:\n" + "\n".join(lines), COLOR_DANGER)

                tasks_to_run = [task for task in candidates if _is_due(task) and not any(task.id == ivt.id for ivt, _ in invalid_tasks)]
                skipped_count = len(invalid_tasks)
                future_count = len(candidates) - len(tasks_to_run) - skipped_count

                if not tasks_to_run:
                    parts = []
                    if future_count:
                        parts.append(f"{future_count} task hẹn giờ tương lai")
                    if skipped_count:
                        parts.append(f"{skipped_count} task thiếu dữ liệu")
                    _show_snack(self._page, "Không có task hợp lệ để chạy. " + ", ".join(parts) + ".", COLOR_WARNING)
                    return

                # Reset Failed → Pending trước khi chạy lại, nhưng chỉ với task đã tới hạn
                for task in tasks_to_run:
                    if task.status == "Failed":
                        task.status = "Pending"
                        task.error_message = ""
                        task.save()

                msg = f"Đang chạy {len(tasks_to_run)} task đã tới giờ..."
                if future_count:
                    msg += f" Bỏ qua {future_count} task hẹn giờ tương lai."
                _show_snack(self._page, msg, COLOR_SUCCESS)

                for task in tasks_to_run:
                    worker = YouTubeWorker(
                        task,
                        on_done=lambda url: self.refresh(),
                        on_error=lambda err: self.refresh(),
                    )
                    worker.start()
                self.refresh()
            except Exception as ex:
                _show_snack(self._page, f"Lỗi chạy task: {ex}", COLOR_DANGER)

        threading.Thread(target=_run, daemon=True).start()


    def _handle_chrome_close(self, profile_id: int):
        from core.chrome_manager import ChromeManager
        ChromeManager.close(profile_id)
        self.refresh()

    def _on_chrome_closed(self, profile_id: int):
        """Callback khi Chrome bi dong (user click X tren cua so Chrome).
        Gọi từ daemon thread watcher — refresh() sẽ gọi page.update() an toàn.
        """
        self.refresh()

    def _update_chrome_count(self):
        from core.chrome_manager import ChromeManager
        count = sum(1 for v in ChromeManager.get_status().values() if v)
        if self.on_chrome_count_change:
            try:
                self.on_chrome_count_change(count)
            except Exception:
                pass

