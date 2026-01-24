# Home Assistant Konfiguration für den Speiseplan

## REST Sensor Konfiguration

Füge folgende Konfiguration in deine `configuration.yaml` ein:

```yaml
# Speiseplan REST Sensor
rest:
  - resource: http://DEINE_SERVER_IP:5123/api/speiseplan/heute
    scan_interval: 86400 # 1x täglich aktualisieren (24h)
    sensor:
      - name: "Speiseplan Heute"
        value_template: "{{ value_json.day | title }}"
        json_attributes:
          - gerichte
          - desserts
          - kw
          - day
        unique_id: speiseplan_heute

  - resource: http://DEINE_SERVER_IP:5123/api/speiseplan
    scan_interval: 86400 # 1x täglich aktualisieren
    sensor:
      - name: "Speiseplan Woche"
        value_template: "KW {{ value_json.kw }}"
        json_attributes:
          - menu
          - kw
          - year
          - pdf_file
          - updated
        unique_id: speiseplan_woche

  - resource: http://DEINE_SERVER_IP:5123/api/speiseplan/text
    scan_interval: 86400 # 1x täglich aktualisieren
    sensor:
      - name: "Speiseplan Text"
        value_template: "KW {{ value_json.kw }}"
        json_attributes:
          - text
          - kw
        unique_id: speiseplan_text
```

**Ersetze `DEINE_SERVER_IP` mit der IP-Adresse oder dem Hostnamen, auf dem der Speiseplan-Service läuft.**

## Lovelace Dashboard Karten

### Empfohlene Wochenkarte mit Desserts

```yaml
type: markdown
title: 📅 Speiseplan KW {{ state_attr('sensor.speiseplan_woche', 'kw') }}
content: |
  {% set menu = state_attr('sensor.speiseplan_woche', 'menu') %}

  {% if menu %}
  ---
  ### 🔵 Montag
  {% if menu.montag and menu.montag.gerichte %}
  🍽️ **Hauptgericht:**
  {% for gericht in menu.montag.gerichte %}
  - {{ gericht }}
  {% endfor %}
  {% endif %}
  {% if menu.montag and menu.montag.desserts and menu.montag.desserts | length > 0 %}
  🍨 **Vorspeise/Dessert:**
  {% for dessert in menu.montag.desserts %}
  - {{ dessert }}
  {% endfor %}
  {% endif %}

  ---
  ### 🟢 Dienstag
  {% if menu.dienstag and menu.dienstag.gerichte %}
  🍽️ **Hauptgericht:**
  {% for gericht in menu.dienstag.gerichte %}
  - {{ gericht }}
  {% endfor %}
  {% endif %}
  {% if menu.dienstag and menu.dienstag.desserts and menu.dienstag.desserts | length > 0 %}
  🍨 **Vorspeise/Dessert:**
  {% for dessert in menu.dienstag.desserts %}
  - {{ dessert }}
  {% endfor %}
  {% endif %}

  ---
  ### 🟡 Mittwoch
  {% if menu.mittwoch and menu.mittwoch.gerichte %}
  🍽️ **Hauptgericht:**
  {% for gericht in menu.mittwoch.gerichte %}
  - {{ gericht }}
  {% endfor %}
  {% endif %}
  {% if menu.mittwoch and menu.mittwoch.desserts and menu.mittwoch.desserts | length > 0 %}
  🍨 **Vorspeise/Dessert:**
  {% for dessert in menu.mittwoch.desserts %}
  - {{ dessert }}
  {% endfor %}
  {% endif %}

  ---
  ### 🟠 Donnerstag
  {% if menu.donnerstag and menu.donnerstag.gerichte %}
  🍽️ **Hauptgericht:**
  {% for gericht in menu.donnerstag.gerichte %}
  - {{ gericht }}
  {% endfor %}
  {% endif %}
  {% if menu.donnerstag and menu.donnerstag.desserts and menu.donnerstag.desserts | length > 0 %}
  🍨 **Vorspeise/Dessert:**
  {% for dessert in menu.donnerstag.desserts %}
  - {{ dessert }}
  {% endfor %}
  {% endif %}

  ---
  ### 🔴 Freitag
  {% if menu.freitag and menu.freitag.gerichte %}
  🍽️ **Hauptgericht:**
  {% for gericht in menu.freitag.gerichte %}
  - {{ gericht }}
  {% endfor %}
  {% endif %}
  {% if menu.freitag and menu.freitag.desserts and menu.freitag.desserts | length > 0 %}
  🍨 **Vorspeise/Dessert:**
  {% for dessert in menu.freitag.desserts %}
  - {{ dessert }}
  {% endfor %}
  {% endif %}

  ---
  _Zuletzt aktualisiert: {{ state_attr('sensor.speiseplan_woche', 'updated')[:16] | replace('T', ' ') }}_
  {% else %}
  ⚠️ Speiseplan nicht verfügbar
  {% endif %}
```

### Heutiges Menü mit Desserts

```yaml
type: markdown
title: 🍴 Heute gibt es
content: |
  {% set gerichte = state_attr('sensor.speiseplan_heute', 'gerichte') %}
  {% set desserts = state_attr('sensor.speiseplan_heute', 'desserts') %}

  {% if gerichte and gerichte | length > 0 %}
  🍽️ **Hauptgericht:**
  {% for gericht in gerichte %}
  - {{ gericht }}
  {% endfor %}

  {% if desserts and desserts | length > 0 %}
  🍨 **Vorspeise/Dessert:**
  {% for dessert in desserts %}
  - {{ dessert }}
  {% endfor %}
  {% endif %}
  {% else %}
  Kein Menü für heute verfügbar
  {% endif %}
```

### Einfache Text-Karte

```yaml
type: markdown
title: 🍽️ Schulessen
content: |
  {{ state_attr('sensor.speiseplan_text', 'text') }}
```

## Automatisierung: Benachrichtigung am Morgen

```yaml
automation:
  - alias: "Speiseplan Benachrichtigung"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: notify.mobile_app_DEIN_HANDY
        data:
          title: "🍽️ Schulessen heute"
          message: >
            {% set gerichte = state_attr('sensor.speiseplan_heute', 'gerichte') %}
            {% set desserts = state_attr('sensor.speiseplan_heute', 'desserts') %}
            {% if gerichte %}
            Hauptgericht: {{ gerichte | join(', ') }}
            {% if desserts %}
            Dessert: {{ desserts | join(', ') }}
            {% endif %}
            {% else %}
            Kein Menü verfügbar
            {% endif %}
```

## Installation

1. Starte den Speiseplan-Service (siehe README.md)
2. Kopiere die REST-Sensor-Konfiguration in deine `configuration.yaml`
3. Ersetze `DEINE_SERVER_IP` mit der korrekten IP-Adresse
4. Starte Home Assistant neu
5. Füge die Lovelace-Karten zu deinem Dashboard hinzu

## API Endpunkte

| Endpunkt                    | Beschreibung                           |
| --------------------------- | -------------------------------------- |
| `/api/speiseplan`           | Kompletter Wochenspeiseplan            |
| `/api/speiseplan/heute`     | Heutiges Menü mit Gerichten + Desserts |
| `/api/speiseplan/tag/<tag>` | Menü für einen bestimmten Tag          |
| `/api/speiseplan/text`      | Formatierter Text für Markdown         |
| `/api/health`               | Health-Check                           |

## Datenstruktur

Jeder Tag enthält:

- `gerichte`: Array mit Hauptgerichten
- `desserts`: Array mit Vorspeisen/Desserts
