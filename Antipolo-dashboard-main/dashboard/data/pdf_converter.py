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
import re

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
    frame = frame[frame[first_column].astype(str).str.strip().str.lower() != str(first_column).strip().lower()]
    frame.attrs["raw_table"] = table
    return frame


def _cell_lines(value) -> list[str]:
    if value is None:
        return []
    return [line.strip() for line in str(value).splitlines() if line.strip()]


def _numeric_lines(value) -> list[float] | None:
    lines = _cell_lines(value)
    values = []
    for line in lines:
        cleaned = line.replace(",", "")
        try:
            values.append(float(cleaned))
        except ValueError:
            return None
    return values


def _month_matrix_to_frame(frames: list[pd.DataFrame]) -> tuple[pd.DataFrame | None, list[str]]:
    """Expand PDF tables whose rows contain newline-separated top-N records.

    The supplied DOH report uses year marker rows followed by one visually
    merged row: five disease labels in the first cell and five values in each
    JAN..DEC cell. Page breaks may split a year marker from its data row, so
    ``current_year`` intentionally persists across all extracted tables.
    """
    month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                   "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_columns = None
    current_year = None
    records = []
    notes = []

    for frame in frames:
        table = frame.attrs.get("raw_table")
        if not table:
            continue
        for row in table:
            cells = list(row)
            normalized = [str(cell or "").strip().upper() for cell in cells]
            if all(month in normalized for month in month_names):
                month_columns = [normalized.index(month) for month in month_names]
                continue

            first_lines = _cell_lines(cells[0] if cells else None)
            if len(first_lines) == 1 and re.fullmatch(r"(?:19|20)\d{2}", first_lines[0]):
                current_year = int(first_lines[0])
                continue
            if current_year is None or month_columns is None or not first_lines:
                continue

            month_values = []
            for column in month_columns:
                values = _numeric_lines(cells[column] if column < len(cells) else None)
                month_values.append(values)
            if any(values is None or len(values) != len(first_lines) for values in month_values):
                continue

            for disease_index, disease in enumerate(first_lines):
                monthly_total = 0.0
                for month, values in enumerate(month_values, start=1):
                    value = values[disease_index]
                    monthly_total += value
                    records.append({
                        "year": current_year,
                        "month": month,
                        "disease": disease,
                        "cases": value,
                    })

                total_column = max(month_columns) + 1
                totals = _numeric_lines(cells[total_column] if total_column < len(cells) else None)
                if totals is not None and len(totals) == len(first_lines):
                    reported_total = totals[disease_index]
                    if abs(reported_total - monthly_total) > 0.01:
                        notes.append(
                            f"{current_year} {disease}: monthly sum {monthly_total:g} does not match "
                            f"reported total {reported_total:g}."
                        )

    if not records:
        return None, []
    expanded = pd.DataFrame.from_records(records)
    expanded["disease"] = expanded["disease"].str.replace(
        r"\s*\([A-Z]\d{2}(?:-[A-Z]?\d{2})?\)\s*$", "", regex=True,
    )
    notes.insert(0, f"Expanded a year-by-month PDF matrix into {len(expanded):,} monthly row(s).")
    return expanded, notes


def extract_pdf_tables(path: Path) -> tuple[list[pd.DataFrame], dict]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "PDF conversion requires pdfplumber. Install the project's dependencies first."
        ) from exc

    frames = []
    page_reports = []
    document_text = []
    with pdfplumber.open(path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            document_text.append(page_text)
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
    normalized_text = " ".join(document_text).lower().replace("�", "-")
    scope_warnings = []
    source_notes = []
    if "school-aged children" in normalized_text or "school aged children" in normalized_text:
        scope_warnings.append(
            "The source is limited to school-aged children (ages 5-19), not all Antipolo residents. "
            "Do not present it as city-wide all-age surveillance."
        )
    if "top 5 leading" in normalized_text:
        scope_warnings.append(
            "The source reports only the top five categories for each displayed year. A disease's absence "
            "does not mean zero cases, so this is not a complete longitudinal surveillance extract."
        )
    if "no reports were available" in normalized_text and "2020 and 2022" in normalized_text:
        source_notes.append("The source document states that no reports were available for 2020 and 2022.")
    if "field health services information system database" in normalized_text:
        source_notes.append("The document identifies the Field Health Services Information System Database as its source.")
    report["scope_warnings"] = scope_warnings
    report["source_notes"] = source_notes
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
    matrix, matrix_notes = _month_matrix_to_frame(frames)
    if matrix is not None:
        frames = [matrix]
        notes.extend(matrix_notes)
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
    compatible, validation_notes = validate_and_clean_disease_df(combined)

    destination.parent.mkdir(parents=True, exist_ok=True)
    canonical = combined[["year", "month", "disease", "cases"]].copy()
    canonical["year"] = canonical["year"].astype(int)
    canonical["month"] = canonical["month"].astype(int)
    canonical["cases"] = canonical["cases"].round().astype(int)
    if destination.suffix.lower() == ".csv":
        canonical.to_csv(destination, index=False)
    else:
        canonical.to_excel(destination, index=False)

    dashboard_blockers = list(extraction.get("scope_warnings", []))
    dashboard_blockers.extend(note for note in notes if "does not match reported total" in note)
    if compatible.empty:
        dashboard_blockers.append("No extracted rows have usable disease labels and monthly values.")

    report = {
        "input": str(source.resolve()),
        "output": str(destination.resolve()),
        "date_convention": date_convention,
        **extraction,
        "tables_rejected": rejected,
        "rows_written": int(len(canonical)),
        "diseases": sorted(canonical["disease"].unique().tolist()),
        "dashboard_compatible_rows": int(len(compatible)),
        "dashboard_compatible_diseases": sorted(compatible["disease"].unique().tolist()),
        "dashboard_ready": not dashboard_blockers,
        "dashboard_blockers": dashboard_blockers,
        "year_min": int(canonical["year"].min()),
        "year_max": int(canonical["year"].max()),
        "conversion_notes": notes,
        "validation_notes": validation_notes,
        "review_required": True,
        "review_message": (
            "Compare extracted monthly totals with the source PDF and review scope warnings before dashboard upload. "
            "The dashboard accepts arbitrary valid disease labels and will use the converted file as the session dataset."
        ),
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
