"""Local JSON repository. No SQL database or network is required."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def decimal_value(value: Any, *, allow_none: bool = False) -> Decimal | None:
    if value is None or str(value).strip() == "":
        if allow_none:
            return None
        return Decimal("0")
    try:
        result = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError("Masukkan angka yang valid.")
    if not result.is_finite():
        raise ValueError("Angka harus berupa nilai yang valid.")
    return result


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f")


def display_number(value: Any) -> str:
    if value is None:
        return "—"
    number = decimal_value(value)
    return decimal_text(number) or "0"


def _default_data() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "products": [],
        "sessions": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


class LocalJsonRepository:
    """Persists master products and SO sessions in one atomic JSON file."""

    def __init__(self, file_path: str | os.PathLike[str]):
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.recovery_warning = ""
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            data = _default_data()
            self._write(data)
            return data
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("Versi format data lokal tidak dikenal.")
            if not isinstance(data.get("products"), list) or not isinstance(data.get("sessions"), list):
                raise ValueError("Struktur data lokal tidak valid.")
            return data
        except Exception as exc:
            # Preserve the damaged file rather than silently overwriting user data.
            backup = self.path.with_name(self.path.name + ".damaged-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
            try:
                shutil.copy2(self.path, backup)
            except OSError:
                pass
            self.recovery_warning = (
                f"Data lokal sebelumnya tidak dapat dibaca. Salinan pengaman dibuat sebagai {backup.name}. "
                f"Data baru yang kosong dibuat agar aplikasi tetap dapat dibuka. Detail: {exc}"
            )
            data = _default_data()
            self._write(data)
            return data

    def _write(self, data: dict[str, Any] | None = None) -> None:
        payload = data if data is not None else self.data
        payload["updated_at"] = now_iso()
        fd, temp_name = tempfile.mkstemp(prefix="st-so-", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def _commit(self) -> None:
        self._write()

    def list_products(self, query: str = "") -> list[dict[str, Any]]:
        term = (query or "").strip().casefold()
        rows = self.data["products"]
        if term:
            rows = [p for p in rows if term in str(p.get("sku", "")).casefold()
                    or term in str(p.get("name", "")).casefold()
                    or term in str(p.get("barcode", "")).casefold()]
        return sorted((dict(p) for p in rows if p.get("is_active", True)), key=lambda p: p["name"].casefold())

    def add_product(self, sku: str, name: str, unit: str = "pcs", system_stock: Any = "0", barcode: str = "") -> dict[str, Any]:
        sku = (sku or "").strip()
        name = (name or "").strip()
        unit = (unit or "pcs").strip() or "pcs"
        barcode = (barcode or "").strip()
        if not sku or len(sku) > 80:
            raise ValueError("SKU wajib diisi dan maksimal 80 karakter.")
        if not name or len(name) > 180:
            raise ValueError("Nama produk wajib diisi dan maksimal 180 karakter.")
        stock = decimal_value(system_stock)
        if stock is None or stock < 0:
            raise ValueError("Stok sistem tidak boleh negatif.")
        sku_key = sku.casefold()
        if any(p["sku"].casefold() == sku_key for p in self.data["products"]):
            raise ValueError(f"SKU {sku} sudah terdaftar.")
        if barcode and any((p.get("barcode") or "").casefold() == barcode.casefold() for p in self.data["products"]):
            raise ValueError("Barcode sudah digunakan produk lain.")
        row = {
            "id": str(uuid.uuid4()), "sku": sku, "barcode": barcode,
            "name": name, "unit": unit, "system_stock": decimal_text(stock),
            "is_active": True, "created_at": now_iso(),
        }
        self.data["products"].append(row)
        self._commit()
        return dict(row)

    def update_product_stock(self, product_id: str, system_stock: Any) -> dict[str, Any]:
        stock = decimal_value(system_stock)
        if stock is None or stock < 0:
            raise ValueError("Stok sistem tidak boleh negatif.")
        for product in self.data["products"]:
            if str(product["id"]) == str(product_id):
                product["system_stock"] = decimal_text(stock)
                product["updated_at"] = now_iso()
                self._commit()
                return dict(product)
        raise ValueError("Produk tidak ditemukan.")

    def create_session(self, shift_name: str, product_ids: list[str], notes: str = "") -> dict[str, Any]:
        shift_name = (shift_name or "").strip()
        if not shift_name or len(shift_name) > 40:
            raise ValueError("Nama shift wajib diisi (maksimal 40 karakter).")
        if not product_ids:
            raise ValueError("Pilih minimal satu produk untuk stock opname.")
        ids = list(dict.fromkeys(str(x) for x in product_ids))
        products_by_id = {str(p["id"]): p for p in self.data["products"] if p.get("is_active", True)}
        missing = [pid for pid in ids if pid not in products_by_id]
        if missing:
            raise ValueError("Ada produk pilihan yang sudah tidak tersedia.")
        timestamp = datetime.now().astimezone()
        code = "SO-" + timestamp.strftime("%y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4].upper()
        items = []
        for pid in ids:
            product = products_by_id[pid]
            items.append({
                "id": str(uuid.uuid4()), "product_id": pid,
                "sku": product["sku"], "name": product["name"], "unit": product["unit"],
                "system_stock": str(product["system_stock"]),
                "physical_1": None, "physical_2": None, "physical_3": None,
                "physical_4": None, "physical_5": None,
                "physical_total": None, "is_counted": False,
                "difference": None, "counted_at": None,
            })
        session = {
            "id": str(uuid.uuid4()), "session_code": code, "shift_name": shift_name,
            "notes": (notes or "").strip()[:1000], "status": "draft",
            "created_at": now_iso(), "confirmed_at": None, "started_at": None,
            "completed_at": None, "items": items,
        }
        self.data["sessions"].insert(0, session)
        self._commit()
        return self.get_session(session["id"])

    def list_sessions(self) -> list[dict[str, Any]]:
        result = []
        for session in self.data["sessions"][:100]:
            items = session.get("items", [])
            result.append({
                k: session.get(k) for k in (
                    "id", "session_code", "shift_name", "status", "created_at",
                    "started_at", "completed_at", "notes"
                )
            } | {
                "item_count": len(items),
                "counted_count": sum(1 for item in items if item.get("is_counted")),
            })
        return result

    def get_session(self, session_id: str) -> dict[str, Any]:
        for session in self.data["sessions"]:
            if str(session["id"]) == str(session_id):
                return {"session": {k: v for k, v in session.items() if k != "items"},
                        "items": [dict(item) for item in session.get("items", [])]}
        raise ValueError("Sesi stock opname tidak ditemukan.")

    def _session_mutable(self, session_id: str) -> dict[str, Any]:
        for session in self.data["sessions"]:
            if str(session["id"]) == str(session_id):
                return session
        raise ValueError("Sesi stock opname tidak ditemukan.")

    def confirm_session(self, session_id: str) -> dict[str, Any]:
        session = self._session_mutable(session_id)
        if session["status"] != "draft":
            raise ValueError("Hanya sesi draft yang dapat dikonfirmasi.")
        session["status"] = "confirmed"
        session["confirmed_at"] = now_iso()
        self._commit()
        return self.get_session(session_id)

    def start_session(self, session_id: str) -> dict[str, Any]:
        session = self._session_mutable(session_id)
        if session["status"] != "confirmed":
            raise ValueError("Sesi harus dikonfirmasi sebelum dimulai.")
        session["status"] = "in_progress"
        session["started_at"] = now_iso()
        self._commit()
        return self.get_session(session_id)

    def save_count(self, session_id: str, item_id: str, values: list[Any] | dict[str, Any]) -> dict[str, Any]:
        session = self._session_mutable(session_id)
        if session["status"] != "in_progress":
            raise ValueError("Hitungan hanya dapat disimpan pada sesi yang sedang berjalan.")
        if isinstance(values, dict):
            raw_values = [values.get(f"physical_{i}") for i in range(1, 6)]
        else:
            raw_values = list(values)
        if len(raw_values) != 5:
            raise ValueError("Harus ada tepat lima kolom fisik.")
        parsed = [decimal_value(value, allow_none=True) for value in raw_values]
        if all(value is None for value in parsed):
            raise ValueError("Isi minimal satu kolom fisik. Masukkan 0 bila hasil hitung nol.")
        if any(value is not None and value < 0 for value in parsed):
            raise ValueError("Jumlah fisik tidak boleh negatif.")
        item = next((x for x in session["items"] if str(x["id"]) == str(item_id)), None)
        if item is None:
            raise ValueError("Item SO tidak ditemukan.")
        total = sum((value for value in parsed if value is not None), Decimal("0"))
        difference = total - decimal_value(item["system_stock"])
        for index, value in enumerate(parsed, start=1):
            item[f"physical_{index}"] = decimal_text(value)
        item["physical_total"] = decimal_text(total)
        item["is_counted"] = True
        item["difference"] = decimal_text(difference)
        item["counted_at"] = now_iso()
        self._commit()
        return dict(item)

    def complete_session(self, session_id: str) -> dict[str, Any]:
        session = self._session_mutable(session_id)
        if session["status"] != "in_progress":
            raise ValueError("Hanya sesi yang sedang berjalan dapat diselesaikan.")
        total = len(session["items"])
        counted = sum(1 for item in session["items"] if item.get("is_counted"))
        if total == 0 or counted != total:
            raise ValueError(f"Belum semua barang dihitung ({counted}/{total}).")
        session["status"] = "completed"
        session["completed_at"] = now_iso()
        self._commit()
        return self.get_session(session_id)

    def get_shift_analytics(self, days: int = 30) -> dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        groups: dict[str, dict[str, Any]] = {}
        for session in self.data["sessions"]:
            if session.get("status") != "completed" or not session.get("completed_at"):
                continue
            try:
                completed = datetime.fromisoformat(session["completed_at"]).astimezone(timezone.utc)
            except (ValueError, TypeError):
                continue
            if completed < cutoff:
                continue
            shift = session.get("shift_name", "Tanpa Shift")
            group = groups.setdefault(shift, {
                "shift_name": shift, "completed_sessions": 0,
                "counted_lines": 0, "shortage_items": 0,
                "surplus_items": 0, "matched_items": 0, "products": [],
                "_session_codes": set(),
            })
            group["_session_codes"].add(session["session_code"])
            for item in session.get("items", []):
                if not item.get("is_counted"):
                    continue
                difference = decimal_value(item.get("difference"))
                if difference is None:
                    continue
                if difference < 0:
                    status = "kurang"
                    group["shortage_items"] += 1
                elif difference > 0:
                    status = "lebih"
                    group["surplus_items"] += 1
                else:
                    status = "sesuai"
                    group["matched_items"] += 1
                group["counted_lines"] += 1
                group["products"].append({
                    "session_code": session["session_code"],
                    "completed_at": session["completed_at"],
                    "sku": item["sku"], "name": item["name"], "unit": item["unit"],
                    "system_stock": item["system_stock"],
                    "physical_total": item["physical_total"],
                    "difference": item["difference"], "status": status,
                })
        output = []
        for group in groups.values():
            group["completed_sessions"] = len(group.pop("_session_codes"))
            output.append(group)
        output.sort(key=lambda row: row["shift_name"].casefold())
        return {"period": f"{days} hari terakhir", "items": output}


def build_report(data: dict[str, Any]) -> str:
    session = data["session"]
    items = data["items"]
    shortage = [x for x in items if x.get("is_counted") and decimal_value(x.get("difference")) < 0]
    surplus = [x for x in items if x.get("is_counted") and decimal_value(x.get("difference")) > 0]
    matched = [x for x in items if x.get("is_counted") and decimal_value(x.get("difference")) == 0]
    lines = [
        "*LAPORAN STOCK OPNAME - ST*", f"Kode: {session.get('session_code', '-')}",
        f"Shift: {session.get('shift_name', '-')}", f"Status: {session.get('status', '-')}", "",
        f"Jumlah item: {len(items)}", f"Selesai dihitung: {len(shortage) + len(surplus) + len(matched)}",
        f"Sesuai: {len(matched)} item", f"Kurang: {len(shortage)} item", f"Lebih: {len(surplus)} item", "",
        "*RINCIAN SELISIH PER ITEM (TIDAK DIJUMLAHKAN ANTAR SKU)*",
    ]
    for item in items:
        if not item.get("is_counted"):
            lines.append(f"{item['sku']} - {item['name']}: BELUM DIHITUNG")
            continue
        diff = decimal_value(item["difference"])
        state = "SESUAI" if diff == 0 else ("KURANG" if diff < 0 else "LEBIH")
        sign = "+" if diff > 0 else ""
        lines.append(
            f"{item['sku']} - {item['name']}: sistem {display_number(item['system_stock'])} {item['unit']}, "
            f"fisik {display_number(item['physical_total'])} {item['unit']}, "
            f"{state} {sign}{display_number(diff)} {item['unit']}"
        )
    lines.extend(["", "Dibuat melalui ST Stock Opname · Arinex"])
    return "\n".join(lines)
