[app]
title = ST Stock Opname
package.name = ststockopname
package.domain = id.arinex
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json,md
source.exclude_patterns = test_*.py, tests/*, storage/*, .buildozer/*, __pycache__/*
version = 1.1.3

# Aplikasi hanya memakai Kivy dan standard library Python.
# Tidak perlu PostgreSQL, requests, openpyxl, pandas, atau library native tambahan.
requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0
icon.filename = assets/st_icon.png
presplash.filename = assets/st_icon.png

# INTERNET diperlukan hanya jika pengguna mengaktifkan API Arinex atau
# membuka WhatsApp untuk membagikan laporan. Mode lokal tetap offline-first.
android.permissions = INTERNET

# Toolchain ini mengikuti kombinasi yang sudah terbukti berhasil pada
# aplikasi Kivy lain milik pengguna: P4A 2024.01.21 + NDK 25b + API 33.
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = apk

p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
