# Audio Pro C20 W — API-documentatie

De C20 W draait LinkPlay-firmware (`Linkplay.5.2.818333`, project `AudioPro_C20_W`).
Die heeft een HTTP-API die je **direct op het IP-adres** aanspreekt, dus zonder
auto-discovery (UPnP/mDNS). Daardoor werkt hij ook vanuit een ander subnet.

Er zijn twee lagen:

1. **Speaker-API** — rechtstreeks op de speaker (`https://192.168.1.50`).
2. **Controller-API** — de kleine server in [webapp/server.py](webapp/server.py) die de web-UI host
   en de speaker-API doorgeeft (`http://<host>:8020`).

---

## 1. Speaker-API (LinkPlay)

```
GET https://192.168.1.50/httpapi.asp?command=<commando>
```

- Alleen **HTTPS** (poort 443) antwoordt; HTTP geeft niets terug.
- Het certificaat is self-signed → gebruik `curl -k` of zet certificaatcontrole uit.
- Geen authenticatie.
- Antwoord is JSON, of platte tekst (`OK`, `Failed`, `unknown command`).

```bash
curl -k "https://192.168.1.50/httpapi.asp?command=getPlayerStatusEx"
```

### Status en apparaatinfo

| Commando | Wat het doet |
|---|---|
| `getStatusEx` | Apparaatinfo: naam, firmware, IP, MAC, wifi-signaal (`RSSI`), `uuid`, enz. |
| `getPlayerStatusEx` | Afspeelstatus (zie hieronder). |
| `getMetaInfo` | Metadata van de huidige track: `title`, `artist`, `album`, `albumArtURI`, `sampleRate`, `bitDepth`. Lege velden zijn `unknow`/`un_known`. |

**`getPlayerStatusEx`-velden**

| Veld | Betekenis |
|---|---|
| `status` | `play`, `pause`, `stop`, `load` |
| `mode` | Actieve bron (zie modus-tabel) |
| `vol` | Volume 0–100 |
| `mute` | `0` / `1` |
| `Title`, `Artist`, `Album` | **Hex-gecodeerde** UTF-8 (`556E6B6E6F776E` = `Unknown`) |
| `curpos`, `totlen` | Positie / lengte in ms |
| `loop` | Herhaal/shuffle-modus |
| `eq` | Index van actieve EQ-preset |

**Modi (`mode`)**

| Waarde | Bron |
|---|---|
| 0 | Inactief |
| 1 | AirPlay |
| 2 | DLNA |
| 10 | Wi-Fi / netwerk — ook radio via `play:<url>`; dan is `vendor` = `CustomPushUrl` en `Title` de (hex-gecodeerde) URL |
| 20 | Stream via HTTP-API (op deze firmware niet gezien) |
| 31 | Spotify Connect |
| 32 | TIDAL Connect |
| 40 | Line-in |
| 41 | Bluetooth |
| 43 | Optisch |
| 49 | HDMI ARC |
| 99 | Multiroom-slave |

### Afspelen

| Commando | Wat het doet |
|---|---|
| `setPlayerCmd:play:<url>` | Speel een stream-URL af (mp3/aac/http/https). **Hiermee kies je radiozenders.** |
| `setPlayerCmd:m3u:play:<url>` | Speel een `.m3u`/`.pls`-playlist-URL af |
| `setPlayerCmd:pause` | Pauze |
| `setPlayerCmd:resume` | Hervatten |
| `setPlayerCmd:onepause` | Wissel play/pauze |
| `setPlayerCmd:stop` | Stop |
| `setPlayerCmd:prev` / `next` | Vorige / volgende track |
| `setPlayerCmd:seek:<sec>` | Spoel naar positie |
| `setPlayerCmd:loopmode:<n>` | Herhaal/shuffle-modus |

Voorbeeld — NPO Radio 2 afspelen:

```bash
curl -k "https://192.168.1.50/httpapi.asp?command=setPlayerCmd:play:https://icecast.omroep.nl/radio2-bb-mp3"
```

> Let op: zit er een `&` of `?` in de stream-URL, dan URL-encode je die
> (`%26`, `%3F`), anders breekt de speaker het commando af.

### Volume

| Commando | Wat het doet |
|---|---|
| `setPlayerCmd:vol:<0-100>` | Volume instellen |
| `setPlayerCmd:vol%2b%2b` / `vol--` | Volume een stap omhoog / omlaag |
| `setPlayerCmd:mute:1` / `mute:0` | Dempen aan / uit |

### Bron wisselen

```
setPlayerCmd:switchmode:<bron>
```

| `<bron>` | Ingang |
|---|---|
| `wifi` | Netwerk |
| `bluetooth` | Bluetooth |
| `HDMI` | HDMI ARC (tv) |
| `optical` | Optisch |
| `line-in` | Line-in (RCA) |
| `phono` | Phono (niet geverifieerd op deze firmware) |

### Equalizer

| Commando | Wat het doet |
|---|---|
| `EQGetList` | Lijst met presetnamen (`Flat`, `Bass Booster`, `Rock`, …) |
| `EQLoad:<naam>` | Laad een preset, bijv. `EQLoad:Bass Booster` (spatie als `%20`) |
| `EQOn` / `EQOff` | EQ aan / uit |

### Presets

| Commando | Wat het doet |
|---|---|
| `getPresetInfo` | Lijst met opgeslagen presets (nu leeg: `preset_num: 0`) |
| `MCUKeyShortClick:<1-6>` | Speel preset 1–6 af (de speaker heeft er 6, `preset_key: 6`) |

### Overig

| Commando | Wat het doet |
|---|---|
| `setDeviceName:<naam>` | Apparaatnaam wijzigen |
| `setShutdown:<sec>` | Slaaptimer (`-1` = uit); `getShutdown` leest hem uit |
| `reboot` | Herstarten |

---

## 2. Controller-API (`server.py`)

```bash
python3 webapp/server.py                      # standaard: speaker 192.168.1.50, poort 8020
python3 webapp/server.py --speaker 1.2.3.4 --port 9000
```

De server luistert op `0.0.0.0`, dus je opent de app ook op je telefoon via
`http://<ip-van-deze-mac>:8020`. Geen externe Python-packages nodig.

| Methode + pad | Wat het doet |
|---|---|
| `GET /` | De web-app ([webapp/web/index.html](webapp/web/index.html)) |
| `GET /api/cmd?c=<commando>` | Stuurt `<commando>` door naar de speaker-API en geeft het antwoord als JSON terug. Platte-tekstantwoorden komen terug als `{"result": "OK"}`. |
| `GET /api/stations` | Je eigen zenderlijst: `[{"name", "url", "favicon"}]`. Zonder `stations.json` krijg je een standaardlijst met Nederlandse zenders. |
| `PUT /api/stations` | Vervangt de zenderlijst (JSON-array in de body); wordt opgeslagen in `stations.json`. |
| `GET /api/search?q=<tekst>` | Zoekt zenders in [radio-browser.info](https://www.radio-browser.info), gesorteerd op populariteit (max. 40). Geeft `[{"name", "url", "favicon", "country", "bitrate", "codec"}]`. |

Fouten (speaker onbereikbaar, zoekdienst down) komen terug als HTTP 502 met
`{"error": "..."}`.

Voorbeelden:

```bash
curl "localhost:8020/api/cmd?c=setPlayerCmd:vol:20"
curl "localhost:8020/api/search?q=jazz"
```

---

## Home Assistant

Wil je dit ook vanuit Home Assistant doen (bijv. een radiozender in een
automatisering), dan kan dat met een `rest_command` die de speaker direct aanroept:

```yaml
rest_command:
  c20w_play_url:
    url: "https://192.168.1.50/httpapi.asp?command=setPlayerCmd:play:{{ url }}"
    verify_ssl: false
```

Aanroepen met service `rest_command.c20w_play_url` en data `url: https://icecast.omroep.nl/radio2-bb-mp3`.
