import sys
import os
import time 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.social_listener import fetch_posts
from ledger.ledger import clear_ledger, print_ledger
from nodes.pipeline import (
    node1_triage,
    node2_extraction,
    node3_standardization,
    node4_formatting,
    node5_dispatch
)
from tasks import process_social_media_post

# 👇 Added use_queue=False here
def run_pipeline(batch_size=10, crash_simulation=False, crash_at_post="post_005", use_queue=False):
    print("\n" + "="*55)
    print("   MULTILINGUAL PHARMACOVIGILANCE TRACKER")
    print("   Powered by Sarvam AI + Arya Ledger")
    if crash_simulation:
        print(" CRASH SIMULATION MODE ACTIVE")
    print("="*55)

    posts = fetch_posts(batch_size)
    print(f"\nFetched {len(posts)} posts from Social Listener\n")

    reports_submitted = 0
    reports_discarded = 0

    for post in posts:
        print(f"\n{'─'*50}")
        print(f"Processing: {post['id']} [{post['language']}]")
        print(f"Text: {post['text'][:60]}...")
        
        # 👇 ADDED THIS IF STATEMENT (Fixes the gray text!)
        if use_queue:
            process_social_media_post(post)
            continue  # Skips the code below ONLY if we are using the queue
        
        # ── CRASH SIMULATION ──
        # Simulates a server dying mid-pipeline at Node 3
        if crash_simulation and post["id"] == crash_at_post:
            print(f"\n   SIMULATED CRASH at Node 3 for {post['id']}!")
            print(f"  System going down... (Nodes 1 & 2 already saved to Ledger)")
            print(f"\n   Restart the pipeline to see crash recovery...\n")
            return  # Hard stop — like pulling the power cord

        # ── NODE 1: Triage ──
        triage = node1_triage(post)
        if triage["triage_decision"] == "DISCARD":
            reports_discarded += 1
            continue

        # ── NODE 2: Extraction ──
        extraction = node2_extraction(post["id"], post["text"])

        # Pass confidence from triage to extraction result
        extraction["confidence"] = triage.get("confidence", 50)
        
        # ── CRASH POINT ──
        # Crashes AFTER Node 2 but BEFORE Node 3 for the target post
        if crash_simulation and post["id"] == crash_at_post:
            print(f"\n   SIMULATED CRASH — Nodes 1 & 2 saved, Node 3 not yet run!")
            return

        # ── NODE 3: Standardization ──
        standardization = node3_standardization(
            post["id"],
            extraction["symptom_english"]
        )

        # ── NODE 4: Formatting ──
        formatted = node4_formatting(
            post["id"],
            extraction["drug_name"],
            extraction,
            standardization
        )

        # ── NODE 5: Dispatch ──
        node5_dispatch(post["id"], formatted)
        reports_submitted += 1

    print(f"\n{'='*55}")
    print(f"  Reports Submitted : {reports_submitted}")
    print(f"  Noise Discarded   : {reports_discarded}")
    print(f"  Total Processed   : {len(posts)}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

    if mode == "crash":
        print("\n STEP 1: Starting fresh pipeline — will crash at post_005...\n")
        clear_ledger()
        run_pipeline(batch_size=10, crash_simulation=True, crash_at_post="post_005")

    elif mode == "recover":
        print("\n STEP 2: Restarting pipeline — watch ledger skip completed nodes...\n")
        run_pipeline(batch_size=10, crash_simulation=False)
        print_ledger()

    elif mode == "web":
        clear_ledger()
        # 👇 Added use_queue=True here so the web UI uses Celery!
        run_pipeline(batch_size=30, crash_simulation=False, use_queue=True)

    else:
        # Normal terminal run
        clear_ledger()
        run_pipeline(batch_size=10)
        print_ledger()