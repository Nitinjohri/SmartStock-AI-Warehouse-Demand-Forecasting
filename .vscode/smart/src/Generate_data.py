import pandas as pd
import numpy as np
from datetime import datetime, timedelta

SKUS = [
    {"id": "SKU-001", "name": "Wireless Headphones", "base_demand": 45, "lead_time_days": 7},
    {"id": "SKU-002", "name": "USB-C Cables",        "base_demand": 120, "lead_time_days": 5},
    {"id": "SKU-003", "name": "Laptop Stands",       "base_demand": 30, "lead_time_days": 10},
    {"id": "SKU-004", "name": "Mechanical Keyboards", "base_demand": 20, "lead_time_days": 14},
    {"id": "SKU-005", "name": "Webcams",              "base_demand": 55, "lead_time_days": 8},
]

PROMOTIONS = [
    {"start": "2023-11-24", "end": "2023-11-27", "multiplier": 3.2},  # Black Friday
    {"start": "2023-12-23", "end": "2023-12-26", "multiplier": 2.1},  # Christmas
    {"start": "2024-02-14", "end": "2024-02-14", "multiplier": 1.5},  # Valentine's
    {"start": "2024-07-04", "end": "2024-07-04", "multiplier": 1.4},  # July 4th
    {"start": "2024-11-29", "end": "2024-12-02", "multiplier": 3.5},  # Black Friday 2024
]


def is_promotion(date: datetime) -> float:
    for promo in PROMOTIONS:
        start = datetime.strptime(promo["start"], "%Y-%m-%d")
        end   = datetime.strptime(promo["end"],   "%Y-%m-%d")
        if start <= date <= end:
            return promo["multiplier"]
    return 1.0


def generate_sku_sales(sku: dict, start: str = "2022-01-01", end: str = "2024-12-31") -> pd.DataFrame:
    dates = pd.date_range(start=start, end=end, freq="D")
    records = []

    for i, date in enumerate(dates):
        # Long-term upward trend
        trend = 1 + (i / len(dates)) * 0.3

        # Weekly seasonality: Mon-Fri higher, Sat-Sun lower
        dow_factor = {0: 1.2, 1: 1.1, 2: 1.0, 3: 1.1, 4: 1.3, 5: 0.6, 6: 0.4}
        weekly = dow_factor[date.dayofweek]

        # Yearly seasonality: Q4 peak, Q1 dip
        month_factor = {1: 0.8, 2: 0.85, 3: 0.9, 4: 0.95, 5: 1.0, 6: 1.0,
                        7: 0.95, 8: 1.0, 9: 1.05, 10: 1.1, 11: 1.4, 12: 1.5}
        yearly = month_factor[date.month]

        # Promotion boost
        promo = is_promotion(date.to_pydatetime())

        # Gaussian noise
        noise = np.random.normal(1.0, 0.12)

        qty = int(max(0, sku["base_demand"] * trend * weekly * yearly * promo * noise))

        records.append({
            "date":          date.strftime("%Y-%m-%d"),
            "sku_id":        sku["id"],
            "sku_name":      sku["name"],
            "quantity_sold": qty,
            "lead_time_days": sku["lead_time_days"],
            "is_promotion":  int(promo > 1.0),
        })

    return pd.DataFrame(records)


def generate_all(output_path: str = "data/sales_data.csv") -> pd.DataFrame:
    np.random.seed(42)
    frames = [generate_sku_sales(sku) for sku in SKUS]
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df):,} rows → {output_path}")
    return df


if __name__ == "__main__":
    generate_all()