import sys
import os

# Ensure Python can find your nodes folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import ALL your pipeline nodes
from nodes.pipeline import (
    node1_triage,
    node2_extraction,
    node3_standardization,
    node4_formatting,
    node5_dispatch
)

def process_social_media_post(post, crash_simulation=False, crash_at_post="post_005"):
    print(f"\n📥 [PIPELINE WORKER] Processing post '{post['id']}'...")
    
    # ── CRASH SIMULATION (Pre-Node 3 Check) ──
    if crash_simulation and post["id"] == crash_at_post:
        print(f"\n 💥 SIMULATED CRASH at Node 3 for {post['id']}!")
        print(f" System going down... (Nodes 1 & 2 already saved to Ledger)")
        return {'post_id': post['id'], 'status': 'crashed_intentionally'}

    # ── NODE 1: Triage ──
    triage = node1_triage(post)
    if triage["triage_decision"] == "DISCARD":
        print(f"🗑️ {post['id']} discarded as noise.")
        return {'post_id': post['id'], 'status': 'discarded'}

    # ── NODE 2: Extraction ──
    extraction = node2_extraction(post["id"], post["text"])
    extraction["confidence"] = triage.get("confidence", 50)

    # ── CRASH POINT (Post-Node 2 Check) ──
    if crash_simulation and post["id"] == crash_at_post:
        print(f"\n 💥 SIMULATED CRASH — Nodes 1 & 2 saved, Node 3 not yet run!")
        return {'post_id': post['id'], 'status': 'crashed_intentionally'}

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

    print(f"✅ [PIPELINE WORKER] Finished full pipeline for '{post['id']}'.")
    return {'post_id': post['id'], 'status': 'completed'}