"""ST Stock Opname - offline-first Kivy application for Android."""
from __future__ import annotations

import json
import os
import webbrowser
from pathlib import Path
from urllib.parse import quote

from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from api_repository import ApiRepository
from repository import LocalJsonRepository, build_report, decimal_value, display_number

__version__ = "1.1.0"

# Arinex / ST visual palette
NAVY = (0.025, 0.105, 0.235, 1)
BLUE = (0.035, 0.31, 0.61, 1)
BLUE2 = (0.075, 0.40, 0.72, 1)
GOLD = (1.0, 0.72, 0.05, 1)
GREEN = (0.0, 0.57, 0.29, 1)
RED = (0.82, 0.12, 0.15, 1)
BG = (0.94, 0.96, 0.98, 1)
INK = (0.10, 0.15, 0.22, 1)
MUTED = (0.40, 0.46, 0.54, 1)
WHITE = (1, 1, 1, 1)
PALE_BLUE = (0.89, 0.94, 0.99, 1)


def ui_label(text, size=14, color=INK, bold=False, height=None, halign="left"):
    widget = Label(
        text=str(text), font_size=sp(size), color=color, bold=bold,
        halign=halign, valign="middle", size_hint_y=None,
        height=dp(height if height is not None else max(28, size * 1.75)),
    )
    widget.bind(size=lambda inst, _value: setattr(inst, "text_size", (inst.width, None)))
    return widget


def ui_field(hint, text="", multiline=False, input_filter=None, password=False, height=46):
    return TextInput(
        hint_text=hint, text=str(text or ""), multiline=multiline,
        input_filter=input_filter, password=password,
        size_hint_y=None, height=dp(height), padding=[dp(12), dp(10)],
        background_normal="", background_active="",
        background_color=(0.975, 0.982, 0.992, 1),
        foreground_color=INK, cursor_color=BLUE,
        hint_text_color=(0.48, 0.53, 0.60, 1), font_size=sp(14),
    )


def ui_button(text, callback, color=BLUE, height=46, width=None, font_size=14):
    widget = Button(
        text=text, size_hint_y=None, height=dp(height),
        size_hint_x=1 if width is None else None,
        width=dp(width) if width is not None else 0,
        background_normal="", background_down="",
        background_color=color, color=WHITE, bold=True,
        font_size=sp(font_size),
    )
    widget.bind(on_release=callback)
    return widget


class Card(BoxLayout):
    """Simple white container for a product/session row."""
    def __init__(self, height=100, **kwargs):
        super().__init__(orientation=kwargs.pop("orientation", "vertical"), **kwargs)
        self.size_hint_y = None
        self.height = dp(height)
        self.padding = dp(11)
        self.spacing = dp(6)
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*WHITE)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._sync_rect, size=self._sync_rect)

    def _sync_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class BaseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.page = BoxLayout(orientation="vertical", spacing=dp(8), padding=[dp(11), dp(10)])
        self.add_widget(self.page)

    @property
    def app(self):
        return App.get_running_app()

    def reset(self):
        self.page.clear_widgets()

    def header(self, title, subtitle=""):
        bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(66), spacing=dp(8), padding=[dp(10), dp(5)])
        left = BoxLayout(orientation="vertical", spacing=0)
        left.add_widget(ui_label(title, 18, WHITE, True, 30))
        if subtitle:
            left.add_widget(ui_label(subtitle, 10, (0.82, 0.89, 0.97, 1), False, 21))
        bar.add_widget(left)
        back = ui_button("⌂", lambda *_: self.app.go("dashboard"), color=(0.10, 0.22, 0.38, 1), height=44, width=48, font_size=20)
        back.size_hint_x = None
        bar.add_widget(back)
        with bar.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*NAVY)
            rect = RoundedRectangle(pos=bar.pos, size=bar.size, radius=[dp(13)])
        bar.bind(pos=lambda *_: setattr(rect, "pos", bar.pos), size=lambda *_: setattr(rect, "size", bar.size))
        self.page.add_widget(bar)

    def body_scroll(self):
        scroller = ScrollView(do_scroll_x=False, bar_width=dp(4), scroll_type=["bars", "content"])
        content = BoxLayout(orientation="vertical", spacing=dp(9), padding=[dp(1), dp(4), dp(1), dp(12)], size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        scroller.add_widget(content)
        self.page.add_widget(scroller)
        return content


class DashboardScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.reset()
        mode = "OFFLINE · JSON LOKAL" if self.app.mode == "local" else "ONLINE · API ARINEX"
        self.header("ST STOCK OPNAME", f"{mode}  |  v{__version__}")
        body = self.body_scroll()
        products = self.app.repo.list_products()
        sessions = self.app.repo.list_sessions()
        active = sum(1 for item in sessions if item.get("status") in ("draft", "confirmed", "in_progress"))
        stats = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(82))
        stats.add_widget(self.stat_card("MASTER PRODUK", str(len(products))))
        stats.add_widget(self.stat_card("SO AKTIF", str(active)))
        body.add_widget(stats)
        if getattr(self.app.local_repo, "recovery_warning", ""):
            body.add_widget(ui_label(self.app.local_repo.recovery_warning, 10, RED, True, 64))
        if getattr(self.app, "api_restore_warning", ""):
            body.add_widget(ui_label(self.app.api_restore_warning, 10, RED, True, 66))
        body.add_widget(ui_label("MENU UTAMA", 12, MUTED, True, 23))
        body.add_widget(ui_button("GENERAL  ·  INPUT PRODUK", lambda *_: self.app.go("products"), BLUE, 54))
        body.add_widget(ui_button("SETUP STOCK OPNAME", lambda *_: self.app.go("setup"), BLUE2, 54))
        body.add_widget(ui_button("MULAI / RIWAYAT STOCK OPNAME", lambda *_: self.app.go("sessions"), GREEN, 54))
        body.add_widget(ui_button("ANALISIS SELISIH PER SHIFT", lambda *_: self.app.go("analytics"), (0.34, 0.29, 0.56, 1), 54))
        body.add_widget(ui_button("PENGATURAN & INTEGRASI API", lambda *_: self.app.go("settings"), (0.22, 0.30, 0.40, 1), 48))
        body.add_widget(ui_label("ATURAN PERHITUNGAN", 13, INK, True, 26))
        body.add_widget(ui_label(
            "• Fisik total dihitung dari F1 + F2 + F3 + F4 + F5 untuk SKU yang sama.\n"
            "• Selisih = total fisik SKU tersebut − stok sistem SKU tersebut.\n"
            "• Selisih antar-SKU tidak pernah dijumlahkan.\n"
            "• Data offline tersimpan di perangkat; API hanya dipakai bila diaktifkan.",
            12, MUTED, False, 104,
        ))

    def stat_card(self, title, value):
        card = Card(height=84)
        card.add_widget(ui_label(title, 10, MUTED, True, 20))
        card.add_widget(ui_label(value, 24, NAVY, True, 32))
        return card


class ProductScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.reset()
        self.header("GENERAL · PRODUK", "Master barang dan stok sistem")
        body = self.body_scroll()
        body.add_widget(ui_label("INPUT PRODUK", 13, MUTED, True, 23))
        self.sku = ui_field("SKU / kode produk")
        self.barcode = ui_field("Barcode (opsional)")
        self.name = ui_field("Nama produk")
        self.unit = ui_field("Satuan", "pcs")
        self.stock = ui_field("Stok sistem", "0", input_filter="float")
        for widget in (self.sku, self.barcode, self.name, self.unit, self.stock):
            body.add_widget(widget)
        body.add_widget(ui_button("SIMPAN PRODUK", self.save_product, GREEN))
        body.add_widget(ui_label("DAFTAR PRODUK", 13, MUTED, True, 23))
        self.search = ui_field("Cari SKU, nama, atau barcode")
        self.search.bind(text=lambda *_: self.load_products())
        body.add_widget(self.search)
        self.products_box = BoxLayout(orientation="vertical", spacing=dp(7), size_hint_y=None)
        self.products_box.bind(minimum_height=self.products_box.setter("height"))
        body.add_widget(self.products_box)
        self.load_products()

    def save_product(self, *_):
        try:
            item = self.app.repo.add_product(
                self.sku.text, self.name.text, self.unit.text,
                self.stock.text or "0", self.barcode.text,
            )
            self.sku.text = self.barcode.text = self.name.text = ""
            self.stock.text = "0"
            self.unit.text = "pcs"
            self.app.alert(f"Produk {item['sku']} berhasil disimpan.", "Produk tersimpan")
            self.load_products()
        except Exception as exc:
            self.app.alert(str(exc), "Tidak dapat menyimpan produk")

    def load_products(self):
        if not hasattr(self, "products_box"):
            return
        self.products_box.clear_widgets()
        try:
            rows = self.app.repo.list_products(self.search.text if hasattr(self, "search") else "")
            if not rows:
                self.products_box.add_widget(ui_label("Belum ada produk. Tambahkan produk di atas.", 12, MUTED, False, 42))
            for product in rows:
                card = Card(height=128)
                card.add_widget(ui_label(f"{product['sku']} · {product['name']}", 13, NAVY, True, 25))
                card.add_widget(ui_label(
                    f"Barcode: {product.get('barcode') or '-'}   |   Stok sistem: "
                    f"{display_number(product.get('system_stock'))} {product.get('unit', 'pcs')}",
                    11, MUTED, False, 22,
                ))
                if self.app.mode == "local":
                    row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(6))
                    row.add_widget(ui_label("Ubah stok sistem", 10, MUTED, False, 26))
                    stock_input = ui_field("Qty", str(product.get("system_stock", "0")), input_filter="float", height=30)
                    stock_input.size_hint_x = 0.42
                    row.add_widget(stock_input)
                    row.add_widget(ui_button("SIMPAN", lambda _btn, p=product, f=stock_input: self.update_stock(p, f.text), GREEN, 30, 78, 10))
                    card.add_widget(row)
                self.products_box.add_widget(card)
        except Exception as exc:
            self.products_box.add_widget(ui_label(str(exc), 12, RED, False, 44))

    def update_stock(self, product, new_stock):
        try:
            updater = getattr(self.app.repo, "update_product_stock", None)
            if not callable(updater):
                raise RuntimeError("Perubahan stok master melalui mode API belum tersedia. Ubah stok melalui sistem master Arinex.")
            updater(product["id"], new_stock)
            self.app.alert(f"Stok sistem {product['sku']} diperbarui. Snapshot SO yang sudah dibuat tidak berubah.", "Stok diperbarui")
            self.load_products()
        except Exception as exc:
            self.app.alert(str(exc), "Gagal memperbarui stok")


class SetupScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.reset()
        self.header("SETUP STOCK OPNAME", "Pilih item yang akan dihitung")
        body = self.body_scroll()
        body.add_widget(ui_label("SHIFT / TIM", 12, MUTED, True, 22))
        self.shift = ui_field("Contoh: Pagi / Siang / Malam")
        body.add_widget(self.shift)
        self.notes = ui_field("Catatan (opsional)", multiline=True, height=66)
        body.add_widget(self.notes)
        body.add_widget(ui_label("CARI DAN PILIH PRODUK", 12, MUTED, True, 22))
        self.search = ui_field("Cari SKU, nama, atau barcode")
        self.search.bind(text=lambda *_: self.load_products())
        body.add_widget(self.search)
        self.selected_ids = set()
        self.selected_label = ui_label("Dipilih: 0 produk", 12, BLUE, True, 25)
        body.add_widget(self.selected_label)
        self.products_box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.products_box.bind(minimum_height=self.products_box.setter("height"))
        body.add_widget(self.products_box)
        body.add_widget(ui_button("SIMPAN DRAFT SETUP SO", self.save_setup, GREEN, 50))
        self.load_products()

    def load_products(self):
        if not hasattr(self, "products_box"):
            return
        self.products_box.clear_widgets()
        rows = self.app.repo.list_products(self.search.text if hasattr(self, "search") else "")
        if not rows:
            self.products_box.add_widget(ui_label("Master produk masih kosong. Tambahkan produk di menu General.", 12, MUTED, False, 48))
        for product in rows:
            selected = str(product["id"]) in self.selected_ids
            caption = ("✓  " if selected else "＋  ") + f"{product['sku']} · {product['name']}\nStok sistem: {display_number(product.get('system_stock'))} {product.get('unit', 'pcs')}"
            btn = ui_button(caption, lambda _b, p=product: self.toggle_product(p), color=GREEN if selected else (0.22, 0.29, 0.38, 1), height=58, font_size=12)
            self.products_box.add_widget(btn)
        self.selected_label.text = f"Dipilih: {len(self.selected_ids)} produk"

    def toggle_product(self, product):
        pid = str(product["id"])
        if pid in self.selected_ids:
            self.selected_ids.remove(pid)
        else:
            self.selected_ids.add(pid)
        self.load_products()

    def save_setup(self, *_):
        try:
            session = self.app.repo.create_session(self.shift.text, list(self.selected_ids), self.notes.text)
            self.app.alert(
                f"Draft {session['session']['session_code']} tersimpan dengan {len(session['items'])} item.\n\n"
                "Stok sistem sudah disalin sebagai snapshot. Konfirmasi sesi melalui menu Stock Opname.",
                "Setup tersimpan",
            )
            self.app.go("sessions")
        except Exception as exc:
            self.app.alert(str(exc), "Setup belum tersimpan")


class SessionsScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.reset()
        self.header("STOCK OPNAME", "Konfirmasi, mulai, dan riwayat sesi")
        body = self.body_scroll()
        body.add_widget(ui_button("＋  SETUP SO BARU", lambda *_: self.app.go("setup"), BLUE, 48))
        self.sessions_box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.sessions_box.bind(minimum_height=self.sessions_box.setter("height"))
        body.add_widget(self.sessions_box)
        self.load_sessions()

    def load_sessions(self):
        self.sessions_box.clear_widgets()
        try:
            rows = self.app.repo.list_sessions()
            if not rows:
                self.sessions_box.add_widget(ui_label("Belum ada sesi SO. Buat sesi melalui Setup Stock Opname.", 12, MUTED, False, 50))
            for session in rows:
                status = session.get("status", "draft")
                count_text = f"Dihitung: {session.get('counted_count', 0)}/{session.get('item_count', 0)} item"
                card = Card(height=142)
                card.add_widget(ui_label(f"{session['session_code']}  ·  SHIFT {session['shift_name']}", 13, NAVY, True, 25))
                card.add_widget(ui_label(f"Status: {self.status_text(status)}   |   {count_text}", 11, MUTED, False, 22))
                row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
                if status == "draft":
                    row.add_widget(ui_button("KONFIRMASI", lambda _b, sid=session["id"]: self.confirm(sid), BLUE, 38, font_size=11))
                elif status == "confirmed":
                    row.add_widget(ui_button("MULAI SO", lambda _b, sid=session["id"]: self.start(sid), GREEN, 38, font_size=11))
                elif status == "in_progress":
                    row.add_widget(ui_button("LANJUTKAN HITUNG", lambda _b, sid=session["id"]: self.open_count(sid), GREEN, 38, font_size=11))
                else:
                    row.add_widget(ui_button("BUKA LAPORAN", lambda _b, sid=session["id"]: self.show_report(sid), (0.34, 0.29, 0.56, 1), 38, font_size=11))
                row.add_widget(ui_button("DETAIL", lambda _b, sid=session["id"]: self.detail(sid), (0.27, 0.34, 0.42, 1), 38, font_size=11))
                card.add_widget(row)
                self.sessions_box.add_widget(card)
        except Exception as exc:
            self.sessions_box.add_widget(ui_label(str(exc), 12, RED, False, 45))

    @staticmethod
    def status_text(status):
        return {"draft": "Draft", "confirmed": "Dikonfirmasi", "in_progress": "Sedang berjalan", "completed": "Selesai", "cancelled": "Dibatalkan"}.get(status, status)

    def confirm(self, session_id):
        try:
            self.app.repo.confirm_session(session_id)
            self.load_sessions()
            self.app.alert("Sesi telah dikonfirmasi. Tahap berikutnya adalah Mulai SO.", "Konfirmasi berhasil")
        except Exception as exc:
            self.app.alert(str(exc), "Konfirmasi gagal")

    def start(self, session_id):
        try:
            self.app.repo.start_session(session_id)
            self.open_count(session_id)
        except Exception as exc:
            self.app.alert(str(exc), "Tidak dapat memulai SO")

    def open_count(self, session_id):
        self.app.active_session_id = session_id
        self.app.go("count")

    def detail(self, session_id):
        try:
            data = self.app.repo.get_session(session_id)
            lines = [f"{data['session']['session_code']} · {data['session']['shift_name']}"]
            for item in data["items"]:
                flag = "SELESAI" if item.get("is_counted") else "BELUM DIHITUNG"
                lines.append(f"{item['sku']} — {item['name']} — {flag}")
            self.app.alert("\n".join(lines), "Detail sesi")
        except Exception as exc:
            self.app.alert(str(exc), "Detail gagal")

    def show_report(self, session_id):
        try:
            self.app.share_report(self.app.repo.get_session(session_id))
        except Exception as exc:
            self.app.alert(str(exc), "Gagal membuka laporan")


class CountScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.reset()
        try:
            data = self.app.repo.get_session(self.app.active_session_id)
        except Exception as exc:
            self.header("PENGHITUNGAN FISIK", "")
            self.page.add_widget(ui_label(str(exc), 12, RED, False, 50))
            self.page.add_widget(ui_button("KEMBALI", lambda *_: self.app.go("sessions")))
            return
        session = data["session"]
        self.header("PENGHITUNGAN FISIK", f"{session['session_code']} · Shift {session['shift_name']}")
        body = self.body_scroll()
        body.add_widget(ui_label(
            "Isi F1–F5 untuk setiap produk. Kolom kosong diabaikan; isi angka 0 jika hasil hitung memang nol.",
            11, MUTED, False, 49,
        ))
        self.progress = ui_label("", 12, BLUE, True, 27)
        body.add_widget(self.progress)
        self.cards_box = BoxLayout(orientation="vertical", spacing=dp(9), size_hint_y=None)
        self.cards_box.bind(minimum_height=self.cards_box.setter("height"))
        body.add_widget(self.cards_box)
        for item in data["items"]:
            self.cards_box.add_widget(self.make_count_card(session["id"], item))
        body.add_widget(ui_button("SELESAIKAN SO & BUAT LAPORAN", self.complete, GREEN, 52))
        body.add_widget(ui_button("KEMBALI KE DAFTAR SESI", lambda *_: self.app.go("sessions"), (0.26, 0.33, 0.43, 1), 42))
        self.refresh_progress(data["items"])

    def make_count_card(self, session_id, item):
        card = Card(height=310)
        card.add_widget(ui_label(f"{item['sku']} · {item['name']}", 13, NAVY, True, 24))
        card.add_widget(ui_label(
            f"Stok sistem: {display_number(item.get('system_stock'))} {item.get('unit', 'pcs')}",
            11, MUTED, False, 20,
        ))
        grid = GridLayout(cols=3, spacing=dp(6), size_hint_y=None, height=dp(130))
        inputs = []
        for index in range(1, 6):
            value = item.get(f"physical_{index}")
            wrapper = BoxLayout(orientation="vertical", spacing=dp(2))
            wrapper.add_widget(ui_label(f"F{index}", 10, MUTED, True, 17, "center"))
            field = ui_field("Qty", "" if value is None else str(value), input_filter="float", height=43)
            field.size_hint_y = None
            wrapper.add_widget(field)
            grid.add_widget(wrapper)
            inputs.append(field)
        card.add_widget(grid)
        calc = ui_label("Total fisik: —   |   Selisih item: —", 11, BLUE, True, 24)
        card.add_widget(calc)
        state = ui_label("Belum dihitung", 10, MUTED, False, 18)
        card.add_widget(state)

        def recalc(*_):
            try:
                values = [decimal_value(field.text, allow_none=True) for field in inputs]
                if all(value is None for value in values):
                    calc.text = "Total fisik: —   |   Selisih item: —"
                    state.text = "Belum dihitung · isi minimal satu kolom"
                    state.color = MUTED
                    return
                if any(value is not None and value < 0 for value in values):
                    calc.text = "Jumlah fisik tidak boleh negatif"
                    state.text = "Periksa input"
                    state.color = RED
                    return
                from decimal import Decimal
                total = sum((v for v in values if v is not None), Decimal("0"))
                diff = total - decimal_value(item["system_stock"])
                sign = "+" if diff > 0 else ""
                calc.text = f"Total fisik: {display_number(total)}   |   Selisih item: {sign}{display_number(diff)}"
                if diff < 0:
                    state.text, state.color = "KURANG", RED
                elif diff > 0:
                    state.text, state.color = "LEBIH", GREEN
                else:
                    state.text, state.color = "SESUAI", BLUE
            except Exception:
                calc.text = "Input angka belum valid"
                state.text, state.color = "Periksa input", RED

        for field in inputs:
            field.bind(text=recalc)
        recalc()

        def save_item(*_):
            try:
                values = [field.text.strip() or None for field in inputs]
                self.app.repo.save_count(session_id, item["id"], values)
                state.text = "TERSIMPAN"
                state.color = GREEN
                self.refresh_progress()
                self.app.alert(f"Hitungan {item['sku']} tersimpan. Selisih hanya dihitung untuk SKU ini.", "Hitungan tersimpan")
            except Exception as exc:
                self.app.alert(str(exc), "Gagal menyimpan hitungan")

        card.add_widget(ui_button("SIMPAN HITUNGAN ITEM INI", save_item, GREEN, 38, font_size=11))
        return card

    def refresh_progress(self, items=None):
        if items is None:
            try:
                items = self.app.repo.get_session(self.app.active_session_id)["items"]
            except Exception:
                return
        counted = sum(1 for item in items if item.get("is_counted"))
        self.progress.text = f"PROGRESS: {counted}/{len(items)} ITEM DIHITUNG"

    def complete(self, *_):
        try:
            data = self.app.repo.complete_session(self.app.active_session_id)
            self.app.share_report(data)
            self.app.go("sessions")
        except Exception as exc:
            self.app.alert(str(exc), "SO belum dapat diselesaikan")


class AnalyticsScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.reset()
        self.header("ANALISIS SHIFT", "Rincian selisih per SKU · 30 hari")
        body = self.body_scroll()
        body.add_widget(ui_label(
            "Angka ringkasan hanya menghitung jumlah baris item sesuai/kurang/lebih. "
            "Nilai selisih tidak dijumlahkan antarproduk.", 11, MUTED, False, 48,
        ))
        self.result_box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.result_box.bind(minimum_height=self.result_box.setter("height"))
        body.add_widget(self.result_box)
        self.load_data()

    def load_data(self):
        self.result_box.clear_widgets()
        try:
            data = self.app.repo.get_shift_analytics(30)
            self.result_box.add_widget(ui_label(f"Periode: {data.get('period', '30 hari terakhir')}", 11, MUTED, False, 22))
            if not data.get("items"):
                self.result_box.add_widget(ui_label("Belum ada sesi SO selesai dalam periode ini.", 12, MUTED, False, 48))
                return
            for group in data["items"]:
                products = group.get("products", [])
                card_height = 118 + len(products) * 62
                card = Card(height=card_height)
                card.add_widget(ui_label(f"SHIFT {group['shift_name']}", 15, NAVY, True, 27))
                card.add_widget(ui_label(
                    f"Sesi selesai: {group.get('completed_sessions', 0)} · Baris item: {group.get('counted_lines', 0)}",
                    10, MUTED, False, 20,
                ))
                card.add_widget(ui_label(
                    f"Sesuai: {group.get('matched_items', 0)} item   |   "
                    f"Kurang: {group.get('shortage_items', 0)} item   |   "
                    f"Lebih: {group.get('surplus_items', 0)} item",
                    10, INK, True, 24,
                ))
                for product in products:
                    diff = decimal_value(product.get("difference"))
                    if diff < 0:
                        color, state, sign = RED, "KURANG", ""
                    elif diff > 0:
                        color, state, sign = GREEN, "LEBIH", "+"
                    else:
                        color, state, sign = BLUE, "SESUAI", ""
                    card.add_widget(ui_label(
                        f"{product['sku']} · {product['name']} · SO {product.get('session_code', '-')}",
                        11, NAVY, True, 21,
                    ))
                    card.add_widget(ui_label(
                        f"Sistem {display_number(product['system_stock'])} {product['unit']}  |  "
                        f"Fisik {display_number(product['physical_total'])} {product['unit']}  |  "
                        f"{state} {sign}{display_number(diff)} {product['unit']}",
                        10, color, True, 23,
                    ))
                self.result_box.add_widget(card)
        except Exception as exc:
            self.result_box.add_widget(ui_label(str(exc), 12, RED, False, 52))


class SettingsScreen(BaseScreen):
    def on_pre_enter(self, *_):
        self.reset()
        self.header("PENGATURAN", "Lokal offline atau sambungkan API")
        body = self.body_scroll()
        current = "OFFLINE · JSON LOKAL" if self.app.mode == "local" else "ONLINE · API ARINEX"
        body.add_widget(ui_label(f"Mode saat ini: {current}", 14, BLUE, True, 30))
        body.add_widget(ui_label(
            "Mode lokal tidak memerlukan database, server, akun, atau internet untuk input dan hitung SO. "
            "Data tersimpan di penyimpanan privat aplikasi.", 11, MUTED, False, 54,
        ))
        body.add_widget(ui_button("GUNAKAN MODE LOKAL / OFFLINE", self.use_local, GREEN, 48))
        body.add_widget(ui_label("INTEGRASI API ARINEX (OPSIONAL)", 13, MUTED, True, 25))
        self.api_url = ui_field("URL API, contoh https://stock-api.arinex.my.id")
        self.username = ui_field("Username API")
        self.password = ui_field("Password API", password=True)
        for widget in (self.api_url, self.username, self.password):
            body.add_widget(widget)
        body.add_widget(ui_button("TES LOGIN & AKTIFKAN MODE API", self.connect_api, BLUE, 50))
        body.add_widget(ui_label(
            "Catatan: data lokal dan data server adalah dua ruang penyimpanan terpisah. "
            "Mengganti mode tidak memindahkan atau menggabungkan data. Login API memakai HTTPS.",
            11, MUTED, False, 68,
        ))
        body.add_widget(ui_label(f"Lokasi data offline: {self.app.local_data_path}", 9, MUTED, False, 40))

    def use_local(self, *_):
        self.app.set_local_mode()
        self.app.alert("Mode lokal aktif. Aplikasi tidak akan mengirim data ke server.", "Mode offline aktif")
        self.app.go("dashboard")

    def connect_api(self, *_):
        try:
            client, user = ApiRepository.login(self.api_url.text.strip(), self.username.text.strip(), self.password.text)
            self.app.activate_api(client, self.api_url.text.strip(), user)
            self.password.text = ""
            self.app.alert(
                f"Terhubung sebagai {user.get('username', self.username.text.strip())}. "
                "Data berikutnya akan dibaca/disimpan melalui API Arinex.",
                "API tersambung",
            )
            self.app.go("dashboard")
        except Exception as exc:
            self.app.alert(str(exc), "Tidak dapat mengaktifkan API")


class StockOpnameApp(App):
    title = "ST Stock Opname"

    def build(self):
        Window.clearcolor = BG
        self.active_session_id = None
        self.local_data_path = os.path.join(self.user_data_dir, "st_stockopname_data.json")
        self.config_path = os.path.join(self.user_data_dir, "st_config.json")
        self.config = self._read_config()
        self.local_repo = LocalJsonRepository(self.local_data_path)
        self.mode = "local"
        self.repo = self.local_repo
        self.api_restore_warning = ""
        self._restore_api_if_configured()

        self.manager = ScreenManager(transition=SlideTransition(duration=0.12))
        screens = [
            DashboardScreen(name="dashboard"), ProductScreen(name="products"),
            SetupScreen(name="setup"), SessionsScreen(name="sessions"),
            CountScreen(name="count"), AnalyticsScreen(name="analytics"),
            SettingsScreen(name="settings"),
        ]
        for screen in screens:
            self.manager.add_widget(screen)
        self.manager.current = "dashboard"
        return self.manager

    def _read_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        temp = self.config_path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.config, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.config_path)

    def _restore_api_if_configured(self):
        if self.config.get("mode") != "api":
            return
        try:
            client = ApiRepository(self.config.get("api_url", ""), self.config.get("token", ""), timeout=5)
            client._request("GET", "/api/me")
            self.repo = client
            self.mode = "api"
        except Exception as exc:
            # Keep offline mode usable, but clearly warn that local and server data are separate.
            self.repo = self.local_repo
            self.mode = "local"
            self.api_restore_warning = (
                f"Server API tidak tersedia / token kedaluwarsa. Mode lokal aktif; data baru akan "
                f"disimpan terpisah dari server. Buka Pengaturan untuk menyambungkan ulang. Detail: {exc}"
            )

    def activate_api(self, client, api_url, user):
        self.repo = client
        self.mode = "api"
        self.api_restore_warning = ""
        self.config = {"mode": "api", "api_url": api_url.rstrip("/"), "token": client.token,
                       "username": user.get("username", "")}
        self._save_config()

    def set_local_mode(self):
        self.mode = "local"
        self.repo = self.local_repo
        self.api_restore_warning = ""
        self.config = {"mode": "local"}
        self._save_config()

    def go(self, screen_name):
        if self.manager:
            self.manager.current = screen_name

    def alert(self, message, title="Informasi"):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))
        text = ui_label(message, 12, INK, False, 150)
        text.text_size = (dp(280), None)
        content.add_widget(text)
        content.add_widget(ui_button("TUTUP", lambda *_: popup.dismiss(), BLUE, 42))
        popup = Popup(title=title, content=content, size_hint=(0.91, None), height=dp(260), auto_dismiss=True)
        popup.open()

    def share_report(self, data):
        message = build_report(data)
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        content.add_widget(ui_label("Laporan selesai dibuat. Bagikan teks ini melalui WhatsApp atau aplikasi lain.", 11, MUTED, False, 45))
        preview = TextInput(text=message, readonly=True, multiline=True, size_hint_y=1,
                            background_color=(0.97, 0.98, 0.99, 1), foreground_color=INK, font_size=sp(11))
        content.add_widget(preview)
        popup = Popup(title="Laporan Stock Opname", content=content, size_hint=(0.94, 0.86))
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        actions.add_widget(ui_button("SALIN", lambda *_: self.copy_report(message, popup), BLUE, 42, font_size=11))
        actions.add_widget(ui_button("WHATSAPP", lambda *_: self.open_whatsapp(message, popup), GREEN, 42, font_size=11))
        actions.add_widget(ui_button("TUTUP", lambda *_: popup.dismiss(), (0.30, 0.36, 0.43, 1), 42, font_size=11))
        content.add_widget(actions)
        popup.open()

    def copy_report(self, message, popup):
        try:
            Clipboard.copy(message)
            self.alert("Laporan disalin ke clipboard.", "Berhasil")
        except Exception as exc:
            self.alert(f"Clipboard tidak tersedia: {exc}", "Tidak dapat menyalin")

    def open_whatsapp(self, message, popup):
        url = "https://wa.me/?text=" + quote(message)
        try:
            opened = webbrowser.open(url)
            if not opened:
                Clipboard.copy(message)
                self.alert("Tautan WhatsApp tidak terbuka. Laporan sudah dicoba disalin; tempelkan secara manual.", "Bagikan laporan")
        except Exception:
            try:
                Clipboard.copy(message)
            except Exception:
                pass
            self.alert("Tidak dapat membuka WhatsApp. Salin isi laporan dari layar ini.", "Bagikan laporan")


if __name__ == "__main__":
    StockOpnameApp().run()
