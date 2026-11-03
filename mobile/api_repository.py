"""Optional REST adapter for the Arinex Flask API; not required for offline use."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


class ApiRepository:
    def __init__(self, base_url: str, token: str, timeout: int = 20):
        self.base_url = (base_url or "").strip().rstrip("/")
        self.token = (token or "").strip()
        self.timeout = timeout
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc:
            raise ValueError("URL API tidak valid. Gunakan https://alamat-api-anda.")
        if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1"):
            raise ValueError("Mode API produksi wajib menggunakan HTTPS.")

    @classmethod
    def login(cls, base_url: str, username: str, password: str) -> tuple["ApiRepository", dict]:
        client = cls(base_url, "")
        result = client._request("POST", "/api/auth/login", {"username": username, "password": password})
        if not result.get("token"):
            raise RuntimeError("API tidak mengembalikan token login.")
        client.token = result["token"]
        return client, result.get("user", {})

    def _request(self, method: str, path: str, payload=None, params=None):
        url = self.base_url + path
        if params:
            url += "?" + urlencode(params)
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(url, data=body, headers=headers, method=method.upper())
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = response.status
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Tidak dapat terhubung ke API: {exc}") from exc
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"API mengirim respons bukan JSON (HTTP {status}).") from exc
        if status < 200 or status >= 300 or data.get("ok") is False:
            raise RuntimeError(data.get("error") or f"API gagal (HTTP {status}).")
        return data

    def list_products(self, query: str = "") -> list[dict]:
        return self._request("GET", "/api/products", params={"q": query} if query else None).get("items", [])

    def add_product(self, sku: str, name: str, unit: str = "pcs", system_stock="0", barcode="") -> dict:
        return self._request("POST", "/api/products", {
            "sku": sku, "name": name, "unit": unit,
            "system_stock": system_stock, "barcode": barcode,
        }).get("item", {})

    def create_session(self, shift_name: str, product_ids: list, notes: str = "") -> dict:
        created = self._request("POST", "/api/sessions", {
            "shift_name": shift_name, "product_ids": product_ids, "notes": notes,
        }).get("session", {})
        return self.get_session(created["id"])

    def list_sessions(self) -> list[dict]:
        return self._request("GET", "/api/sessions").get("items", [])

    def get_session(self, session_id) -> dict:
        return self._request("GET", f"/api/sessions/{session_id}")

    def confirm_session(self, session_id):
        return self._request("POST", f"/api/sessions/{session_id}/confirm", {})

    def start_session(self, session_id):
        return self._request("POST", f"/api/sessions/{session_id}/start", {})

    def save_count(self, session_id, item_id, values):
        if isinstance(values, dict):
            payload = {f"physical_{i}": values.get(f"physical_{i}") for i in range(1, 6)}
        else:
            payload = {f"physical_{i}": values[i - 1] for i in range(1, 6)}
        return self._request("PUT", f"/api/sessions/{session_id}/items/{item_id}", payload).get("item", {})

    def complete_session(self, session_id):
        self._request("POST", f"/api/sessions/{session_id}/complete", {})
        return self.get_session(session_id)

    def get_shift_analytics(self, days: int = 30) -> dict:
        # Existing Arinex API returns a fixed 30-day window.
        return self._request("GET", "/api/analytics/shifts")
