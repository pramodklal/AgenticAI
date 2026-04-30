from __future__ import annotations

from pathlib import Path
from PyPDF2 import PdfReader

pdf_path = Path(r"D:\GenAI_Project_2025\myHealthCoach\docs\aiagent.pdf")
reader = PdfReader(str(pdf_path))
print(f"pages={len(reader.pages)}")

for i, page in enumerate(reader.pages, start=1):
    text = (page.extract_text() or "").strip().replace("\n", " ")
    print(f"\n---PAGE {i}---")
    if text:
        print(text[:2500])
    else:
        print("[no extractable text]")
