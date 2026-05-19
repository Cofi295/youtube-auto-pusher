"""
ui/setup_wizard.py
==================
SetupWizard — First-run 3-step wizard cho nguoi dung moi.

Cac buoc:
  Step 1: Chao mung + gioi thieu ung dung
  Step 2: Ket noi YouTube (OAuth flow)
  Step 3: Hoan tat + hien thi thong tin kenh

Thiet ke:
  - Full-screen overlay (khong block click nen, nhung de chu y)
  - Chay OAuth trong thread rieng (khong block UI)
  - Loading spinner + status text trong luc cho
  - Auto-tao Profile sau khi auth thanh cong
"""

import threading
import flet as ft
from pathlib import Path
from typing import Callable, Optional

from core.database import DatabaseManager, Profile
from core.oauth_helper import OAuthHelper

from ui.components import (
    COLOR_BG_DARK, COLOR_BG_CARD, COLOR_TEXT_MAIN, COLOR_TEXT_SUB,
    COLOR_ACCENT, COLOR_BORDER, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING,
    COLOR_PRIMARY, COLOR_CHROME,
)

BASE_DIR = Path(__file__).resolve().parent.parent


class SetupWizard:
    """
    First-run Wizard — hien thi khi chua co Profile nao.

    Usage:
        wizard = SetupWizard(page, on_complete=callback)
        wizard.show()
    """

    STEP_WELCOME = 0
    STEP_CONNECT = 1
    STEP_DONE    = 2

    def __init__(self, page: ft.Page, on_complete: Optional[Callable] = None):
        self.page         = page
        self.on_complete  = on_complete
        self.current_step = self.STEP_WELCOME
        self.profile      = None
        self.channel_info = {}

        self._overlay = None
        self._content_area = ft.Container()

    def show(self):
        """Hien thi wizard duoi dang full-screen overlay."""
        self._build_overlay()
        self.page.overlay.append(self._overlay)
        self._go_step(self.STEP_WELCOME)
        self.page.update()

    def close(self):
        """Dong wizard."""
        if self._overlay and self._overlay in self.page.overlay:
            self.page.overlay.remove(self._overlay)
            try:
                self.page.update()
            except Exception:
                pass

    def _build_overlay(self):
        """Tao overlay container."""
        self._overlay = ft.Container(
            content=ft.Container(
                content=self._content_area,
                width=560,
                bgcolor=COLOR_BG_CARD,
                border_radius=20,
                border=ft.border.all(2, COLOR_ACCENT),
                shadow=ft.BoxShadow(
                    spread_radius=4, blur_radius=40,
                    color="#00000099", offset=ft.Offset(0, 8),
                ),
                padding=ft.padding.all(28),
            ),
            bgcolor="#00000088",
            alignment=ft.Alignment(0, 0),
            expand=True,
            on_click=lambda _: None,
        )

    def _go_step(self, step: int):
        """Chuyen buoc wizard."""
        self.current_step = step
        if step == self.STEP_WELCOME:
            self._content_area.content = self._build_welcome()
        elif step == self.STEP_CONNECT:
            self._content_area.content = self._build_connect()
        elif step == self.STEP_DONE:
            self._content_area.content = self._build_done()
        try:
            self.page.update()
        except Exception:
            pass

    # ──────────────────────────────────────────
    # STEP 1: WELCOME
    # ──────────────────────────────────────────

    def _build_welcome(self) -> ft.Column:
        name_field = ft.TextField(
            label="Ten kenh YouTube cua ban *",
            label_style=ft.TextStyle(color=COLOR_TEXT_SUB),
            text_style=ft.TextStyle(color=COLOR_TEXT_MAIN),
            bgcolor=COLOR_BG_DARK,
            border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT,
            border_radius=12,
            hint_text="Vi du: Kenh Gaming Cua Toi",
            hint_style=ft.TextStyle(color="#4A4F70"),
            text_size=16,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=14),
        )

        info_box = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, color=COLOR_ACCENT, size=18),
                    ft.Text("Ung dung se giup ban:", size=13, color=COLOR_TEXT_SUB, weight=ft.FontWeight.W_600),
                ], spacing=10),
                ft.Text("  • Tu dong upload video len YouTube", size=12, color=COLOR_TEXT_SUB),
                ft.Text("  • Len lich dang theo thoi gian", size=12, color=COLOR_TEXT_SUB),
                ft.Text("  • Quan ly nhieu kenh cung luc", size=12, color=COLOR_TEXT_SUB),
                ft.Text("  • Thong bao Telegram khi xong", size=12, color=COLOR_TEXT_SUB),
            ], spacing=6),
            bgcolor=f"{COLOR_ACCENT}11",
            border_radius=12,
            padding=ft.padding.all(16),
            border=ft.border.all(1, f"{COLOR_ACCENT}33"),
        )

        error_text = ft.Text("", color=COLOR_DANGER, size=13)

        def do_next(_):
            name = name_field.value.strip()
            if not name:
                error_text.value = "Vui long nhap ten kenh!"
                try:
                    error_text.update()
                except Exception:
                    pass
                return

            self.profile = DatabaseManager.create_profile(name=name)
            self._go_step(self.STEP_CONNECT)

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.VIDEO_CAMERA_FRONT_OUTLINED, color=COLOR_ACCENT, size=32),
                ft.Column([
                    ft.Text("Chao mung den voi", size=13, color=COLOR_TEXT_SUB),
                    ft.Text("YouTube Auto Pusher", size=24, weight=ft.FontWeight.W_800, color=COLOR_TEXT_MAIN),
                ], spacing=2),
            ], spacing=16),

            ft.Divider(height=1, color=COLOR_BORDER),

            ft.Text(
                "Ung dung tu dong day video len YouTube."
                " Chi can ket noi tai khoan Google la san sang su dung!",
                size=14, color=COLOR_TEXT_SUB,
            ),

            ft.Container(height=12),

            name_field,

            info_box,

            error_text,

            ft.Container(height=16),

            ft.Row([
                ft.Container(expand=True),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ARROW_FORWARD, size=18),
                        ft.Text("Tiep tuc: Ket noi YouTube", size=14, weight=ft.FontWeight.W_600),
                    ], spacing=10),
                    style=ft.ButtonStyle(
                        bgcolor=COLOR_ACCENT, color=COLOR_TEXT_MAIN,
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.padding.symmetric(horizontal=28, vertical=14),
                    ),
                    on_click=do_next,
                ),
            ], spacing=0),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # ──────────────────────────────────────────
    # STEP 2: CONNECT YOUTUBE (OAUTH)
    # ──────────────────────────────────────────

    def _build_connect(self) -> ft.Column:
        status_ref = [ft.Text("San sang ket noi...", size=13, color=COLOR_TEXT_SUB)]
        spinner = ft.ProgressRing(width=24, height=24, stroke_width=3, color=COLOR_ACCENT)
        spinner.visible = False

        connect_btn = ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.LINK, size=18),
                ft.Text("Ket noi YouTube cua toi", size=14, weight=ft.FontWeight.W_600),
            ], spacing=10),
            style=ft.ButtonStyle(
                bgcolor=COLOR_CHROME, color=COLOR_TEXT_MAIN,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.padding.symmetric(horizontal=28, vertical=14),
            ),
            width=float("inf"),
        )

        help_box = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.HELP_OUTLINE, color=COLOR_WARNING, size=16),
                    ft.Text("Se xay gi?", size=12, color=COLOR_TEXT_SUB, weight=ft.FontWeight.W_600),
                ], spacing=8),
                ft.Text("  1. Trinh duyệt se mo tu dong", size=11, color=COLOR_TEXT_SUB),
                ft.Text("  2. Ban dang nhap Gmail cua minh", size=11, color=COLOR_TEXT_SUB),
                ft.Text("  3. Cho phep truy cap YouTube", size=11, color=COLOR_TEXT_SUB),
                ft.Text("  4. Tro lai day -> Xong!", size=11, color=COLOR_TEXT_SUB),
            ], spacing=4),
            bgcolor=f"{COLOR_WARNING}11",
            border_radius=10,
            padding=ft.padding.all(12),
            border=ft.border.all(1, f"{COLOR_WARNING}33"),
        )

        def do_connect(_):
            connect_btn.disabled = True
            spinner.visible = True
            status_ref[0].value = "Dang mo trinh duyet... Vui long doi"
            status_ref[0].color = COLOR_PRIMARY
            try:
                connect_btn.update()
                spinner.update()
                status_ref[0].update()
            except Exception:
                pass

            def _run_oauth():
                try:
                    info = OAuthHelper.quick_connect(self.profile)
                    self.channel_info = info
                    if info:
                        self.page.run_task(self._go_step, self.STEP_DONE)
                    else:
                        status_ref[0].value = "Khong the lay thong tin kenh. Thu lai?"
                        status_ref[0].color = COLOR_DANGER
                        connect_btn.disabled = False
                        spinner.visible = False
                        try:
                            self.page.update()
                        except Exception:
                            pass
                except FileNotFoundError as ex:
                    status_ref[0].value = f"Loi: Khong tim thay API key. {ex}"
                    status_ref[0].color = COLOR_DANGER
                    connect_btn.disabled = False
                    spinner.visible = False
                    try:
                        self.page.update()
                    except Exception:
                        pass
                except Exception as ex:
                    status_ref[0].value = f"Loi ket noi: {ex}"
                    status_ref[0].color = COLOR_DANGER
                    connect_btn.disabled = False
                    spinner.visible = False
                    try:
                        self.page.update()
                    except Exception:
                        pass

            threading.Thread(target=_run_oauth, daemon=True).start()

        connect_btn.on_click = do_connect

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.LINK, color=COLOR_CHROME, size=28),
                ft.Text("Ket noi YouTube", size=22, weight=ft.FontWeight.W_800, color=COLOR_TEXT_MAIN),
            ], spacing=12),

            ft.Divider(height=1, color=COLOR_BORDER),

            ft.Text(
                f"Kenh: {self.profile.name}",
                size=15, color=COLOR_ACCENT, weight=ft.FontWeight.W_600,
            ),

            ft.Container(height=16),

            ft.Container(
                content=ft.Row([spinner, status_ref[0]], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=COLOR_BG_DARK,
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=20, vertical=16),
                border=ft.border.all(1, COLOR_BORDER),
                width=float("inf"),
            ),

            ft.Container(height=12),

            connect_btn,

            help_box,

        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # ──────────────────────────────────────────
    # STEP 3: DONE
    # ──────────────────────────────────────────

    def _build_done(self) -> ft.Column:
        channel_name = self.channel_info.get("title", self.profile.name)
        subs = self.channel_info.get("subscriber_count", 0)
        videos = self.channel_info.get("video_count", 0)

        stats_row = ft.Row([
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{subs:,}", size=20, weight=ft.FontWeight.W_800, color=COLOR_TEXT_MAIN),
                    ft.Text("Nguoi theo doi", size=11, color=COLOR_TEXT_SUB),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=COLOR_BG_DARK,
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                expand=True,
                alignment=ft.Alignment(0, 0),
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text(str(videos), size=20, weight=ft.FontWeight.W_800, color=COLOR_TEXT_MAIN),
                    ft.Text("Video", size=11, color=COLOR_TEXT_SUB),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=COLOR_BG_DARK,
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                expand=True,
                alignment=ft.Alignment(0, 0),
            ),
        ], spacing=12)

        next_steps = ft.Container(
            content=ft.Column([
                ft.Text("Tiep theo ban co the:", size=13, color=COLOR_TEXT_SUB, weight=ft.FontWeight.W_600),
                ft.Text("  1. Nhem vao the kenh > Tasks > Them video", size=12, color=COLOR_TEXT_SUB),
                ft.Text("  2. Chinh sua tieu de, mo ta, tag", size=12, color=COLOR_TEXT_SUB),
                ft.Text("  3. Dat lich hoac an \"Chay ngay\"", size=12, color=COLOR_TEXT_SUB),
            ], spacing=4),
            bgcolor=f"{COLOR_SUCCESS}11",
            border_radius=10,
            padding=ft.padding.all(14),
            border=ft.border.all(1, f"{COLOR_SUCCESS}33"),
        )

        def do_finish(_):
            self.close()
            if self.on_complete:
                self.on_complete()

        return ft.Column([
            ft.Container(
                content=ft.Icon(ft.Icons.CHECK_CIRCLE, size=56, color=COLOR_SUCCESS),
                bgcolor=f"{COLOR_SUCCESS}18",
                border_radius=ft.border_radius.circular(30),
                width=80, height=80,
                alignment=ft.Alignment(0, 0),
            ),

            ft.Text("Ket noi thanh cong!", size=22, weight=ft.FontWeight.W_800, color=COLOR_SUCCESS),

            ft.Text(
                f"Kenh \"{channel_name}\" da san sang su dung.",
                size=14, color=COLOR_TEXT_SUB,
            ),

            ft.Container(height=12),

            stats_row,

            next_steps,

            ft.Container(height=16),

            ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ROCKET_LAUNCH_OUTLINED, size=18, color=COLOR_TEXT_MAIN),
                    ft.Text("Bat dau su dung!", size=14, weight=ft.FontWeight.W_600),
                ], spacing=10),
                style=ft.ButtonStyle(
                    bgcolor=COLOR_SUCCESS, color=COLOR_TEXT_MAIN,
                    shape=ft.RoundedRectangleBorder(radius=12),
                    padding=ft.padding.symmetric(horizontal=32, vertical=14),
                ),
                on_click=do_finish,
                width=float("inf"),
            ),

        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
