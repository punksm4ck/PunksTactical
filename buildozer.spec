[app]

# ── Identity ──────────────────────────────────────────────────────────────────
title           = PUNKS Omni Dashboard
package.name    = punksomni
package.domain  = net.punks

# ── Source ────────────────────────────────────────────────────────────────────
source.dir       = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
source.exclude_dirs = tests, bin, build, .buildozer, .git, __pycache__, venv, .venv

# ── Version ───────────────────────────────────────────────────────────────────
version          = 2.1.0

# ── Requirements ──────────────────────────────────────────────────────────────
requirements = python3,kivy,kivymd==1.2.0,pillow,android,pyjnius

# ── Android Permissions ───────────────────────────────────────────────────────
# INTERNET is required for WebView CDN loads (Leaflet, CartoDB, Chart.js)
# and mesh sync. Without this all WebView network requests are silently blocked.
android.permissions = INTERNET, ACCESS_NETWORK_STATE, ACCESS_WIFI_STATE, WAKE_LOCK

# ── Android Build Settings ────────────────────────────────────────────────────
android.minapi = 21
android.api    = 33
android.ndk    = 25b
android.archs  = arm64-v8a, armeabi-v7a

# cleartext HTTP for localhost:45678 BridgeServer is handled in Python via
# setMixedContentMode(0) on the WebView — no manifest entry needed.

# ── Orientation ───────────────────────────────────────────────────────────────
orientation = landscape

# ── Presplash / Icon ─────────────────────────────────────────────────────────
#icon.filename      = %(source.dir)s/icon.png
#presplash.filename = %(source.dir)s/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
