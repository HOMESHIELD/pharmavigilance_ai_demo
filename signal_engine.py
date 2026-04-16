import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
import numpy as np
from tabulate import tabulate


from scipy.stats import chi2_contingency

def chi_square(a,b,c,d):
    table = [[a,b],[c,d]]
    chi2, p, _, _ = chi2_contingency(table)
    return chi2

import sqlite3
import pandas as pd
import json

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ledger", "ledger.db")

def load_ledger_data(db_path=DB_PATH):

    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query(
        """
        SELECT post_id, node, data
        FROM ledger
        WHERE node IN ('node2_extraction', 'node3_standardization')
        """,
        conn
    )

    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["drug", "symptom"])

    node2 = df[df.node == "node2_extraction"].copy()
    node3 = df[df.node == "node3_standardization"].copy()

    node2["drug"] = node2["data"].apply(
        lambda x: json.loads(x).get("drug_name")
    )

    node3["symptom"] = node3["data"].apply(
        lambda x: json.loads(x).get("meddra_term")
    )

    merged = pd.merge(
        node2[["post_id", "drug"]],
        node3[["post_id", "symptom"]],
        on="post_id"
    )

    return merged

def calculate_signals(df):
    if df.empty:
        return "No data found in ledger."

    signals = []
    unique_drugs = df['drug'].unique()
    unique_symptoms = df['symptom'].unique()

    # Total reports in database
    total_n = len(df)

    for drug in unique_drugs:
        for symptom in unique_symptoms:
            # a: Specific Drug + Specific ADR
            a = len(df[(df['drug'] == drug) & (df['symptom'] == symptom)])
            
            if a < 2: continue # Skip if only 1 case (too low for a signal)

            # b: Specific Drug + Other ADRs
            b = len(df[(df['drug'] == drug) & (df['symptom'] != symptom)])
            
            # c: Other Drugs + Specific ADR
            c = len(df[(df['drug'] != drug) & (df['symptom'] == symptom)])
            
            # d: Other Drugs + Other ADRs
            d = len(df[(df['drug'] != drug) & (df['symptom'] != symptom)])

            # Avoid division by zero
            if (c + d) == 0 or (a + b) == 0 or c == 0:
                prr = 0
            else:
                # The PRR Formula
                prr = (a / (a + b)) / (c / (c + d))
            
            chi2_value = chi_square(a,b,c,d)    

            # Determine Signal Strength
            status = "🟢 NORMAL"
            if prr >= 2 and a >= 3 and chi2_value >= 4:
                status = "🔥 STRONG SIGNAL"
            elif prr >= 1.5: status = "🟡 MONITORING"

            signals.append({
                "Drug": drug,
                "Symptom": symptom,
                "Cases (a)": a,
                "PRR Score": round(prr, 2),
                "Chi-Square": round(chi2_value, 2),
                "Alert Level": status
            })

        result_df = pd.DataFrame(signals)

        if result_df.empty:
            print("⚠ No PRR signals detected yet (insufficient repeated ADR cases).")
            return result_df

        return result_df.sort_values(by="PRR Score", ascending=False)

if __name__ == "__main__":
    print("🧠 Analyzing Ledger for Safety Signals...")
    df_ledger = load_ledger_data()
    df_signals = calculate_signals(df_ledger)
    
    print("\n--- SAFETY SIGNAL REPORT ---")
    print(tabulate(df_signals, headers='keys', tablefmt='psql', showindex=False))