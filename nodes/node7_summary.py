import sys
sys.stdout.reconfigure(encoding='utf-8')

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from signal_engine import calculate_signals, load_ledger_data
from trend_analyzer import analyze_trends, load_trend_data
# Load API key
load_dotenv()

client = OpenAI(
    base_url="https://api.sarvam.ai/v1",
    api_key=os.getenv("SARVAM_API_KEY")
)

def generate_executive_summary(signal_data, trend_data):
    print("✍️  Node 7: Synthesizing medical insights...")

    if isinstance(signal_data, str) or signal_data.empty:
        signal_brief = [{"message": "No statistical PRR safety signals detected."}]
    else:
        signal_brief = signal_data.head(3).to_dict(orient='records')

    if isinstance(trend_data, str) or trend_data.empty:
        trend_brief = [{"message": "No emerging ADR trends detected."}]
    else:
        trend_brief = trend_data.head(3).to_dict(orient='records')

    prompt = f"""
    You are a Senior Pharmacovigilance Officer. Summarize the following safety data into a 
    professional executive briefing for the Drug Safety Board.
    
    TOP SIGNALS (PRR Analysis):
    {json.dumps(signal_brief, indent=2)}

    EMERGING TRENDS (Velocity Analysis):
    {json.dumps(trend_brief, indent=2)}

    INSTRUCTIONS:
    - Write a 3-paragraph pharmacovigilance signal detection executive briefing suitable for CDSCO or WHO-style safety monitoring review.
    - Paragraph 1: High-level overview of the most critical risks.
    - Paragraph 2: Specific drug-symptom pairs that require immediate clinical review.
    - Paragraph 3: Recommendation for the next 7 days (e.g., 'Increase monitoring', 'Draft physician alert').
    - Tone: Clinical, urgent but calm, and professional.
    """

    try:
        response = client.chat.completions.create(
            model="sarvam-m", # Using sarvam-m for high-quality reasoning
            messages=[
                {"role": "system", "content": "You are a medical writing expert in Pharmacovigilance."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        import re

        summary = response.choices[0].message.content

        # Remove internal reasoning blocks if present
        summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL | re.IGNORECASE).strip()

        return summary

    except Exception as e:
        return f"Error generating summary: {e}"

if __name__ == "__main__":
    # --- Integration Logic ---
    # In a real run, you'd import your previous scripts
    from signal_engine import calculate_signals, load_ledger_data
    from trend_analyzer import analyze_trends, load_trend_data

    # 1. Get the Math
    signals = calculate_signals(load_ledger_data())
    trends  = analyze_trends(load_trend_data())

    # 2. Get the AI Narrative
    executive_brief = generate_executive_summary(signals, trends)

    print("\n" + "="*50)
    print("🏥 OFFICIAL DRUG SAFETY EXECUTIVE BRIEF")
    print("="*50)
    print(executive_brief)
    print("="*50)