# Speiseplan Service für Home Assistant

Ein Python-Service, der den Schul-Speiseplan von der Wollino-Webseite lädt, aus PDFs extrahiert und als REST API für Home Assistant bereitstellt.

## Features

- 🔍 Automatisches Finden der PDF für die aktuelle Kalenderwoche
- 📄 Extraktion des Menüs aus PDF-Dateien
- 🌐 REST API für einfache Integration
- 🏠 Fertige Home Assistant Konfiguration
- 💾 Caching für bessere Performance
- 📱 Unterstützung für Benachrichtigungen

## Installation

### 1. Repository klonen oder Dateien kopieren

```bash
cd /pfad/zu/deinem/projekt
```

### 2. Python Virtual Environment erstellen (empfohlen)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. Service testen

```bash
python speiseplan_service.py
```

### 5. API Server starten

```bash
python api_server.py
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
    scan_interval: 3600
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

## Docker Deployment (optional)

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

EXPOSE 5123

CMD ["python", "api_server.py"]
```

### Docker Compose

```yaml
version: "3.8"
services:
  speiseplan:
    build: .
    ports:
      - "5123:5123"
    restart: unless-stopped
    volumes:
      - ./cache:/app/cache
```

### Container starten

```bash
docker-compose up -d
```

## Als Systemd Service (Linux)

Erstelle `/etc/systemd/system/speiseplan.service`:

```ini
[Unit]
Description=Speiseplan Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/speiseplan
ExecStart=/home/pi/speiseplan/venv/bin/python api_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Aktivieren und starten:

```bash
sudo systemctl daemon-reload
sudo systemctl enable speiseplan
sudo systemctl start speiseplan
```

## Konfiguration

Die Konfiguration erfolgt direkt in `speiseplan_service.py`:

| Variable      | Beschreibung                 | Standard                                      |
| ------------- | ---------------------------- | --------------------------------------------- |
| `WOLLINO_URL` | URL zur Speiseplan-Übersicht | `https://www.wollino.de/grundschulenc4f8564f` |
| `CACHE_FILE`  | Pfad zur Cache-Datei         | `speiseplan_cache.json`                       |

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
