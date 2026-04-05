# Speiseplan Service für Home Assistant

Ein Python-Service, der den Schul-Speiseplan von der Wollino-Website automatisch herunterlädt, aus PDFs extrahiert und als REST API für Home Assistant bereitstellt.

## Features

- 📥 **Automatischer PDF-Download** von der Wollino-Website
- 📄 Extraktion des Menüs aus PDF-Dateien
- 🌐 REST API für einfache Integration
- 🏠 Fertige Home Assistant Konfiguration
- 💾 24-Stunden Caching für bessere Performance
- 🐳 Docker-Image über GitHub Packages verfügbar
- 📱 Unterstützung für Benachrichtigungen

## Installation

### 1. Repository klonen oder Dateien kopieren

```bash
cd /pfad/zu/deinem/projekt
```

### 2. uv installieren

```bash
pip install uv
```

### 3. Abhängigkeiten synchronisieren

```bash
uv sync --locked
```

Dadurch wird automatisch eine lokale virtuelle Umgebung in `.venv/` mit den in `pyproject.toml` und `uv.lock` definierten Abhängigkeiten erstellt.

### 4. Umgebung aktivieren (optional)

```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 5. PDF-Dateien ablegen

Lade die Speiseplan-PDFs von https://www.wollino.de/newpage herunter und lege sie in den Ordner `pdf_speiseplaene/`.

### 6. Service testen

```bash
uv run python speiseplan_service.py
```

### 7. API Server starten

```bash
uv run python api_server.py
```

Der Server läuft standardmäßig auf Port 5123: http://localhost:5123

## API Endpoints

| Endpoint                         | Beschreibung                   |
| -------------------------------- | ------------------------------ |
| `GET /api/speiseplan`            | Kompletter Wochenspeiseplan    |
| `GET /api/speiseplan?kw=4`       | Speiseplan für KW 4            |
| `GET /api/speiseplan/heute`      | Heutiges Menü                  |
| `GET /api/speiseplan/text`       | Formatierter Text für Markdown |
| `GET /api/speiseplan/tag/montag` | Menü für einen bestimmten Tag  |
| `GET /api/health`                | Health Check                   |

## Home Assistant Integration

Siehe [homeassistant/configuration.md](homeassistant/configuration.md) für die vollständige Konfiguration.

### Schnellstart

1. Füge in deiner `configuration.yaml` hinzu:

```yaml
rest:
  - resource: http://DEINE_SERVER_IP:5123/api/speiseplan/heute
    scan_interval: 86400 # 1x täglich aktualisieren
    sensor:
      - name: "Speiseplan Heute"
        value_template: "{{ value_json.day | title }}"
        json_attributes:
          - gerichte
          - kw
        unique_id: speiseplan_heute
```

2. Erstelle eine Markdown-Karte im Dashboard:

```yaml
type: markdown
title: 🍽️ Schulessen heute
content: |
  {% set gerichte = state_attr('sensor.speiseplan_heute', 'gerichte') %}
  {% for gericht in gerichte %}
  - {{ gericht }}
  {% endfor %}
```

## Docker Deployment

### Mit GitHub Packages (empfohlen)

Das Docker-Image wird automatisch bei jedem Push auf `main` gebaut und in GitHub Packages veröffentlicht.

```bash
# Image pullen (ersetze USERNAME mit dem GitHub-Nutzernamen)
docker pull ghcr.io/USERNAME/speiseplan:latest

# Mit Docker Compose starten
docker-compose up -d
```

### Lokales Build

```bash
# Image lokal bauen
docker build -t speiseplan .

# Container starten
docker run -d -p 5123:5123 --name speiseplan speiseplan
```

### Docker Compose

Die `docker-compose.yml` ist bereits konfiguriert:

```yaml
version: "3.8"
services:
  speiseplan:
    image: ghcr.io/USERNAME/speiseplan:latest
    ports:
      - "5123:5123"
    restart: unless-stopped
    volumes:
      - speiseplan_cache:/app/cache
      - speiseplan_pdfs:/app/pdf_speiseplaene
    environment:
      - TZ=Europe/Berlin
```

Für lokales Build ändere `image:` zu `build: .`

## Konfiguration

Die Konfiguration erfolgt direkt in `speiseplan_service.py`:

| Variable     | Beschreibung         | Standard                |
| ------------ | -------------------- | ----------------------- |
| `CACHE_FILE` | Pfad zur Cache-Datei | `speiseplan_cache.json` |

## Fehlerbehebung

### PDF wird nicht gefunden

- Überprüfe, ob die Wollino-Webseite erreichbar ist
- Prüfe die Logs auf Fehlermeldungen
- Die PDF-Benennung muss dem Muster `KW_XX_Speiseplan` folgen

### Menü wird nicht korrekt extrahiert

Das PDF-Format kann variieren. Prüfe die extrahierten Texte in den Logs und passe ggf. die `parse_menu_text()` Funktion an.

### API nicht erreichbar

- Prüfe ob der Service läuft: `curl http://localhost:5123/api/health`
- Prüfe Firewall-Einstellungen
- Prüfe ob der Port 5123 frei ist

## Lizenz

MIT

## Autor

Erstellt für die Integration des Schul-Speiseplans in Home Assistant.
