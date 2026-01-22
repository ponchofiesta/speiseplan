"""
PDF Download Script für Wollino Speisepläne.

Versucht automatisch die PDFs herunterzuladen.
Falls der automatische Download fehlschlägt (wegen Bot-Schutz),
werden die PDF-URLs angezeigt für manuellen Download.

Usage:
    python download_pdfs.py
    python download_pdfs.py --kw 4  # Nur KW 4 herunterladen
    python download_pdfs.py --manual  # Zeige nur URLs für manuellen Download
"""

import re
import time
import argparse
import logging
import gzip
import zlib
from pathlib import Path
import cloudscraper
from bs4 import BeautifulSoup

# Versuche brotli zu importieren (optional)
try:
    import brotli

    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Konstanten
PDF_FOLDER = Path("pdf_speiseplaene")
BASE_URL = "https://www.wollino.de/"

# Navigation Pfad durch die Website
NAV_STEPS = [
    {"name": "Startseite", "url": "https://www.wollino.de/"},
    # {"name": "Verpflegung", "url": "https://www.wollino.de/galerie"},
    # {"name": "Grundschulen", "url": "https://www.wollino.de/grundschulen"},
    {"name": "Menüpläne", "url": "https://www.wollino.de/newpage"},
]


def create_session() -> cloudscraper.CloudScraper:
    """Erstellt eine cloudscraper Session die einen Browser simuliert."""
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True,
            "mobile": False,
        },
        delay=10,  # Delay für JavaScript challenges
        interpreter="nodejs",  # Versuche nodejs für JS-Challenges
    )

    # Zusätzliche Header für realistischeres Verhalten
    scraper.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        }
    )

    return scraper


def navigate_to_menuplaene(scraper: cloudscraper.CloudScraper) -> str:
    """
    Navigiert durch die Website wie ein normaler Nutzer.
    Gibt den HTML-Inhalt der Menüplan-Seite zurück.
    """
    last_response = None

    for step in NAV_STEPS:
        logger.info(f"Navigiere zu: {step['name']} ({step['url']})")

        # Setze Referer vom vorherigen Schritt
        if last_response:
            scraper.headers["Referer"] = last_response.url

        try:
            response = scraper.get(step["url"], timeout=30)
            response.raise_for_status()

            # Kurze Pause wie ein echter Nutzer
            time.sleep(1.5)

            last_response = response
            logger.info(f"  ✓ {step['name']} geladen ({len(response.text)} Bytes)")

        except Exception as e:
            logger.error(f"  ✗ Fehler bei {step['name']}: {e}")
            raise

    return last_response.text if last_response else ""


def extract_pdf_links(html: str) -> list[dict]:
    """
    Extrahiert PDF-Links aus dem HTML der Menüplan-Seite.

    Returns:
        Liste von Dicts mit 'url', 'kw', 'filename'
    """
    soup = BeautifulSoup(html, "html.parser")
    pdf_links = []

    # Finde alle Links die auf PDFs zeigen
    for link in soup.find_all("a", href=True):
        href = link["href"]

        # Nur Speiseplan PDFs für Grundschule
        if "Speiseplan" in href and ".pdf" in href.lower() and "Grundschule" in href:
            # Extrahiere KW aus dem Dateinamen
            kw_match = re.search(r"KW[_\s]?(\d{1,2})", href, re.IGNORECASE)
            if kw_match:
                kw = int(kw_match.group(1))

                # Generiere einen sauberen Dateinamen
                filename = f"KW_{kw:02d}_Speiseplan_Grundschule.pdf"

                # Prüfe ob diese KW schon in der Liste ist
                if not any(p["kw"] == kw for p in pdf_links):
                    pdf_links.append(
                        {
                            "url": href,
                            "kw": kw,
                            "filename": filename,
                            "text": link.get_text(strip=True),
                        }
                    )
                    logger.info(f"  Gefunden: KW {kw} - {link.get_text(strip=True)}")

    # Sortiere nach KW
    pdf_links.sort(key=lambda x: x["kw"])

    return pdf_links


def decompress_content(content: bytes, encoding: str) -> bytes:
    """
    Dekomprimiert Daten basierend auf Content-Encoding.

    Args:
        content: Die komprimierten Bytes
        encoding: Der Content-Encoding Header (gzip, deflate, br)

    Returns:
        Dekomprimierte Bytes
    """
    encoding = encoding.lower() if encoding else ""

    if "br" in encoding:
        # Brotli-Dekomprimierung
        if HAS_BROTLI:
            try:
                return brotli.decompress(content)
            except Exception as e:
                logger.warning(f"Brotli-Dekomprimierung fehlgeschlagen: {e}")
        else:
            logger.warning(
                "Brotli-komprimierte Daten, aber brotli nicht installiert. Installiere mit: pip install brotli"
            )

    elif "gzip" in encoding:
        # Gzip-Dekomprimierung
        try:
            return gzip.decompress(content)
        except Exception as e:
            logger.warning(f"Gzip-Dekomprimierung fehlgeschlagen: {e}")

    elif "deflate" in encoding:
        # Deflate-Dekomprimierung
        try:
            return zlib.decompress(content, -zlib.MAX_WBITS)
        except Exception as e:
            logger.warning(f"Deflate-Dekomprimierung fehlgeschlagen: {e}")

    return content


def download_pdf(
    scraper: cloudscraper.CloudScraper, pdf_info: dict, referer: str
) -> bool:
    """
    Lädt eine PDF-Datei herunter.

    Args:
        scraper: cloudscraper Session
        pdf_info: Dict mit 'url', 'kw', 'filename'
        referer: Referer URL (die Menüplan-Seite)

    Returns:
        True wenn erfolgreich
    """
    # Setze Referer für den Download
    scraper.headers["Referer"] = referer
    scraper.headers["Sec-Fetch-Site"] = "cross-site"
    # Akzeptiere keine Komprimierung für PDF-Downloads
    scraper.headers["Accept-Encoding"] = "identity"
    scraper.headers["Accept"] = "application/pdf,*/*"

    filepath = PDF_FOLDER / pdf_info["filename"]

    try:
        logger.info(f"Lade herunter: KW {pdf_info['kw']} -> {pdf_info['filename']}")

        response = scraper.get(pdf_info["url"], timeout=60)
        response.raise_for_status()

        content = response.content

        # Prüfe auf Komprimierung und dekomprimiere falls nötig
        content_encoding = response.headers.get("Content-Encoding", "")
        if content_encoding:
            logger.info(f"  Content-Encoding: {content_encoding}")
            content = decompress_content(content, content_encoding)

        # Prüfe die ersten Bytes - PDF muss mit %PDF beginnen
        if content[:4] != b"%PDF":
            # Versuche trotzdem Dekomprimierung
            logger.info(f"  Erste Bytes: {content[:16].hex()}")

            # Versuche Brotli
            if HAS_BROTLI:
                try:
                    decompressed = brotli.decompress(content)
                    if decompressed[:4] == b"%PDF":
                        logger.info("  ✓ Brotli-Dekomprimierung erfolgreich")
                        content = decompressed
                except:
                    pass

            # Versuche Gzip
            if content[:4] != b"%PDF":
                try:
                    decompressed = gzip.decompress(content)
                    if decompressed[:4] == b"%PDF":
                        logger.info("  ✓ Gzip-Dekomprimierung erfolgreich")
                        content = decompressed
                except:
                    pass

        # Finale Prüfung
        content_type = response.headers.get("Content-Type", "")
        if content[:4] != b"%PDF":
            logger.warning(
                f"  ⚠ Keine gültige PDF für KW {pdf_info['kw']} (Content-Type: {content_type}, Erste Bytes: {content[:8].hex()})"
            )
            # Speichere trotzdem für Debugging
            debug_file = filepath.with_suffix(".debug")
            with open(debug_file, "wb") as f:
                f.write(content)
            logger.info(f"  Debug-Datei gespeichert: {debug_file}")
            return False

        # Speichere die PDF
        PDF_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(content)

        logger.info(f"  ✓ Gespeichert: {filepath} ({len(content)} Bytes)")
        return True

    except Exception as e:
        logger.error(f"  ✗ Fehler beim Download: {e}")
        return False


def download_all_pdfs(target_kw: int = None) -> dict:
    """
    Hauptfunktion: Lädt alle (oder eine bestimmte) PDF(s) herunter.

    Args:
        target_kw: Wenn angegeben, nur diese KW herunterladen

    Returns:
        Dict mit Statistiken
    """
    stats = {"found": 0, "downloaded": 0, "skipped": 0, "failed": 0, "pdfs": []}

    logger.info("=" * 60)
    logger.info("Wollino PDF Downloader")
    logger.info("=" * 60)

    # Session erstellen
    logger.info("\n1. Erstelle Browser-Session...")
    scraper = create_session()

    # Durch die Website navigieren
    logger.info("\n2. Navigiere durch die Website...")
    try:
        html = navigate_to_menuplaene(scraper)
    except Exception as e:
        logger.error(f"Navigation fehlgeschlagen: {e}")
        return stats

    # PDF-Links extrahieren
    logger.info("\n3. Extrahiere PDF-Links...")
    pdf_links = extract_pdf_links(html)
    stats["found"] = len(pdf_links)

    if not pdf_links:
        logger.warning("Keine PDF-Links gefunden!")
        return stats

    logger.info(f"   {len(pdf_links)} Speisepläne gefunden")

    # PDFs herunterladen
    logger.info("\n4. Lade PDFs herunter...")

    for pdf_info in pdf_links:
        # Wenn eine bestimmte KW gewünscht ist, andere überspringen
        if target_kw is not None and pdf_info["kw"] != target_kw:
            continue

        # Prüfe ob PDF schon existiert
        filepath = PDF_FOLDER / pdf_info["filename"]
        if filepath.exists():
            logger.info(f"   Überspringe KW {pdf_info['kw']} (existiert bereits)")
            stats["skipped"] += 1
            stats["pdfs"].append(
                {"kw": pdf_info["kw"], "status": "skipped", "file": str(filepath)}
            )
            continue

        # Kurze Pause zwischen Downloads
        time.sleep(1)

        # Download
        if download_pdf(scraper, pdf_info, NAV_STEPS[-1]["url"]):
            stats["downloaded"] += 1
            stats["pdfs"].append(
                {"kw": pdf_info["kw"], "status": "downloaded", "file": str(filepath)}
            )
        else:
            stats["failed"] += 1
            stats["pdfs"].append({"kw": pdf_info["kw"], "status": "failed"})

    # Zusammenfassung
    logger.info("\n" + "=" * 60)
    logger.info("Zusammenfassung:")
    logger.info(f"  Gefunden:      {stats['found']} PDFs")
    logger.info(f"  Heruntergeladen: {stats['downloaded']} PDFs")
    logger.info(f"  Übersprungen:  {stats['skipped']} PDFs")
    logger.info(f"  Fehlgeschlagen: {stats['failed']} PDFs")
    logger.info("=" * 60)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Lade Wollino Speisepläne herunter")
    parser.add_argument(
        "--kw", type=int, help="Nur bestimmte Kalenderwoche herunterladen"
    )
    parser.add_argument(
        "--force", action="store_true", help="Existierende PDFs überschreiben"
    )
    args = parser.parse_args()

    # Wenn --force, lösche existierende PDFs
    if args.force and PDF_FOLDER.exists():
        if args.kw:
            pattern = f"KW_{args.kw:02d}_*.pdf"
            for f in PDF_FOLDER.glob(pattern):
                f.unlink()
                logger.info(f"Gelöscht: {f}")
        else:
            for f in PDF_FOLDER.glob("*.pdf"):
                f.unlink()
                logger.info(f"Gelöscht: {f}")

    stats = download_all_pdfs(target_kw=args.kw)

    # Exit code basierend auf Erfolg
    if stats["failed"] > 0:
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
