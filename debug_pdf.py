"""
Debug-Skript um die PDF-Struktur zu analysieren
"""

import io
import requests
import pdfplumber

# Headers für die Anfrage
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Aktuelle PDF URL für KW 4
PDF_URL = "https://cdn.website-editor.net/s/721848d81245444e84308a4698fc2668/files/uploaded/KW_04_Speiseplan+Grundschule_AEN.pdf?Expires=1771581145&Signature=bzCJOPafmfVucezqTwWs69SjbE2F5G6LLqW1Yulwcecig80cplhVIe8qoFMdAs4nmAoAPTyBV~hhJQSBD7-EvayEhZ~GeS6F54e1OGMGQmjAPXr2qrCVnXecErhzNypxaU3Jz7dWNnGSzOsB8ZjOlq2TUiUCT6iswUpTaDMRFBTGCo6wxZ-3P760KvHVVTNql9Aaf64VFRZCcArUVGQs3iVnaISnNNxSoY6RT0-QSzCoP9fbwgv3XKBx9CTCJ2jARO~l1CuanCR5fKDm7ok00ZbzFm7APt9aavu4XNn6a3p4-bIzOcdSbeD-HnJwuFfqSpbiLi04cbjR7UM~u2RKCg__&Key-Pair-Id=K2NXBXLF010TJW"


def main():
    print("Lade PDF herunter...")
    response = requests.get(PDF_URL, headers=HEADERS, timeout=60)
    response.raise_for_status()
    pdf_content = response.content
    print(f"PDF heruntergeladen: {len(pdf_content)} bytes\n")

    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()

        print(f"Page width: {page.width}, height: {page.height}")

        print("\n--- SUCHE NACH TAGES-MARKERN ---")
        markers = ["OM", "ID", "IM", "OD", "RF", "MO", "DI", "MI", "DO", "FR"]
        for w in words:
            if w["text"].upper() in markers:
                print(f"  x={w['x0']:6.1f}, y={w['top']:6.1f}: {w['text']}")

        print("\n--- ALLE WOERTER MIT Y < 300 (Header-Bereich) ---")
        header_words = [w for w in words if w["top"] < 300]
        header_words_sorted = sorted(header_words, key=lambda x: (x["top"], x["x0"]))
        for w in header_words_sorted[:80]:
            print(f"  x={w['x0']:6.1f}, y={w['top']:6.1f}: {w['text']}")

        print("\n--- WOERTER GRUPPIERT NACH Y-POSITION ---")
        y_groups = {}
        for w in words:
            y = round(w["top"] / 20) * 20
            if y not in y_groups:
                y_groups[y] = []
            y_groups[y].append(w)

        for y in sorted(y_groups.keys())[:20]:
            row_words = sorted(y_groups[y], key=lambda x: x["x0"])
            row_text = " | ".join([f"{w['text']}({w['x0']:.0f})" for w in row_words])
            print(f"  y={y}: {row_text}")


if __name__ == "__main__":
    main()
