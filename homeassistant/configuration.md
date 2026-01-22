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

## Lovelace Dashboard Karte

### Markdown Karte für den formatierten Speiseplan

```yaml
type: markdown
title: 🍽️ Schulessen
content: |
  {{ state_attr('sensor.speiseplan_text', 'text') }}
```

### Entities Karte für das heutige Menü

```yaml
type: entities
title: Heutiges Schulessen
entities:
  - entity: sensor.speiseplan_heute
    name: Tag
  - type: attribute
    entity: sensor.speiseplan_heute
    attribute: gerichte
    name: Gerichte
```

### Custom Template Karte (detailliert)

```yaml
type: markdown
title: 📅 Speiseplan der Woche
content: |
  **Kalenderwoche {{ state_attr('sensor.speiseplan_woche', 'kw') }}**

  {% set menu = state_attr('sensor.speiseplan_woche', 'menu') %}

  {% if menu %}
  🔵 **Montag**
  {% for gericht in menu.montag.gerichte %}
  - {{ gericht }}
  {% endfor %}

  🟢 **Dienstag**
  {% for gericht in menu.dienstag.gerichte %}
  - {{ gericht }}
  {% endfor %}

  🟡 **Mittwoch**
  {% for gericht in menu.mittwoch.gerichte %}
  - {{ gericht }}
  {% endfor %}

  🟠 **Donnerstag**
  {% for gericht in menu.donnerstag.gerichte %}
  - {{ gericht }}
  {% endfor %}

  🔴 **Freitag**
  {% for gericht in menu.freitag.gerichte %}
  - {{ gericht }}
  {% endfor %}
  {% else %}
  Kein Speiseplan verfügbar
  {% endif %}
```

### Heutiges Menü Highlight Karte

```yaml
type: markdown
title: 🍴 Heute gibt es
content: |
  {% set gerichte = state_attr('sensor.speiseplan_heute', 'gerichte') %}
  {% if gerichte %}
  {% for gericht in gerichte %}
  **{{ gericht }}**
  {% endfor %}
  {% else %}
  Kein Menü für heute verfügbar
  {% endif %}
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
            {% if gerichte %}
            {{ gerichte | join(', ') }}
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
