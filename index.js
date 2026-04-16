const express = require("express");
const cors = require("cors");
const { exec } = require("child_process");
const fs = require("fs");
const path = require("path");
const PROJECT_ROOT = __dirname;
// Load .env from Python project so subprocesses inherit it
const dotenv = require("dotenv");
dotenv.config({ path: path.join(__dirname, ".env") });
const app = express();
app.use(cors());
app.use(express.json());

// ── Path to your Python project ──
// ── CLOUD-SAFE PATHING ──
// Since index.js and main.py are in the same root folder now:
const PYTHON_PROJECT = __dirname;
const ANALYTICS_PATH = __dirname;
const LEDGER_FILE = path.join(__dirname, "ledger", "ledger.db");
const Database = require("better-sqlite3");

// ── Load .env from Python project ──
dotenv.config({ path: path.join(PYTHON_PROJECT, ".env") });

// ── Helper: run a Python command ──
function runPython(command) {
  return new Promise((resolve, reject) => {
    const env = { ...process.env, PYTHONIOENCODING: "utf-8" };
    exec(command, {
      cwd: PYTHON_PROJECT,
      shell: true,
      timeout: 300000,
      maxBuffer: 1024 * 1024 * 10,
      env: env
    }, (error, stdout, stderr) => {
      console.log("--- STDOUT ---");
      console.log(stdout?.substring(0, 300));
      console.log("--- STDERR ---");
      console.log(stderr?.substring(0, 300));

      if (stdout && stdout.includes("MULTILINGUAL PHARMACOVIGILANCE")) {
        resolve({ stdout, stderr });
      } else if (error && !stdout) {
        reject({ error: error.message, stderr });
      } else {
        resolve({ stdout, stderr });
      }
    });
  });
}
// ── Helper: read ledger ──
// function readLedger() {
//   try {
//     if (!fs.existsSync(LEDGER_FILE)) return [];
//     const data = fs.readFileSync(LEDGER_FILE, "utf8");
//     return JSON.parse(data);
//   } catch (e) {
//     return [];
//   }
// }
function readLedger() {
  try {
    if (!fs.existsSync(LEDGER_FILE)) return [];
    const db = new Database(LEDGER_FILE, { readonly: true });
    
    // Enable WAL mode for reading too
    db.pragma("journal_mode = WAL");
    
    const rows = db.prepare(`
      SELECT timestamp, post_id, node, data
      FROM ledger
      ORDER BY id ASC
    `).all();
    
    db.close();
    
    return rows.map(row => ({
      timestamp: row.timestamp,
      post_id:   row.post_id,
      node:      row.node,
      data:      JSON.parse(row.data)
    }));
  } catch (e) {
    console.error("Ledger read error:", e.message);
    return [];
  }
}

// ─────────────────────────────────────────────
// ROUTE 1: Get ledger entries
// ─────────────────────────────────────────────
app.get("/api/ledger", (req, res) => {
  const ledger = readLedger();
  res.json(ledger);
});

// ─────────────────────────────────────────────
// ROUTE 2: Get all submitted ADR reports
// ─────────────────────────────────────────────
app.get("/api/reports", (req, res) => {
  const ledger = readLedger();

  // Only return node4_formatting entries (the full report)
  const allReports = ledger
    .filter((entry) => entry.node === "node4_formatting")
    .map((entry) => ({
      post_id: entry.post_id,
      timestamp: entry.timestamp,
      drug_name: entry.data.drug_name,
      symptom_raw: entry.data.symptom_raw,
      meddra_term: entry.data.meddra_term,
      meddra_code: entry.data.meddra_code,
      original_text: entry.data.original_text,
      report_version: entry.data.report_version,
      confidence:   entry.data.confidence,        // Retained
      review_flag:  entry.data.review_flag,       // Retained
    }));

  // Add the split logic for the frontend UI
  // If confidence is missing, we assume 90 (safe). You can also use the review_flag!
  const autoApproved = allReports.filter((r) => r.confidence >= 85 && r.review_flag !== true);
  const needsReview = allReports.filter((r) => r.confidence < 85 || r.review_flag === true);

  // Send them as two separate arrays so your React tabs work perfectly
  res.json({
      success: true,
      auto_approved: autoApproved,
      needs_review: needsReview
  });
});



// ─────────────────────────────────────────────
// ROUTE 2.5: Handle Human Review (Approve/Deny)
// ─────────────────────────────────────────────
app.post("/api/review/:post_id", (req, res) => {
  const { post_id } = req.params;
  const { action } = req.body; // "approve" or "deny"

  console.log(`[HITL] Human reviewed post ${post_id}. Action: ${action.toUpperCase()}`);

  // In a full production system, this is where you would execute a python script 
  // to append "node6_human_review" to your immutable SQLite ledger!
  // For now, if you are reading the JSON directly, you can append a mock ledger entry,
  // or trigger a backend function here to update the post's status.

  res.json({
    success: true,
    message: `Post ${post_id} was successfully ${action}d.`
  });
});



// ─────────────────────────────────────────────
// ROUTE 3: Get pipeline status per post
// ─────────────────────────────────────────────
app.get("/api/pipeline-status", (req, res) => {
  const ledger = readLedger();

  // Group by post_id
  const statusMap = {};
  ledger.forEach((entry) => {
    if (!statusMap[entry.post_id]) {
      statusMap[entry.post_id] = {
        post_id: entry.post_id,
        raw_text: entry.data.raw_text || entry.data.original_text || "",
        language: entry.data.language || "",
        nodes_completed: [],
        triage_decision: entry.data.triage_decision || "",
        drug_name: entry.data.drug_name || "",
        meddra_term: entry.data.meddra_term || "",
        status: "in_progress",
      };
    }
    statusMap[entry.post_id].nodes_completed.push(entry.node);

    // Pick up extra fields as they appear
    if (entry.data.triage_decision)
      statusMap[entry.post_id].triage_decision = entry.data.triage_decision;
    if (entry.data.drug_name)
      statusMap[entry.post_id].drug_name = entry.data.drug_name;
    if (entry.data.meddra_term)
      statusMap[entry.post_id].meddra_term = entry.data.meddra_term;
    if (entry.data.language)
      statusMap[entry.post_id].language = entry.data.language;
    if (entry.data.raw_text)
      statusMap[entry.post_id].raw_text = entry.data.raw_text;
    // ── Confidence and review flag ──
    if (entry.data.confidence !== undefined)
      statusMap[entry.post_id].confidence = entry.data.confidence;
    if (entry.data.review_flag)
      statusMap[entry.post_id].review_flag = entry.data.review_flag;

    // Mark complete if node5 done or discarded
    if (
      entry.node === "node5_dispatch" ||
      entry.data.triage_decision === "DISCARD"
    ) {
      statusMap[entry.post_id].status = "complete";
    }
  });

  res.json(Object.values(statusMap));
});

// ─────────────────────────────────────────────
// ROUTE 4: Run normal pipeline
// ─────────────────────────────────────────────
app.post("/api/run", async (req, res) => {
  try {
    const result = await runPython("python main.py web");
    const ledger = readLedger();
    console.log("✅ Ledger entries after run:", ledger.length);
    res.json({ success: true, output: result.stdout });
  } catch (e) {
    console.log("❌ Error:", e);
    res.status(500).json({ success: false, error: e.error });
  }
});

// ─────────────────────────────────────────────
// ROUTE 5: Simulate crash
// ─────────────────────────────────────────────
app.post("/api/crash", async (req, res) => {
  try {
    const result = await runPython("python main.py crash");
    res.json({ success: true, output: result.stdout });
  } catch (e) {
    res.status(500).json({ success: false, error: e.error });
  }
});

// ─────────────────────────────────────────────
// ROUTE 6: Recover from crash
// ─────────────────────────────────────────────
app.post("/api/recover", async (req, res) => {
  try {
    const result = await runPython("python main.py recover");
    res.json({ success: true, output: result.stdout });
  } catch (e) {
    res.status(500).json({ success: false, error: e.error });
  }
});

// ─────────────────────────────────────────────
// ROUTE 7: Analytics data
// ─────────────────────────────────────────────
app.get("/api/analytics", (req, res) => {
  const ledger = readLedger();

  // Language breakdown
  const languages = {};
  const drugs = {};
  const symptoms = {};
  let totalProcessed = 0;
  let totalDiscarded = 0;
  let totalSubmitted = 0;

  ledger.forEach((entry) => {
    if (entry.node === "node1_triage") {
      totalProcessed++;
      const lang = entry.data.language || "Unknown";
      languages[lang] = (languages[lang] || 0) + 1;
      if (entry.data.triage_decision === "DISCARD") totalDiscarded++;
    }
    if (entry.node === "node4_formatting") {
      totalSubmitted++;
      const drug = entry.data.drug_name || "Unknown";
      drugs[drug] = (drugs[drug] || 0) + 1;
      const symptom = entry.data.meddra_term || "Unknown";
      symptoms[symptom] = (symptoms[symptom] || 0) + 1;
    }
  });

  res.json({
    summary: { totalProcessed, totalSubmitted, totalDiscarded },
    languages: Object.entries(languages).map(([name, value]) => ({
      name,
      value,
    })),
    drugs: Object.entries(drugs).map(([name, value]) => ({ name, value })),
    symptoms: Object.entries(symptoms).map(([name, value]) => ({
      name,
      value,
    })),
  });
});


// ─────────────────────────────────────────────
// ROUTE 8: Download E2B XML Report
// ─────────────────────────────────────────────
app.get("/api/export-e2b/:post_id", (req, res) => {
  const postId = req.params.post_id;
  const ledger = readLedger();

  // Find the finalized formatting data for this specific post
  const reportEntry = ledger.find(
    (entry) => entry.post_id === postId && entry.node === "node4_formatting"
  );

  if (!reportEntry) {
    return res.status(404).send("Report not fully processed yet.");
  }

  // Extract the real data found by your AI pipeline
  const { drug_name, meddra_term, original_text } = reportEntry.data;
  
  // Generate timestamp like 20260408123000
  const timestamp = new Date().toISOString().replace(/[-:T.]/g, "").slice(0, 14);

  const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<ichicsr lang="en">
    <ichicsrmessageheader>
        <messagetype>ichicsr</messagetype>
        <messageformatversion>2.1</messageformatversion>
        <messageformatrelease>2.0</messageformatrelease>
        <messagenumb>MSG-${timestamp}</messagenumb>
        <messagesenderidentifier>KYRO-PV-SYSTEM</messagesenderidentifier>
        <messagereceiveridentifier>CDSCO-INDIA</messagereceiveridentifier>
        <messagedate>${timestamp}</messagedate>
    </ichicsrmessageheader>
    <safetyreport>
        <safetyreportversion>1</safetyreportversion>
        <safetyreportid>IN-KYRO-${postId}</safetyreportid>
        <primarysourcecountry>IN</primarysourcecountry>
        <occurcountry>IN</occurcountry>
        <patient>
            <patientinitials>PRIVACY_FILTERED</patientinitials>
            <reaction>
                <primarysourcereaction>${meddra_term || "Unknown"}</primarysourcereaction>
            </reaction>
            <drug>
                <medicinalproduct>${drug_name || "Unknown"}</medicinalproduct>
                <drugcharacterization>1</drugcharacterization>
            </drug>
        </patient>
        <summary>
            <narrativeincludeclinical>${original_text}</narrativeincludeclinical>
        </summary>
    </safetyreport>
</ichicsr>`;

  // Tell the browser to download this as an XML file
  res.setHeader("Content-Disposition", `attachment; filename=E2B_Report_${postId}.xml`);
  res.setHeader("Content-Type", "application/xml");
  res.send(xmlContent);
});






app.get("/api/signals/prr", (req, res) => {

  const scriptPath = path.join(ANALYTICS_PATH, "signal_engine.py");

  exec(`python "${scriptPath}"`, (err, stdout, stderr) => {

    if (err) {
      console.error(stderr);
      return res.status(500).json({
        error: "PRR analysis failed",
        details: stderr
      });
    }

    const lines = stdout.split("\n");

    const parsed = [];

    lines.forEach(line => {
      if (line.includes("|") && line.includes("Crocin")) {

        const parts = line.split("|").map(x => x.trim());

        parsed.push({
          drug: parts[1],
          symptom: parts[2],
          cases: parts[3],
          prr: parts[4],
          chi_square: parts[5],
          alert: parts[6]
        });
      }
    });

    res.json(parsed);

  });

});
app.get("/api/signals/trends", (req, res) => {

  const scriptPath = path.join(ANALYTICS_PATH, "trend_analyzer.py");

  exec(`python "${scriptPath}"`, (err, stdout, stderr) => {

    if (err) {
      console.error(stderr);
      return res.status(500).json({
        error: "Trend analysis failed",
        details: stderr
      });
    }

      const jsonStart = stdout.indexOf("[");
      const jsonEnd = stdout.lastIndexOf("]") + 1;

      if (jsonStart !== -1 && jsonEnd !== -1) {
        const jsonPart = stdout.slice(jsonStart, jsonEnd);
        return res.json(JSON.parse(jsonPart));
      }

      res.json([]);

  });

});

app.get("/api/signals/summary", (req, res) => {

  const scriptPath = path.join(
    ANALYTICS_PATH,
    "nodes",
    "node7_summary.py"
  );

  exec(`python "${scriptPath}"`, (err, stdout, stderr) => {

    if (err) {
      console.error(stderr);
      return res.status(500).json({
        error: "Summary generation failed",
        details: stderr
      });
    }

    res.json({ output: stdout });

  });

});
// ─────────────────────────────────────────────
// START SERVER
// ─────────────────────────────────────────────
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`\n🚀 Pharma API Server running on http://localhost:${PORT}`);
  console.log(`📁 Reading ledger from: ${LEDGER_FILE}`);
});