"""
Flask REST API für den Speiseplan Service.
Stellt Endpoints für Home Assistant zur Verfügung.
"""

from flask import Flask, jsonify, request
from speiseplan_service import (
    get_speiseplan,
    get_today_menu,
    format_menu_for_display,
    get_current_week_number,
)

app = Flask(__name__)


@app.route("/api/speiseplan", methods=["GET"])
def api_speiseplan():
    """
    Gibt den kompletten Speiseplan für eine Woche zurück.

    Query Parameter:
        kw: Kalenderwoche (optional, Standard: aktuelle Woche)

    Returns:
        JSON mit dem kompletten Wochenspeiseplan
    """
    kw = request.args.get("kw", type=int)
    speiseplan = get_speiseplan(kw)
    return jsonify(speiseplan)


@app.route("/api/speiseplan/heute", methods=["GET"])
def api_heute():
    """
    Gibt das Menü für den heutigen Tag zurück.

    Returns:
        JSON mit dem Tagesmenü
    """
    return jsonify(get_today_menu())


@app.route("/api/speiseplan/text", methods=["GET"])
def api_text():
    """
    Gibt den formatierten Speiseplan als Text zurück.
    Ideal für Markdown-Karten in Home Assistant.

    Query Parameter:
        kw: Kalenderwoche (optional, Standard: aktuelle Woche)

    Returns:
        Formatierter Text
    """
    kw = request.args.get("kw", type=int)
    speiseplan = get_speiseplan(kw)
    text = format_menu_for_display(speiseplan)
    return jsonify({"text": text, "kw": speiseplan.get("kw")})


@app.route("/api/speiseplan/tag/<tag>", methods=["GET"])
def api_tag(tag: str):
    """
    Gibt das Menü für einen bestimmten Tag zurück.

    Args:
        tag: Wochentag (montag, dienstag, mittwoch, donnerstag, freitag)

    Query Parameter:
        kw: Kalenderwoche (optional, Standard: aktuelle Woche)

    Returns:
        JSON mit dem Tagesmenü
    """
    valid_days = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag"]
    tag = tag.lower()

    if tag not in valid_days:
        return jsonify(
            {"error": f"Ungültiger Tag: {tag}. Gültig sind: {', '.join(valid_days)}"}
        ), 400

    kw = request.args.get("kw", type=int)
    speiseplan = get_speiseplan(kw)

    if speiseplan.get("error"):
        return jsonify({"error": speiseplan["error"]}), 404

    menu = speiseplan.get("menu", {})
    day_menu = menu.get(tag, {})

    return jsonify(
        {
            "tag": tag,
            "kw": speiseplan.get("kw"),
            "gerichte": day_menu.get("gerichte", []),
        }
    )


@app.route("/api/health", methods=["GET"])
def health():
    """Health Check Endpoint."""
    return jsonify({"status": "ok", "current_kw": get_current_week_number()})


@app.route("/", methods=["GET"])
def index():
    """Startseite mit API-Dokumentation."""
    return """
    <html>
    <head>
        <title>Speiseplan API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }
            pre { background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }
            h2 { color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>🍽️ Speiseplan API</h1>
        <p>REST API für den Schul-Speiseplan von Wollino</p>

        <h2>Endpoints</h2>

        <h3>GET /api/speiseplan</h3>
        <p>Kompletter Wochenspeiseplan</p>
        <pre>GET /api/speiseplan?kw=4</pre>

        <h3>GET /api/speiseplan/heute</h3>
        <p>Heutiges Menü</p>

        <h3>GET /api/speiseplan/text</h3>
        <p>Formatierter Text für Markdown-Anzeige</p>

        <h3>GET /api/speiseplan/tag/{tag}</h3>
        <p>Menü für einen bestimmten Tag (montag, dienstag, mittwoch, donnerstag, freitag)</p>
        <pre>GET /api/speiseplan/tag/montag</pre>

        <h3>GET /api/health</h3>
        <p>Health Check</p>

        <h2>Home Assistant Integration</h2>
        <p>Siehe <code>homeassistant/</code> Ordner für Konfigurationsbeispiele.</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5123, debug=True)
