import datetime
import os

def generate_e2b_xml(post_id, drug_name, reaction_text, raw_text):
    # Generate current timestamp for the report
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    # ICH E2B Regulatory XML Template
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<ichicsr lang="en">
    <ichicsrmessageheader>
        <messagetype>ichicsr</messagetype>
        <messageformatversion>2.1</messageformatversion>
        <messageformatrelease>2.0</messageformatrelease>
        <messagenumb>MSG-{timestamp}</messagenumb>
        <messagesenderidentifier>KYRO-PV-SYSTEM</messagesenderidentifier>
        <messagereceiveridentifier>CDSCO-INDIA</messagereceiveridentifier>
        <messagedate>{timestamp}</messagedate>
    </ichicsrmessageheader>
    <safetyreport>
        <safetyreportversion>1</safetyreportversion>
        <safetyreportid>IN-KYRO-{post_id}</safetyreportid>
        <primarysourcecountry>IN</primarysourcecountry>
        <occurcountry>IN</occurcountry>
        <patient>
            <patientinitials>PRIVACY_FILTERED</patientinitials>
            <reaction>
                <primarysourcereaction>{reaction_text}</primarysourcereaction>
            </reaction>
            <drug>
                <medicinalproduct>{drug_name}</medicinalproduct>
                <drugcharacterization>1</drugcharacterization>
            </drug>
        </patient>
        <summary>
            <narrativeincludeclinical>{raw_text}</narrativeincludeclinical>
        </summary>
    </safetyreport>
</ichicsr>
"""
    # Save the file to an "exports" folder
    os.makedirs("exports", exist_ok=True)
    filename = os.path.join("exports", f"E2B_Report_{post_id}.xml")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_content)
    
    print(f"✅ Regulatory E2B XML Report generated successfully: {filename}")
    return filename

if __name__ == "__main__":
    print("🚀 Simulating E2B Report Generation for Post 901...")
    
    # In a full run, these variables would be pulled from your SQLite ledger
    generate_e2b_xml(
        post_id="post_901",
        drug_name="crocin",
        reaction_text="dizziness",
        raw_text="Took crocin and feeling very dizzy."
    )