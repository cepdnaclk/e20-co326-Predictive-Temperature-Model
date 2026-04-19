import argparse
import csv
import os
import sqlite3
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Export telemetry to CSV")
    parser.add_argument("--db", default="/data/telemetry.db", help="Path to SQLite database")
    parser.add_argument("--minutes", type=int, default=60, help="Lookback window in minutes")
    parser.add_argument(
        "--out",
        default=None,
        help="Output CSV path. Default: /data/exports/telemetry_<timestamp>.csv",
    )
    args = parser.parse_args()

    if args.out is None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_path = f"/data/exports/telemetry_{ts}.csv"
    else:
        out_path = args.out

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_timestamp, actual_temp, predicted_temp, predicted_for,
               prediction_horizon_sec, threshold, trend, trend_slope,
               is_anomaly, window_avg, ingested_at
        FROM telemetry
        WHERE ingested_at >= datetime('now', ?)
        ORDER BY id ASC
        """,
        (f"-{args.minutes} minutes",),
    )

    rows = cur.fetchall()
    headers = [
        "source_timestamp",
        "actual_temp",
        "predicted_temp",
        "predicted_for",
        "prediction_horizon_sec",
        "threshold",
        "trend",
        "trend_slope",
        "is_anomaly",
        "window_avg",
        "ingested_at",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    conn.close()
    print(f"exported_rows={len(rows)}")
    print(f"csv_path={out_path}")


if __name__ == "__main__":
    main()
