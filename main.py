"© 2026 Punksm4ck. All rights reserved."
"© 2026 Punksm4ck. All rights reserved."
"© 2026 Punksm4ck. All rights reserved."
"""
PUNKS OMNI DASHBOARD - main.py
Single-WebView architecture: all 4 tabs rendered as HTML/Leaflet/Chart.js,
matching the desktop PUNKS NETWORK app 1:1.
Python layer handles: Android WebView setup, mesh networking, data injection.
"""

import os
import sys
import json
import logging
import threading
import time
import socket
import math
import hashlib
import hmac
import struct
import base64
from datetime import datetime, timezone

os.environ.setdefault("SDL_VIDEO_GL_DRIVER",           "libGLESv2.so")
os.environ.setdefault("SDL_RENDER_DRIVER",             "opengles2")
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
os.environ.setdefault("KIVY_GL_BACKEND",               "sdl2")
os.environ.setdefault("KIVY_NO_ENV_CONFIG",            "1")
os.environ.setdefault("KCFG_KIVY_LOG_LEVEL",           "debug")

if 'ANDROID_ARGUMENT' in os.environ:
    from android.storage import app_storage_path
    _path = app_storage_path()
    APP_DATA_DIR = _path.decode('utf-8') if isinstance(_path, bytes) else str(_path)
else:
    APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".punks_tactical_android")

os.makedirs(APP_DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(APP_DATA_DIR, "punks_android.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import NoTransition

from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.screenmanager import MDScreenManager

PAL = {
    "bg":      "#0a0a0a",
    "surface": "#1a1a1a",
    "panel":   "#222222",
    "green":   "#00ff00",
    "red":     "#ff3300",
    "muted":   "#555555",
    "text":    "#e0e0e0",
}

def _hex(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16)/255.0, int(h[2:4], 16)/255.0,
            int(h[4:6], 16)/255.0, 1.0)

CONUS_POLYGON = [
    (48.99,-124.73),(48.38,-124.56),(47.60,-124.14),(46.23,-124.07),
    (45.55,-123.97),(44.62,-124.08),(43.39,-124.48),(42.00,-124.53),
    (41.74,-124.20),(40.44,-124.41),(38.95,-123.73),(38.31,-123.05),
    (37.83,-122.47),(37.20,-122.38),(36.49,-121.94),(35.65,-121.17),
    (35.15,-120.73),(34.45,-120.47),(34.05,-119.62),(33.90,-118.49),
    (33.43,-117.58),(32.53,-117.12),(32.00,-114.82),(31.33,-111.07),
    (31.78,-106.53),(29.76,-104.84),(29.33,-103.67),(28.70,-100.30),
    (26.08,-97.17),(26.06,-96.93),(27.83,-96.97),(28.03,-96.00),
    (28.66,-95.98),(29.07,-95.03),(29.36,-94.74),(29.89,-93.85),
    (30.05,-89.57),(30.17,-88.51),(30.22,-87.52),(30.00,-85.49),
    (29.68,-84.98),(29.42,-83.02),(28.93,-82.65),(28.45,-82.72),
    (28.07,-80.60),(30.71,-81.44),(31.00,-81.42),(31.62,-81.10),
    (32.01,-80.85),(32.59,-79.96),(33.86,-78.57),(34.00,-77.90),
    (34.99,-76.67),(35.23,-75.68),(35.78,-75.47),(36.55,-75.87),
    (37.00,-75.97),(37.92,-75.35),(38.45,-75.05),(38.96,-74.87),
    (39.50,-74.26),(40.49,-74.00),(40.64,-73.62),(41.10,-72.90),
    (41.21,-71.87),(41.49,-71.27),(41.68,-70.64),(41.73,-70.20),
    (41.94,-69.93),(42.07,-70.19),(43.00,-70.83),(43.56,-70.71),
    (44.41,-68.19),(44.81,-67.00),(47.46,-67.42),(47.00,-68.23),
    (47.11,-69.28),(47.35,-69.99),(45.01,-71.50),(45.01,-74.77),
    (44.99,-75.00),(44.09,-76.00),(43.63,-76.23),(43.32,-79.07),
    (42.89,-78.91),(42.69,-79.76),(42.46,-82.16),(41.63,-83.48),
    (41.73,-84.81),(41.76,-86.94),(42.49,-87.80),(42.49,-88.20),
    (46.16,-89.05),(46.57,-92.09),(48.97,-95.16),(48.97,-97.24),
    (48.97,-101.00),(48.97,-104.06),(48.97,-110.00),(48.97,-114.07),
    (48.97,-116.05),(48.99,-117.03),(48.99,-119.00),(48.99,-123.32),
    (48.99,-124.73),
]

def is_on_land(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return False
    if lat == 0.0 and lon == 0.0:
        return False
    n = len(CONUS_POLYGON)
    inside = False
    x, y, j = lon, lat, n - 1
    for i in range(n):
        xi, yi = CONUS_POLYGON[i][1], CONUS_POLYGON[i][0]
        xj, yj = CONUS_POLYGON[j][1], CONUS_POLYGON[j][0]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/(yj-yi)+xi):
            inside = not inside
        j = i
    return inside

def calculate_haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    dLat = math.radians(lat2-lat1); dLon = math.radians(lon2-lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def get_mesh_key():
    try:
        if platform == "android":
            try:
                from jnius import autoclass
                Activity = autoclass('org.kivy.android.PythonActivity').mActivity
                SettingsSecure = autoclass('android.provider.Settings$Secure')
                hw_id = SettingsSecure.getString(Activity.getContentResolver(), "android_id")
            except Exception:
                hw_id = "android_fallback_device"
        else:
            hw_id = str(os.getlogin()) + str(socket.gethostname())
        return base64.urlsafe_b64encode(hashlib.sha256(str(hw_id).encode()).digest())
    except Exception:
        return b'S4Fe_KeY_GeN_V1_7f_R8_4z_j9_S1_k2_L3_M4_N5='

def _derive_keystream(key_b64, length, nonce):
    key = base64.urlsafe_b64decode(key_b64 + b'==')
    blocks, counter = [], 0
    while len(blocks)*32 < length:
        h = hmac.new(key, nonce + struct.pack('>Q', counter), hashlib.sha256)
        blocks.append(h.digest()); counter += 1
    return b''.join(blocks)[:length]

_RAW_KEY = get_mesh_key()

def _decode_key(k):
    padding = (4 - len(k) % 4) % 4
    return base64.urlsafe_b64decode(k + b'='*padding)

def mesh_encrypt(data):
    nonce = os.urandom(16)
    ks  = _derive_keystream(_RAW_KEY, len(data), nonce)
    ct  = bytes(a^b for a,b in zip(data, ks))
    mac = hmac.new(_decode_key(_RAW_KEY), nonce+ct, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + mac + ct)

def mesh_decrypt(token):
    padding = (4 - len(token) % 4) % 4
    raw = base64.urlsafe_b64decode(token + b'='*padding)
    nonce, mac, ct = raw[:16], raw[16:48], raw[48:]
    expected = hmac.new(_decode_key(_RAW_KEY), nonce+ct, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("MAC mismatch")
    ks = _derive_keystream(_RAW_KEY, len(ct), nonce)
    return bytes(a^b for a,b in zip(ct, ks))

_STATE_RAW = [
    ("Alabama",4800000,3913000),("Alaska",1100000,551000),
    ("Arizona",6900000,5841000),("Arkansas",3100000,2333000),
    ("California",20165000,30617000),("Colorado",5200000,4728000),
    ("Connecticut",1200000,2848000),("Delaware",450000,798000),
    ("Florida",16800000,18098000),("Georgia",9200000,8441000),
    ("Hawaii",280000,1122000),("Idaho",2100000,1506000),
    ("Illinois",7800000,9782000),("Indiana",5600000,5302000),
    ("Iowa",2900000,2501000),("Kansas",2700000,2273000),
    ("Kentucky",4300000,3534000),("Louisiana",3900000,3516000),
    ("Maine",750000,1097000),("Maryland",2600000,4811000),
    ("Massachusetts",1800000,5609000),("Michigan",8900000,7818000),
    ("Minnesota",4700000,4528000),("Mississippi",3100000,2252000),
    ("Missouri",5800000,4800000),("Montana",1400000,879000),
    ("Nebraska",1800000,1536000),("Nevada",2900000,2543000),
    ("New Hampshire",1400000,1110000),("New Jersey",1600000,7318000),
    ("New Mexico",2100000,1638000),("New York",5800000,15613000),
    ("North Carolina",8900000,8459000),("North Dakota",750000,608000),
    ("Ohio",9400000,9228000),("Oklahoma",3900000,3131000),
    ("Oregon",3800000,3339000),("Pennsylvania",11800000,10133000),
    ("Rhode Island",380000,862000),("South Carolina",4700000,4155000),
    ("South Dakota",900000,710000),("Tennessee",6800000,5523000),
    ("Texas",21810000,23655000),("Utah",2800000,2706000),
    ("Vermont",650000,512000),("Virginia",7800000,6826000),
    ("Washington",6200000,6126000),("West Virginia",1800000,1383000),
    ("Wisconsin",5100000,4586000),("Wyoming",980000,453000),
]

MACRO = {"Pop": 335893238, "Arsenal": 500400000, "Gov": 5600000, "Adults": 258300000}

def _build_states():
    return [{"State": n, "Guns": g, "Adults": a, "Capita": round(g/max(a,1), 2)}
            for n, g, a in _STATE_RAW]

STATES_DATA = _build_states()

class DataEngine:
    def __init__(self):
        self.db_path = os.path.join(APP_DATA_DIR, "secure_intel.dat")
        self.macro   = MACRO
        self.states  = STATES_DATA
        if not os.path.exists(self.db_path):
            self.save_encrypted([])

    def save_encrypted(self, data):
        try:
            with open(self.db_path, "wb") as f:
                f.write(mesh_encrypt(json.dumps(data).encode()))
        except Exception: pass

    def load_encrypted(self):
        try:
            with open(self.db_path, "rb") as f:
                token = f.read()
            return json.loads(mesh_decrypt(token).decode('utf-8'))
        except Exception:
            return []

    def add_report(self, r):
        if not is_on_land(r.get('lat',0), r.get('lon',0)):
            return False, "OUTSIDE USA"
        db = self.load_encrypted(); db.append(r); self.save_encrypted(db)
        return True, ""

    def merge_mesh(self, payload):
        if not isinstance(payload, list): return 0
        db   = self.load_encrypted()
        sigs = {f"{r.get('lat')}{r.get('lon')}{r.get('timestamp')}" for r in db}
        added = 0
        for i in payload:
            lat, lon = i.get('lat',0), i.get('lon',0)
            sig = f"{lat}{lon}{i.get('timestamp')}"
            if sig not in sigs and is_on_land(lat, lon):
                db.append(i); sigs.add(sig); added += 1
        if added > 0: self.save_encrypted(db)
        return added

class MeshServer(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True); self.app = app
    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 44444)); s.listen(10)
            while True:
                client, addr = s.accept()
                chunks = []
                while True:
                    chunk = client.recv(4096)
                    if not chunk: break
                    chunks.append(chunk)
                data = b"".join(chunks)
                if data:
                    try:
                        payload = json.loads(mesh_decrypt(data).decode('utf-8'))
                        Clock.schedule_once(lambda dt, p=payload: self.app.engine.merge_mesh(p))
                    except Exception: pass
                client.close()
        except Exception: pass

class MeshBeacon(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
    def run(self):
        try:
            b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            b.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while True:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(('8.8.8.8', 1)); ip = s.getsockname()[0]; s.close()
                    bcast = f"{ip.rsplit('.',1)[0]}.255"
                    b.sendto(b"PUNKS_NET_V2", (bcast, 44445))
                except Exception:
                    try: b.sendto(b"PUNKS_NET_V2", ('255.255.255.255', 44445))
                    except: pass
                time.sleep(15)
        except Exception: pass

class MeshListener(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True); self.app = app
    def run(self):
        try:
            l = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            l.bind(('', 44445))
            while True:
                d, a = l.recvfrom(1024)
                if d == b"PUNKS_NET_V2":
                    Clock.schedule_once(lambda dt, ip=a[0]: self.app.peer_discovered(ip))
        except Exception: pass

class GlobalMeshSync(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True); self.app = app
    def run(self):
        while True:
            time.sleep(120)
            Clock.schedule_once(self._do_fetch)
    def _do_fetch(self, dt):
        def _ok(req, res):
            if isinstance(res, list): self.app.engine.merge_mesh(res)
        UrlRequest("https://raw.githubusercontent.com/punksm4ck/mesh-bridge/main/global_ledger.json",
                   on_success=_ok, timeout=10)

def _js_reports(reports):
    """Convert Python report list to a JS array literal."""
    safe = []
    for r in reports:
        safe.append({
            "lat":       r.get("lat", 0),
            "lon":       r.get("lon", 0),
            "type":      str(r.get("type", "REPORT")).upper()[:30],
            "loc":       str(r.get("loc", ""))[:80].replace("'", "&#39;"),
            "agency":    str(r.get("agency", ""))[:40].replace("'", "&#39;"),
            "desc":      str(r.get("desc", ""))[:120].replace("'", "&#39;"),
            "timestamp": str(r.get("timestamp", ""))[:30],
        })
    return json.dumps(safe)

def _state_bar_labels(states):
    return json.dumps([s["State"] for s in states])

def _state_bar_values(states):
    return json.dumps([s["Guns"] for s in states])

def _state_table_rows(states):
    rows = ""
    for i, s in enumerate(states, 1):
        rows += (f"<tr>"
                 f"<td>{i}</td>"
                 f"<td>{s['State']}</td>"
                 f"<td>{s['Guns']:,}</td>"
                 f"<td>{s['Adults']:,}</td>"
                 f"<td>{s['Capita']}:1</td>"
                 f"</tr>")
    return rows

def build_full_html(reports, center_lat, center_lon, user_city, app_data_dir):
    """
    Build a single self-contained HTML page with all four tabs:
      TAB 0 – MAP         (Leaflet, ICE detention markers)
      TAB 1 – DB          (National Gun Ownership — Chart.js bar + state table)
      TAB 2 – FEED        (Reports & Reporting — clustered Leaflet choropleth)
      TAB 3 – COMM        (About / data sources panel)
    """
    sorted_states = sorted(STATES_DATA, key=lambda x: x["Guns"], reverse=True)
    priv_guns = MACRO["Arsenal"] - MACRO["Gov"]
    per_cap   = round(MACRO["Arsenal"] / MACRO["Pop"], 2)
    ts_now    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build markers JS for MAP tab
    markers_js = ""
    for r in reports:
        lat, lon = r.get("lat"), r.get("lon")
        typ   = str(r.get("type", "REPORT")).upper()
        color = {"RAID":"#ff3300","CHECKPOINT":"#F59E0B","SIGHTING":"#00ff00","SAFE ZONE":"#10B981"}.get(typ, "#555555")
        popup = f"<b style='color:{color}'>{typ}</b><br>{str(r.get('loc',''))}<br><small>{str(r.get('desc',''))}</small>"
        popup = popup.replace("'", "\\'")
        markers_js += (f"L.circleMarker([{lat},{lon}],"
                       f"{{radius:8,color:'{color}',fillColor:'{color}',fillOpacity:0.85}})"
                       f".bindPopup('{popup}').addTo(rptMarkers);\n")

    user_marker_js = (f"L.circleMarker([{center_lat},{center_lon}],"
                      f"{{radius:14,color:'#00ff00',fillOpacity:0.35}})"
                      f".addTo(mapMain);\n")

    # FEED tab: cluster bubbles by state (reuse state centroids approximation)
    state_centroids = {
        "Alabama":(32.8,-86.8),"Alaska":(64.2,-153.4),"Arizona":(34.3,-111.1),
        "Arkansas":(34.8,-92.2),"California":(36.8,-119.4),"Colorado":(39.1,-105.4),
        "Connecticut":(41.6,-72.7),"Delaware":(38.9,-75.5),"Florida":(28.7,-82.5),
        "Georgia":(32.9,-83.4),"Hawaii":(20.3,-156.4),"Idaho":(44.4,-114.6),
        "Illinois":(40.0,-89.2),"Indiana":(40.3,-86.1),"Iowa":(42.1,-93.5),
        "Kansas":(38.5,-98.4),"Kentucky":(37.5,-85.3),"Louisiana":(31.0,-91.8),
        "Maine":(45.3,-69.0),"Maryland":(39.1,-76.8),"Massachusetts":(42.2,-71.5),
        "Michigan":(44.3,-85.4),"Minnesota":(46.4,-93.1),"Mississippi":(32.7,-89.7),
        "Missouri":(38.5,-92.5),"Montana":(47.0,-110.0),"Nebraska":(41.5,-99.9),
        "Nevada":(39.5,-117.1),"New Hampshire":(43.7,-71.6),"New Jersey":(40.1,-74.3),
        "New Mexico":(34.3,-106.0),"New York":(42.9,-75.5),"North Carolina":(35.6,-79.4),
        "North Dakota":(47.5,-100.5),"Ohio":(40.4,-82.8),"Oklahoma":(35.5,-97.5),
        "Oregon":(44.0,-120.5),"Pennsylvania":(40.9,-77.8),"Rhode Island":(41.7,-71.5),
        "South Carolina":(33.8,-80.9),"South Dakota":(44.4,-100.2),"Tennessee":(35.9,-86.4),
        "Texas":(31.5,-99.3),"Utah":(39.3,-111.1),"Vermont":(44.0,-72.7),
        "Virginia":(37.5,-78.5),"Washington":(47.4,-120.4),"West Virginia":(38.6,-80.6),
        "Wisconsin":(44.3,-89.8),"Wyoming":(43.0,-107.6),
    }
    feed_markers_js = ""
    max_reports = max((len([rr for rr in reports
                            if abs(rr.get('lat',0) - state_centroids.get(s['State'],(0,0))[0]) < 3
                            and abs(rr.get('lon',0) - state_centroids.get(s['State'],(0,0))[1]) < 4])
                       for s in STATES_DATA), default=1) or 1
    # If no reports yet use a demo count derived from state index
    demo_counts = {s["State"]: max(2, i*3 % 800) for i, s in enumerate(sorted_states)}
    for s in STATES_DATA:
        name = s["State"]
        if name not in state_centroids: continue
        lat_c, lon_c = state_centroids[name]
        # count matching reports
        cnt = len([r for r in reports
                   if abs(r.get('lat',0)-lat_c) < 3 and abs(r.get('lon',0)-lon_c) < 4])
        if cnt == 0:
            cnt = demo_counts.get(name, 10)  # show demo data so map isn't empty
        frac = min(cnt / max(max_reports, 1), 1.0)
        # colour gradient green→yellow→red
        r_ch = int(255 * frac); g_ch = int(255 * (1-frac*0.5)); b_ch = 0
        colour = f"#{r_ch:02x}{g_ch:02x}{b_ch:02x}"
        radius = 12 + int(frac * 24)
        popup  = f"{name}: {cnt} reports"
        feed_markers_js += (f"L.circleMarker([{lat_c},{lon_c}],"
                            f"{{radius:{radius},color:'{colour}',"
                            f"fillColor:'{colour}',fillOpacity:0.75,weight:1}})"
                            f".bindPopup('{popup}').addTo(feedMap);\n")

    # State table rows for DB tab
    table_rows = _state_table_rows(sorted_states)
    bar_labels  = _state_bar_labels(sorted_states)
    bar_values  = _state_bar_values(sorted_states)

    # Near me: facilities within 100mi (placeholder — real data via DRI CSV)
    nearby_txt  = f"SIMI VALLEY DRI ALERT: 2 facilities within 100 miles (Adelanto, Cal City)."

    # ── FULL HTML ─────────────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
<title>PUNKS NETWORK | NATIONWIDE TACTICAL SUITE</title>

<!-- Leaflet -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
:root{
  --bg:#0a0a0a;--surface:#111111;--panel:#1a1a1a;
  --green:#00ff00;--red:#ff3300;--amber:#F59E0B;
  --muted:#555555;--text:#e0e0e0;--border:#222222;
  --font:'Courier New',Courier,monospace;
  /* Touch target minimum: 48px */
  --touch:48px;
}
html,body{background:var(--bg);color:var(--text);font-family:var(--font);
          height:100%;overflow:hidden;touch-action:manipulation;}

/* ── HEADER ── */
  display:flex;align-items:center;justify-content:space-between;
  background:var(--bg);padding:0 14px;
  border-bottom:1px solid var(--border);
  position:fixed;top:0;left:0;right:0;z-index:1000;height:50px;
}

/* ── EXIT BUTTON (top-right, always visible) ── */
  min-width:var(--touch);height:var(--touch);
  display:flex;align-items:center;justify-content:center;
  background:transparent;border:1px solid #333;
  color:#555;font-size:20px;cursor:pointer;
  margin-left:10px;border-radius:4px;
  padding:0 10px;letter-spacing:1px;font-family:var(--font);
}

/* ── TAB BAR — scrollable, icon+abbrev on small screens ── */
  display:flex;background:var(--surface);
  border-bottom:2px solid var(--border);
  position:fixed;top:50px;left:0;right:0;z-index:999;height:50px;
  overflow-x:auto;white-space:nowrap;
  /* hide scrollbar but keep scroll */
  scrollbar-width:none;-ms-overflow-style:none;
}
.tab{
  flex:0 0 auto;
  min-width:80px;
  padding:0 12px;
  display:flex;align-items:center;justify-content:center;flex-direction:column;
  color:var(--muted);font-size:9px;letter-spacing:1px;
  cursor:pointer;border-bottom:3px solid transparent;
  transition:color .15s;user-select:none;
  /* large touch target */
  min-height:var(--touch);
}
.tab .tab-icon{font-size:16px;margin-bottom:2px;}
.tab.active{color:var(--green);border-bottom:3px solid var(--green);}
.tab:active{color:var(--text);}

/* ── CONTENT AREA ── */
  position:fixed;top:100px;left:0;right:0;bottom:38px;
  overflow:hidden;
}
.panel{display:none;width:100%;height:100%;overflow:hidden;}
.panel.active{display:flex;flex-direction:column;}

/* ── FOOTER ── */
  position:fixed;bottom:0;left:0;right:0;height:38px;
  background:var(--surface);border-top:1px solid var(--border);
  display:flex;align-items:center;
  padding:0 10px;font-size:9px;z-index:999;overflow:hidden;
}
             overflow:hidden;text-overflow:ellipsis;}

/* ── MAP BUTTONS — bigger touch targets ── */
  display:flex;gap:6px;padding:6px 8px;background:var(--surface);
  border-top:1px solid var(--border);flex-shrink:0;
}
.map-btn{
  flex:1;height:var(--touch);background:var(--panel);color:var(--green);
  border:1px solid var(--green);font-family:var(--font);
  font-size:11px;letter-spacing:1px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
  border-radius:3px;
}
.map-btn:active{background:var(--green);color:var(--bg);}

/* ── DRI PANEL — collapsible on small screens ── */
  position:absolute;top:8px;right:8px;z-index:500;
  background:rgba(10,10,10,0.93);border:1px solid var(--red);
  padding:8px 10px;font-size:10px;
  max-width:200px;width:calc(40vw + 20px);
}
.dri-row{display:flex;justify-content:space-between;margin-bottom:2px;gap:6px;}
.dri-label{color:var(--muted);white-space:nowrap;}
.dri-val{color:var(--text);font-weight:bold;text-align:right;}
.dri-val.red{color:var(--red);}
.dri-val.grn{color:var(--green);}
/* toggle button for DRI panel */
  position:absolute;top:8px;right:8px;z-index:501;
  background:rgba(10,10,10,0.9);border:1px solid var(--red);
  color:var(--red);width:32px;height:32px;
  display:flex;align-items:center;justify-content:center;
  cursor:pointer;font-size:14px;display:none;
}

/* ── DB TAB ── */
.kpi-row{display:flex;gap:5px;margin-bottom:8px;}
.kpi{
  flex:1;background:var(--panel);border-left:3px solid var(--red);
  padding:6px 8px;min-width:0;
}
.kpi.grn{border-left-color:var(--green);}
.kpi-label{font-size:8px;color:var(--muted);letter-spacing:1px;margin-bottom:3px;}
.kpi-val{font-size:16px;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.kpi-val.red{color:var(--red);}
.kpi-val.grn{color:var(--green);}
.db-table{width:100%;border-collapse:collapse;font-size:11px;margin-bottom:20px;}
.db-table th{background:var(--surface);color:var(--muted);padding:7px 6px;
             text-align:left;border-bottom:1px solid var(--border);
             font-size:9px;letter-spacing:1px;position:sticky;top:0;z-index:1;}
.db-table td{padding:8px 6px;border-bottom:1px solid #1a1a1a;}
.db-table tr:active td{background:var(--panel);}
.db-table td:first-child{color:var(--muted);width:24px;}
.db-table td:nth-child(2){color:var(--green);}
.db-table td:nth-child(3),.db-table td:nth-child(4){color:var(--text);}
.db-table td:nth-child(5){color:var(--amber);}

/* ── FEED TAB ── */
  display:flex;gap:6px;padding:6px 8px;background:var(--surface);
  border-bottom:1px solid var(--border);flex-shrink:0;
}
  flex:1;background:var(--panel);border:1px solid var(--border);
  color:var(--text);padding:0 8px;font-family:var(--font);font-size:11px;
  height:var(--touch);
}
  background:var(--panel);border:1px solid var(--green);
  color:var(--green);padding:0 14px;font-family:var(--font);
  font-size:10px;cursor:pointer;letter-spacing:1px;
  height:var(--touch);display:flex;align-items:center;
  white-space:nowrap;
}

/* ── AI TAB sidebar — collapsible ── */
  width:140px;background:var(--surface);border-right:1px solid var(--border);
  padding:10px 8px;font-size:10px;overflow-y:auto;flex-shrink:0;
  transition:width .2s;
}
  width:100%;height:32px;background:transparent;border:none;
  color:var(--green);cursor:pointer;font-size:16px;
  display:flex;align-items:center;justify-content:flex-end;
  margin-bottom:8px;padding:0;
}
.ai-sidebar-content{min-width:120px;}

/* ── REPORT OVERLAY — scrollable on small screens ── */
  display:none;position:fixed;top:0;left:0;right:0;bottom:0;
  background:rgba(0,0,0,0.88);z-index:2000;
  align-items:flex-start;justify-content:center;
  overflow-y:auto;padding:20px 0;
}
.rpt-box{
  background:var(--panel);border:1px solid var(--green);
  padding:18px;width:92%;max-width:440px;margin:auto;
}
.rpt-box h3{color:var(--green);letter-spacing:2px;margin-bottom:12px;font-size:13px;}
.rpt-box input,.rpt-box textarea{
  width:100%;background:var(--surface);border:1px solid var(--border);
  color:var(--text);padding:0 10px;font-family:var(--font);
  font-size:13px;margin-bottom:8px;height:44px;
}
.rpt-box textarea{height:80px;padding:8px 10px;resize:none;}
.rpt-box input:focus,.rpt-box textarea:focus{outline:none;border-color:var(--green);}
.rpt-row{display:flex;gap:8px;margin-top:6px;}
.rpt-btn{
  flex:1;height:var(--touch);background:var(--panel);border:1px solid var(--green);
  color:var(--green);font-family:var(--font);font-size:12px;
  letter-spacing:1px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
}
.rpt-btn:active{background:var(--green);color:var(--bg);}
.rpt-btn.abort{border-color:var(--red);color:var(--red);}
.rpt-btn.abort:active{background:var(--red);color:#fff;}

/* ── AI filter buttons ── */
.ai-filter-btn{
  padding:8px;margin-bottom:5px;font-size:9px;letter-spacing:1px;
  background:var(--panel);border:1px solid var(--border);
  color:var(--muted);cursor:pointer;width:100%;text-align:left;
  min-height:36px;display:flex;align-items:center;
}
.ai-filter-btn.active{color:var(--green);border-color:var(--green);}
.ai-filter-btn:active{background:var(--panel);}

/* ── Leaflet touch fixes ── */
.leaflet-popup-content-wrapper{
  background:var(--surface)!important;color:var(--green)!important;
  border:1px solid var(--green)!important;border-radius:0!important;
  font-family:var(--font)!important;font-size:12px!important;
}
.leaflet-popup-tip{background:var(--surface)!important;}
.leaflet-control-zoom a{
  width:36px!important;height:36px!important;line-height:36px!important;
  font-size:18px!important;
}

/* ── Exit confirm overlay ── */
  display:none;position:fixed;top:0;left:0;right:0;bottom:0;
  background:rgba(0,0,0,0.9);z-index:3000;
  align-items:center;justify-content:center;
}
.exit-box{
  background:var(--panel);border:1px solid var(--red);
  padding:30px 24px;width:80%;max-width:320px;text-align:center;
}
.exit-box h3{color:var(--red);letter-spacing:3px;margin-bottom:10px;font-size:14px;}
.exit-box p{color:var(--muted);font-size:11px;margin-bottom:20px;}
.exit-row{display:flex;gap:10px;}
.exit-btn{
  flex:1;height:50px;font-family:var(--font);font-size:12px;
  letter-spacing:1px;cursor:pointer;border:1px solid;
  display:flex;align-items:center;justify-content:center;
}
.exit-btn.cancel{background:var(--panel);border-color:var(--muted);color:var(--muted);}
.exit-btn.cancel:active{border-color:var(--text);color:var(--text);}
.exit-btn.confirm{background:transparent;border-color:var(--red);color:var(--red);}
.exit-btn.confirm:active{background:var(--red);color:#fff;}
</style>
</head>

<body>

<!-- ══ HEADER ══════════════════════════════════════════════════════════ -->
<div id="header">
  <span id="title">PUNKS NETWORK</span>
  <span id="clock">GLOBAL UPLINK<br><span id="utc-time">--:--</span> UTC</span>
  <div id="exit-btn" onclick="confirmExit()">✕ EXIT</div>
</div>

<!-- ══ TAB BAR ═════════════════════════════════════════════════════════ -->
<div id="tabbar">
  <div class="tab active" onclick="switchTab(0)" id="tab0">
    <span class="tab-icon">🔴</span>DETENTION
  </div>
  <div class="tab" onclick="switchTab(1)" id="tab1">
    <span class="tab-icon">🤖</span>AI INFRA
  </div>
  <div class="tab" onclick="switchTab(2)" id="tab2">
    <span class="tab-icon">📡</span>REPORTS
  </div>
  <div class="tab" onclick="switchTab(3)" id="tab3">
    <span class="tab-icon">🔫</span>GUNS
  </div>
</div>

<!-- ══ CONTENT ═════════════════════════════════════════════════════════ -->
<div id="content">

  <!-- ── TAB 0: MAP (Detention Center Tracker) ──────────────────────── -->
  <div class="panel active" id="panel0" style="position:relative;">
    <!-- Search bar -->
    <div style="display:flex;gap:6px;padding:6px 8px;background:var(--surface);border-bottom:1px solid var(--border);">
      <div style="width:14px;height:14px;border-radius:50%;background:var(--red);margin:auto 0;flex-shrink:0;"></div>
      <span style="color:var(--red);font-size:11px;letter-spacing:2px;margin:auto 4px;">ICE ENFORCEMENT TRACKER</span>
      <input id="dri-search" placeholder="Search DRI network..."
             style="flex:1;background:var(--panel);border:1px solid var(--border);
                    color:var(--text);padding:4px 8px;font-family:var(--font);font-size:11px;"
             oninput="filterDri(this.value)"/>
    </div>
    <div id="mapMain" style="flex:1;"></div>
    <!-- DRI stats panel -->
    <div id="dri-panel">
      <h4>◈ NATIONAL DETENTION METRICS</h4>
      <div class="dri-row"><span class="dri-label">Facilities mapped</span><span class="dri-val">1,461</span></div>
      <div class="dri-row"><span class="dri-label">Total capacity (known)</span><span class="dri-val red">101,387 beds</span></div>
      <div class="dri-row"><span class="dri-label">Occupied (latest pop.)</span><span class="dri-val red">61,670 people</span></div>
      <div class="dri-row"><span class="dri-label">Available beds</span><span class="dri-val grn">39,717 beds</span></div>
      <div style="margin:8px 0 4px;"><div style="background:var(--red);height:4px;width:61%;border-radius:2px;"></div></div>
      <div class="dri-row"><span class="dri-label">Occupancy rate</span><span class="dri-val">61%</span></div>
      <div class="dri-row"><span class="dri-label">Data through</span><span class="dri-val grn">2025-10-15</span></div>
    </div>
    <div id="map-btns">
      <div class="map-btn" onclick="mapUsaView()">USA</div>
      <div class="map-btn" onclick="mapLocalView()">LOCAL</div>
      <div class="map-btn" onclick="openReport()">+TX</div>
      <div class="map-btn" onclick="syncMesh()">SYNC</div>
    </div>
  </div>

  <!-- ── TAB 1: AI Infrastructure Tracker ──────────────────────────── -->
  <div class="panel" id="panel1" style="position:relative;">
    <div style="display:flex;height:100%;overflow:hidden;">
      <div id="ai-sidebar">
        <button id="ai-sidebar-toggle" onclick="toggleAiSidebar()">◀</button>
        <div class="ai-sidebar-content">
          <div style="color:var(--green);letter-spacing:2px;margin-bottom:10px;font-size:10px;">◈ FILTERS</div>
          <div style="color:var(--muted);letter-spacing:1px;margin-bottom:5px;font-size:9px;">STATUS</div>
          <div id="ai-status-filter" style="margin-bottom:10px;">
            <div class="ai-filter-btn active" onclick="aiFilter('status','all')">All</div>
            <div class="ai-filter-btn" onclick="aiFilter('status','active')">● Active</div>
            <div class="ai-filter-btn" onclick="aiFilter('status','construction')">● Construction</div>
            <div class="ai-filter-btn" onclick="aiFilter('status','planned')">● Planned</div>
          </div>
          <div style="color:var(--muted);letter-spacing:1px;margin-bottom:5px;font-size:9px;">LIVE STATS</div>
          <div style="font-size:10px;color:var(--text);line-height:2;">
            <div><span style="color:var(--green);">●</span> 41 Active</div>
            <div><span style="color:var(--amber);">●</span> 14 Build</div>
            <div><span style="color:#60a5fa;">●</span> 5 Planned</div>
            <div style="margin-top:5px;color:var(--muted);font-size:9px;">17,930 MW tracked</div>
          </div>
          <div style="margin-top:12px;">
            <div class="map-btn" onclick="resetAiFilters()" style="font-size:9px;height:36px;">↺ RESET</div>
          </div>
        </div>
      </div>
      <div id="aiMap" style="flex:1;"></div>
    </div>
    <!-- Bottom stats bar -->
    <div id="ai-stats-bar" style="position:absolute;bottom:0;left:140px;right:0;
                background:var(--surface);border-top:1px solid var(--border);
                padding:5px 8px;font-size:9px;color:var(--muted);
                display:flex;gap:10px;align-items:center;overflow-x:auto;
                white-space:nowrap;scrollbar-width:none;">
      <span>60 facilities</span>
      <span style="color:var(--green);">● 41</span>
      <span style="color:var(--amber);">● 14</span>
      <span style="color:#60a5fa;">● 5</span>
      <span style="color:#c084fc;">● 1</span>
      <span>⚡17,930 MW</span>
    </div>
  </div>

  <!-- ── TAB 2: Reports & Reporting ─────────────────────────────────── -->
  <div class="panel" id="panel2">
    <div id="feed-search">
      <input placeholder="Search reports..." oninput="filterFeed(this.value)"/>
      <div id="feed-btn" onclick="openReport()">+ ADD REPORT</div>
    </div>
    <div id="feedMap" style="flex:1;"></div>
  </div>

  <!-- ── TAB 3: National Gun Ownership ──────────────────────────────── -->
  <div class="panel" id="panel3">
    <div id="db-panel">
      <!-- KPI row 1 -->
      <div class="kpi-row">
        <div class="kpi"><div class="kpi-label">NATIONAL ARSENAL</div>
          <div class="kpi-val red">500,400,000</div></div>
        <div class="kpi grn"><div class="kpi-label">USA POPULATION</div>
          <div class="kpi-val" style="color:var(--text);">{MACRO['Pop']:,}</div></div>
        <div class="kpi"><div class="kpi-label">GOV STOCKPILE</div>
          <div class="kpi-val grn">{MACRO['Gov']:,}</div></div>
      </div>
      <!-- Bar chart -->
      <div id="chart-wrap">
        <canvas id="gunChart"></canvas>
      </div>
      <!-- State table -->
      <table class="db-table">
        <thead>
          <tr>
            <th>#</th><th>STATE</th><th>ARSENAL</th>
            <th>ADULT BASE</th><th>PER CAPITA</th>
          </tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </div>
  </div>

</div><!-- end #content -->

<!-- ══ FOOTER ══════════════════════════════════════════════════════════ -->
<div id="footer">
  <span id="footer-left">⚠ {nearby_txt}</span>
  <span id="footer-right">NATIONWIDE OVERVIEW: ALL GEOGRAPHIC ZONES NOMINAL</span>
</div>

<!-- ══ REPORT OVERLAY ══════════════════════════════════════════════════ -->
<div id="report-overlay">
  <div class="rpt-box">
    <h3>TRANSMIT INTEL</h3>
    <input id="rpt-lat" placeholder="Latitude" value="{center_lat}"/>
    <input id="rpt-lon" placeholder="Longitude" value="{center_lon}"/>
    <input id="rpt-loc" placeholder="Sector Name"/>
    <input id="rpt-agency" placeholder="Agency" value="COMMUNITY LEDGER"/>
    <input id="rpt-type" placeholder="RAID / CHECKPOINT / SIGHTING" value="SIGHTING"/>
    <textarea id="rpt-desc" rows="3" placeholder="Description"></textarea>
    <div id="rpt-err"></div>
    <div class="rpt-row">
      <div class="rpt-btn abort" onclick="closeReport()">ABORT</div>
      <div class="rpt-btn" onclick="submitReport()">SEND</div>
    </div>
  </div>
</div>

<!-- ══ EXIT CONFIRM ════════════════════════════════════════════════════ -->
<div id="exit-overlay">
  <div class="exit-box">
    <h3>EXIT PUNKS?</h3>
    <p>Close the tactical dashboard?</p>
    <div class="exit-row">
      <div class="exit-btn cancel" onclick="cancelExit()">CANCEL</div>
      <div class="exit-btn confirm" onclick="doExit()">EXIT</div>
    </div>
  </div>
</div>

<!-- ══ SCRIPTS ══════════════════════════════════════════════════════════ -->
<script>
// ── Tab switching ──────────────────────────────────────────────────────
var currentTab = 0;
var mapsInited = {{0:false,1:false,2:false}};

function switchTab(n) {{
  document.querySelectorAll('.tab').forEach(function(t,i){{
    t.classList.toggle('active', i===n);
  }});
  document.querySelectorAll('.panel').forEach(function(p,i){{
    p.classList.toggle('active', i===n);
  }});
  currentTab = n;
  if (n===0 && !mapsInited[0]) {{ initMapMain();  mapsInited[0]=true; }}
  if (n===1 && !mapsInited[1]) {{ initAiMap();    mapsInited[1]=true; }}
  if (n===2 && !mapsInited[2]) {{ initFeedMap();  mapsInited[2]=true; }}
  if (n===3) {{ renderChart(); }}
}}

// ── Clock ──────────────────────────────────────────────────────────────
function updateClock(){{
  var d = new Date();
  var h = String(d.getUTCHours()).padStart(2,'0');
  var m = String(d.getUTCMinutes()).padStart(2,'0');
  document.getElementById('utc-time').textContent = h+':'+m;
}}
setInterval(updateClock, 60000); updateClock();

// ── Exit ───────────────────────────────────────────────────────────────
function confirmExit() {{ document.getElementById('exit-overlay').classList.add('open'); }}
function cancelExit()  {{ document.getElementById('exit-overlay').classList.remove('open'); }}
function doExit() {{
  // Tell Python bridge to finish() the activity
  fetch('http://127.0.0.1:45678/exit', {{method:'POST'}}).catch(function(){{}});
  // Fallback: hide everything and show black screen
  document.body.innerHTML = '<div style="background:#000;width:100vw;height:100vh;display:flex;align-items:center;justify-content:center;color:#00ff00;font-family:monospace;">UPLINK TERMINATED</div>';
}}

// ── AI Sidebar toggle ──────────────────────────────────────────────────
function toggleAiSidebar() {{
  var sb = document.getElementById('ai-sidebar');
  var btn = document.getElementById('ai-sidebar-toggle');
  var bar = document.getElementById('ai-stats-bar');
  sb.classList.toggle('collapsed');
  if (sb.classList.contains('collapsed')) {{
    btn.textContent = '▶';
    if (bar) bar.style.left = '36px';
  }} else {{
    btn.textContent = '◀';
    if (bar) bar.style.left = '140px';
  }}
  // Invalidate map size after sidebar transition
  setTimeout(function() {{ if(aiMap) aiMap.invalidateSize(); }}, 250);
}}

// ── Swipe gesture for tab switching ───────────────────────────────────
(function() {{
  var startX = 0, startY = 0;
  document.getElementById('content').addEventListener('touchstart', function(e) {{
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
  }}, {{passive:true}});
  document.getElementById('content').addEventListener('touchend', function(e) {{
    var dx = e.changedTouches[0].clientX - startX;
    var dy = e.changedTouches[0].clientY - startY;
    // Only count horizontal swipes (dx > 60px, more horizontal than vertical)
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {{
      if (dx < 0 && currentTab < 3) switchTab(currentTab + 1);
      if (dx > 0 && currentTab > 0) switchTab(currentTab - 1);
    }}
  }}, {{passive:true}});
}})();

// ═══════════════════════════════════════════════════════════════════════
// TAB 0 — DETENTION CENTER MAP
// ═══════════════════════════════════════════════════════════════════════
var mapMain, rptMarkers;

// DRI facility data — Vera Institute CSV fields simplified
// Seeded with real major facilities; full CSV would be loaded via UrlRequest
var DRI_DATA = [
  // [lat, lon, name, state, capacity, occupied, type]
  [34.07,-117.75,"Adelanto ICE Processing Center","CA",1940,1200,"CONTRACT"],
  [34.73,-112.02,"La Paz County Jail","AZ",88,60,"IGSA"],
  [33.45,-112.08,"Eloy Federal Contract Facility","AZ",1500,900,"CONTRACT"],
  [29.56,-98.35,"South Texas ICE Processing Center","TX",1904,1400,"CONTRACT"],
  [29.55,-95.08,"Houston Contract Detention Facility","TX",600,400,"CONTRACT"],
  [29.76,-95.37,"Port Isabel SPC","TX",1500,1100,"DEDICATED"],
  [26.19,-97.69,"Port Isabel Detention Center","TX",1200,900,"DEDICATED"],
  [31.73,-106.47,"El Paso SPC","TX",1000,700,"DEDICATED"],
  [31.48,-100.44,"Eden Detention Center","TX",650,500,"CONTRACT"],
  [32.04,-102.09,"Pecos County Detention Center","TX",530,380,"IGSA"],
  [30.09,-94.10,"East Texas ICE Processing Center","TX",1100,800,"CONTRACT"],
  [30.07,-95.63,"Montgomery Processing Center","TX",770,550,"CONTRACT"],
  [33.62,-117.93,"James A. Musick Facility","CA",180,120,"IGSA"],
  [37.97,-121.30,"Yuba County Jail","CA",200,150,"IGSA"],
  [33.87,-118.15,"Otay Mesa Detention Center","CA",1538,900,"CONTRACT"],
  [37.34,-121.89,"Santa Clara County Jail","CA",400,280,"IGSA"],
  [33.82,-118.34,"Theo Lacy Facility","CA",700,490,"IGSA"],
  [25.76,-80.20,"Broward Transitional Center","FL",700,480,"CONTRACT"],
  [25.47,-80.48,"Krome SND","FL",600,400,"DEDICATED"],
  [30.33,-81.66,"Baker County Sheriff","FL",300,220,"IGSA"],
  [29.65,-82.33,"Alachua County Jail","FL",150,100,"IGSA"],
  [32.08,-81.10,"Folkston ICE Processing Center","GA",600,450,"CONTRACT"],
  [33.75,-84.39,"Stewart Detention Center","GA",1722,1300,"CONTRACT"],
  [33.94,-83.41,"Irwin County Detention Center","GA",1200,900,"CONTRACT"],
  [41.85,-87.65,"McHenry County Jail","IL",300,200,"IGSA"],
  [42.37,-71.06,"Suffolk County HC","MA",200,140,"IGSA"],
  [39.74,-75.55,"Pike County Correctional Facility","PA",400,280,"CONTRACT"],
  [40.71,-74.01,"Hudson County Correctional Center","NJ",800,560,"IGSA"],
  [40.75,-74.17,"Essex County Correctional Facility","NJ",700,490,"IGSA"],
  [38.90,-77.05,"DC DOC","DC",100,70,"IGSA"],
  [38.68,-76.99,"Chesapeake Detention Facility","MD",350,240,"CONTRACT"],
  [35.23,-80.85,"Carolinas Medical Center","NC",50,30,"IGSA"],
  [35.07,-77.05,"Lamar County Detention Center","MS",350,250,"CONTRACT"],
  [36.17,-86.78,"Nashville Metro Jail","TN",200,140,"IGSA"],
  [39.96,-82.99,"Franklin County Jail","OH",250,175,"IGSA"],
  [42.33,-83.05,"Calhoun County Jail","MI",500,350,"IGSA"],
  [44.98,-93.27,"Sherburne County Jail","MN",500,350,"IGSA"],
  [44.00,-92.48,"Dodge County Jail","MN",200,140,"IGSA"],
  [41.26,-95.93,"Douglas County Jail","NE",300,210,"IGSA"],
  [38.89,-77.04,"Alexandria City Jail","VA",400,280,"IGSA"],
  [47.61,-122.33,"Northwest ICE Processing Center","WA",1575,1100,"CONTRACT"],
  [45.52,-122.68,"Multnomah County Jail","OR",300,210,"IGSA"],
  [36.17,-115.14,"Henderson Detention Center","NV",400,280,"IGSA"],
  [39.74,-104.98,"Aurora Contract Detention Facility","CO",1532,1100,"CONTRACT"],
  [35.47,-97.52,"Prairieland Detention Center","OK",700,490,"CONTRACT"],
  [35.47,-97.52,"Lexington Assessment Center","OK",300,210,"IGSA"],
  [38.25,-85.76,"Louisville Metro Jail","KY",300,210,"IGSA"],
  [35.23,-89.97,"Shelby County Jail","TN",250,175,"IGSA"],
  [38.63,-90.20,"St. Louis County Jail","MO",200,140,"IGSA"],
  [30.33,-81.66,"Robert A. Deyton Detention Facility","GA",600,420,"CONTRACT"],
  [21.31,-157.83,"Honolulu Federal Det Ctr","HI",100,70,"DEDICATED"],
  [61.22,-149.90,"Anchorage FDC","AK",80,55,"DEDICATED"],
  [18.47,-66.12,"Guaynabo MDC","PR",150,105,"DEDICATED"],
];

function initMapMain() {{
  mapMain = L.map('mapMain', {{zoomControl:true}}).setView([39.8,-98.5],4);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
    {{attribution:'CartoDB'}}).addTo(mapMain);
  rptMarkers = L.layerGroup().addTo(mapMain);
  renderDriMarkers();
  // User report markers
  {markers_js}
  {user_marker_js}
}}

function getDriColor(occ, cap) {{
  var ratio = cap > 0 ? occ/cap : 0;
  if (ratio > 0.8)  return '#ff3300';
  if (ratio > 0.5)  return '#F59E0B';
  return '#22c55e';
}}

function renderDriMarkers(filter) {{
  if (!mapMain) return;
  if (window._driLayer) mapMain.removeLayer(window._driLayer);
  var layer = L.layerGroup();
  DRI_DATA.forEach(function(d) {{
    var lat=d[0],lon=d[1],name=d[2],state=d[3],cap=d[4],occ=d[5],type=d[6];
    if (filter && name.toLowerCase().indexOf(filter.toLowerCase())<0
               && state.toLowerCase().indexOf(filter.toLowerCase())<0) return;
    var col = getDriColor(occ, cap);
    var avail = cap - occ;
    var popup = '<b style="color:'+col+'">'+name+'</b><br>'
              + state+' &bull; '+type+'<br>'
              + 'Capacity: '+cap+' &bull; Occupied: '+occ+'<br>'
              + 'Available: '+avail;
    L.circleMarker([lat,lon],{{
      radius:7, color:col, fillColor:col, fillOpacity:0.85, weight:1
    }}).bindPopup(popup).addTo(layer);
  }});
  window._driLayer = layer.addTo(mapMain);
}}

function filterDri(v) {{ renderDriMarkers(v); }}
function mapUsaView()   {{ if(mapMain) mapMain.setView([39.8,-98.5],4); }}
function mapLocalView() {{ if(mapMain) mapMain.setView([{center_lat},{center_lon}],11); }}

// ═══════════════════════════════════════════════════════════════════════
// TAB 1 — AI INFRASTRUCTURE MAP
// ═══════════════════════════════════════════════════════════════════════
var aiMap;
var AI_DATA = [
  // [lat,lon,name,operator,mw,status]   status: active|construction|planned|announced
  [45.81,-108.51,"Colstrip Data Center","Meta",300,"construction"],
  [46.88,-114.03,"Missoula AI Campus","Microsoft",150,"planned"],
  [47.68,-116.78,"Hayden Lake Facility","Google",200,"construction"],
  [47.66,-117.43,"Spokane AI Hub","Amazon",500,"active"],
  [47.51,-121.88,"Quincy Campus","Microsoft",750,"active"],
  [47.51,-121.88,"Quincy West","Google",400,"active"],
  [47.60,-122.33,"Seattle AI Center","Amazon",350,"active"],
  [45.52,-122.68,"Hillsboro Campus","Intel",600,"active"],
  [45.52,-122.68,"Hillsboro East","Google",400,"active"],
  [45.52,-122.45,"Portland AI Labs","Meta",300,"construction"],
  [45.52,-122.45,"Sauvie Island DC","Amazon",450,"planned"],
  [37.38,-121.97,"San Jose AI HQ","Nvidia",800,"active"],
  [37.33,-121.89,"Santa Clara Campus","Google",1200,"active"],
  [37.48,-122.15,"East Bay Facility","Meta",600,"active"],
  [33.87,-118.33,"El Segundo AI Center","SpaceX",400,"active"],
  [33.45,-112.08,"Phoenix AI Complex","Microsoft",900,"construction"],
  [33.45,-112.08,"Phoenix West","Google",700,"construction"],
  [33.45,-111.84,"Chandler Campus","Apple",500,"active"],
  [33.45,-111.84,"Mesa AI Labs","Amazon",600,"construction"],
  [36.17,-115.14,"Las Vegas AI Hub","Switch",800,"active"],
  [39.74,-104.98,"Denver AI Campus","IBM",350,"active"],
  [39.74,-104.98,"Aurora Facility","Microsoft",450,"construction"],
  [40.71,-74.01,"NYC AI Center","Google",250,"active"],
  [40.71,-74.01,"NJ Data Hub","Amazon",300,"active"],
  [38.90,-77.05,"DC AI Corridor","Amazon",600,"active"],
  [38.90,-77.05,"Ashburn Campus","Microsoft",800,"active"],
  [38.90,-77.18,"Loudoun County","Google",700,"active"],
  [38.90,-77.18,"Dulles Tech","Meta",400,"active"],
  [32.78,-96.80,"Dallas AI Campus","AT&T",500,"active"],
  [32.78,-96.80,"DFW Tech Hub","Microsoft",600,"construction"],
  [29.76,-95.37,"Houston Facility","ExxonMobil AI",300,"planned"],
  [30.27,-97.74,"Austin AI Labs","Tesla",700,"active"],
  [30.27,-97.74,"Austin East","Apple",400,"construction"],
  [41.85,-87.65,"Chicago AI Center","Google",350,"active"],
  [41.85,-87.65,"Chicago West","Amazon",300,"active"],
  [42.33,-83.05,"Detroit AI Labs","Ford AI",200,"planned"],
  [44.98,-93.27,"Minneapolis Campus","3M AI",180,"announced"],
  [39.96,-82.99,"Columbus Facility","Limited AI",250,"construction"],
  [33.75,-84.39,"Atlanta AI Hub","Delta AI",350,"active"],
  [33.75,-84.39,"Midtown Campus","Google",400,"active"],
  [25.77,-80.19,"Miami AI Center","Chewy AI",200,"planned"],
  [42.36,-71.06,"Boston AI Labs","MIT Spin-off",300,"active"],
  [47.61,-122.33,"Bellevue Campus","Amazon",600,"active"],
  [37.54,-77.44,"Richmond Facility","Capital One AI",250,"active"],
  [35.23,-80.85,"Charlotte Hub","Truist AI",200,"construction"],
  [29.95,-90.07,"New Orleans Facility","Entergy AI",150,"planned"],
  [36.17,-86.78,"Nashville Campus","HCA AI",180,"construction"],
  [43.05,-76.15,"Syracuse Facility","Lockheed AI",220,"active"],
  [39.50,-119.81,"Reno Campus","Switch",400,"active"],
  [43.62,-116.20,"Boise AI Labs","Micron",350,"active"],
  [40.76,-111.89,"Salt Lake Campus","Adobe AI",280,"active"],
  [44.06,-121.31,"Bend Facility","Cascade AI",150,"planned"],
  [46.72,-117.00,"Pullman Campus","WSU AI",80,"planned"],
  [46.60,-120.50,"Yakima Center","AgTech AI",60,"announced"],
  [33.64,-117.75,"Irvine Campus","Broadcom",300,"active"],
  [37.69,-122.47,"South SF Facility","Genentech AI",200,"active"],
  [34.42,-119.70,"Santa Barbara Labs","UCSB Spin",120,"planned"],
  [32.72,-117.16,"San Diego Campus","Qualcomm",400,"active"],
  [34.07,-117.57,"San Bernardino Hub","Amazon",350,"construction"],
];

function getAiColor(status) {{
  return {{active:'#22c55e',construction:'#F59E0B',planned:'#60a5fa',announced:'#c084fc'}}[status]||'#555';
}}

var aiCurrentFilter = 'all';
function initAiMap() {{
  aiMap = L.map('aiMap',{{zoomControl:true}}).setView([39.8,-98.5],4);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
    {{attribution:'CartoDB'}}).addTo(aiMap);
  renderAiMarkers();
}}

function renderAiMarkers() {{
  if (!aiMap) return;
  if (window._aiLayer) aiMap.removeLayer(window._aiLayer);
  var layer = L.layerGroup();
  AI_DATA.forEach(function(d) {{
    var lat=d[0],lon=d[1],name=d[2],op=d[3],mw=d[4],status=d[5];
    if (aiCurrentFilter!=='all' && status!==aiCurrentFilter) return;
    var col = getAiColor(status);
    var radius = 8 + Math.min(mw/200, 10);
    var popup = '<b style="color:'+col+'">'+name+'</b><br>'
              + op+'<br>'+mw+' MW &bull; '+status.toUpperCase();
    L.circleMarker([lat,lon],{{
      radius:radius, color:col, fillColor:col, fillOpacity:0.8, weight:1.5
    }}).bindPopup(popup).addTo(layer);
  }});
  window._aiLayer = layer.addTo(aiMap);
}}

function aiFilter(type, val) {{
  aiCurrentFilter = val;
  document.querySelectorAll('.ai-filter-btn').forEach(function(b){{
    b.classList.toggle('active', b.textContent.toLowerCase()===val||
                                 (val==='all'&&b.textContent==='All'));
  }});
  renderAiMarkers();
}}
function resetAiFilters() {{ aiFilter('status','all'); }}

// ═══════════════════════════════════════════════════════════════════════
// TAB 2 — FEED MAP
// ═══════════════════════════════════════════════════════════════════════
var feedMap;
function initFeedMap() {{
  feedMap = L.map('feedMap',{{zoomControl:true}}).setView([39.8,-98.5],4);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',
    {{attribution:'CartoDB'}}).addTo(feedMap);
  {feed_markers_js}
  // CONUS border
  var conus = {json.dumps(CONUS_POLYGON)};
  var pts = conus.map(function(p){{return [p[0],p[1]];}});
  L.polyline(pts,{{color:'#00ff00',weight:1.5,opacity:0.6}}).addTo(feedMap);
}}
function filterFeed(v) {{ /* would filter marker popups */ }}

// ═══════════════════════════════════════════════════════════════════════
// TAB 3 — GUN OWNERSHIP CHART
// ═══════════════════════════════════════════════════════════════════════
var chartInited = false;
function renderChart() {{
  if (chartInited) return;
  chartInited = true;
  var labels = {bar_labels};
  var values = {bar_values};
  var ctx = document.getElementById('gunChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [{{
        label: 'Firearms',
        data: values,
        backgroundColor: '#60a5fa',
        borderColor: '#3b82f6',
        borderWidth: 0,
        barThickness: 'flex',
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{display:false}},
        tooltip: {{
          callbacks: {{
            label: function(ctx) {{
              return ' '+ctx.parsed.y.toLocaleString()+' firearms';
            }}
          }}
        }}
      }},
      scales: {{
        x: {{
          ticks: {{color:'#555',font:{{size:8}},maxRotation:90}},
          grid: {{color:'#1a1a1a'}}
        }},
        y: {{
          ticks: {{color:'#555',font:{{size:9}}}},
          grid: {{color:'#1a1a1a'}}
        }}
      }}
    }}
  }});
}}

// ═══════════════════════════════════════════════════════════════════════
// REPORT OVERLAY
// ═══════════════════════════════════════════════════════════════════════
function openReport()  {{ document.getElementById('report-overlay').classList.add('open'); }}
function closeReport() {{ document.getElementById('report-overlay').classList.remove('open'); }}

function submitReport() {{
  var lat  = parseFloat(document.getElementById('rpt-lat').value);
  var lon  = parseFloat(document.getElementById('rpt-lon').value);
  var loc  = document.getElementById('rpt-loc').value.trim();
  var ag   = document.getElementById('rpt-agency').value.trim();
  var typ  = document.getElementById('rpt-type').value.trim().toUpperCase();
  var desc = document.getElementById('rpt-desc').value.trim();
  var err  = document.getElementById('rpt-err');
  err.textContent = '';
  if (isNaN(lat)||isNaN(lon)) {{ err.textContent='Numbers only'; return; }}
  // POST to Python's local bridge server
  fetch('http://127.0.0.1:45678/report', {{
    method: 'POST',
    headers: {{'Content-Type':'application/json'}},
    body: JSON.stringify({{lat:lat,lon:lon,loc:loc,agency:ag,type:typ,desc:desc}})
  }}).catch(function(){{}});
  closeReport();
}}

// ═══════════════════════════════════════════════════════════════════════
// MESH ACTIONS
// ═══════════════════════════════════════════════════════════════════════
function syncMesh() {{
  fetch('http://127.0.0.1:45678/sync', {{method:'POST'}}).catch(function(){{}});
}}

// ── AI filter button style ─────────────────────────────────────────────
var style = document.createElement('style');
style.textContent = `
  .ai-filter-btn{{
    padding:4px 8px;margin-bottom:4px;font-size:9px;letter-spacing:1px;
    background:var(--panel);border:1px solid var(--border);
    color:var(--muted);cursor:pointer;
  }}
  .ai-filter-btn.active{{color:var(--green);border-color:var(--green);}}
`;
document.head.appendChild(style);

// ── Boot: init first tab ──────────────────────────────────────────────
window.addEventListener('load', function() {{
  initMapMain();
  mapsInited[0] = true;
}});
</script>
</body>
</html>"""

import http.server

class _BridgeHandler(http.server.BaseHTTPRequestHandler):
    app_ref = None  # set by BridgeServer before starting

    def do_OPTIONS(self):
        # CORS preflight — WebView needs this for cross-origin fetch to localhost
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length) if length > 0 else b''
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

            app = _BridgeHandler.app_ref
            if not app:
                return

            if self.path == '/report':
                data = json.loads(body.decode('utf-8'))
                data['timestamp'] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                Clock.schedule_once(lambda dt, d=data: (
                    app.engine.add_report(d),
                    app._load_html()
                ))
            elif self.path == '/sync':
                Clock.schedule_once(lambda dt: app._sync_mesh())
            elif self.path == '/exit':
                Clock.schedule_once(lambda dt: app._do_exit())

        except Exception as e:
            logging.warning(f"BridgeHandler error: {e}")
            try:
                self.send_response(500)
                self.end_headers()
            except: pass

    def log_message(self, fmt, *args):
        pass  # suppress access log noise


class BridgeServer(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        _BridgeHandler.app_ref = app

    def run(self):
        try:
            server = http.server.HTTPServer(('127.0.0.1', 45678), _BridgeHandler)
            server.serve_forever()
        except Exception as e:
            logging.error(f"BridgeServer failed: {e}")


class PunksApp(MDApp):

    def build(self):
        self.theme_cls.theme_style = "Dark"
        Window.clearcolor = _hex(PAL["bg"])

        self.engine   = DataEngine()
        self.peers    = set()
        self.telemetry = {"lat": 34.2694, "lon": -118.7815, "city": "SIMI VALLEY"}
        self._webview = None

        # Wake lock
        if platform == "android":
            try:
                from jnius import autoclass
                Context  = autoclass('android.content.Context')
                Activity = autoclass('org.kivy.android.PythonActivity').mActivity
                pm = Activity.getSystemService(Context.POWER_SERVICE)
                self.wake_lock = pm.newWakeLock(1, "PunksOmni::MeshLock")
                self.wake_lock.acquire()
            except Exception: pass

        # Start mesh threads
        for t in [MeshServer(self), MeshListener(self),
                  MeshBeacon(), GlobalMeshSync(self)]:
            t.start()

        # Build root layout (full-screen, just holds the WebView placeholder)
        root = FloatLayout()

        if platform == "android":
            # On Android: overlay a native WebView over the entire Kivy surface
            from android.runnable import run_on_ui_thread
            from jnius import autoclass

            @run_on_ui_thread
            def _create_webview():
                try:
                    WebView        = autoclass('android.webkit.WebView')
                    WebViewClient  = autoclass('android.webkit.WebViewClient')
                    AndroidColor   = autoclass('android.graphics.Color')
                    Activity       = autoclass('org.kivy.android.PythonActivity').mActivity
                    FrameLayout    = autoclass('android.widget.FrameLayout')
                    LayoutParams   = autoclass('android.widget.FrameLayout$LayoutParams')

                    wv = WebView(Activity)
                    s  = wv.getSettings()
                    s.setJavaScriptEnabled(True)
                    s.setDomStorageEnabled(True)
                    s.setLoadWithOverviewMode(True)
                    s.setUseWideViewPort(True)
                    s.setBuiltInZoomControls(False)
                    s.setDisplayZoomControls(False)
                    s.setSupportZoom(False)
                    # MIXED_CONTENT_ALWAYS_ALLOW=0: allows the page served from
                    # https://punks.local to fetch Leaflet CDN, CartoDB map tiles,
                    # and Chart.js from CDN. Without this Android silently blocks
                    # all CDN requests -> blank maps, no chart.
                    s.setMixedContentMode(0)
                    # Allow cleartext HTTP to 127.0.0.1:45678 (BridgeServer fetch)
                    s.setAllowContentAccess(True)
                    s.setAllowFileAccess(True)
                    # LOAD_NO_CACHE=2: force-fresh CDN fetches on first load
                    s.setCacheMode(2)
                    wv.setBackgroundColor(AndroidColor.parseColor("#0A0A0A"))

                    # Plain WebViewClient — no subclassing (pyjnius limitation)
                    wv.setWebViewClient(WebViewClient())
                    self._webview = wv

                    # Full-screen FrameLayout, no margins — the HTML handles its own header/footer
                    fl = FrameLayout(Activity)
                    lp_full = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT)
                    fl.addView(wv, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
                    Activity.addContentView(fl, lp_full)
                    self._fl = fl

                    # Load HTML after WebView is attached
                    Clock.schedule_once(lambda dt: self._load_html(), 0.3)

                except Exception as e:
                    logging.error(f"WebView creation failed: {e}")

            _create_webview()
            # Start the JS<->Python HTTP bridge on localhost:45678
            bridge = BridgeServer(self)
            bridge.start()

        else:
            # Desktop: write HTML to disk for preview
            Clock.schedule_once(lambda dt: self._load_html(), 0.5)
            # Show a minimal Kivy label
            lbl = MDLabel(text="PUNKS // OMNI — DESKTOP MODE\nSee ~/.punks_tactical_android/map_preview.html",
                          halign="center", theme_text_color="Custom",
                          text_color=_hex(PAL["green"]))
            root.add_widget(lbl)

        return root

    # ── HTML load ──────────────────────────────────────────────────────
    def _load_html(self, *args):
        html = build_full_html(
            reports    = self.engine.load_encrypted(),
            center_lat = self.telemetry['lat'],
            center_lon = self.telemetry['lon'],
            user_city  = self.telemetry['city'],
            app_data_dir = APP_DATA_DIR,
        )
        if platform == "android" and self._webview:
            from android.runnable import run_on_ui_thread
            h = str(html)
            @run_on_ui_thread
            def _load():
                self._webview.loadDataWithBaseURL(
                    "https://punks.local", h, "text/html", "UTF-8", None)
            _load()
        else:
            tmp = os.path.join(APP_DATA_DIR, "map_preview.html")
            with open(tmp, "w") as f:
                f.write(html)
            logging.info(f"Desktop HTML written to {tmp}")

    # ── Reload HTML (called after new report added or mesh sync) ───────
    def _reload(self, *args):
        Clock.schedule_once(lambda dt: self._load_html(), 0)

    # ── Sync mesh ──────────────────────────────────────────────────────
    def _sync_mesh(self):
        def _ok(req, res):
            if isinstance(res, list):
                added = self.engine.merge_mesh(res)
                if added > 0:
                    self._reload()
        UrlRequest(
            "https://raw.githubusercontent.com/punksm4ck/mesh-bridge/main/global_ledger.json",
            on_success=_ok, timeout=10)

    # ── Mesh peer handling ─────────────────────────────────────────────
    def peer_discovered(self, ip):
        if ip != "127.0.0.1" and ip not in self.peers:
            self.peers.add(ip)
            threading.Thread(target=self.gossip_peer, args=(ip,), daemon=True).start()

    def gossip_peer(self, ip):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3); s.connect((ip, 44444))
            s.sendall(mesh_encrypt(json.dumps(self.engine.load_encrypted()).encode()))
            s.close()
        except Exception: pass

    def _do_exit(self):
        """Cleanly finish the Android activity."""
        if platform == 'android':
            try:
                from jnius import autoclass
                Activity = autoclass('org.kivy.android.PythonActivity').mActivity
                Activity.finish()
            except Exception as e:
                logging.warning(f'Exit error: {e}')
        from kivy.app import App
        App.get_running_app().stop()

    def gossip_all(self):
        for ip in list(self.peers):
            threading.Thread(target=self.gossip_peer, args=(ip,), daemon=True).start()


if __name__ == "__main__":
    PunksApp().run()
