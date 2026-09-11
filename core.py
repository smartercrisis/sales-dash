import pandas as pd
import numpy as np
import difflib

CITY_CANONICAL = {
    "cairo": ["cairo", "القاهرة", "kahira", "qahira", "al qahira"],
    "new cairo": ["new cairo", "التجمع", "el tagamoa", "tagamoa", "5th settlement", "التجمع الخامس"],
    "giza": ["giza", "الجيزة", "gizah", "el giza"],
    "6th of october": ["6th of october", "6 october", "السادس من أكتوبر", "october city", "٦ أكتوبر"],
    "sheikh zayed": ["sheikh zayed", "الشيخ زايد", "shikh zayed"],
    "alexandria": ["alexandria", "alex", "الإسكندرية", "eskendereya", "iskandariya"],
    "mansoura": ["mansoura", "المنصورة", "el mansoura"],
    "tanta": ["tanta", "طنطا"],
    "ismailia": ["ismailia", "الإسماعيلية"],
    "suez": ["suez", "السويس"],
    "port said": ["port said", "بورسعيد", "bur said"],
    "aswan": ["aswan", "أسوان"],
    "luxor": ["luxor", "الأقصر", "al uqsur"],
    "hurghada": ["hurghada", "الغردقة"],
    "sharm el sheikh": ["sharm el sheikh", "شرم الشيخ", "sharm"],
    "mahalla": ["mahalla", "المحلة الكبرى", "el mahalla"],
    "zagazig": ["zagazig", "الزقازيق"],
    "damietta": ["damietta", "دمياط"],
    "fayoum": ["fayoum", "الفيوم"],
    "beni suef": ["beni suef", "بني سويف"],
    "minya": ["minya", "المنيا"],
    "assiut": ["assiut", "أسيوط"],
    "sohag": ["sohag", "سوهاج"],
    "qena": ["qena", "قنا"],
}

CITY_COORDS = {
    "cairo": (30.0444, 31.2357), "new cairo": (30.0300, 31.4700),
    "giza": (30.0131, 31.2089), "6th of october": (29.9660, 30.9232),
    "sheikh zayed": (30.0700, 30.9500), "alexandria": (31.2001, 29.9187),
    "mansoura": (31.0409, 31.3785), "tanta": (30.7865, 31.0004),
    "ismailia": (30.5965, 32.2715), "suez": (29.9668, 32.5498),
    "port said": (31.2565, 32.2841), "aswan": (24.0889, 32.8998),
    "luxor": (25.6872, 32.6396), "hurghada": (27.2579, 33.8116),
    "sharm el sheikh": (27.9158, 34.3300), "mahalla": (30.9700, 31.1667),
    "zagazig": (30.5877, 31.5020), "damietta": (31.4165, 31.8133),
    "fayoum": (29.3084, 30.8428), "beni suef": (29.0661, 31.0994),
    "minya": (28.1099, 30.7503), "assiut": (27.1809, 31.1837),
    "sohag": (26.5569, 31.6948), "qena": (26.1551, 32.7160),
}

_lookup = {}
for canon, variants in CITY_CANONICAL.items():
    for v in variants:
        _lookup[v.strip().lower()] = canon


def normalize_city(raw):
    """Returns (canonical_name, matched_bool)."""
    if pd.isna(raw) or str(raw).strip() == "":
        return "Unmapped", False
    key = str(raw).strip().lower()
    if key in _lookup:
        return _lookup[key].title(), True
    match = difflib.get_close_matches(key, _lookup.keys(), n=1, cutoff=0.75)
    if match:
        return _lookup[match[0]].title(), True
    return str(raw).strip().title(), False  # kept as-is, flagged unmapped


def clean_data(df, col_map):
    """
    col_map: dict like {"date": "OrderDate", "city": "City", "product": "Item",
                         "amount": "Total", "returned": "Status"}
    Returns (cleaned_df, report_dict)
    """
    # Guard 1: if two logical fields were mapped to the same raw column
    # (e.g. user picked "Item Name" for both product and city by mistake),
    # fail with a clear message instead of a confusing downstream crash.
    picked = [v for v in col_map.values() if v]
    dupes = {c for c in picked if picked.count(c) > 1}
    if dupes:
        raise ValueError(
            f"The same column ({', '.join(dupes)}) was selected for more than one field. "
            f"Each field needs its own column."
        )

    rename_map = {v: k for k, v in col_map.items() if v}
    df = df.rename(columns=rename_map)

    # Guard 2: if the raw file itself has duplicate column names, pandas can
    # end up with two columns sharing the same label after rename, which
    # turns df["city"] into a DataFrame instead of a Series and breaks
    # everything downstream silently. Keep the first occurrence only.
    df = df.loc[:, ~df.columns.duplicated()].copy()

    report = {"total_rows": len(df)}

    for col in ["date", "city", "product", "amount"]:
        if col not in df.columns:
            df[col] = np.nan

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["date", "amount", "product"]).copy()
    report["dropped_rows"] = before - len(df)

    # city column defensively coerced to a plain string Series first —
    # covers cases where the source column came in as numeric, mixed
    # type, or (after Guard 2) still oddly shaped.
    city_series = df["city"]
    if isinstance(city_series, pd.DataFrame):
        city_series = city_series.iloc[:, 0]

    normalized = city_series.apply(normalize_city)
    df["city_clean"] = normalized.apply(lambda x: x[0])
    matched_flags = normalized.apply(lambda x: bool(x[1]))
    report["unmapped_cities"] = int((matched_flags == False).sum())  # noqa: E712

    if col_map.get("returned"):
        df["returned"] = df["returned"].astype(str).str.strip().str.lower().isin(
            ["1", "true", "yes", "returned", "y", "مرتجع", "نعم"]
        )
    else:
        df["returned"] = False

    report["clean_rows"] = len(df)
    return df, report
