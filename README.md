# Audio Pro (LinkPlay) voor Home Assistant

Bestuur Audio Pro W-speakers (getest met de **C20 W**) via het vaste IP-adres.
Er wordt geen auto-discovery gebruikt, dus het werkt ook als de speaker in een
ander subnet / VLAN zit dan Home Assistant.

## Functies

- **Media player**: afspelen, pauze, stop, vorige/volgende, volume, dempen
- **Bron kiezen**: Wi-Fi, Bluetooth, TV (HDMI), Optical, Line-in, Phono
- **Equalizer** als *sound mode* (Flat, Bass Booster, Rock, …)
- **Radiozenders**
  - eigen zenderlijst, te bewerken in de opties van de integratie
  - *select*-entiteit "Radiozender" voor dashboards en automatiseringen
  - zenders bladeren en afspelen via **Media** in Home Assistant, inclusief de
    [Radio Browser](https://www.home-assistant.io/integrations/radio_browser/)-integratie
    (als je die hebt toegevoegd) met duizenden zenders
- `media_player.play_media` met een willekeurige stream-URL

Naast de media player krijg je losse entiteiten, handig voor dashboards en automatiseringen:

| Entiteit | Type | Wat |
|---|---|---|
| Volume | number | 0–100 % |
| Dempen | switch | mute aan/uit |
| Audiobron | select | Wi-Fi, Bluetooth, TV (HDMI), Optical, Line-in, Phono |
| Radiozender | select | kies uit je eigen zenderlijst |
| Equalizer-preset | select | Flat, Movie, Rock, … |
| Equalizer | switch | EQ aan/uit |
| Balans | number | −1 (links) tot 1 (rechts) |
| Slaaptimer | number | minuten tot standby, 0 = uit |
| Status-LED | switch | lampje op de speaker aan/uit |
| Wifi-signaal | sensor | RSSI in dBm |
| Herstarten | button | speaker herstarten |
| Preset *n* | button | presets die op de speaker zelf zijn opgeslagen (alleen als die er zijn) |

Vanaf Home Assistant 2026.3 toont de integratie een eigen icoon.

## Installatie via HACS

1. HACS → menu (⋮) → **Custom repositories**
2. Repository: `https://github.com/zaag/audiopro`, type **Integration** → *Add*
3. Zoek **Audio Pro (LinkPlay)** in HACS en installeer
4. Herstart Home Assistant
5. **Instellingen → Apparaten & diensten → Integratie toevoegen → Audio Pro (LinkPlay)**
6. Vul het IP-adres van de speaker in (bijv. `192.168.1.50`)

Home Assistant moet de speaker op **HTTPS-poort 443** kunnen bereiken. De speaker
moet de stream-URL's zelf kunnen ophalen (internet, of Home Assistant als je
lokale media afspeelt).

## Radiozenders aanpassen

**Instellingen → Apparaten & diensten → Audio Pro → Configureren.** Eén zender per regel:

```
NPO Radio 2 | https://icecast.omroep.nl/radio2-bb-mp3
Qmusic | https://stream.qmusic.nl/qmusic/mp3
```

Stream-URL's vind je bijvoorbeeld op [radio-browser.info](https://www.radio-browser.info).

## Voorbeelden

Zender kiezen in een automatisering:

```yaml
action: select.select_option
target:
  entity_id: select.audio_pro_c20_w_radiozender
data:
  option: NPO Radio 2
```

Een willekeurige stream afspelen:

```yaml
action: media_player.play_media
target:
  entity_id: media_player.audio_pro_c20_w
data:
  media_content_type: music
  media_content_id: https://icecast.omroep.nl/3fm-bb-mp3
```

De entity-ID's hangen af van de naam van je speaker.

## Losse web-app

In [`webapp/`](webapp) staat een losse web-app die je zonder Home Assistant op een
computer kunt draaien (`python3 webapp/server.py`, daarna `http://localhost:8020`).
De API van de speaker staat beschreven in [API.md](API.md).
