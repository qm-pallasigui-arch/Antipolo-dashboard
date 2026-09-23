"""Offline converter for text-based PDF surveillance tables.

This intentionally does not participate in Dash uploads.  PDF extraction can
be slow and table boundaries are uncertain, so conversion produces both a
canonical file and a JSON audit report for review before dashboard ingestion.
Scanned/image-only PDFs are rejected; OCR is outside this converter's scope.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from dashboard.data.date_parser import DATE_CONVENTIONS, normalize_surveillance_table
from dashboard.data.validation import validate_and_clean_disease_df


def _table_to_frame(table: list[list]) -> pd.DataFrame | None:
    rows = [row for row in table if row and any(cell not in (None, "") for cell in row)]
    if len(rows) < 2:
        return None
    header_index = next(
        (i for i, row in enumerate(rows) if any(str(cell).strip().lower() in {"disease", "cases"} for cell in row)),
        0,
    )
    header = [str(cell or f"column_{i + 1}").strip() for i, cell in enumerate(rows[header_index])]
    width = len(header)
    body = [(list(row) + [None] * width)[:width] for row in rows[header_index + 1:]]
    frame = pd.DataFrame(body, columns=header)
    # Repeated page headers are common in extracted tables.
    first_column = frame.columns[0]
    return frame[frame[first_column].astype(str).str.strip().str.lower() != str(first_column).strip().lower()]


def extract_pdf_tables(path: Path) -> tuple[list[pd.DataFrame], dict]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "PDF conversion requires pdfplumber. Install the project's dependencies first."
        ) from exc

    frames = []
    page_reports = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            accepted = 0
            for table in tables:
                frame = _table_to_frame(table)
                if frame is not None and not frame.empty:
                    frames.append(frame)
                    accepted += 1
            page_reports.append({
                "page": page_number,
                "tables_detected": len(tables),
                "nonempty_tables": accepted,
            })
    report = {"pages": len(page_reports), "page_results": page_reports, "tables_extracted": len(frames)}
    return frames, report


def convert_pdf(
    input_path: str | Path,
    output_path: str | Path,
    date_convention: str = "day-first",
) -> dict:
    source = Path(input_path)
    destination = Path(output_path)
    if source.suffix.lower() != ".pdf":
        raise ValueError("Input must be a PDF file.")
    if destination.suffix.lower() not in {".csv", ".xlsx"}:
        raise ValueError("Output must end in .csv or .xlsx.")
    if date_convention not in DATE_CONVENTIONS:
        raise ValueError(f"Unsupported date convention: {date_convention}")

    frames, extraction = extract_pdf_tables(source)
    normalized = []
    notes = []
    rejected = []
    for index, frame in enumerate(frames, start=1):
        try:
            monthly, table_notes = normalize_surveillance_table(frame, date_convention)
        except ValueError as exc:
            rejected.append({"table": index, "reason": str(exc)})
            continue
        normalized.append(monthly)
        notes.extend(f"Table {index}: {note}" for note in table_notes)

    if not normalized:
        raise ValueError(
            "No usable surveillance table was found. The PDF may be scanned, or its tables may not contain "
            "disease, cases, and recognizable date columns."
        )

    combined = pd.concat(normalized, ignore_index=True)
    combined = combined.groupby(["year", "month", "disease"], as_index=False)["cases"].sum(min_count=1)
    cleaned, validation_notes = validate_and_clean_disease_df(combined)
    if cleaned.empty:
        raise ValueError("PDF tables were extracted, but no valid tracked-disease rows remained after validation.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    canonical = cleaned[["year", "month", "disease", "cases"]]
    if destination.suffix.lower() == ".csv":
        canonical.to_csv(destination, index=False)
    else:
        canonical.to_excel(destination, index=False)

    report = {
        "input": str(source.resolve()),
        "output": str(destination.resolve()),
        "date_convention": date_convention,
        **extraction,
        "tables_rejected": rejected,
        "rows_written": int(len(canonical)),
        "diseases": sorted(canonical["disease"].unique().tolist()),
        "year_min": int(canonical["year"].min()),
        "year_max": int(canonical["year"].max()),
        "conversion_notes": notes,
        "validation_notes": validation_notes,
        "review_required": True,
        "review_message": "Compare extracted monthly totals with the source PDF before dashboard upload.",
    }
    report_path = destination.with_suffix(destination.suffix + ".report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report"] = str(report_path.resolve())
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Convert text-based PDF surveillance tables to monthly CSV/XLSX.")
    parser.add_argument("input_pdf")
    parser.add_argument("output", help="Destination ending in .csv or .xlsx")
    parser.add_argument(
        "--date-convention",
        choices=sorted(DATE_CONVENTIONS),
        default="day-first",
        help="How to interpret ambiguous numeric dates (default: day-first).",
    )
    args = parser.parse_args(argv)
    report = convert_pdf(args.input_pdf, args.output, args.date_convention)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
