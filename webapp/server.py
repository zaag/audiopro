#!/usr/bin/env python3
"""Audio Pro C20 W controller: serves the web UI and proxies the LinkPlay HTTP API.

Usage: python3 server.py [--speaker 192.168.1.50] [--port 8020]
"""
import argparse
import json
import ssl
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIONS_FILE = ROOT / "stations.json"
RADIO_BROWSER = "https://de1.api.radio-browser.info"

# The speaker uses a self-signed certificate.
INSECURE = ssl.create_default_context()
INSECURE.check_hostname = False
INSECURE.verify_mode = ssl.CERT_NONE

# python.org builds on macOS ship without CA certs; fall back to the system bundle.
try:
    import certifi
    VERIFIED = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    VERIFIED = ssl.create_default_context()
    if Path("/etc/ssl/cert.pem").exists():
        VERIFIED.load_verify_locations("/etc/ssl/cert.pem")

DEFAULT_STATIONS = [
    {"name": "NPO Radio 1", "url": "https://icecast.omroep.nl/radio1-bb-mp3"},
    {"name": "NPO Radio 2", "url": "https://icecast.omroep.nl/radio2-bb-mp3"},
    {"name": "NPO 3FM", "url": "https://icecast.omroep.nl/3fm-bb-mp3"},
    {"name": "NPO Klassiek", "url": "https://icecast.omroep.nl/radio4-bb-mp3"},
    {"name": "Radio 538", "url": "https://22533.live.streamtheworld.com/RADIO538.mp3"},
    {"name": "Qmusic", "url": "https://stream.qmusic.nl/qmusic/mp3"},
    {"name": "Sky Radio", "url": "https://22533.live.streamtheworld.com/SKYRADIO.mp3"},
    {"name": "Radio 10", "url": "https://22533.live.streamtheworld.com/RADIO10.mp3"},
    {"name": "Veronica", "url": "https://22533.live.streamtheworld.com/VERONICA.mp3"},
    {"name": "BNR Nieuwsradio", "url": "https://stream.bnr.nl/bnr_mp3_128_20"},
]


def load_stations():
    if STATIONS_FILE.exists():
        return json.loads(STATIONS_FILE.read_text())
    return DEFAULT_STATIONS


def save_stations(stations):
    STATIONS_FILE.write_text(json.dumps(stations, indent=2, ensure_ascii=False))


class Handler(SimpleHTTPRequestHandler):
    speaker = "192.168.1.50"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / "web"), **kw)

    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def speaker_cmd(self, command):
        url = f"https://{self.speaker}/httpapi.asp?command={urllib.parse.quote(command, safe=':/,;')}"
        with urllib.request.urlopen(url, context=INSECURE, timeout=6) as r:
            text = r.read().decode("utf-8", "replace")
        try:
            return json.loads(text)
        except ValueError:
            return {"result": text.strip()}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/api/cmd":
                return self.send_json(self.speaker_cmd(q["c"][0]))
            if u.path == "/api/stations":
                return self.send_json(load_stations())
            if u.path == "/api/search":
                params = urllib.parse.urlencode({
                    "name": q.get("q", [""])[0], "limit": 40, "hidebroken": "true",
                    "order": "clickcount", "reverse": "true",
                })
                req = urllib.request.Request(
                    f"{RADIO_BROWSER}/json/stations/search?{params}",
                    headers={"User-Agent": "audiopro-controller/1.0"})
                with urllib.request.urlopen(req, context=VERIFIED, timeout=10) as r:
                    res = json.loads(r.read())
                return self.send_json([{
                    "name": s["name"].strip(), "url": s["url_resolved"] or s["url"],
                    "favicon": s.get("favicon", ""), "country": s.get("countrycode", ""),
                    "bitrate": s.get("bitrate", 0), "codec": s.get("codec", ""),
                } for s in res])
        except Exception as e:  # noqa: BLE001 - report any upstream failure to the UI
            return self.send_json({"error": str(e)}, 502)
        return super().do_GET()

    def do_PUT(self):
        if self.path != "/api/stations":
            return self.send_json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        stations = json.loads(self.rfile.read(length))
        save_stations(stations)
        self.send_json(stations)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speaker", default="192.168.1.50")
    ap.add_argument("--port", type=int, default=8020)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    Handler.speaker = args.speaker
    print(f"Audio Pro controller op http://localhost:{args.port}  (speaker {args.speaker})")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
