# meddra_api.py (Cloud-Safe Version)

SYMPTOM_MAP = {
    "dizziness":        {"term": "Vertigo",                  "code": "10047340"},
    "nausea":           {"term": "Nausea",                   "code": "10028813"},
    "vomiting":         {"term": "Vomiting",                 "code": "10047700"},
    "headache":         {"term": "Headache",                 "code": "10019211"},
    "rash":             {"term": "Rash",                     "code": "10037844"},
    "itching":          {"term": "Pruritus",                 "code": "10037087"},
    "stomach pain":     {"term": "Abdominal pain",           "code": "10000081"},
    "chest pain":       {"term": "Chest pain",               "code": "10008479"},
    "muscle pain":      {"term": "Myalgia",                  "code": "10028411"},
    "weakness":         {"term": "Asthenia",                 "code": "10003549"},
    "insomnia":         {"term": "Insomnia",                 "code": "10022437"},
    "drowsiness":       {"term": "Somnolence",               "code": "10041349"},
    "hearing loss":     {"term": "Hearing impaired",         "code": "10019245"},
    "vision problem":   {"term": "Vision blurred",           "code": "10047531"},
    "tremor":           {"term": "Tremor",                   "code": "10044562"},
    "swelling":         {"term": "Angioedema",               "code": "10002424"},
    "difficulty breathing": {"term": "Dyspnoea",             "code": "10013968"},
    "high blood pressure":  {"term": "Hypertension",         "code": "10020772"},
    "diarrhea":         {"term": "Diarrhoea",                "code": "10012735"},
    "loss of appetite": {"term": "Decreased appetite",       "code": "10061428"},
    "loose motions":    {"term": "Diarrhoea",    "code": "10012735"},
    "loose motion":     {"term": "Diarrhoea",    "code": "10012735"},
    "stomach upset":    {"term": "Abdominal pain","code": "10000081"},
}

def lookup_symptom(symptom_text):
    """
    Takes a plain-English symptom description,
    returns the official MedDRA term and code using string matching.
    """
    symptom_lower = symptom_text.lower().strip()

    # Check for a direct or partial match
    for keyword, medical_data in SYMPTOM_MAP.items():
        if keyword in symptom_lower:
            return {
                "input_symptom": symptom_text,
                "meddra_term": medical_data["term"],
                "meddra_code": medical_data["code"],
                "match_found": True
            }

    # No match found — return as-is
    return {
        "input_symptom": symptom_text,
        "meddra_term": symptom_text.title(),
        "meddra_code": "UNKNOWN",
        "match_found": False
    }