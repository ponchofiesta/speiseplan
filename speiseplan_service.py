"""
Speiseplan Service für Home Assistant
Liest Wochenspeisepläne aus lokalen PDF-Dateien.

Die PDFs werden automatisch von https://www.wollino.de/newpage heruntergeladen
und im Ordner 'pdf_speiseplaene/' gespeichert.

Verwendet:
- download_pdfs.py: Automatischer Download der PDFs
- parse_pdfs.py: Parsing der PDF-Inhalte
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Importiere Funktionen aus den anderen Modulen
from download_pdfs import download_all_pdfs
from parse_pdfs import find_pdf_for_week, extract_menu_from_pdf, format_menu_for_display

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konstanten
PDF_FOLDER = Path("pdf_speiseplaene")
CACHE_FILE = "speiseplan_cache.json"


def get_current_week_number() -> int:
    """Gibt die aktuelle Kalenderwoche zurück."""
    return datetime.now().isocalendar()[1]


def ensure_pdf_available(week_number: int) -> Optional[Path]:
    """
    Stellt sicher, dass die PDF für eine Kalenderwoche verfügbar ist.
    Lädt sie bei Bedarf automatisch herunter.

    Returns:
        Path zur PDF-Datei oder None wenn nicht verfügbar
    """
    # Prüfe ob PDF bereits existiert
    pdf_path = find_pdf_for_week(week_number)
    if pdf_path:
        logger.info(f"PDF für KW {week_number} bereits vorhanden: {pdf_path}")
        return pdf_path

    # Versuche automatisch herunterzuladen
    logger.info(f"PDF für KW {week_number} nicht gefunden, starte Download...")
    try:
        stats = download_all_pdfs(target_kw=week_number)

        if stats["downloaded"] > 0:
            logger.info(f"PDF für KW {week_number} erfolgreich heruntergeladen")
            # Suche die heruntergeladene PDF
            return find_pdf_for_week(week_number)
        elif stats["skipped"] > 0:
            # PDF existiert jetzt (wurde möglicherweise parallel heruntergeladen)
            return find_pdf_for_week(week_number)
        else:
            logger.warning(f"Konnte PDF für KW {week_number} nicht herunterladen")
            return None

    except Exception as e:
        logger.error(f"Fehler beim automatischen Download: {e}")
        return None


def get_speiseplan(week_number: int = None) -> dict:
    """
    Hauptfunktion: Holt den Speiseplan für eine bestimmte Woche.
    Lädt die PDF bei Bedarf automatisch herunter.
    """
    if week_number is None:
        week_number = get_current_week_number()

    logger.info(f"Hole Speiseplan für KW {week_number}")

    # Cache prüfen (24 Stunden gültig)
    cached = load_cache(week_number)
    if cached:
        logger.info("Speiseplan aus Cache geladen")
        return cached

    # PDF-Datei finden oder herunterladen
    pdf_path = ensure_pdf_available(week_number)
    if not pdf_path:
        return {
            "error": f"Kein Speiseplan für KW {week_number} verfügbar. Automatischer Download fehlgeschlagen.",
            "kw": week_number,
            "menu": None,
        }

    # Menü extrahieren (extract_menu_from_pdf aus parse_pdfs.py nimmt Path)
    menu = extract_menu_from_pdf(pdf_path)

    result = {
        "kw": week_number,
        "year": datetime.now().year,
        "pdf_file": str(pdf_path),
        "menu": menu,
        "updated": datetime.now().isoformat(),
    }

    # Cache speichern
    save_cache(week_number, result)

    return result


def load_cache(week_number: int) -> Optional[dict]:
    """Lädt den Cache wenn er aktuell ist (max 24h)."""
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
            if cache.get("kw") == week_number:
                updated = datetime.fromisoformat(cache.get("updated", "2000-01-01"))
                if datetime.now() - updated < timedelta(hours=24):
                    return cache
                else:
                    logger.info("Cache älter als 24 Stunden, lade neu...")
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def save_cache(week_number: int, data: dict):
    """Speichert in den Cache."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Fehler beim Cache-Speichern: {e}")


def format_speiseplan_for_display(speiseplan: dict) -> str:
    """
    Formatiert den vollständigen Speiseplan für die Anzeige.
    Wrapper um format_menu_for_display aus parse_pdfs.py.
    """
    if speiseplan.get("error"):
        return speiseplan["error"]

    menu = speiseplan.get("menu", {})
    kw = speiseplan.get("kw", "?")

    output = [f"📅 Speiseplan KW {kw}"]
    output.append(format_menu_for_display(menu))

    return "\n".join(output)


def get_today_menu() -> dict:
    """Gibt das Menü für heute zurück."""
    today = datetime.now()
    day_mapping = {
        0: "montag",
        1: "dienstag",
        2: "mittwoch",
        3: "donnerstag",
        4: "freitag",
        5: "samstag",
        6: "sonntag",
    }

    day_name = day_mapping.get(today.weekday())

    if day_name in ["samstag", "sonntag"]:
        return {
            "day": day_name,
            "message": "Am Wochenende gibt es kein Schulessen.",
            "gerichte": [],
        }

    speiseplan = get_speiseplan()

    if speiseplan.get("error"):
        return {"day": day_name, "error": speiseplan["error"], "gerichte": []}

    menu = speiseplan.get("menu", {})
    day_menu = menu.get(day_name, {})

    return {
        "day": day_name,
        "kw": speiseplan.get("kw"),
        "gerichte": day_menu.get("gerichte", []),
    }


def list_available_pdfs() -> list:
    """Listet alle verfügbaren PDFs im Ordner."""
    if not PDF_FOLDER.exists():
        return []
    return list(PDF_FOLDER.glob("*.pdf"))


if __name__ == "__main__":
    print("=" * 60)
    print("Speiseplan Service - Lokale PDF-Version")
    print("=" * 60)

    # Zeige verfügbare PDFs
    pdfs = list_available_pdfs()
    if pdfs:
        print(f"\nVerfügbare PDFs in '{PDF_FOLDER}':")
        for pdf in pdfs:
            print(f"  - {pdf.name}")
    else:
        print(f"\nKeine PDFs gefunden in '{PDF_FOLDER}'")
        print("Bitte PDFs von https://www.wollino.de/newpage herunterladen")

    print("\n" + "-" * 60)

    # Hole aktuellen Speiseplan
    print("\nHole aktuellen Speiseplan...")
    plan = get_speiseplan()
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    print("\n" + "=" * 50 + "\n")
    print(format_speiseplan_for_display(plan))

    print("\n" + "=" * 50 + "\n")
    print("Heutiges Menü:")
    print(json.dumps(get_today_menu(), ensure_ascii=False, indent=2))
