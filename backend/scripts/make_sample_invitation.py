"""Write the sample shop's Campaign Invitation as a PDF, the document the Evolus extractor reads in the demo.

Everything in it comes from backend/src/marginarena/sample/glow_lab_bkk.json, so the PDF can't drift from the data the
Arena uses. It is clearly labelled as a fictional sample, not a document issued by the marketplace.

    uv run --project backend --with reportlab python backend/scripts/make_sample_invitation.py
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SAMPLE = Path(__file__).resolve().parents[1] / "src" / "marginarena" / "sample"
OUT = SAMPLE / "glow-lab-bkk-invitation.pdf"


def main() -> None:
    raw = json.loads((SAMPLE / "glow_lab_bkk.json").read_text())
    invitation = raw["invitation"]
    catalogue = {row["id"]: row for row in raw["catalogue"]}
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Campaign Invitation", styles["Title"]),
        Paragraph(
            "Fictional sample for the MarginArena demo. Glow Lab BKK and this invitation are invented; it was not issued "
            "by any marketplace.",
            styles["Italic"],
        ),
        Spacer(1, 6 * mm),
    ]
    facts = [
        ("Marketplace", invitation["marketplace"]),
        ("Seller", raw["shop"]),
        ("Campaign", invitation["campaign"]),
        ("Slot", invitation["slot"]),
        ("Registration closes", invitation["registration_closes"]),
    ]
    story.append(Table([[k, v] for k, v in facts], colWidths=[45 * mm, 120 * mm], hAlign="LEFT"))
    story += [
        Spacer(1, 6 * mm),
        Paragraph(
            f"You are invited to register these {len(invitation['items'])} products. Each must be sold at least the "
            "minimum discount below its list price during the slot.",
            styles["Normal"],
        ),
        Spacer(1, 4 * mm),
    ]
    rows = [["No.", "SKU", "Product", "List price (THB)", "Minimum discount"]]
    for n, item in enumerate(invitation["items"], start=1):
        product = catalogue[item["sku"]]
        discount = f"{round(float(item['required_discount']) * 100)}%"
        rows.append([str(n), item["sku"], product["name"], product["list_price"], discount])
    table = Table(rows, colWidths=[12 * mm, 22 * mm, 70 * mm, 30 * mm, 35 * mm], hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef0f3")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9ced6")),
                ("ALIGN", (3, 1), (4, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(table)
    SimpleDocTemplate(str(OUT), pagesize=A4, title="Campaign Invitation (fictional sample)").build(story)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
