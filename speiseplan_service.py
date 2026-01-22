"""
Speiseplan Service für Home Assistant
Lädt den Wochenspeiseplan als PDF und extrahiert das Menü.
"""

import re
import io
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import requests
from bs4 import BeautifulSoup
import pdfplumber

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konstanten
WOLLINO_URL = "https://www.wollino.de/grundschulenc4f8564f"
CACHE_FILE = "speiseplan_cache.json"

# HTTP Headers um als normaler Browser erkannt zu werden
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.wollino.de/",
    "Connection": "keep-alive",
}

# Bekannte PDF-URLs (werden beim ersten erfolgreichen Abruf gespeichert)
# Diese URLs können manuell aktualisiert werden, wenn die automatische Erkennung fehlschlägt
KNOWN_PDF_URLS_FILE = "known_pdf_urls.json"


def get_current_week_number() -> int:
    """Gibt die aktuelle Kalenderwoche zurück."""
    return datetime.now().isocalendar()[1]


def get_week_dates(week_number: int, year: int = None) -> dict:
    """Gibt die Wochentage für eine bestimmte KW zurück."""
    if year is None:
        year = datetime.now().year

    # Ersten Tag der Woche berechnen (Montag)
    first_day_of_year = datetime(year, 1, 1)
    # ISO Woche beginnt mit Montag
    first_monday = first_day_of_year + timedelta(
        days=(7 - first_day_of_year.weekday()) % 7
    )
    if first_day_of_year.weekday() <= 3:  # Mo-Do
        first_monday = first_monday - timedelta(days=7)

    week_start = first_monday + timedelta(weeks=week_number - 1)

    days = {
        "montag": week_start,
        "dienstag": week_start + timedelta(days=1),
        "mittwoch": week_start + timedelta(days=2),
        "donnerstag": week_start + timedelta(days=3),
        "freitag": week_start + timedelta(days=4),
    }
    return days


def fetch_pdf_links() -> list[dict]:
    """
    Holt alle PDF-Links von der Wollino-Webseite.
    Gibt eine Liste von Dicts mit 'url', 'kw' und 'text' zurück.
    """
    pdf_links = []

    # Versuche zuerst, bekannte URLs zu laden
    known_urls = load_known_urls()
    if known_urls:
        logger.info(f"Verwende {len(known_urls)} bekannte PDF-URLs")
        return known_urls

    # Versuche die Website zu scrapen
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        response = session.get(WOLLINO_URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Alle Links finden, die auf PDFs zeigen
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "Speiseplan" in href and ".pdf" in href.lower():
                # KW aus dem Dateinamen extrahieren (z.B. KW_04 oder KW_38)
                kw_match = re.search(r"KW[_\s]?(\d{1,2})", href, re.IGNORECASE)
                if kw_match:
                    kw = int(kw_match.group(1))
                    pdf_links.append(
                        {"url": href, "kw": kw, "text": link.get_text(strip=True)}
                    )
                    logger.info(f"Gefunden: KW {kw} - {link.get_text(strip=True)}")

        # Erfolgreiche URLs speichern
        if pdf_links:
            save_known_urls(pdf_links)

    except requests.RequestException as e:
        logger.error(f"Fehler beim Abrufen der Webseite: {e}")
        logger.info("Versuche Fallback mit manuell hinterlegten URLs...")

    return pdf_links


def load_known_urls() -> list[dict]:
    """Lädt bekannte PDF-URLs aus der Datei."""
    try:
        with open(KNOWN_PDF_URLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Prüfe ob die URLs noch aktuell sind (nicht älter als 14 Tage)
            updated = datetime.fromisoformat(data.get("updated", "2000-01-01"))
            if datetime.now() - updated < timedelta(days=14):
                return data.get("urls", [])
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def save_known_urls(urls: list[dict]):
    """Speichert bekannte PDF-URLs in einer Datei."""
    try:
        with open(KNOWN_PDF_URLS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"urls": urls, "updated": datetime.now().isoformat()},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except IOError as e:
        logger.error(f"Fehler beim Speichern der URLs: {e}")


def add_known_url(url: str, kw: int, text: str = ""):
    """
    Fügt eine bekannte PDF-URL manuell hinzu.
    Nützlich wenn die automatische Erkennung fehlschlägt.
    """
    urls = load_known_urls()

    # Prüfe ob KW schon existiert
    for u in urls:
        if u["kw"] == kw:
            u["url"] = url
            u["text"] = text
            save_known_urls(urls)
            return

    urls.append({"url": url, "kw": kw, "text": text})
    save_known_urls(urls)
    logger.info(f"URL für KW {kw} hinzugefügt")


def find_pdf_for_week(week_number: int) -> Optional[str]:
    """
    Findet die PDF-URL für eine bestimmte Kalenderwoche.
    """
    pdf_links = fetch_pdf_links()

    for link in pdf_links:
        if link["kw"] == week_number:
            logger.info(f"PDF für KW {week_number} gefunden: {link['url']}")
            return link["url"]

    logger.warning(f"Keine PDF für KW {week_number} gefunden")
    return None


def download_pdf(url: str) -> Optional[bytes]:
    """Lädt eine PDF-Datei herunter."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logger.error(f"Fehler beim Herunterladen der PDF: {e}")
        return None


def extract_menu_from_pdf(pdf_content: bytes) -> dict:
    """
    Extrahiert das Menü aus der PDF.
    Gibt ein Dictionary mit dem Menü pro Tag zurück.
    """
    menu = {
        "montag": {"gerichte": []},
        "dienstag": {"gerichte": []},
        "mittwoch": {"gerichte": []},
        "donnerstag": {"gerichte": []},
        "freitag": {"gerichte": []},
    }

    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            page = pdf.pages[0]
            words = page.extract_words()

            # Parse basierend auf Y-Position der Tages-Marker
            menu = parse_wollino_by_rows(words)

    except Exception as e:
        logger.error(f"Fehler beim Extrahieren des Menüs aus der PDF: {e}")
        import traceback

        traceback.print_exc()

    return menu


def parse_wollino_by_rows(words: list) -> dict:
    """
    Parst den Wollino-Speiseplan basierend auf Y-Position.

    Das PDF-Layout:
    - Spalte links: Info/Legende
    - Spalte mitte-links: Tages-Marker (OM, ID, IM, OD, RF)
    - Spalte mitte: Menü 1
    - Spalte mitte-rechts: Menü 2
    - Spalte rechts: Desserts/Snacks

    Die Gerichte werden nach Y-Position den Tagen zugeordnet.
    """
    menu = {
        "montag": {"gerichte": []},
        "dienstag": {"gerichte": []},
        "mittwoch": {"gerichte": []},
        "donnerstag": {"gerichte": []},
        "freitag": {"gerichte": []},
    }

    # Finde die Y-Positionen der Tages-Marker
    day_markers = {}  # {day: y_position}
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
        logger.warning("Keine Tages-Marker gefunden")
        return menu

    logger.info(f"Tages-Marker gefunden: {day_markers}")

    # Sortiere Tage nach Y-Position
    sorted_days = sorted(day_markers.items(), key=lambda x: x[1])

    # Berechne Y-Bereiche für jeden Tag
    day_ranges = {}  # {day: (y_start, y_end)}
    for i, (day, y_start) in enumerate(sorted_days):
        if i + 1 < len(sorted_days):
            y_end = sorted_days[i + 1][1]
        else:
            y_end = 600  # Seitenende
        day_ranges[day] = (y_start, y_end)

    logger.info(f"Tag-Bereiche: {day_ranges}")

    # Wörter die wir ignorieren
    skip_words = {
        "om",
        "id",
        "im",
        "od",
        "rf",  # Tages-Marker
        "menü",
        "menüplan",
        "kw",
        "vom",
        "bis",
        "stand:",  # Header
        "zusatzstoffe",
        "allergene",
        "farbstoff",
        "konservierung",
        "gluten",
        "krebstiere",
        "eier",
        "sojabohnen",
        "milch",
        "schalenfrüchte",
        "sellerie",
        "senf",
        "sesam",
        "lupine",
        "weichtiere",
        "erdnüsse",
        "schwefeldioxid",
        "vegan",
        "veggie",
        "rind",
        "geflügel",
        "fisch",
        "spuren",
        "kreuzkonta-",
        "minationen",
        "können",
        "nicht",
        "ausgeschlossen",
        "änderungen",
        "vorbehalten",
        "werden.",
        "phenylalaninquelle",
        "abführend",
        "koffeinhaltig",
        "chininhaltig",
        "geschmacksverstärker",
        "gewachst",
        "antioxidationsmittel",
        "phosphat",
        "süßungsmittel",
        "geschwärzt",
        "geschwefelt",
        "schutzatmosphähre",
        "unter",
        "wolfsburger",
        "grundschulen",
        "sonderkost:",
        "bei",
        "und",
        "nach",
        "anmeldung",
        "unverträglichkeiten",
        "rücksprache.",
        "verpackt",
        "ich",
        "mag",
        "alles",
        "gemüsefreunde",
        "desserts",
        "snacks",
        "vorspeisen,",
        "nachmittags-",
        "obst-",
        "oder",
        "gemüseauswahl",  # Generische Begriffe
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "1a",
        "8a",
        "8b",  # Zahlen
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",  # Allergen-Codes
        "allergien",
        "dinkel)",
        "roggen,",
        "weizen,",
        "(weizen,",
        "(weizen)",  # Allergen-Infos
    }

    # Sammle Wörter pro Tag (nur aus dem Menü-Bereich, x > 250)
    for w in words:
        text = w["text"]
        x = w["x0"]
        y = w["top"]

        # Nur Wörter im Menü-Bereich (rechts vom Tages-Marker)
        if x < 250:
            continue

        # Ignoriere Header (y < 80)
        if y < 80:
            continue

        # Ignoriere Skip-Wörter
        if text.lower() in skip_words:
            continue

        # Ignoriere einzelne Buchstaben und kurze Wörter
        if len(text) <= 2:
            continue

        # Ignoriere Allergene in Klammern
        if text.startswith("(") or text.endswith(")"):
            continue

        # Finde den passenden Tag
        for day, (y_start, y_end) in day_ranges.items():
            if y_start - 10 <= y < y_end:  # Etwas Puffer oben
                # Bereinige den Text
                clean = clean_word(text)
                if clean and len(clean) > 2:
                    menu[day]["gerichte"].append(clean)
                break

    # Kombiniere die Wörter zu Gerichten
    for day in menu:
        menu[day]["gerichte"] = build_gerichte(menu[day]["gerichte"])

    return menu


def clean_word(text: str) -> str:
    """Bereinigt ein einzelnes Wort."""
    # Entferne Klammern und Allergen-Codes
    clean = re.sub(r"\([^)]*\)", "", text)
    clean = re.sub(r"[A-Z]$", "", clean)  # Einzelner Buchstabe am Ende
    return clean.strip()


def build_gerichte(words: list) -> list:
    """
    Baut aus einer Liste von Wörtern sinnvolle Gerichte zusammen.
    """
    if not words:
        return []

    # Bekannte Gerichte-Patterns (was zusammengehört)
    gericht_starters = {
        "Veg.": ["Bällchen"],
        "Vollkorn": ["Penne", "Brötchen"],
        "Gemüse-Linsen-": ["Bolognese"],
        "Hochzeitssuppe": ["mit", "Geflügel"],
        "Lachs": ["in", "Krosspanade"],
        "Blattsalat": ["mit", "Mais"],
        "Lasagne": ["mit", "Rindfleisch"],
        "Vegetarische": ["Lasagne"],
        "Gemischter": ["Salat"],
    }

    # Wörter die alleine keinen Sinn machen
    incomplete_words = {"mit", "in", "Geflügel", "Gurke,", "Tomate", "Vegetarische"}

    # Entferne Duplikate und behalte die Reihenfolge
    seen = set()
    unique_words = []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique_words.append(w)

    # Kombiniere zusammengehörige Wörter
    combined = []
    i = 0
    while i < len(unique_words):
        word = unique_words[i]

        # Überspringe unvollständige Wörter
        if word in incomplete_words:
            i += 1
            continue

        # Prüfe ob dieses Wort der Start eines bekannten Gerichts ist
        if word in gericht_starters:
            gericht = word
            expected = gericht_starters[word]
            j = i + 1
            while j < len(unique_words) and j - i <= len(expected):
                next_word = unique_words[j]
                if next_word in expected:
                    gericht += " " + next_word
                    j += 1
                else:
                    break
            combined.append(gericht)
            i = j
        else:
            combined.append(word)
            i += 1

    # Filtere zu kurze Einträge und bereinige
    result = []
    for g in combined:
        g = g.strip()
        if len(g) > 3 and g not in result:
            # Entferne Wörter die nur Allergen-Codes sind
            if not re.match(r"^[A-Z\s]+$", g):
                result.append(g)

    return result


def parse_wollino_tables(tables: list) -> dict:
    """
    Parst Wollino-Speiseplan-Tabellen.
    Das Format hat typischerweise Tage als Spaltenüberschriften.
    """
    menu = {
        "montag": {"gerichte": []},
        "dienstag": {"gerichte": []},
        "mittwoch": {"gerichte": []},
        "donnerstag": {"gerichte": []},
        "freitag": {"gerichte": []},
    }

    days_patterns = {
        r"mo\b|montag": "montag",
        r"di\b|dienstag": "dienstag",
        r"mi\b|mittwoch": "mittwoch",
        r"do\b|donnerstag": "donnerstag",
        r"fr\b|freitag": "freitag",
    }

    # Wörter die wir überspringen wollen
    skip_words = [
        "zusatzstoffe",
        "allergene",
        "farbstoff",
        "konservierung",
        "gluten",
        "krebstiere",
        "eier",
        "fisch",
        "soja",
        "laktose",
        "nüsse",
        "sellerie",
        "senf",
        "sesam",
        "schwefel",
        "lupine",
        "weichtiere",
        "vegan",
        "veggie",
        "geflügel",
        "rind",
        "sonderkost",
        "anmeldung",
        "rücksprache",
        "kreuzkontamination",
        "menüplan",
        "wolfsburg",
        "grundschule",
        "phenylalaninquelle",
        "abführend",
        "koffeinhaltig",
        "chininhaltig",
        "geschmacksverstärker",
        "gewachst",
        "antioxidationsmittel",
        "phosphat",
        "süßungsmittel",
        "geschwärzt",
        "geschwefelt",
        "spuren",
    ]

    for table in tables:
        if not table:
            continue

        day_columns = {}

        # Finde Header-Zeile mit Wochentagen
        for row_idx, row in enumerate(table):
            if not row:
                continue

            for col_idx, cell in enumerate(row):
                if not cell:
                    continue
                cell_lower = str(cell).lower().strip()

                for pattern, day in days_patterns.items():
                    if re.search(pattern, cell_lower):
                        day_columns[col_idx] = day
                        break

            # Wenn wir Tage gefunden haben, parse die folgenden Zeilen
            if day_columns:
                break

        # Parse die Datenzeilen
        if day_columns:
            for row in table[row_idx + 1 :]:
                if not row:
                    continue

                for col_idx, day in day_columns.items():
                    if col_idx >= len(row):
                        continue

                    cell = row[col_idx]
                    if not cell:
                        continue

                    cell_text = str(cell).strip()

                    # Bereinige den Text
                    clean_text = clean_menu_text(cell_text, skip_words)

                    if clean_text and clean_text not in menu[day]["gerichte"]:
                        menu[day]["gerichte"].append(clean_text)

    return menu


def parse_wollino_text(text: str) -> dict:
    """
    Parst den Speiseplan aus dem extrahierten Text.
    Für den Fall, dass die Tabellen-Extraktion nicht funktioniert.
    """
    menu = {
        "montag": {"gerichte": []},
        "dienstag": {"gerichte": []},
        "mittwoch": {"gerichte": []},
        "donnerstag": {"gerichte": []},
        "freitag": {"gerichte": []},
    }

    # Versuche, die Gerichte über Zeilenposition und Datum zu identifizieren
    lines = text.split("\n")

    days_patterns = [
        (r"(?:mo(?:ntag)?)\s*[,\.]?\s*(\d{1,2}\.\d{1,2}\.)", "montag"),
        (r"(?:di(?:enstag)?)\s*[,\.]?\s*(\d{1,2}\.\d{1,2}\.)", "dienstag"),
        (r"(?:mi(?:ttwoch)?)\s*[,\.]?\s*(\d{1,2}\.\d{1,2}\.)", "mittwoch"),
        (r"(?:do(?:nnerstag)?)\s*[,\.]?\s*(\d{1,2}\.\d{1,2}\.)", "donnerstag"),
        (r"(?:fr(?:eitag)?)\s*[,\.]?\s*(\d{1,2}\.\d{1,2}\.)", "freitag"),
    ]

    skip_words = [
        "zusatzstoffe",
        "allergene",
        "farbstoff",
        "konservierung",
        "gluten",
        "sonderkost",
        "anmeldung",
        "menüplan",
        "wolfsburg",
        "grundschule",
        "spuren",
        "kreuzkontamination",
    ]

    current_day = None

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue

        line_lower = line.lower()

        # Prüfe ob Zeile einen Tag markiert
        for pattern, day in days_patterns:
            if re.search(pattern, line_lower, re.IGNORECASE):
                current_day = day
                continue

        # Wenn wir einen aktuellen Tag haben und die Zeile relevant ist
        if current_day:
            if any(skip in line_lower for skip in skip_words):
                continue

            clean_text = clean_menu_text(line, skip_words)
            if clean_text and len(clean_text) > 5:
                menu[current_day]["gerichte"].append(clean_text)

    return menu


def clean_menu_text(text: str, skip_words: list) -> str:
    """
    Bereinigt den Menütext von Allergenen und Zusatzstoffen.
    """
    if not text:
        return ""

    # Prüfe auf Skip-Wörter
    text_lower = text.lower()
    for skip in skip_words:
        if skip in text_lower:
            return ""

    # Entferne Allergen-Codes (einzelne Buchstaben/Zahlen in Klammern oder am Ende)
    # z.B. "A (Weizen)", "11 G C", etc.
    clean = re.sub(r"\([^)]*\)", "", text)  # Entferne Klammern
    clean = re.sub(r"\b[A-Z]\b", "", clean)  # Einzelne Großbuchstaben
    clean = re.sub(r"\b\d{1,2}\b", "", clean)  # Ein- und zweistellige Zahlen
    clean = re.sub(r"\s+", " ", clean)  # Mehrfache Leerzeichen
    clean = clean.strip()

    # Entferne Zeilenumbrüche und ersetze durch Kommas
    clean = re.sub(r"\n+", ", ", clean)
    clean = re.sub(r",\s*,", ",", clean)  # Doppelte Kommas
    clean = clean.strip(", ")

    return clean


def parse_menu_text(text: str, tables: list) -> dict:
    """
    Parst den extrahierten Text und die Tabellen, um das Menü zu strukturieren.
    """
    menu = {
        "montag": {"gerichte": []},
        "dienstag": {"gerichte": []},
        "mittwoch": {"gerichte": []},
        "donnerstag": {"gerichte": []},
        "freitag": {"gerichte": []},
    }

    # Versuche zunächst, die Tabellen zu parsen
    if tables:
        menu = parse_tables(tables, menu)

    # Fallback: Text-basiertes Parsing
    if not any(menu[day]["gerichte"] for day in menu):
        menu = parse_text_fallback(text, menu)

    return menu


def parse_tables(tables: list, menu: dict) -> dict:
    """
    Parst die extrahierten Tabellen.
    Speisepläne haben oft eine Tabellenstruktur mit Tagen als Spalten.
    """
    days_mapping = {
        "mo": "montag",
        "montag": "montag",
        "di": "dienstag",
        "dienstag": "dienstag",
        "mi": "mittwoch",
        "mittwoch": "mittwoch",
        "do": "donnerstag",
        "donnerstag": "donnerstag",
        "fr": "freitag",
        "freitag": "freitag",
    }

    current_day_index = {}

    for row in tables:
        if not row:
            continue

        # Prüfen ob es eine Header-Zeile mit Tagen ist
        for i, cell in enumerate(row):
            if cell:
                cell_lower = cell.lower().strip()
                for key, day in days_mapping.items():
                    if key in cell_lower:
                        current_day_index[i] = day
                        break

        # Wenn wir Tage gefunden haben, die folgenden Zeilen als Gerichte speichern
        if current_day_index:
            for col_idx, day in current_day_index.items():
                if col_idx < len(row) and row[col_idx]:
                    cell_text = row[col_idx].strip()
                    # Überspringe Header und leere Zellen
                    if cell_text and not any(
                        d in cell_text.lower() for d in days_mapping.keys()
                    ):
                        if cell_text not in menu[day]["gerichte"]:
                            menu[day]["gerichte"].append(cell_text)

    return menu


def parse_text_fallback(text: str, menu: dict) -> dict:
    """
    Fallback-Parsing wenn keine Tabellen erkannt wurden.
    """
    days = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag"]
    lines = text.split("\n")
    current_day = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Prüfe ob die Zeile einen Wochentag enthält
        line_lower = line.lower()
        for day in days:
            if day in line_lower or day[:2] in line_lower.split():
                current_day = day
                # Entferne den Tag aus der Zeile für eventuelle Gerichte danach
                remaining = re.sub(
                    rf"\b{day}\b", "", line_lower, flags=re.IGNORECASE
                ).strip()
                if remaining and len(remaining) > 3:
                    menu[current_day]["gerichte"].append(remaining)
                break
        else:
            # Wenn kein Tag gefunden, aber wir einen aktuellen Tag haben
            if current_day and len(line) > 3:
                menu[current_day]["gerichte"].append(line)

    return menu


def get_speiseplan(week_number: int = None) -> dict:
    """
    Hauptfunktion: Holt den Speiseplan für eine bestimmte Woche.
    Wenn keine Woche angegeben, wird die aktuelle Woche verwendet.
    """
    if week_number is None:
        week_number = get_current_week_number()

    logger.info(f"Hole Speiseplan für KW {week_number}")

    # Cache prüfen
    cached = load_cache(week_number)
    if cached:
        logger.info("Speiseplan aus Cache geladen")
        return cached

    # PDF-URL finden
    pdf_url = find_pdf_for_week(week_number)
    if not pdf_url:
        return {
            "error": f"Kein Speiseplan für KW {week_number} verfügbar",
            "kw": week_number,
            "menu": None,
        }

    # PDF herunterladen
    pdf_content = download_pdf(pdf_url)
    if not pdf_content:
        return {
            "error": "PDF konnte nicht heruntergeladen werden",
            "kw": week_number,
            "menu": None,
        }

    # Menü extrahieren
    menu = extract_menu_from_pdf(pdf_content)

    result = {
        "kw": week_number,
        "year": datetime.now().year,
        "pdf_url": pdf_url,
        "menu": menu,
        "updated": datetime.now().isoformat(),
    }

    # In Cache speichern
    save_cache(week_number, result)

    return result


def load_cache(week_number: int) -> Optional[dict]:
    """Lädt den Speiseplan aus dem Cache, wenn er noch gültig ist."""
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
            if cache.get("kw") == week_number:
                # Cache ist maximal 12 Stunden gültig
                updated = datetime.fromisoformat(cache.get("updated", "2000-01-01"))
                if datetime.now() - updated < timedelta(hours=12):
                    return cache
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def save_cache(week_number: int, data: dict):
    """Speichert den Speiseplan im Cache."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Fehler beim Speichern des Cache: {e}")


def format_menu_for_display(speiseplan: dict) -> str:
    """
    Formatiert den Speiseplan für die Anzeige.
    """
    if speiseplan.get("error"):
        return speiseplan["error"]

    menu = speiseplan.get("menu", {})
    kw = speiseplan.get("kw", "?")

    output = [f"📅 Speiseplan KW {kw}\n"]

    day_emojis = {
        "montag": "🔵 Montag",
        "dienstag": "🟢 Dienstag",
        "mittwoch": "🟡 Mittwoch",
        "donnerstag": "🟠 Donnerstag",
        "freitag": "🔴 Freitag",
    }

    for day, emoji_label in day_emojis.items():
        if day in menu:
            gerichte = menu[day].get("gerichte", [])
            if gerichte:
                output.append(f"\n{emoji_label}:")
                for gericht in gerichte:
                    output.append(f"  • {gericht}")
            else:
                output.append(f"\n{emoji_label}: Kein Menü verfügbar")

    return "\n".join(output)


def get_today_menu() -> dict:
    """Gibt das Menü für den heutigen Tag zurück."""
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
            "message": "Am Wochenende gibt es keinen Schulessen.",
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


if __name__ == "__main__":
    # Test
    print("Hole aktuellen Speiseplan...")
    plan = get_speiseplan()
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    print("\n" + "=" * 50 + "\n")
    print(format_menu_for_display(plan))
    print("\n" + "=" * 50 + "\n")
    print("Heutiges Menü:")
    print(json.dumps(get_today_menu(), ensure_ascii=False, indent=2))
