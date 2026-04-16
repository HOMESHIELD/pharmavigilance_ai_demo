import sys
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
import warnings

# 🔥 NEW: Tell Python to look in the parent directory for modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import your actual Node 1 logic!
from nodes.pipeline import node1_triage  # Adjust import path if needed based on your folder structure

warnings.filterwarnings("ignore")

def evaluate_pipeline():
    print("🚀 Starting Multilingual ADR Detection Evaluation...\n")
    
    df = pd.read_csv("evaluation_dataset.csv")
    y_true = df["true_label"].tolist()
    y_pred = []

    print("Processing posts through Node 1 (Sarvam AI Triage)...")
    for index, row in df.iterrows():
        # Create a mock "post" dictionary to feed Node 1
        mock_post = {
            "id": f"eval_{index}",
            "text": row["text"],
            "language": "mixed",
            "platform": "evaluation"
        }
        
        # Run it through your pipeline
        result = node1_triage(mock_post)
        
        if result["is_adr"]:
            y_pred.append(1)
        else:
            y_pred.append(0)

    print("\n" + "="*60)
    print("📊 MODEL EVALUATION METRICS (SMM4H + Indian Languages)")
    print("="*60)
    
    # Calculate detailed metrics
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary')
    
    print(f"Overall F1-Score: {f1:.4f}")
    print(f"Precision:        {precision:.4f} (How many detected ADRs were real)")
    print(f"Recall:           {recall:.4f} (How many real ADRs were successfully caught)")
    print("\n* Note on Recall: As per pharmacovigilance standards, missing a real ADR is dangerous, so a high recall is prioritized.")
    print("-" * 60)
    
    report = classification_report(y_true, y_pred, target_names=["No ADE (0)", "Has ADE (1)"])
    print(report)

    # Generate Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Reds", 
                xticklabels=["Predicted: No", "Predicted: Yes"], 
                yticklabels=["Actual: No", "Actual: Yes"])
    
    plt.title("ADR Detection Confusion Matrix (Mixed Languages)")
    plt.tight_layout()
    plt.savefig("adr_evaluation.png", dpi=300)
    
    print("\n✅ Evaluation complete! Metrics printed and 'adr_evaluation.png' saved.")

if __name__ == "__main__":
    evaluate_pipeline()