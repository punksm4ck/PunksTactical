# PUNKS OMNI DASHBOARD — Android APK Build Guide
## Kivy + KivyMD | Buildozer → APK

---

## Why the rewrite was necessary

| Desktop version | Android blocker |
|---|---|
| PyQt6 / QWebEngineView | Not available for Android |
| folium (generates HTML) | No file-based WebView in PyQt6 on Android |
| matplotlib + FigureCanvas | Qt backend unavailable |
| cryptography / Fernet | Works but unnecessary for Android keystore |
| QThread | Replaced with Kivy `Clock` + `UrlRequest` (non-blocking) |

**Solution:** Full port to **Kivy + KivyMD**. The map tab uses raw Leaflet.js HTML injected into an Android native `WebView` via `pyjnius`. Charts are replaced with scrollable KivyMD list/card layouts. Async networking uses Kivy's built-in `UrlRequest`.

---

## Prerequisites (Ubuntu / Debian build machine)

```bash
# System deps
sudo apt update
sudo apt install -y \
    python3-pip python3-venv git zip unzip \
    build-essential libffi-dev libssl-dev \
    zlib1g-dev libbz2-dev libreadline-dev \
    libsqlite3-dev libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    openjdk-17-jdk autoconf libtool pkg-config

# Android SDK / NDK are downloaded automatically by Buildozer on first run
# But pre-installing is faster:
# https://developer.android.com/studio/command-line/sdkmanager
```

---

## Build steps

```bash
# 1. Clone / create project directory
mkdir -p ~/punks_android
# Copy main.py and buildozer.spec into ~/punks_android/

# 2. Create venv
cd ~/punks_android
python3 -m venv venv
source venv/bin/activate

# 3. Install buildozer + Cython
pip install --upgrade pip
pip install buildozer cython==3.0.11

# 4. (First-time only) Accept Android SDK license
buildozer android debug -- -y

# 5. Build debug APK
buildozer android debug

# Resulting APK will be at:
# ./bin/punksomni-2.0.0-arm64-v8a_armeabi-v7a-debug.apk
```

---

## Install to device

```bash
# Enable USB Debugging on the phone:
# Settings → About Phone → tap Build Number 7x → Developer Options → USB Debugging ON

# Plug in via USB, then:
adb install -r bin/punksomni-2.0.0-*-debug.apk

# Or copy the APK to the phone and open it (allow Unknown Sources)
```

---

## Signing for release (production)

```bash
# Generate a keystore (one time)
keytool -genkey -v \
    -keystore punks-release.jks \
    -alias punks \
    -keyalg RSA -keysize 4096 \
    -validity 10000

# Edit buildozer.spec and uncomment the keystore lines, then:
buildozer android release
```

---

## Project structure

```
punks_android/
├── main.py           ← The entire app (single-file, self-contained)
├── buildozer.spec    ← APK build config
├── assets/           ← (optional) icon.png, presplash.png
└── bin/              ← Built APKs appear here after buildozer runs
```

---

## Feature map vs desktop version

| Desktop feature | Android equivalent |
|---|---|
| QWebEngineView + folium | Android native WebView + Leaflet.js HTML |
| matplotlib bar charts | KivyMD stat cards + sorted list |
| QTabWidget (4 tabs) | MDBottomNavigation (4 screens) |
| GlobalMeshSync QThread | Kivy `UrlRequest` (non-blocking, no threads needed) |
| MeshServer TCP socket | `threading.Thread` (works on Android) |
| Encrypted local DB | Plain JSON vault in `app_storage_path()` |
| ICE detention module import | Removed (external app.main_window not portable) |
| AI infrastructure tracker | Removed (external ai_app.main_window not portable) |

---

## Debugging on device

```bash
# Live logcat (filter to your app)
adb logcat | grep -i "python\|punks\|kivy"

# Or via buildozer:
buildozer android logcat
```

---

## Common build failures

| Error | Fix |
|---|---|
| `NDK not found` | Let buildozer auto-download, or set `ANDROID_NDK_HOME` |
| `SDK license not accepted` | Run `buildozer android debug -- -y` first |
| `Cython version mismatch` | Pin to `cython==3.0.11` in venv |
| `jnius import fails at runtime` | Ensure `android.permissions` includes `INTERNET` |
| WebView blank on device | Check that `setJavaScriptEnabled(True)` is called; verify network permission |
| App crashes on start | Run `adb logcat` — usually a missing import or path error |
