#!/usr/bin/env python3
"""Extrae UF del SII (fuente oficial) sin incorporar credenciales en Android.

Uso: python scripts/sii_uf.py 2026
La salida es JSON con fechas ISO, pesos CLP y fuente. Falla si no hay valores.
"""
import json
import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser

class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.stack = []
        self.cell = None
        self.row = None
    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.stack.append([])
        elif self.stack and tag == "tr":
            self.row = []
        elif self.stack and tag in ("td", "th") and self.row is not None:
            self.cell = []
    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.stack:
            self.stack[-1].append(self.row)
            self.row = None
        elif tag == "table" and self.stack:
            self.tables.append(self.stack.pop())

def parse_sii(html, year):
    # Tabla resumen: Día | Ene | Feb | ... | Dic. No confundir con tablas mensuales.
    parser = Tables()
    parser.feed(html)
    result = {}
    number = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")
    for table in parser.tables:
        for index, row in enumerate(table):
            header = [x.lower().strip() for x in row]
            if len(header) < 13 or header[0] not in ("día", "dia") or not header[1].startswith("ene") or not header[12].startswith("dic"):
                continue
            for record in table[index+1:]:
                if len(record) < 13 or not record[0].strip().isdigit():
                    continue
                day = int(record[0])
                for month in range(1, 13):
                    value = record[month].strip()
                    if not number.fullmatch(value):
                        continue
                    try:
                        key = date(year, month, day).isoformat()
                    except ValueError:
                        continue
                    result[key] = int(value.replace(".", "").replace(",", ""))
            if result:
                return result
    raise ValueError("No se encontró una tabla anual de UF reconocible en el SII")

def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else date.today().year
    if not 2000 <= year <= 2100:
        raise ValueError("Año fuera del rango permitido")
    url = f"https://www.sii.cl/valores_y_fechas/uf/uf{year}.htm"
    req = urllib.request.Request(url, headers={"User-Agent":"Finiquito-UF-Official-Importer/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        html = response.read(2_000_000).decode("utf-8", errors="replace")
    values = parse_sii(html, year)
    print(json.dumps({"source":"Servicio de Impuestos Internos (SII)","source_url":url,"year":year,"unit":"CLP cents","values":values},ensure_ascii=False,sort_keys=True,indent=2))

if __name__ == "__main__":
    main()
