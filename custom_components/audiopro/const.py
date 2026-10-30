"""Constants for the Audio Pro integration."""

DOMAIN = "audiopro"

CONF_STATIONS = "stations"

SCAN_INTERVAL_SECONDS = 5

# Settings (EQ, balance, LED, sleep timer, wifi signal, presets) are polled every
# SETTINGS_EVERY_N_POLLS * SCAN_INTERVAL_SECONDS seconds.
SETTINGS_EVERY_N_POLLS = 6

# switchmode argument -> label shown in Home Assistant
SOURCES = {
    "wifi": "Wi-Fi",
    "bluetooth": "Bluetooth",
    "HDMI": "TV (HDMI)",
    "optical": "Optical",
    "line-in": "Line-in",
    "phono": "Phono",
}

# getPlayerStatusEx "mode" -> switchmode argument
MODE_TO_SOURCE = {
    "1": "wifi",
    "2": "wifi",
    "10": "wifi",
    "20": "wifi",
    "31": "wifi",
    "32": "wifi",
    "36": "wifi",
    "40": "line-in",
    "41": "bluetooth",
    "42": "phono",
    "43": "optical",
    "47": "line-in",
    "49": "HDMI",
}

# Vendor reported for streams started with setPlayerCmd:play:<url>
VENDOR_URL = "CustomPushUrl"

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


def stations_to_text(stations: list[dict[str, str]]) -> str:
    """Render stations as one 'Name | URL' line each."""
    return "\n".join(f"{s['name']} | {s['url']}" for s in stations)


def text_to_stations(text: str) -> list[dict[str, str]]:
    """Parse 'Name | URL' lines; raise ValueError on a malformed line."""
    stations = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        name, sep, url = line.rpartition("|")
        name, url = name.strip(), url.strip()
        if not sep or not name or not url.startswith(("http://", "https://")):
            raise ValueError(line)
        stations.append({"name": name, "url": url})
    return stations
