import sys
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.meddra_api import lookup_symptom
from tools.cdsco_api import submit_report
from ledger.ledger import write_entry, get_completed_node

# ── Initialize Sarvam client ──
client = OpenAI(
    base_url="https://api.sarvam.ai/v1",
    api_key=os.getenv("SARVAM_API_KEY")
)

# ─────────────────────────────────────────────
# NODE 1 — TRIAGE (Sarvam-30B)
# Real AI decides if post is an ADR or noise
# ─────────────────────────────────────────────

def node1_triage(post):
    post_id   = post["id"]
    node_name = "node1_triage"

    # Check ledger — already done?
    cached = get_completed_node(post_id, node_name)
    if cached:
        print(f"  [Node 1] Skipping {post_id} — already in ledger")
        return cached

    print(f"  [Node 1] Calling sarvam-m for triage...")

    try:
        response = client.chat.completions.create(
    model="sarvam-m",
    messages=[
        {
            "role": "system",
            "content": (
               "You are a pharmacovigilance triage classifier. "
                "Analyze the text and respond in EXACTLY this format:\n"
                "DECISION: YES or NO\n"
                "CONFIDENCE: a number from 0 to 100\n"
                "Where DECISION is YES if the text mentions BOTH a medicine name "
                "AND a negative physical symptom or side effect, NO otherwise. "
                "CONFIDENCE is how certain you are — 90-100 means very clear ADR, "
                "60-89 means probable, below 60 means uncertain. "
                "Examples:\n"
                "Text: 'Maine Crocin li aur chakkar aa raha hai' → DECISION: YES, CONFIDENCE: 95\n"
                "Text: 'Dolo 650 se koi side effect nahi' → DECISION: NO, CONFIDENCE: 98\n"
                "Text: 'Aaj mausam achha hai' → DECISION: NO, CONFIDENCE: 99\n"
                "Reply in EXACTLY this format, nothing else:\n"
                "DECISION: YES\n"
                "CONFIDENCE: 90"
            )
        },
        {
            "role": "user",
            "content": f"Classify this text: {post['text']}"
        }
    ],
    max_tokens=500,
    temperature=0
)
        import re
        raw = response.choices[0].message.content.strip()
        print(f"  [DEBUG Node1] Raw response: {repr(raw[:100])}")

        # Strip <think> tags
        clean = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL|re.IGNORECASE)
        clean = re.sub(r'<think>.*', '', clean, flags=re.DOTALL|re.IGNORECASE)
        clean = clean.strip()
        print(f"  [DEBUG Node1] Clean response: {repr(clean[:100])}")

        # Parse DECISION and CONFIDENCE
        is_adr = False
        confidence = 50  # default

        for line in clean.split("\n"):
            line = line.strip()
            if line.startswith("DECISION:"):
                decision = line.replace("DECISION:", "").strip().upper()
                is_adr = "YES" in decision and "NO" not in decision
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(re.search(r'\d+', line).group())
                    confidence = max(0, min(100, confidence))  # clamp 0-100
                except:
                    confidence = 50

        # If parsing failed (think block cut off), use fallback
        if clean == '' or "DECISION" not in clean.upper():
            text = post["text"].lower()
            false_positives = [
                "koi side effect nahi", "no side effect", "side effect nahi",
                "nahi hua", "theek ho gaya", "theek ho", "best medicine", "bilkul theek"
            ]
            has_false_positive = any(fp in text for fp in false_positives)

            if has_false_positive:
                is_adr = False
                confidence = 95
            elif "YES" in raw.upper():
                is_adr = True
                confidence = 60  # uncertain since think block was cut off
            elif "NO" in raw.upper():
                is_adr = False
                confidence = 60
            else:
                drugs = ["crocin","dolo","paracetamol","ibuprofen","azithromycin",
                        "amoxicillin","metformin","aspirin","cetirizine","omeprazole",
                        "pantoprazole","atorvastatin","ciplox"]
                symptoms = ["chakkar","ulti","dard","pain","rash","nausea","vomit",
                            "itch","swelling","headache","weakness","motions","kharab",
                            "வலி","சொறி","குமட்டல்","വേദന","ഓക്കാനം","തലവേദന"]
                is_adr = (any(d in text for d in drugs) and
                          any(s in text for s in symptoms) and
                          not has_false_positive)
                confidence = 55  # keyword-based, lower confidence

        else:
            # Clean has YES or NO — use it directly
            is_adr = "YES" in clean and "NO" not in clean[:10]
        # answer = response.choices[0].message.content.strip().upper()
        # print(f"  [DEBUG Node1] Raw response: {repr(answer)}")  # ADD THIS

        # is_adr = "YES" in answer
        
        # false_positives = [
                #         "koi side effect nahi", "no side effect",
                #         "side effect nahi", "nahi hua", "theek ho gaya",
                #         "best medicine", "bilkul theek", "no problem"]

    except Exception as e:
        print(f"  [Node 1] ⚠️  Sarvam API error: {e} — falling back to keyword check")
        # Fallback to keyword matching if API fails
        text = post["text"].lower()
        drugs    = ["crocin","dolo","paracetamol","ibuprofen","azithromycin",
                    "amoxicillin","metformin","aspirin","cetirizine","omeprazole",
                    "pantoprazole","atorvastatin","ciplox"]
        symptoms = ["chakkar","ulti","dard","pain","rash","nausea","vomit",
                    "itch","swelling","headache","weakness","வலி","சொறி",
                    "குமட்டல்","വേദന","ഓക്കാനം","തലവേദന"]
        false_positives = [
        "koi side effect nahi", "no side effect", "bilkul theek",
        "side effect nahi", "nahi hua", "theek ho gaya", "best medicine"]
        drug_found    = any(d in text for d in drugs)
        symptom_found = any(s in text for s in symptoms)
        no_false      = not any(fp in text for fp in false_positives)
        is_adr        = drug_found and symptom_found and no_false

    result = {
        "post_id":         post_id,
        "raw_text":        post["text"],
        "language":        post["language"],
        "platform":        post["platform"],
        "is_adr":          is_adr,
        "confidence":      confidence,
        "triage_decision": "PROCEED" if is_adr else "DISCARD"
    }

    write_entry(post_id, node_name, result)
    status = "✅ ADR DETECTED" if is_adr else "🗑️  NOISE — discarding"
    print(f"  [Node 1] {post_id} → {status} (confidence: {confidence}%)")
    return result


# ─────────────────────────────────────────────
# NODE 2 — TRANSLATION & EXTRACTION (Sarvam-105B)
# Real AI extracts drug + symptom from any language
# ─────────────────────────────────────────────

def node2_extraction(post_id, raw_text):
    node_name = "node2_extraction"

    cached = get_completed_node(post_id, node_name)
    if cached:
        print(f"  [Node 2] Skipping {post_id} — already in ledger")
        return cached

    print(f"  [Node 2] Calling Sarvam-105B for extraction...")

    drug_name       = "Unknown Drug"
    symptom_english = "Unknown Symptom"

    try:
        response = client.chat.completions.create(
            model="sarvam-m",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a multilingual medical entity extractor. "
                        "The user will give you a social media post in any Indian language "
                        "(Hindi, Tamil, Malayalam, Hinglish, or mixed). "
                        "You MUST extract BOTH the drug/medicine name AND the symptom. "
                        "Drug names are often brand names like Crocin, Dolo, Paracetamol, "
                        "Ibuprofen, Azithromycin, Amoxicillin, Metformin, Aspirin, "
                        "Cetirizine, Omeprazole, Atorvastatin, Ciplox. "
                        "Respond in EXACTLY this format with no extra text:\n"
                        "DRUG: <drug name>\n"
                        "SYMPTOM: <symptom in plain English>\n"
                        "Example response:\n"
                        "DRUG: Crocin\n"
                        "SYMPTOM: dizziness\n"
                        "If you truly cannot find either, write UNKNOWN."
                    )
                },
                {
                    "role": "user",
                    "content": f"Post: {raw_text}"
                }
            ],
            max_tokens=1024,
            temperature=0
        )

        import re
        content = response.choices[0].message.content.strip()

        # Strip <think> tags
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL|re.IGNORECASE)
        content = re.sub(r'<think>.*', '', content, flags=re.DOTALL|re.IGNORECASE)
        content = content.strip()

        # Parse DRUG and SYMPTOM — ONE parse loop only
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("DRUG:"):
                drug_name = line.replace("DRUG:", "").strip()
            elif line.startswith("SYMPTOM:"):
                symptom_english = line.replace("SYMPTOM:", "").strip()

    except Exception as e:
        print(f"  [Node 2] Sarvam error: {e}")

    # ── Keyword fallback if Sarvam returned Unknown ──
    # This runs ALWAYS after try/except if values are still Unknown
    if drug_name == "Unknown Drug" or symptom_english == "Unknown Symptom":
        print(f"  [Node 2] Using keyword fallback...")
        drug_map = {
            "crocin":"Crocin 650","dolo":"Dolo 650","paracetamol":"Paracetamol",
            "ibuprofen":"Ibuprofen","azithromycin":"Azithromycin",
            "amoxicillin":"Amoxicillin","metformin":"Metformin",
            "aspirin":"Aspirin","cetirizine":"Cetirizine",
            "omeprazole":"Omeprazole","pantoprazole":"Pantoprazole",
            "atorvastatin":"Atorvastatin","ciplox":"Ciplox"
        }
        symptom_map = {
            "നെഞ്ച":"chest pain",     # chest in Malayalam
            "വിറയ്":"tremor",          # trembling
            "chest":"chest pain",
            "chakkar":"dizziness","ulti":"vomiting",
            "dard":"pain","rash":"rash","itch":"itching","motions":"diarrhea",
            "kharab":"stomach pain","weakness":"weakness","neend":"drowsiness",
            "വേദന":"pain","ഓക്കാനം":"nausea","തലവേദന":"headache",
            "വീർ":"swelling","ശ്വാസം":"difficulty breathing"
        }
        text_lower = raw_text.lower()
        if drug_name == "Unknown Drug":
            drug_name = next((v for k,v in drug_map.items() if k in text_lower), "Unknown Drug")
        if symptom_english == "Unknown Symptom":
            symptom_english = next((v for k,v in symptom_map.items() if k in text_lower), "Unknown Symptom")

    result = {
        "post_id":         post_id,
        "drug_name":       drug_name,
        "symptom_english": symptom_english,
        "original_text":   raw_text
    }

    write_entry(post_id, node_name, result)
    print(f"  [Node 2] {post_id} → Drug: {drug_name} | Symptom: {symptom_english}")
    return result

# ─────────────────────────────────────────────
# NODE 3 — MEDICAL STANDARDIZATION
# Maps plain English symptom → MedDRA code
# ─────────────────────────────────────────────

def node3_standardization(post_id, symptom_english):
    node_name = "node3_standardization"

    cached = get_completed_node(post_id, node_name)
    if cached:
        print(f"  [Node 3] Skipping {post_id} — already in ledger")
        return cached

    meddra_result = lookup_symptom(symptom_english)

    result = {
        "post_id":     post_id,
        "symptom_raw": symptom_english,
        "meddra_term": meddra_result["meddra_term"],
        "meddra_code": meddra_result["meddra_code"],
        "match_found": meddra_result["match_found"]
    }

    write_entry(post_id, node_name, result)
    print(f"  [Node 3] {post_id} → MedDRA: {meddra_result['meddra_term']} [{meddra_result['meddra_code']}]")
    return result


# ─────────────────────────────────────────────
# NODE 4 — COMPLIANCE FORMATTING
# ─────────────────────────────────────────────

def node4_formatting(post_id, drug_name, node2_data, node3_data):
    node_name = "node4_formatting"

    cached = get_completed_node(post_id, node_name)
    if cached:
        print(f"  [Node 4] Skipping {post_id} — already in ledger")
        return cached

    # Flag for human review if confidence below 75
    confidence = node2_data.get("confidence",
                  # get from triage via ledger
                  50)

    result = {
        "post_id":        post_id,
        "drug_name":      drug_name,
        "symptom_raw":    node3_data["symptom_raw"],
        "meddra_term":    node3_data["meddra_term"],
        "meddra_code":    node3_data["meddra_code"],
        "original_text":  node2_data["original_text"],
        "report_version": "CDSCO-ADR-v2.1",
        "source":         "Multilingual Social Listener",
        "confidence":     confidence,
        "review_flag":    "HUMAN_REVIEW" if confidence < 75 else "AUTO_APPROVED"
    }

    
    write_entry(post_id, node_name, result)
    print(f"  [Node 4] {post_id} → Compliance JSON built ✅ [{result['review_flag']}]")

    return result


# ─────────────────────────────────────────────
# NODE 5 — DISPATCH
# ─────────────────────────────────────────────

def node5_dispatch(post_id, formatted_payload):
    node_name = "node5_dispatch"

    cached = get_completed_node(post_id, node_name)
    if cached:
        print(f"  [Node 5] Skipping {post_id} — already in ledger")
        return cached

    receipt = submit_report(formatted_payload)

    result = {
        "post_id":      post_id,
        "status":       receipt["status"],
        "reference_id": receipt["reference_id"],
        "submitted_at": receipt["submitted_at"]
    }

    write_entry(post_id, node_name, result)
    print(f"  [Node 5] {post_id} → Submitted! Ref: {receipt['reference_id']} ✅")
    return result






