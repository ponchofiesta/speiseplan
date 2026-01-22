"""
PDF Parsing Script für Wollino Speisepläne.

Liest lokale PDF-Dateien aus dem Ordner pdf_speiseplaene/
und extrahiert die Menüs für jeden Wochentag.

Usage:
    python parse_pdfs.py                    # Parse alle PDFs
    python parse_pdfs.py --kw 4             # Nur KW 4 parsen
    python parse_pdfs.py --file datei.pdf   # Bestimmte Datei parsen
    python parse_pdfs.py --debug            # Debug-Ausgabe für Analyse
"""

import re
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import pdfplumber

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Konstanten
PDF_FOLDER = Path("pdf_speiseplaene")
CACHE_FILE = "speiseplan_cache.json"


def find_pdf_for_week(week_number: int) -> Optional[Path]:
    """Findet die PDF-Datei für eine bestimmte Kalenderwoche."""
    if not PDF_FOLDER.exists():
        return None

    patterns = [
        f"*KW_{week_number:02d}*.pdf",
        f"*KW_{week_number}*.pdf",
        f"*KW{week_number:02d}*.pdf",
    ]

    for pattern in patterns:
        files = list(PDF_FOLDER.glob(pattern))
        grundschule_files = [f for f in files if "Grundschule" in f.name]
        if grundschule_files:
            return grundschule_files[0]
        elif files:
            return files[0]

    return None


def extract_menu_from_pdf(pdf_path: Path, debug: bool = False) -> dict:
    """
    Extrahiert das Menü aus einer PDF-Datei.

    Args:
        pdf_path: Pfad zur PDF-Datei
        debug: Wenn True, gibt Debug-Informationen aus

    Returns:
        Dictionary mit Menü pro Tag
    """
    menu = {
        "montag": {"gerichte": []},
        "dienstag": {"gerichte": []},
        "mittwoch": {"gerichte": []},
        "donnerstag": {"gerichte": []},
        "freitag": {"gerichte": []},
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()

            if debug:
                logger.info(f"Extrahierte {len(words)} Wörter aus der PDF")
                # Speichere Debug-Daten
                debug_file = pdf_path.with_suffix(".debug.json")
                with open(debug_file, "w", encoding="utf-8") as f:
                    json.dump(words, f, ensure_ascii=False, indent=2)
                logger.info(f"Debug-Daten gespeichert in: {debug_file}")

            menu = parse_wollino_by_rows(words, debug)

    except Exception as e:
        logger.error(f"Fehler beim Extrahieren des Menüs: {e}")
        import traceback

        traceback.print_exc()

    return menu


def parse_wollino_by_rows(words: list, debug: bool = False) -> dict:
    """
    Parst den Wollino-Speiseplan basierend auf Y-Position.

    Das PDF-Layout:
    - Spalte links: Info/Legende
    - Spalte mitte-links: Tages-Marker (OM, ID, IM, OD, RF)
    - Spalte mitte: Menü 1
    - Spalte mitte-rechts: Menü 2
    - Spalte rechts: Desserts/Snacks
    """
    menu = {
        "montag": {"gerichte": []},
        "dienstag": {"gerichte": []},
        "mittwoch": {"gerichte": []},
        "donnerstag": {"gerichte": []},
        "freitag": {"gerichte": []},
    }

    # Finde die Y-Positionen der Tages-Marker
    day_markers = {}
    marker_map = {
        "OM": "montag",
        "ID": "dienstag",
        "IM": "mittwoch",
        "OD": "donnerstag",
        "RF": "freitag",
    }

    for w in words:
        text = w["text"].upper()
        if text in marker_map:
            day_markers[marker_map[text]] = w["top"]

    if not day_markers:
        logger.warning("Keine Tages-Marker (OM, ID, IM, OD, RF) gefunden")
        return menu

    if debug:
        logger.info(f"Tages-Marker gefunden: {day_markers}")

    # Sortiere Tage nach Y-Position
    sorted_days = sorted(day_markers.items(), key=lambda x: x[1])

    # Berechne Y-Bereiche für jeden Tag
    day_ranges = {}
    for i, (day, y_start) in enumerate(sorted_days):
        if i + 1 < len(sorted_days):
            y_end = sorted_days[i + 1][1]
        else:
            y_end = 600
        day_ranges[day] = (y_start, y_end)

    if debug:
        logger.info(f"Tag-Bereiche: {day_ranges}")

    # Wörter die wir ignorieren
    skip_words = {
        "om",
        "id",
        "im",
        "od",
        "rf",
        "menü",
        "menüplan",
        "kw",
        "vom",
        "bis",
        "stand:",
        "zusatzstoffe",
        "allergene",
        "farbstoff",
        "konservierung",
        "gluten",
        "krebstiere",
        "eier",
        "fisch",
        "erdnuss",
        "soja",
        "milch",
        "schalenfrüchte",
        "sellerie",
        "senf",
        "sesam",
        "sulfit",
        "lupinen",
        "weichtiere",
        "weizen",
        "roggen",
        "gerste",
        "hafer",
        "dinkel",
        "walnuss",
        "cashew",
        "pekan",
        "paranuss",
        "pistazie",
        "macadamia",
        "mandel",
        "haselnuss",
        "sonderkost",
        "anmeldung",
        "grundschule",
        "wolfsburg",
        "speiseplan",
        "wollino",
        "gmbh",
        "woche",
        "januar",
        "februar",
        "märz",
        "april",
        "mai",
        "juni",
        "juli",
        "august",
        "september",
        "oktober",
        "november",
        "dezember",
        "2024",
        "2025",
        "2026",
        "montag",
        "dienstag",
        "mittwoch",
        "donnerstag",
        "freitag",
        "mo",
        "di",
        "mi",
        "do",
        "fr",
    }

    # X-Position der Menü-Spalten
    menu_x_start = 100
    menu_x_end = 500

    # Sammle Wörter nach Tag
    day_words = {day: [] for day in menu}

    for w in words:
        text = w["text"].strip()
        x = w["x0"]
        y = w["top"]

        # Skip wenn zu weit links oder rechts
        if x < menu_x_start or x > menu_x_end:
            continue

        # Skip Marker und bekannte Skip-Wörter
        if text.lower() in skip_words:
            continue

        # Skip einzelne Buchstaben/Zahlen (Allergene)
        if len(text) <= 2:
            continue

        # Skip wenn es ein Allergen-Code ist
        if re.match(r"^[A-Z]{1,2}\d*$", text) or re.match(r"^\d{1,2}$", text):
            continue

        # Finde den Tag für diese Y-Position
        for day, (y_start, y_end) in day_ranges.items():
            if y_start <= y < y_end:
                day_words[day].append({"text": text, "x": x, "y": y})
                break

    # Gruppiere Wörter zu Zeilen
    for day, words_list in day_words.items():
        if not words_list:
            continue

        # Sortiere nach Y, dann X
        words_list.sort(key=lambda w: (round(w["y"] / 5) * 5, w["x"]))

        # Gruppiere nach Y-Position (Toleranz 8 Pixel)
        lines = []
        current_line = []
        last_y = None

        for w in words_list:
            if last_y is None or abs(w["y"] - last_y) < 8:
                current_line.append(w["text"])
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [w["text"]]
            last_y = w["y"]

        if current_line:
            lines.append(" ".join(current_line))

        # Bereinige und füge hinzu
        for line in lines:
            clean = clean_menu_text(line, skip_words)
            if clean and len(clean) > 3 and clean not in menu[day]["gerichte"]:
                menu[day]["gerichte"].append(clean)

        if debug and menu[day]["gerichte"]:
            logger.info(f"{day}: {menu[day]['gerichte']}")

    return menu


def clean_menu_text(text: str, skip_words: set) -> str:
    """Bereinigt den Menütext."""
    if not text:
        return ""

    if text.lower() in skip_words:
        return ""

    # Entferne Allergen-Codes
    clean = re.sub(r"\([^)]*\)", "", text)
    clean = re.sub(r"\b[A-Z]\b", "", clean)
    clean = re.sub(r"\b\d{1,2}\b", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    clean = clean.strip()

    return clean


def parse_all_pdfs(target_kw: int = None, debug: bool = False) -> dict:
    """
    Parst alle PDFs im Ordner oder eine bestimmte KW.

    Returns:
        Dictionary mit allen geparsten Speiseplänen
    """
    results = {}

    if not PDF_FOLDER.exists():
        logger.error(f"Ordner '{PDF_FOLDER}' existiert nicht!")
        return results

    pdf_files = list(PDF_FOLDER.glob("*.pdf"))

    if not pdf_files:
        logger.warning(f"Keine PDF-Dateien in '{PDF_FOLDER}' gefunden")
        return results

    logger.info(f"Gefunden: {len(pdf_files)} PDF-Dateien")

    for pdf_path in pdf_files:
        # Extrahiere KW aus Dateinamen
        kw_match = re.search(r"KW[_\s]?(\d{1,2})", pdf_path.name, re.IGNORECASE)
        if not kw_match:
            logger.warning(f"Konnte KW nicht aus '{pdf_path.name}' extrahieren")
            continue

        kw = int(kw_match.group(1))

        # Wenn bestimmte KW gewünscht, andere überspringen
        if target_kw is not None and kw != target_kw:
            continue

        logger.info(f"\nParse: {pdf_path.name} (KW {kw})")

        menu = extract_menu_from_pdf(pdf_path, debug)

        results[kw] = {
            "kw": kw,
            "file": str(pdf_path),
            "menu": menu,
            "parsed": datetime.now().isoformat(),
        }

        # Zeige Zusammenfassung
        total_dishes = sum(len(menu[day]["gerichte"]) for day in menu)
        logger.info(f"  → {total_dishes} Gerichte extrahiert")

    return results


def format_menu_for_display(menu: dict) -> str:
    """Formatiert das Menü für die Konsolenausgabe."""
    output = []

    day_emojis = {
        "montag": "🔵 Montag",
        "dienstag": "🟢 Dienstag",
        "mittwoch": "🟡 Mittwoch",
        "donnerstag": "🟠 Donnerstag",
        "freitag": "🔴 Freitag",
    }

    for day, emoji_label in day_emojis.items():
        gerichte = menu.get(day, {}).get("gerichte", [])
        if gerichte:
            output.append(f"\n{emoji_label}:")
            for gericht in gerichte:
                output.append(f"  • {gericht}")
        else:
            output.append(f"\n{emoji_label}: Kein Menü")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Parse Wollino Speiseplan PDFs")
    parser.add_argument("--kw", type=int, help="Nur bestimmte Kalenderwoche parsen")
    parser.add_argument("--file", type=str, help="Bestimmte PDF-Datei parsen")
    parser.add_argument("--debug", action="store_true", help="Debug-Ausgabe aktivieren")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("Wollino Speiseplan PDF Parser")
    print("=" * 60)

    if args.file:
        # Einzelne Datei parsen
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            logger.error(f"Datei nicht gefunden: {pdf_path}")
            exit(1)

        menu = extract_menu_from_pdf(pdf_path, args.debug)

        if args.json:
            print(json.dumps(menu, ensure_ascii=False, indent=2))
        else:
            print(format_menu_for_display(menu))
    else:
        # Alle PDFs parsen
        results = parse_all_pdfs(target_kw=args.kw, debug=args.debug)

        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for kw, data in sorted(results.items()):
                print(f"\n{'=' * 60}")
                print(f"📅 Speiseplan KW {kw}")
                print(f"   Datei: {data['file']}")
                print("=" * 60)
                print(format_menu_for_display(data["menu"]))

    print()


if __name__ == "__main__":
    main()
