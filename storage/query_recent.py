import argparse
import sqlite3


def main():
    parser = argparse.ArgumentParser(description="Query recent telemetry rows")
    parser.add_argument("--db", default="/data/telemetry.db", help="Path to SQLite database")
    parser.add_argument("--minutes", type=int, default=15, help="Lookback window in minutes")
    parser.add_argument("--limit", type=int, default=100, help="Maximum rows to return")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_timestamp, actual_temp, predicted_temp, predicted_for, threshold, trend
        FROM telemetry
        WHERE ingested_at >= datetime('now', ?)
        ORDER BY id DESC
        LIMIT ?
        """,
        (f"-{args.minutes} minutes", args.limit),
    )

    rows = cur.fetchall()
    print(
        "source_timestamp,actual_temp,predicted_temp,predicted_for,threshold,trend"
    )
    for row in rows:
        print(
            f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}"
        )

    conn.close()


if __name__ == "__main__":
    main()
