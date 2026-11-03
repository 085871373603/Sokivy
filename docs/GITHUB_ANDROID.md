# Panduan upload GitHub dan build APK lewat browser Android

Panduan ini menggunakan GitHub Actions agar Anda tidak perlu memasang Terminal, SSH, Buildozer, Android SDK, atau NDK di ponsel.

## 1. Siapkan file proyek

1. Download `ST-Stock-Opname-Offline.zip` dari ChatGPT.
2. Buka aplikasi Files / My Files Android.
3. Ekstrak ZIP.
4. Pastikan folder hasil ekstrak berisi `README.md`, `mobile`, `tests`, `docs`, dan `.github`.
5. Jangan mengubah nama folder `mobile` atau `.github`.

## 2. Buat repository

1. Buka GitHub dan login.
2. Tekan tombol `+` → `New repository`.
3. Repository name: `ST-Stock-Opname`.
4. Pilih `Private`.
5. Jangan centang Add a README, .gitignore, atau license karena semua sudah ada di source.
6. Tekan `Create repository`.

## 3. Upload seluruh source

Di halaman repository, pilih `Add file` → `Upload files`.

- Unggah seluruh isi folder proyek dengan struktur folder tetap dipertahankan.
- Bila browser Android tidak dapat memilih folder sekaligus, gunakan mode Desktop Site atau unggah per folder. Buat path file sesuai struktur repo; contoh `mobile/main.py` harus berada di dalam folder `mobile`.
- Pastikan file di folder tersembunyi `.github/workflows` ikut masuk. Pada file manager, aktifkan opsi `Show hidden files` bila folder `.github` tidak terlihat.
- File workflow yang wajib ada:
  - `.github/workflows/tests.yml`
  - `.github/workflows/build-android.yml`
- Pastikan tidak ada `st_stockopname_data.json`, `.env`, token, password, atau hasil build pribadi yang ikut terunggah.

Jika UI upload browser ponsel tidak menerima folder tersembunyi, buat file workflow secara manual melalui GitHub `Add file` → `Create new file`. Pada nama file, masukkan persis `.github/workflows/build-android.yml`, lalu salin isi file dari source ZIP. Ulangi untuk `tests.yml`.

Commit message yang disarankan: `Initial offline-first ST Stock Opname`.

## 4. Jalankan pemeriksaan otomatis

1. Buka tab `Actions` pada repository.
2. Jika ada notifikasi yang meminta mengaktifkan Actions, tekan Enable.
3. Workflow `ST Stock Opname - Unit Tests` akan menjalankan tes saat commit.
4. Pastikan hasilnya hijau (`Success`). Bila gagal, buka detail job dan baca langkah yang berwarna merah.

Tes ini memeriksa logika lokal dan sintaks Python. Tes ini bukan pengganti uji perangkat Android.

## 5. Build APK

1. Buka tab `Actions`.
2. Pilih workflow `Build ST Stock Opname APK` di panel kiri.
3. Tekan `Run workflow`.
4. Pilih branch `main` (atau `master` bila itu branch utama repository).
5. Tekan tombol hijau `Run workflow`.
6. Buka proses yang baru berjalan.
7. Tunggu sampai job selesai dengan status hijau.
8. Di bagian bawah halaman run, temukan `Artifacts`.
9. Download `ST-Stock-Opname-Android-APK`.
10. Ekstrak artifact ZIP; file `.apk` ada di dalamnya.

GitHub Free memiliki kuota menit Actions dan retensi artifact sesuai kebijakan paket. Workflow menyimpan artifact selama 14 hari.

## 6. Bila workflow gagal

- `buildozer.spec not found`: pastikan file berada di `mobile/buildozer.spec` dan `workdir: mobile` tidak berubah.
- Workflow tidak muncul: pastikan nama dan lokasi file tepat di `.github/workflows/build-android.yml` serta sudah di-commit ke branch utama.
- `No matching distribution` atau kegagalan recipe: buka log Buildozer dan catat bagian error pertama yang relevan; jangan menebak paket tambahan. Source offline ini sengaja hanya memakai `python3,kivy`.
- `Artifact not found`: periksa apakah langkah Build APK sukses dan path output di workflow masih menggunakan output action `filename`.
- Gagal karena kuota: periksa Settings → Billing and licensing → Actions di GitHub.

## 7. Instalasi pada Android

1. Ekstrak artifact hasil build.
2. Ketuk file APK.
3. Bila diminta, izinkan browser/file manager memasang aplikasi dari sumber tersebut.
4. Tekan Install.
5. Buka `ST Stock Opname`.
6. Tambahkan produk percobaan, buat sesi SO, konfirmasi, mulai, isi F1–F5, simpan, lalu selesaikan.

Build workflow menghasilkan **debug APK** untuk pengujian internal, bukan APK release yang telah ditandatangani untuk Play Store.
