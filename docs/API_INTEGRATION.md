# Integrasi API Arinex (opsional)

Aplikasi berjalan penuh di mode lokal tanpa API. File `mobile/api_repository.py` adalah adapter REST opsional untuk Flask API Arinex versi yang menyediakan endpoint berikut.

## Cara mengaktifkan dari aplikasi

1. Deploy backend Flask Arinex pada subdomain API dan aktifkan HTTPS.
2. Pastikan database dan tabel di backend sudah siap.
3. Buat akun owner/staf API melalui proses backend.
4. Di ST Stock Opname buka Pengaturan → Integrasi API.
5. Isi URL API, username, dan password.
6. Tekan `Tes Login & Aktifkan Mode API`.
7. Aplikasi memanggil `POST /api/auth/login`, menerima token, lalu memvalidasi token dengan `GET /api/me`.

Password hanya digunakan pada proses login dan tidak disimpan. Token disimpan pada penyimpanan privat aplikasi.

## Endpoint yang digunakan adapter

| Method | Endpoint | Kegunaan |
|---|---|---|
| POST | `/api/auth/login` | Mendapatkan token Bearer |
| GET | `/api/me` | Memvalidasi token saat startup |
| GET | `/api/products?q=` | Mencari master produk |
| POST | `/api/products` | Menambah master produk |
| POST | `/api/sessions` | Membuat sesi SO dan snapshot item |
| GET | `/api/sessions` | Daftar sesi |
| GET | `/api/sessions/{id}` | Detail sesi dan item |
| POST | `/api/sessions/{id}/confirm` | Konfirmasi sesi |
| POST | `/api/sessions/{id}/start` | Mulai SO |
| PUT | `/api/sessions/{id}/items/{item_id}` | Simpan lima angka fisik |
| POST | `/api/sessions/{id}/complete` | Menyelesaikan SO |
| GET | `/api/analytics/shifts` | Analisis shift 30 hari |

Semua endpoint setelah login memakai header `Authorization: Bearer <token>`.

## Bentuk data penting

Buat sesi:

```json
{
  "shift_name": "Pagi",
  "notes": "SO rak minuman",
  "product_ids": [12, 13]
}
```

Simpan hitungan satu item:

```json
{
  "physical_1": "2",
  "physical_2": "3",
  "physical_3": null,
  "physical_4": "0",
  "physical_5": null
}
```

Backend harus menganggap `null` sebagai kolom yang belum diisi dan `0` sebagai hasil hitung nol. Per item, `physical_total` adalah jumlah nilai fisik yang tidak null; `difference = physical_total - system_stock`.

## Perhatian kompatibilitas

- Adapter ini disesuaikan dengan endpoint Flask Arinex yang telah digunakan pada proyek sebelumnya. Jika backend Anda berubah, samakan endpoint/field pada `api_repository.py`.
- Backend harus mengembalikan objek JSON dengan pola `{"ok": true, ...}` dan error `{"ok": false, "error": "..."}`.
- Endpoint list produk harus mengembalikan `{"items": [...]}`; detail sesi harus mengembalikan `{"session": {...}, "items": [...]}`.
- API produksi harus memakai HTTPS. Jangan membuka port PostgreSQL ke internet dan jangan menaruh password PostgreSQL ke aplikasi Android.
- Mode lokal dan API adalah dua dataset berbeda. Peralihan mode tidak melakukan migrasi/sinkronisasi otomatis.
- Pada mode API, perubahan stok master sebaiknya dilakukan lewat sistem master Arinex. Aplikasi ini belum mengirim perubahan stok master ke endpoint update produk.
