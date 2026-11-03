# ST Stock Opname — Arinex Digital Solution

**Versi 1.1.0 · Offline-first · Python Kivy · Android**

ST Stock Opname adalah aplikasi pencatatan stock opname yang dapat dipakai tanpa PostgreSQL, tanpa server, dan tanpa koneksi internet untuk pekerjaan utamanya. Produk, sesi, hitungan lima kolom fisik, dan analisis shift disimpan sebagai **JSON lokal** di penyimpanan privat aplikasi Android.

Saat backend Arinex siap, aplikasi dapat dialihkan ke **mode API** melalui menu Pengaturan. Adapter API kompatibel dengan endpoint Flask Arinex yang dijelaskan di `docs/API_INTEGRATION.md`.

## Fitur

- Master produk: SKU unik, barcode opsional, nama, satuan, dan stok sistem.
- Pencarian produk berdasarkan SKU, nama, atau barcode.
- Setup SO: pilih item dari master, tentukan shift, simpan draft.
- Alur status: `draft → confirmed → in_progress → completed`.
- Snapshot stok sistem dibuat saat sesi SO dibuat. Perubahan stok master setelah itu tidak mengubah snapshot sesi.
- Lima kolom hitung fisik (F1–F5), total otomatis, dan selisih per SKU.
- Kolom kosong tidak dihitung; masukkan `0` bila hasil hitung memang nol.
- SO tidak dapat diselesaikan sebelum semua item dihitung.
- Riwayat SO, laporan WhatsApp, serta analisis shift 30 hari.
- Analisis menampilkan rincian selisih per produk. **Selisih antar-SKU tidak dijumlahkan.**
- Integrasi REST API opsional; aplikasi tetap berfungsi dalam mode lokal bila API tidak aktif.

## Rumus

Untuk satu SKU/baris produk:

```text
Total Fisik SKU = F1 + F2 + F3 + F4 + F5
Selisih SKU     = Total Fisik SKU - Stok Sistem SKU
```

Contoh: SKU A stok sistem 10, fisik 8 → selisih SKU A `-2`. SKU B stok sistem 20, fisik 22 → selisih SKU B `+2`. Kedua hasil tetap ditampilkan terpisah; tidak dijadikan angka bersih nol.

## Struktur repository

```text
ST-Stock-Opname-Offline/
├── .github/
│   └── workflows/
│       ├── build-android.yml     # Build APK via GitHub Actions
│       └── tests.yml             # Tes logika lokal dan sintaks Python
├── docs/
│   ├── API_INTEGRATION.md        # Kontrak API opsional
│   └── GITHUB_ANDROID.md         # Upload repo dan ambil APK
├── mobile/
│   ├── assets/st_icon.png        # Ikon aplikasi ST
│   ├── api_repository.py         # Adapter REST API opsional (stdlib)
│   ├── android.txt               # Metadata Kivy Launcher
│   ├── buildozer.spec             # Konfigurasi APK
│   ├── main.py                    # UI Kivy
│   └── repository.py              # JSON lokal, validasi, rumus, analisis
├── tests/
│   └── test_repository.py         # Tes otomatis alur dan rumus
├── .gitignore
└── README.md
```

## Persyaratan

- Mode lokal: tidak perlu server atau database.
- Membuat APK: repository GitHub dan GitHub Actions aktif.
- Menghubungkan API: backend Flask Arinex yang kompatibel, akun API, dan URL HTTPS.
- Koneksi internet hanya dibutuhkan untuk build APK di GitHub, login/sinkronisasi API, atau membuka WhatsApp. Input lokal dan perhitungan tidak membutuhkan internet.

## Upload ke GitHub

1. Ekstrak ZIP ini. Buka folder hasil ekstrak `ST-Stock-Opname-Offline`.
2. Di GitHub, buat repository baru bernama `ST-Stock-Opname`.
3. Pilih repository **Private** bila aplikasi ini dipakai internal.
4. Upload **isi folder proyek**, bukan file ZIP sebagai satu berkas. Struktur folder harus tetap sama.
5. Pastikan file tersembunyi `.github/workflows/build-android.yml` dan `.github/workflows/tests.yml` ikut terunggah. Tanpa file workflow, GitHub tidak akan menjalankan build otomatis.
6. Commit ke branch `main` atau `master`.
7. Buka tab **Actions**. Workflow `ST Stock Opname - Unit Tests` akan menjalankan tes. Workflow `Build ST Stock Opname APK` dapat berjalan otomatis saat file `mobile/` berubah.
8. Untuk memulai build manual: Actions → **Build ST Stock Opname APK** → **Run workflow** → Run workflow.
9. Setelah selesai, buka hasil run → bagian **Artifacts** → download `ST-Stock-Opname-Android-APK`.
10. Ekstrak artifact dan instal APK debug di Android. Izinkan instalasi dari sumber yang digunakan bila Android meminta izin.

Petunjuk langkah upload dari browser Android dan penanganan workflow ada di `docs/GITHUB_ANDROID.md`.

## Menjalankan tes lokal

Tes logika repository tidak membutuhkan Kivy:

```text
python -m unittest discover -s tests -v
```

Pemeriksaan sintaks:

```text
python -m py_compile mobile/main.py mobile/repository.py mobile/api_repository.py
```

Build APK menggunakan Buildozer. Konfigurasi `buildozer.spec` hanya meminta `python3,kivy`; tidak ada `psycopg2`, `requests`, SQLAlchemy, atau library database yang perlu dipasang di Android.

## Penyimpanan dan keamanan data

- File data lokal berada di `App.user_data_dir` pada Android, bukan di root repository GitHub.
- Data tidak otomatis diunggah ke server dalam mode lokal.
- Saat berpindah ke mode API, data lokal tidak otomatis dipindahkan/digabungkan dengan data server. Jika server tidak tersedia saat startup, aplikasi masuk mode lokal dan menampilkan peringatan bahwa data akan tersimpan terpisah.
- Jangan menghapus aplikasi sebelum membuat cadangan atau memindahkan data yang diperlukan. Uninstall dapat menghapus penyimpanan privat aplikasi.
- API produksi hanya menerima HTTPS. Token API disimpan di ruang privat aplikasi.
- Repository tidak berisi password database, token, file `.env`, maupun kredensial GitHub.

## Catatan batas pengujian

Paket ini mencakup tes otomatis untuk penyimpanan JSON, SKU unik, snapshot stok, lima kolom, validasi penyelesaian, laporan per SKU, dan analisis shift. APK tetap harus dibangun oleh GitHub Actions dan diuji pada perangkat Android nyata. Lingkungan pembuatan source ini tidak menjalankan emulator Android atau toolchain SDK/NDK; karena itu keberhasilan build final belum dapat diklaim sebelum workflow GitHub selesai.

## Identitas

**ST Stock Opname**  
Arinex Digital Solution — Your Partner in Digital Transformation.
