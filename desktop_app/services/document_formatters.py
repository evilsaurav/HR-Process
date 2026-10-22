"""
Service: document_formatters.py
Purpose: Reusable data formatting and normalization utilities for HR document generation.
"""

import re
import datetime
from typing import Tuple, Any, Optional
from num2words import num2words


def get_title_and_relation(gender: Optional[str]) -> Tuple[str, str]:
    """
    Returns (title, relation) based on candidate gender.
    Input: "Male" / "M" / "Female" / "F" (case-insensitive, whitespace-tolerant)
    Returns: ("Mr.", "S/o") or ("Ms.", "D/o")
    Fallback: ("Mr.", "S/o") if gender is unspecified, empty, or unrecognized.
    """
    if not gender:
        return "Mr.", "S/o"
    g = str(gender).strip().lower()
    if g in ["female", "f", "woman", "girl", "ms", "mrs"]:
        return "Ms.", "D/o"
    return "Mr.", "S/o"


def format_address_multiline(address: Optional[str]) -> str:
    """
    Formats a comma-separated address into a clean multi-line block (max 3 lines)
    suitable for letter recipient blocks.
    - If <= 3 parts, joined by newlines.
    - If > 3 parts, packed into max 3 balanced lines:
      Line 1: first 2 parts
      Line 2: next 2 parts
      Line 3: remaining parts
    Returns string separated by '\n'.
    """
    if not address or not str(address).strip():
        return ""
    raw_parts = [p.strip() for p in str(address).split(",") if p.strip()]
    if not raw_parts:
        return ""

    parts = []
    for i, part in enumerate(raw_parts):
        if i < len(raw_parts) - 1:
            parts.append(part + ",")
        else:
            parts.append(part)

    if len(parts) <= 3:
        return "\n".join(parts)

    lines = [
        " ".join(parts[:2]),
        " ".join(parts[2:4]),
        " ".join(parts[4:])
    ]
    return "\n".join([line.strip() for line in lines[:3] if line.strip()])


def amount_to_indian_words(amount: Any) -> str:
    """
    Converts a currency amount into Indian numbering system words.
    Accepts int, float, or formatted strings like '25,000', '₹ 25,000/-'.
    Returns Title-cased words + ' Only', e.g., 'Twenty-Five Thousand Only'.
    """
    if amount is None:
        return ""
    # Clean non-digit characters except decimal point and negative sign
    cleaned = (
        str(amount)
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace(",", "")
        .replace("/-", "")
        .strip()
    )
    if not cleaned:
        return ""

    try:
        num = float(cleaned)
        int_val = int(round(num))
    except (ValueError, TypeError):
        return str(amount)

    if int_val == 0:
        return "Zero Only"

    try:
        words = num2words(int_val, lang="en_IN").title()
        return f"{words} Only"
    except Exception:
        # Fallback to default en if en_IN encounters any edge case
        words = num2words(int_val, lang="en").title()
        return f"{words} Only"


def format_date_long(date_value: Any, fallback: str = "") -> str:
    """
    Normalizes a date input to the standard HR long format: '%d %B %Y' (e.g. '15 January 2024').
    Accepts string (various common formats), datetime.date, datetime.datetime, or pandas.Timestamp.
    Returns fallback if input cannot be parsed safely without raising exceptions.
    """
    if date_value is None:
        return fallback

    # Check if object has strftime (datetime, date, Timestamp)
    if hasattr(date_value, "strftime"):
        try:
            return date_value.strftime("%d %B %Y")
        except Exception:
            pass

    s = str(date_value).strip()
    if not s or s.lower() in ["none", "nan", "nat", "null"]:
        return fallback

    # Clean any timestamp fragments (e.g. ' 00:00:00', 'T00:00:00', etc.)
    s_cleaned = re.sub(r'[T\s]+\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?.*$', '', s).strip()

    # Try explicit common date formats
    common_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d %B %Y",
        "%d %b %Y",
        "%d.%m.%Y",
    ]
    for target_str in ([s_cleaned, s] if s_cleaned != s else [s_cleaned]):
        for fmt in common_formats:
            try:
                dt = datetime.datetime.strptime(target_str, fmt)
                return dt.strftime("%d %B %Y")
            except ValueError:
                pass

    # Optional pandas parsing fallback for any irregular strings
    try:
        import pandas as pd
        parsed = pd.to_datetime(s_cleaned, errors="coerce", dayfirst=True)
        if parsed is not pd.NaT and not pd.isna(parsed):
            return parsed.strftime("%d %B %Y")
    except Exception:
        pass

    return fallback if fallback != "" else s


def calculate_end_date(start_date_str: Any, years: int = 1) -> str:
    """
    Calculates the contract end date: start_date + years - 1 day.
    Used for Offer letter '{{END DATE}}' and Extension letter '{{Extension end date}}'.
    Input can be a date string or datetime object.
    Returns '%d %B %Y' formatted string, e.g., '15 January 2024' -> '14 January 2025'.
    """
    if not start_date_str:
        return ""

    dt = None
    if hasattr(start_date_str, "strftime") and isinstance(start_date_str, (datetime.date, datetime.datetime)):
        dt = start_date_str
    else:
        s = str(start_date_str).strip()
        # Clean any timestamp fragments
        s_cleaned = re.sub(r'[T\s]+\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?.*$', '', s).strip()
        common_formats = [
            "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
            "%Y/%m/%d", "%d %B %Y", "%d %b %Y", "%d.%m.%Y"
        ]
        for target_str in ([s_cleaned, s] if s_cleaned != s else [s_cleaned]):
            for fmt in common_formats:
                try:
                    dt = datetime.datetime.strptime(target_str, fmt)
                    break
                except ValueError:
                    pass
            if dt is not None:
                break

        if dt is None:
            try:
                import pandas as pd
                parsed = pd.to_datetime(s_cleaned, errors="coerce", dayfirst=True)
                if parsed is not pd.NaT and not pd.isna(parsed):
                    dt = parsed.to_pydatetime()
            except Exception:
                pass

    if dt is None:
        return ""

    # Leap-year safe year replacement
    try:
        next_dt = dt.replace(year=dt.year + years)
    except ValueError:
        # e.g. Feb 29 in leap year rolling over to Feb 28 in non-leap year
        next_dt = dt.replace(year=dt.year + years, day=28)

    end_dt = next_dt - datetime.timedelta(days=1)
    return end_dt.strftime("%d %B %Y")


def format_currency_inr(amount: Any) -> str:
    """
    Formats a numeric amount with Indian rupee symbol and comma grouping.
    Example: 25000 -> '₹25,000'
    Handles integers, floats, and strings with currency symbols/commas.
    """
    if amount is None:
        return ""
    cleaned = (
        str(amount)
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace(",", "")
        .replace("/-", "")
        .strip()
    )
    if not cleaned:
        return ""

    try:
        val = int(round(float(cleaned)))
        return f"₹{val:,}"
    except (ValueError, TypeError):
        return f"₹{cleaned}"
