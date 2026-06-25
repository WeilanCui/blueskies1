from __future__ import annotations

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SEED_DIR = Path(__file__).resolve().parents[2] / "data"


def _resolve_seed_dir(seed_dir: Path | str | None) -> Path:
    if seed_dir is None:
        return DEFAULT_SEED_DIR
    return Path(seed_dir)


def discover_csv_files(seed_dir: Path | str | None = None) -> list[Path]:
    directory = _resolve_seed_dir(seed_dir)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.csv"))


def iter_csv_product_rows(seed_dir: Path | str | None = None):
    """Yield product rows from every CSV in the seed directory.

    Expected format: brand, product_name, ingredient1, ingredient2, ...
    Ingredients occupy separate columns because the source files are comma-delimited.
    """
    for csv_path in discover_csv_files(seed_dir):
        with csv_path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                continue

            if len(header) < 3:
                logger.warning("Skipping %s: expected at least 3 columns, got %s", csv_path.name, header)
                continue

            for line_number, row in enumerate(reader, start=2):
                if len(row) < 2:
                    continue

                brand = row[0].strip()
                product_name = row[1].strip()
                if not brand or not product_name:
                    continue

                ingredients = [cell.strip() for cell in row[2:] if cell.strip()]
                yield {
                    "source_file": csv_path.name,
                    "line_number": line_number,
                    "brand": brand,
                    "product_name": product_name,
                    "ingredients": ingredients,
                    "raw_inci_text": ", ".join(ingredients),
                }
