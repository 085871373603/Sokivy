[app]
title = ST Stock Opname
package.name = ststockopname
package.domain = id.arinex
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json,md
version = 1.1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
icon.filename = assets/st_icon.png
presplash.filename = assets/st_icon.png

# INTERNET is only used when the user explicitly connects to the Arinex API
# or shares a report through WhatsApp. Offline data entry remains available.
android.permissions = INTERNET
android.api = 36
android.minapi = 23
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = False

[buildozer]
log_level = 2
warn_on_root = 1
