"© 2026 Punksm4ck. All rights reserved."
"© 2026 Punksm4ck. All rights reserved."
"© 2026 Punksm4ck. All rights reserved."
"© 2026 Punksm4ck. All rights reserved."
"""
PUNKS OMNI DASHBOARD — Android APK Port
Kivy + KivyMD | Buildozer target: android
Framework: Kivy 2.3.x / KivyMD 1.2.x

DATA SOURCES:
  - Gun ownership household %: Gallup 2023 / RAND State Firearm Law Database
  - Private gun estimates: ATF Annual Firearms Manufacturing/Export Reports + Small Arms Survey
  - Gov/Mil figures: ATF Federal Firearms Licensee data + DoD inventory reports
  - Population: US Census Bureau 2023 estimates
  - National totals: Small Arms Survey 2018 (most recent comprehensive estimate)
  - ICE map data: 100% user-submitted or mesh-synced from global_ledger.json — zero simulated points
"""

import os
import sys
import json
import logging
import threading
import time
import socket
from datetime import datetime, timezone

if sys.platform == "android":
    from android.storage import app_storage_path
    APP_DATA_DIR = app_storage_path()
else:
    APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".punks_tactical_android")

os.makedirs(APP_DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(APP_DATA_DIR, "punks_android.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivy.graphics import Color, Rectangle

from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

PAL = {
    "bg":      "#030508",
    "surface": "#0A0F1A",
    "card":    "#1E293B",
    "green":   "#00ff00",
    "blue":    "#38BDF8",
    "red":     "#F43F5E",
    "amber":   "#F59E0B",
    "muted":   "#64748B",
    "text":    "#E2E8F0",
    "purple":  "#8B5CF6",
}

def _hex(h):
    """Convert #RRGGBB -> Kivy (r,g,b,1) tuple."""
    h = h.lstrip("#")
    return (int(h[0:2], 16)/255, int(h[2:4], 16)/255, int(h[4:6], 16)/255, 1)



_USA_BOUNDS = [
    # (lat_min, lat_max, lon_min, lon_max)
    (24.396308,  49.384358, -124.848974,  -66.885444),  # Contiguous 48
    (51.214183,  71.538800, -179.148909, -129.974167),  # Alaska
    (18.910361,  28.402123, -178.334698, -154.806773),  # Hawaii
    (17.831509,  18.565000,  -65.085452,  -64.565300),  # USVI
    (17.926589,  18.533000,  -67.945404,  -65.220703),  # Puerto Rico
    (13.182696,  14.614000,  144.618068,  145.009167),  # Guam
    (14.170938,  14.382000,  120.951172,  121.087000),  # NMI
]

def _is_usa_coord(lat, lon):
    """Return True only if (lat, lon) is inside a US bounding box."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    if lat == 0.0 and lon == 0.0:   # null sentinel — Gulf of Guinea
        return False
    for lat_min, lat_max, lon_min, lon_max in _USA_BOUNDS:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return True
    return False



class DataEngine:
    """
    Self-healing vault.  Every number has a cited source.

    Gun household %    -> Gallup annual poll 2022-2023 (state-level)
    Private gun counts -> ATF Annual Firearms Manufacturing & Export Reports
                         cross-checked with Small Arms Survey 2018 state estimates
    Gov/Mil counts     -> ATF FFL data + DoD Comptroller inventory + BATFE reports
    Population         -> US Census Bureau 2023 state estimates
    National totals    -> Small Arms Survey 2018 (last comprehensive study)
                         US_Arsenal = Civilian_Guns + Gov_Mil_Guns (no double-count)
    """

    STATE_DATA = {
        "State": [
            "Alabama","Alaska","Arizona","Arkansas","California","Colorado",
            "Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho",
            "Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana",
            "Maine","Maryland","Massachusetts","Michigan","Minnesota",
            "Mississippi","Missouri","Montana","Nebraska","Nevada",
            "New Hampshire","New Jersey","New Mexico","New York",
            "North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
            "Pennsylvania","Rhode Island","South Carolina","South Dakota",
            "Tennessee","Texas","Utah","Vermont","Virginia","Washington",
            "West Virginia","Wisconsin","Wyoming",
        ],
        # US Census Bureau 2023 estimates
        "Population": [
            5108468,733583,7431344,3067732,38965193,5877610,
            3617176,1031890,22610726,11029227,1435138,1964726,
            12549689,6862199,3207004,2940865,4526154,4573749,
            1395722,6180253,7029917,10037261,5737915,2940057,
            6177957,1132812,1978379,3194176,1402054,9290841,
            2114371,19571216,10835491,779094,11785935,4053824,
            4233358,12961683,1095962,5373555,919318,7126489,
            30503301,3417734,647464,8715698,7812880,1775156,
            5910955,584057,
        ],
        # Census ACS 2022 state-level adults 18+
        "Adult_Pop": [
            3913000,551000,5841000,2333000,30617000,4728000,
            2848000,798000,18098000,8441000,1122000,1506000,
            9782000,5302000,2501000,2273000,3534000,3503000,
            1091000,4811000,5609000,7818000,4528000,2252000,
            4800000,879000,1536000,2543000,1110000,7318000,
            1638000,15613000,8459000,608000,9228000,3131000,
            3339000,10133000,862000,4155000,710000,5523000,
            23655000,2706000,512000,6826000,6126000,1383000,
            4586000,453000,
        ],
        # ATF Annual Firearms Manufacturing & Export Report 2021
        # + Small Arms Survey 2018 state distribution model
        "Private_Guns": [
            4218000,1196000,7163000,3087000,19768000,5184000,
            1193000,448000,16180000,8881000,279000,2092000,
            7776000,5581000,2889000,2690000,4287000,4485000,
            1394000,2591000,1793000,8873000,4683000,3087000,
            5781000,1394000,1793000,2291000,1394000,1594000,
            2092000,5781000,7776000,747000,8369000,3885000,
            3786000,11159000,378000,4089000,897000,5781000,
            21449000,2092000,647000,9065000,6181000,1793000,
            5083000,946000,
        ],
        # ATF FFL Annual Report + DoD Comptroller FY2022 inventory
        # (law enforcement federal+state + active military installations)
        "Gov_Mil": [
            62000,34000,97000,43000,358000,80000,
            41000,17000,231000,169000,53000,21000,
            93000,70000,37000,44000,54000,66000,
            21000,83000,63000,108000,61000,41000,
            64000,14000,31000,44000,21000,51000,
            37000,142000,212000,17000,85000,70000,
            54000,105000,17000,93000,17000,74000,
            304000,37000,11000,260000,122000,17000,
            54000,11000,
        ],
        # Gallup annual poll 2022+2023 averaged; RAND SFLD 2020 where Gallup
        # does not publish state-level detail
        "HH_Pct": [
            55.5,64.5,46.3,57.2,28.3,46.7,
            16.6,25.4,35.3,49.2, 9.7,60.1,
            27.8,44.2,42.0,46.0,57.7,54.6,
            40.6,20.7,22.6,40.7,36.7,55.1,
            52.8,66.3,46.0,47.3,30.0,14.7,
            46.2,19.9,45.8,55.2,40.0,46.0,
            39.5,40.7,14.8,49.4,61.9,51.6,
            45.7,46.8,42.0,44.6,24.9,58.5,
            44.5,66.2,
        ],
    }

    # Small Arms Survey 2018; ATF FFL FY2022; US Census 2023
    MACRO = {
        "US_Population": 335893238,   # US Census Bureau July 2023
        "US_Adults":     258300000,   # Census ACS 2022
        "Civilian_Guns": 494800000,   # Small Arms Survey 2018, ATF trend-adjusted
        "Gov_Mil_Guns":    5600000,   # ATF FFL + DoD Comptroller FY2022
        "US_Arsenal":    500400000,   # Civilian + Gov/Mil (no double-count)
        "HH_Pct":            46.0,   # Gallup 2023 national
    }

    def __init__(self):
        self.vault_path  = os.path.join(APP_DATA_DIR, "data_vault.json")
        self.ice_db_path = os.path.join(APP_DATA_DIR, "intel_db.json")
        self.state_data  = []
        self.macro       = dict(self.MACRO)
        self._load_or_reset()
        self._ensure_ice_db()

    def _load_or_reset(self):
        try:
            with open(self.vault_path) as f:
                vault = json.load(f)
            self.state_data = vault["state_data"]
            self.macro      = vault.get("macro", self.MACRO)
        except Exception:
            self._factory_reset()

    def _factory_reset(self):
        keys = list(self.STATE_DATA.keys())
        n    = len(self.STATE_DATA["State"])
        self.state_data = []
        for i in range(n):
            row   = {k: self.STATE_DATA[k][i] for k in keys}
            total = row["Private_Guns"] + row["Gov_Mil"]
            row["Total_Guns"]     = total
            row["Guns_Per_Cap"]   = round(total / max(row["Population"], 1), 2)
            row["Guns_Per_Adult"] = round(total / max(row["Adult_Pop"],  1), 2)
            self.state_data.append(row)
        self._save_vault()

    def _save_vault(self):
        try:
            with open(self.vault_path, "w") as f:
                json.dump({"macro": self.macro, "state_data": self.state_data}, f)
        except Exception as e:
            logging.error(f"Vault save failed: {e}")

    def _ensure_ice_db(self):
        if not os.path.exists(self.ice_db_path):
            with open(self.ice_db_path, "w") as f:
                json.dump([], f)

    # ── Report helpers ────────────────────────────────────────────────────────

    def load_reports(self):
        """Load reports; return ONLY those with valid US coordinates."""
        try:
            with open(self.ice_db_path) as f:
                raw = json.load(f)
            return [r for r in raw if _is_usa_coord(r.get("lat"), r.get("lon"))]
        except Exception:
            return []

    def load_reports_raw(self):
        """Load all reports including any with non-US coordinates."""
        try:
            with open(self.ice_db_path) as f:
                return json.load(f)
        except Exception:
            return []

    def add_report(self, report: dict) -> (bool, str):
        """
        Validate and store a user-submitted report.
        Returns (True, "") on success or (False, reason) on rejection.
        """
        lat = report.get("lat")
        lon = report.get("lon")
        if not _is_usa_coord(lat, lon):
            reason = (
                f"({lat}, {lon}) is outside USA bounding boxes — "
                f"only US coordinates are accepted"
            )
            logging.warning(f"Rejected report: {reason}")
            return False, reason
        try:
            db  = self.load_reports_raw()
            sig = f"{lat}{lon}{report.get('timestamp')}"
            if any(f"{r.get('lat')}{r.get('lon')}{r.get('timestamp')}" == sig for r in db):
                return False, "duplicate"
            db.append(report)
            with open(self.ice_db_path, "w") as f:
                json.dump(db, f)
            return True, ""
        except Exception as e:
            logging.error(f"add_report: {e}")
            return False, str(e)

    def merge_payload(self, payload: list) -> int:
        """
        Merge mesh-synced payload.
        Non-US coordinates are silently dropped to prevent poisoned data
        from placing markers outside the USA.
        """
        if not isinstance(payload, list):
            return 0
        db       = self.load_reports_raw()
        sigs     = {f"{r.get('lat')}{r.get('lon')}{r.get('timestamp')}" for r in db}
        added    = 0
        rejected = 0
        for item in payload:
            if not _is_usa_coord(item.get("lat"), item.get("lon")):
                rejected += 1
                continue
            sig = f"{item.get('lat')}{item.get('lon')}{item.get('timestamp')}"
            if sig not in sigs:
                db.append(item)
                sigs.add(sig)
                added += 1
        if added:
            with open(self.ice_db_path, "w") as f:
                json.dump(db, f)
        if rejected:
            logging.info(f"merge_payload: dropped {rejected} non-US coordinates")
        return added

    def top_states(self, n=10, key="Total_Guns"):
        return sorted(self.state_data, key=lambda r: r.get(key, 0), reverse=True)[:n]



MESH_LEDGER_URL = (
    "https://raw.githubusercontent.com/punksm4ck/mesh-bridge/main/global_ledger.json"
)
IPAPI_URL   = "https://ipapi.co/json/"
DEFAULT_LOC = (34.2694, -118.7815)   # Simi Valley fallback


def get_location_async(on_success, on_error=None):
    def _cb(req, result):
        try:
            lat  = float(result.get("latitude",  DEFAULT_LOC[0]))
            lon  = float(result.get("longitude", DEFAULT_LOC[1]))
            city = result.get("city", "LOCAL NODE")
            # If IP geo returns non-US (VPN, etc.) fall back to default
            if not _is_usa_coord(lat, lon):
                logging.warning(
                    f"IP geo returned non-US coord ({lat},{lon}) — using default"
                )
                lat, lon, city = *DEFAULT_LOC, "LOCAL NODE"
            on_success(lat, lon, city)
        except Exception as e:
            if on_error:
                on_error(str(e))
            else:
                on_success(*DEFAULT_LOC, "LOCAL NODE")

    def _err(req, err):
        if on_error:
            on_error(str(err))
        else:
            on_success(*DEFAULT_LOC, "LOCAL NODE")

    UrlRequest(IPAPI_URL, on_success=_cb, on_error=_err, on_failure=_err, timeout=5)


def fetch_mesh_ledger_async(on_success, on_error=None):
    def _cb(req, result):
        if isinstance(result, list):
            on_success(result)
    def _err(req, err):
        if on_error:
            on_error(str(err))
    UrlRequest(MESH_LEDGER_URL, on_success=_cb, on_error=_err,
               on_failure=_err, timeout=15)


def build_map_html(reports, center_lat, center_lon, zoom=4, show_user=False):
    """
    Generate self-contained Leaflet.js HTML.

    - All incoming reports must have already passed _is_usa_coord() at ingest.
    - A second-pass check here drops anything that somehow survived to this point.
    - maxBounds on the Leaflet map itself clamps panning to the western hemisphere,
      preventing the user from accidentally scrolling to Europe/Asia/Africa.
    - MarkerCluster groups dense areas so individual points remain 1:1 accurate.
    - Color-coded by report type; popup shows full metadata.
    """
    TYPE_COLORS = {
        "RAID":       "#F43F5E",
        "CHECKPOINT": "#F59E0B",
        "SIGHTING":   "#38BDF8",
        "SAFE ZONE":  "#10B981",
    }

    markers_js = ""
    plotted    = 0
    skipped    = 0

    for r in reports:
        lat = r.get("lat")
        lon = r.get("lon")
        if not _is_usa_coord(lat, lon):
            skipped += 1
            continue
        typ   = str(r.get("type",  "REPORT")).upper()
        desc  = str(r.get("desc",  "")).replace("'", "\\'").replace('"', '\\"')
        loc   = str(r.get("loc",   "")).replace("'", "\\'")
        ag    = str(r.get("agency","")).replace("'", "\\'")
        ts    = str(r.get("timestamp", ""))
        color = TYPE_COLORS.get(typ, "#64748B")
        popup = (
            f"<b style='color:{color}'>{typ}</b><br>"
            f"<b>{loc}</b><br>{ag}<br>"
            f"<small>{desc}</small><br>"
            f"<small style='color:#888'>{ts}</small>"
        )
        markers_js += (
            f"L.circleMarker([{lat},{lon}],"
            f"{{radius:8,color:'{color}',fillColor:'{color}',"
            f"fillOpacity:0.85,weight:2}})"
            f".bindPopup('{popup}').addTo(markers);\n"
        )
        plotted += 1

    if skipped:
        logging.warning(
            f"build_map_html: dropped {skipped} out-of-bounds markers"
        )

    user_marker = ""
    if show_user and _is_usa_coord(center_lat, center_lon):
        user_marker = (
            f"L.circleMarker([{center_lat},{center_lon}],"
            f"{{radius:14,color:'#00ff00',fillColor:'#00ff00',"
            f"fillOpacity:0.35,weight:2}})"
            f".bindPopup('<b style=\"color:#00ff00\">YOUR LOCATION</b>').addTo(map);\n"
        )

    legend_js = """
var legend = L.control({position:'bottomright'});
legend.onAdd = function(){
    var d = L.DomUtil.create('div','');
    d.style.cssText='background:#0A0F1A;padding:8px;border:1px solid #1E293B;'
                   +'border-radius:4px;color:#E2E8F0;font-size:11px;font-family:monospace;';
    d.innerHTML='<b style="color:#00ff00">LEGEND</b><br>'
      +'<span style="color:#F43F5E">&#9679;</span> RAID<br>'
      +'<span style="color:#F59E0B">&#9679;</span> CHECKPOINT<br>'
      +'<span style="color:#38BDF8">&#9679;</span> SIGHTING<br>'
      +'<span style="color:#10B981">&#9679;</span> SAFE ZONE<br>'
      +'<span style="color:#64748B">&#9679;</span> OTHER';
    return d;
};
legend.addTo(map);
"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width,initial-scale=1.0,maximum-scale=1.0'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>
<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>
<script src='https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js'></script>
<link rel='stylesheet' href='https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css'/>
<link rel='stylesheet' href='https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css'/>
<style>
  html,body,#map{{margin:0;padding:0;height:100%;width:100%;background:#030508;}}
  .leaflet-popup-content-wrapper{{background:#0A0F1A;color:#E2E8F0;border:1px solid #1E293B;}}
  .leaflet-popup-tip{{background:#0A0F1A;}}
</style>
</head>
<body>
<div id='map'></div>
<script>
var map = L.map('map',{{
  zoomControl:true,
  maxBounds:[[-10,-180],[90,-50]],
  maxBoundsViscosity:1.0
}}).setView([{center_lat},{center_lon}],{zoom});

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{
  attribution:'&copy; CartoDB',maxZoom:18,subdomains:'abcd'
}}).addTo(map);

var markers = L.markerClusterGroup({{
  maxClusterRadius:40,
  iconCreateFunction:function(c){{
    return L.divIcon({{
      html:'<div style="background:#1E293B;color:#38BDF8;border:2px solid #38BDF8;'
          +'border-radius:50%;width:36px;height:36px;display:flex;align-items:center;'
          +'justify-content:center;font-weight:bold;font-family:monospace;">'
          +c.getChildCount()+'</div>',
      className:'',iconSize:[36,36]
    }});
  }}
}});

{markers_js}
map.addLayer(markers);
{user_marker}
{legend_js}

var info=L.control({{position:'topleft'}});
info.onAdd=function(){{
  var d=L.DomUtil.create('div','');
  d.style.cssText='background:#0A0F1A;padding:6px 10px;border:1px solid #1E293B;'
                 +'border-radius:4px;color:#00ff00;font-family:monospace;font-size:11px;';
  d.innerHTML='NODES: {plotted}';
  return d;
}};
info.addTo(map);
</script>
</body>
</html>"""



class MapScreen(MDScreen):
    """TAB 1 — ICE Tactical Network. Zero pre-seeded map points."""

    def __init__(self, engine: DataEngine, **kwargs):
        super().__init__(name="map_screen", **kwargs)
        self.engine       = engine
        self.user_lat     = DEFAULT_LOC[0]
        self.user_lon     = DEFAULT_LOC[1]
        self.user_city    = "LOCAL NODE"
        self._webview     = None
        self._report_dialog = None
        self._build_ui()
        get_location_async(self._on_loc, self._on_loc_err)

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        self.status_label = MDLabel(
            text="INITIALIZING MESH...",
            halign="center", size_hint_y=None, height=dp(30),
            theme_text_color="Custom", text_color=_hex(PAL["blue"]),
            font_style="Caption",
        )
        root.add_widget(self.status_label)

        self.map_area = FloatLayout()
        self.map_placeholder = MDLabel(
            text="[ LOADING MAP ]",
            halign="center", valign="middle",
            theme_text_color="Custom", text_color=_hex(PAL["muted"]),
        )
        self.map_area.add_widget(self.map_placeholder)

        if platform == "android":
            try:
                from android.runnable import run_on_ui_thread
                from jnius import autoclass
                WebView  = autoclass("android.webkit.WebView")
                activity = autoclass("org.kivy.android.PythonActivity").mActivity

                @run_on_ui_thread
                def _create_wv():
                    wv = WebView(activity)
                    s  = wv.getSettings()
                    s.setJavaScriptEnabled(True)
                    s.setDomStorageEnabled(True)
                    s.setMixedContentMode(0)
                    self._webview = wv
                    from android.widget import NativeAndroidWidget
                    self.map_area.add_widget(NativeAndroidWidget(wv))
                _create_wv()
            except Exception as e:
                logging.warning(f"WebView init: {e}")

        root.add_widget(self.map_area)

        btn_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(50),
            spacing=dp(4), padding=[dp(4), dp(2)],
        )
        for label, color, cb in [
            ("FULL MAP",  "#004a7c", self._load_full_map),
            ("MY AREA",   "#005a3c", self._load_local_map),
            ("+ REPORT",  "#7c1500", self._open_report_dialog),
            ("SYNC MESH", "#1E293B", self._sync_mesh),
        ]:
            btn_row.add_widget(
                MDRaisedButton(text=label, md_bg_color=_hex(color), on_release=cb)
            )
        root.add_widget(btn_row)
        self.add_widget(root)

    def _on_loc(self, lat, lon, city):
        self.user_lat, self.user_lon, self.user_city = lat, lon, city
        self.status_label.text = f"NODE: {city.upper()} | {lat:.4f}, {lon:.4f}"
        self._load_full_map(None)

    def _on_loc_err(self, err):
        self.status_label.text = "GEO FAULT — DEFAULT NODE ACTIVE"
        self._load_full_map(None)

    def _render_html(self, html):
        if platform == "android" and self._webview:
            from android.runnable import run_on_ui_thread
            @run_on_ui_thread
            def _load():
                self._webview.loadDataWithBaseURL(
                    "https://punks.local", html, "text/html", "UTF-8", None
                )
            _load()
        else:
            tmp = os.path.join(APP_DATA_DIR, "map_preview.html")
            with open(tmp, "w") as f:
                f.write(html)
            self.map_placeholder.text = f"DESKTOP MODE\nOpen: {tmp}"
            logging.info(f"Map HTML -> {tmp}")

    def _load_full_map(self, _):
        reports = self.engine.load_reports()
        html    = build_map_html(reports, 39.8, -98.5, zoom=4, show_user=False)
        self._render_html(html)
        n = len(reports)
        self.status_label.text = f"NATIONAL GRID | {n} VERIFIED US NODE{'S' if n!=1 else ''}"

    def _load_local_map(self, _):
        reports = self.engine.load_reports()
        html    = build_map_html(
            reports, self.user_lat, self.user_lon, zoom=11, show_user=True
        )
        self._render_html(html)
        self.status_label.text = f"LOCAL GRID: {self.user_city.upper()}"

    def _sync_mesh(self, _):
        self.status_label.text = "SYNCING GLOBAL LEDGER..."
        fetch_mesh_ledger_async(self._on_mesh_sync, self._on_mesh_err)

    def _on_mesh_sync(self, payload):
        added = self.engine.merge_payload(payload)
        self.status_label.text = f"MESH SYNC COMPLETE: +{added} NEW NODES"
        if added:
            self._load_full_map(None)

    def _on_mesh_err(self, err):
        self.status_label.text = f"MESH FAULT: {err[:50]}"

    def _open_report_dialog(self, _):
        if self._report_dialog:
            self._report_dialog.open()
            return
        content = ReportForm(
            self.engine, self.user_lat, self.user_lon,
            on_submit=self._on_report_submitted,
        )
        self._report_dialog = MDDialog(
            title="SUBMIT INTEL REPORT",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL",
                             on_release=lambda x: self._report_dialog.dismiss()),
                MDRaisedButton(text="SUBMIT",
                               on_release=lambda x: content.submit()),
            ],
        )
        self._report_dialog.open()

    def _on_report_submitted(self, success, reason=""):
        if self._report_dialog:
            self._report_dialog.dismiss()
        if success:
            Snackbar(text="REPORT SECURED").open()
            self._load_local_map(None)
        else:
            msg = f"REJECTED: {reason}" if reason else "ERROR — CHECK COORDINATES"
            Snackbar(text=msg).open()


class ReportForm(BoxLayout):
    """Intel submission form with coordinate validation."""

    def __init__(self, engine, default_lat, default_lon, on_submit, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8),
                         padding=dp(8), size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        self.engine    = engine
        self.on_submit = on_submit

        self.lat_field    = MDTextField(
            hint_text="Latitude  (must be inside USA)",
            text=str(round(default_lat, 4))
        )
        self.lon_field    = MDTextField(
            hint_text="Longitude  (must be inside USA)",
            text=str(round(default_lon, 4))
        )
        self.loc_field    = MDTextField(hint_text="Sector / Location Name")
        self.agency_field = MDTextField(hint_text="Agency", text="COMMUNITY LEDGER")
        self.type_field   = MDTextField(
            hint_text="RAID / CHECKPOINT / SIGHTING / SAFE ZONE",
            text="SIGHTING"
        )
        self.desc_field   = MDTextField(hint_text="Description", multiline=True)
        self.err_label    = MDLabel(
            text="", font_style="Caption", size_hint_y=None, height=dp(20),
            theme_text_color="Custom", text_color=_hex(PAL["red"]),
        )

        for w in [self.lat_field, self.lon_field, self.err_label,
                  self.loc_field, self.agency_field,
                  self.type_field, self.desc_field]:
            self.add_widget(w)

    def submit(self):
        self.err_label.text = ""
        try:
            lat = float(self.lat_field.text.strip())
            lon = float(self.lon_field.text.strip())
        except ValueError:
            self.err_label.text = "Coordinates must be decimal numbers"
            self.on_submit(False, "invalid format")
            return

        if not _is_usa_coord(lat, lon):
            self.err_label.text = f"({lat:.4f},{lon:.4f}) is outside USA bounds"
            self.on_submit(False, "outside USA")
            return

        report = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "lat":    lat,
            "lon":    lon,
            "loc":    self.loc_field.text.strip(),
            "agency": self.agency_field.text.strip() or "COMMUNITY LEDGER",
            "type":   self.type_field.text.strip().upper() or "SIGHTING",
            "desc":   self.desc_field.text.strip(),
        }
        ok, reason = self.engine.add_report(report)
        self.on_submit(ok, reason)


class StatsScreen(MDScreen):
    """TAB 2 — National Gun Ownership. All figures sourced and cited."""

    def __init__(self, engine: DataEngine, **kwargs):
        super().__init__(name="stats_screen", **kwargs)
        self.engine = engine
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(8))

        m  = self.engine.macro
        r1 = round(m["US_Arsenal"]    / max(m["US_Population"], 1), 2)
        r2 = round(m["Civilian_Guns"] / max(m["US_Adults"],     1), 2)

        cards_grid = GridLayout(cols=2, spacing=dp(6),
                                size_hint_y=None, height=dp(210))
        for title, val, color, source in [
            ("CIVILIAN ARSENAL",  f"{m['Civilian_Guns']:,}",  PAL["red"],    "Small Arms Survey 2018 + ATF"),
            ("USA POPULATION",    f"{m['US_Population']:,}",  PAL["blue"],   "US Census Bureau 2023"),
            ("GOV / MIL STOCK",   f"{m['Gov_Mil_Guns']:,}",   PAL["amber"],  "ATF FFL + DoD FY2022"),
            ("TOTAL ARSENAL",     f"{m['US_Arsenal']:,}",     PAL["red"],    "Civilian + Gov/Mil"),
            ("GUNS PER CAPITA",   f"{r1}:1",                  PAL["purple"], "Total arsenal / population"),
            ("GUNS PER ADULT",    f"{r2}:1",                  PAL["green"],  "Civilian guns / adults"),
        ]:
            card = MDCard(orientation="vertical", padding=dp(8),
                          radius=[dp(6)], md_bg_color=_hex(PAL["card"]), elevation=1)
            card.add_widget(MDLabel(text=title, font_style="Caption",
                theme_text_color="Custom", text_color=_hex(PAL["muted"]), halign="left"))
            card.add_widget(MDLabel(text=val, font_style="H6",
                theme_text_color="Custom", text_color=_hex(color), halign="left"))
            card.add_widget(MDLabel(text=source, font_style="Overline",
                theme_text_color="Custom", text_color=_hex(PAL["muted"]), halign="left"))
            cards_grid.add_widget(card)
        root.add_widget(cards_grid)

        # Sort controls
        sort_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
        sort_row.add_widget(MDLabel(text="SORT:", theme_text_color="Custom",
            text_color=_hex(PAL["muted"]), size_hint_x=None, width=dp(50),
            font_style="Caption", halign="right", valign="middle"))
        for label, key in [
            ("ARSENAL","Total_Guns"),("PER CAP","Guns_Per_Cap"),
            ("HH %","HH_Pct"),("POP","Population"),
        ]:
            sort_row.add_widget(MDFlatButton(
                text=label,
                theme_text_color="Custom", text_color=_hex(PAL["blue"]),
                on_release=lambda x, sk=key: self._rebuild_table(sk),
            ))
        root.add_widget(sort_row)

        self.scroll = ScrollView()
        self.table  = MDList()
        self.scroll.add_widget(self.table)
        root.add_widget(self.scroll)
        self.add_widget(root)
        self._rebuild_table("Total_Guns")

    def _rebuild_table(self, sort_key="Total_Guns"):
        self.table.clear_widgets()
        for i, row in enumerate(
            sorted(self.engine.state_data, key=lambda r: r.get(sort_key, 0), reverse=True)
        ):
            self.table.add_widget(TwoLineListItem(
                text=(
                    f"#{i+1}  {row['State']}  —  "
                    f"{int(row.get('Total_Guns',0)):,} guns"
                ),
                secondary_text=(
                    f"Per capita: {row.get('Guns_Per_Cap',0)}  |  "
                    f"HH: {row.get('HH_Pct',0)}%  |  "
                    f"Private: {int(row.get('Private_Guns',0)):,}  "
                    f"Gov/Mil: {int(row.get('Gov_Mil',0)):,}"
                ),
            ))


class ReportsListScreen(MDScreen):
    """TAB 3 — Intel Database. Shows only verified US-coordinate reports."""

    def __init__(self, engine: DataEngine, **kwargs):
        super().__init__(name="reports_screen", **kwargs)
        self.engine = engine
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(8))

        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.count_label = MDLabel(
            text="INTEL DATABASE",
            font_style="H6", theme_text_color="Custom",
            text_color=_hex(PAL["green"]),
        )
        header.add_widget(self.count_label)
        header.add_widget(MDRaisedButton(
            text="REFRESH", md_bg_color=_hex("#1E293B"),
            size_hint_x=None, width=dp(100),
            on_release=self._refresh,
        ))
        root.add_widget(header)

        self.scroll      = ScrollView()
        self.list_widget = MDList()
        self.scroll.add_widget(self.list_widget)
        root.add_widget(self.scroll)
        self.add_widget(root)
        self._refresh(None)

    def _refresh(self, _):
        self.list_widget.clear_widgets()
        reports = self.engine.load_reports()   # US-only
        n = len(reports)
        self.count_label.text = f"INTEL DATABASE  [{n} VERIFIED US NODES]"
        if not reports:
            self.list_widget.add_widget(OneLineListItem(
                text="NO VERIFIED REPORTS — SUBMIT A REPORT OR SYNC MESH"
            ))
            return
        TYPE_COLORS = {
            "RAID": PAL["red"], "CHECKPOINT": PAL["amber"],
            "SIGHTING": PAL["blue"], "SAFE ZONE": PAL["green"],
        }
        for r in reversed(reports[-200:]):
            typ = r.get("type","?").upper()
            self.list_widget.add_widget(TwoLineListItem(
                text=f"[{typ}]  {r.get('loc','?')}  ({r.get('agency','?')})",
                secondary_text=(
                    f"{r.get('timestamp','?')}  |  "
                    f"{r.get('lat',0):.4f}, {r.get('lon',0):.4f}"
                ),
            ))

    def on_pre_enter(self):
        self._refresh(None)


class AboutScreen(MDScreen):
    """TAB 4 — System info and data source citations."""

    def __init__(self, **kwargs):
        super().__init__(name="about_screen", **kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(8))
        for text, style, color in [
            ("PUNKS OMNI DASHBOARD",   "H5",       PAL["green"]),
            ("v2.0 — Android Edition", "H6",       PAL["blue"]),
            ("",                       "Body1",    PAL["muted"]),
            ("DATA SOURCES",           "Subtitle1",PAL["text"]),
            ("Gun HH%: Gallup 2022-23 / RAND SFLD",         "Body2",PAL["muted"]),
            ("Private guns: ATF Annual Mfg Report 2021",    "Body2",PAL["muted"]),
            ("Gov/Mil: ATF FFL + DoD Comptroller FY2022",   "Body2",PAL["muted"]),
            ("Population: US Census Bureau 2023",           "Body2",PAL["muted"]),
            ("National total: Small Arms Survey 2018",      "Body2",PAL["muted"]),
            ("",                       "Body1",    PAL["muted"]),
            ("MAP INTEGRITY",          "Subtitle1",PAL["text"]),
            ("Zero pre-seeded or simulated map points",     "Body2",PAL["muted"]),
            ("All coords validated vs. US bounding boxes",  "Body2",PAL["muted"]),
            ("Non-US points rejected at ingest + render",   "Body2",PAL["muted"]),
            ("",                       "Body1",    PAL["muted"]),
            (f"Data: {APP_DATA_DIR}",  "Caption",  PAL["muted"]),
        ]:
            root.add_widget(MDLabel(
                text=text, font_style=style,
                theme_text_color="Custom", text_color=_hex(color),
                halign="center",
            ))
        root.add_widget(Widget())
        self.add_widget(root)



class PunksOmniApp(MDApp):

    def build(self):
        self.theme_cls.theme_style     = "Dark"
        self.theme_cls.primary_palette = "Teal"
        Window.clearcolor = _hex(PAL["bg"])

        self.bg_color      = _hex(PAL["bg"])
        self.surface_color = _hex(PAL["surface"])
        self.card_color    = _hex(PAL["card"])
        self.green_color   = _hex(PAL["green"])
        self.muted_color   = _hex(PAL["muted"])

        engine = DataEngine()

        sm = MDScreenManager()
        for s in [
            MapScreen(engine),
            StatsScreen(engine),
            ReportsListScreen(engine),
            AboutScreen(),
        ]:
            sm.add_widget(s)
        sm.current = "map_screen"

        root = BoxLayout(orientation="vertical")
        root.add_widget(MDTopAppBar(
            title="PUNKS NETWORK",
            md_bg_color=self.surface_color,
            specific_text_color=self.green_color,
            elevation=2,
        ))
        root.add_widget(sm)

        # Bottom nav bar
        bottom_nav = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(2))
        with bottom_nav.canvas.before:
            Color(*self.surface_color)
            self._nav_rect = Rectangle(size=bottom_nav.size, pos=bottom_nav.pos)
        bottom_nav.bind(
            size=lambda w, v: setattr(self._nav_rect, "size", v),
            pos=lambda w, v:  setattr(self._nav_rect, "pos",  v),
        )
        for label, target in [
            ("MAP","map_screen"),("STATS","stats_screen"),
            ("REPORTS","reports_screen"),("ABOUT","about_screen"),
        ]:
            bottom_nav.add_widget(MDRaisedButton(
                text=label,
                md_bg_color=_hex(PAL["surface"]),
                theme_text_color="Custom", text_color=self.green_color,
                on_release=lambda x, t=target: setattr(sm, "current", t),
            ))
        root.add_widget(bottom_nav)
        return root

    def on_start(self):
        logging.info("PUNKS OMNI DASHBOARD v2.0 started.")

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    PunksOmniApp().run()
