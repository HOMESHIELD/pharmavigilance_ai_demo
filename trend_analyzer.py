import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
from datetime import datetime, timedelta
from tabulate import tabulate

import sqlite3
import pandas as pd
import json
from datetime import datetime

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ledger", "ledger.db")

def load_trend_data(db_path=DB_PATH):

    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query(
        """
        SELECT timestamp, post_id, node, data
        FROM ledger
        WHERE node IN ('node2_extraction', 'node3_standardization')
        """,
        conn
    )

    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["date", "drug", "symptom"])

    node2 = df[df.node == "node2_extraction"].copy()
    node3 = df[df.node == "node3_standardization"].copy()

    node2["drug"] = node2["data"].apply(
        lambda x: json.loads(x).get("drug_name")
    )

    node3["symptom"] = node3["data"].apply(
        lambda x: json.loads(x).get("meddra_term")
    )

    merged = pd.merge(
        node2[["post_id", "timestamp", "drug"]],
        node3[["post_id", "symptom"]],
        on="post_id"
    )

    merged["date"] = pd.to_datetime(merged["timestamp"])

    return merged[["date", "drug", "symptom"]]

def analyze_trends(df, days_window=7):
    if df.empty: return "No data."

    # 1. Define Windows
    now = datetime.now()
    threshold = now - timedelta(days=3)
    
    current_period = df[df['date'] >= threshold]
    baseline_period = df[df['date'] < threshold]

    trends = []
    # Analyze by Drug-Symptom Pairs
    pairs = df.groupby(['drug', 'symptom']).size().index

    for drug, symptom in pairs:
        # Counts
        count_now = len(current_period[(current_period['drug'] == drug) & (current_period['symptom'] == symptom)])
        count_base = len(baseline_period[(baseline_period['drug'] == drug) & (baseline_period['symptom'] == symptom)])
        
        # Calculate Velocity (Growth)
        if count_base == 0:
            velocity = 100.0 if count_now > 0 else 0.0
        else:
            velocity = ((count_now - count_base) / count_base) * 100
                # Categorize
        if count_now > 0 and count_base == 0:
            status = "🆕 EMERGING"
        elif velocity > 50:
            status = "📈 RISING FAST"
        elif velocity < -20:
            status = "📉 DECLINING"
        else:
            status = "🔄 STABLE"

        trends.append({
            "Drug": drug,
            "Symptom": symptom,
            "Recent (7d)": count_now,
            "Historical": count_base,
            "Velocity %": f"{velocity:+.1f}%",
            "Trend Status": status
        })

    return pd.DataFrame(trends).sort_values(by=["Trend Status", "Recent (7d)"], ascending=False)

if __name__ == "__main__":
    print("🕒 Analyzing Safety Trends and Velocity...")

    df_ledger = load_trend_data()

    df_trends = analyze_trends(df_ledger)

    print("\n--- PHARMACOVIGILANCE TREND REPORT ---")

    if isinstance(df_trends, str):
        print(df_trends)
    else:
        print(json.dumps(df_trends.to_dict(orient="records")))