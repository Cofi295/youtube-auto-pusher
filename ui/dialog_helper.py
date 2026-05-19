"""
ui/dialog_helper.py
===================
Helper mở/đóng AlertDialog cho Flet 0.84.

API Flet 0.84 cho dialog:
  - page.show_dialog(dialog)  → mở dialog (push lên dialog stack)
  - page.pop_dialog()         → đóng dialog (pop khỏi stack)

Lưu ý: page.open() / page.close() là Flet 0.21.x, không tồn tại trong 0.84.
        page.dialog = ... là Flet pre-0.21, cũng không còn.
"""

import flet as ft


def open_dialog(page: ft.Page, dialog: ft.AlertDialog):
    """Mở AlertDialog – dùng page.show_dialog() chuẩn Flet 0.84."""
    page.show_dialog(dialog)


def close_dialog(page: ft.Page, dialog: ft.AlertDialog):
    """Đóng AlertDialog – dùng page.pop_dialog() chuẩn Flet 0.84."""
    page.pop_dialog()
