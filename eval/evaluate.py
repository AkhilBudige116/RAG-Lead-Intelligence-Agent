import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List
from collections import defaultdict
from app.db.session import SessionLocal
from app.ingestion.parser import ParsedEmailData
from app.extraction.extractor import LeadExtractor
from app.rag.retriever import SectorRetriever
from app.classification.engine import SectorClassifier
from app.dedup.detector import detect_duplicates


def run_evaluation(
    data_path: str = "eval/labelled_data/evaluation_dataset.json",
    split_target: str = "test",
    min_accuracy: float = 0.80
) -> Dict[str, Any]:
    print(f"\n========================================================")
    print(f"  RAG LEAD SEGREGATION AGENT - EVALUATION FRAMEWORK    ")
    print(f"========================================================")
    print(f"Loading labelled dataset from: {data_path}")

    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}")
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        dataset: List[Dict[str, Any]] = json.load(f)

    # Filter by split
    if split_target != "all":
        eval_items = [d for d in dataset if d.get("split") == split_target]
    else:
        eval_items = dataset

    print(f"Total samples: {len(dataset)} | Evaluating split: '{split_target}' ({len(eval_items)} emails)")

    db = SessionLocal()
    extractor = LeadExtractor()
    retriever = SectorRetriever()
    classifier = SectorClassifier()

    # Metrics accumulators
    total_samples = len(eval_items)
    correct_classifications = 0
    needs_review_count = 0
    review_suggestion_correct = 0

    company_name_matches = 0
    email_matches = 0
    phone_found = 0
    website_found = 0

    per_sector_tp = defaultdict(int)
    per_sector_fp = defaultdict(int)
    per_sector_fn = defaultdict(int)
    confusion_matrix = defaultdict(lambda: defaultdict(int))

    dup_cases_count = 0
    dup_detected_count = 0

    start_total_time = time.time()

    for idx, item in enumerate(eval_items):
        t0 = time.time()
        # Parse into ParsedEmailData
        email_data = ParsedEmailData(
            sender_name=item.get("sender_name"),
            sender_email=item.get("sender_email"),
            subject=item.get("subject"),
            body=item.get("body"),
            signature=item.get("signature"),
            evidence_sources=["body", "signature"] if item.get("signature") else ["body"]
        )

        # 1. Extraction
        lead = extractor.extract(email_data)

        # Check Extraction Accuracies
        gt_company = item.get("ground_truth_company")
        if (gt_company is None and lead.company_name is None) or (
            gt_company and lead.company_name and gt_company.lower() in lead.company_name.lower()
        ):
            company_name_matches += 1

        if lead.email and lead.email.lower() == item.get("ground_truth_email", "").lower():
            email_matches += 1

        if lead.phones:
            phone_found += 1
        if lead.website:
            website_found += 1

        # Check Duplicate Detection (if item marked as duplicate)
        if item.get("is_duplicate_of"):
            dup_cases_count += 1
            dup_res = detect_duplicates(lead, db)
            if dup_res.match_type != "none":
                dup_detected_count += 1

        # 2. RAG Retrieval
        trace = retriever.retrieve(lead, body_snippet=email_data.body)

        # 3. Classification & Decision Gate
        cls_res, gate, sec = classifier.classify_lead(lead, trace, db)

        # Consolidate into DB so subsequent duplicate pair items can match against existing records
        try:
            from app.dedup.consolidator import consolidate_lead
            consolidate_lead(
                lead=lead,
                raw_email=email_data,
                classification=cls_res,
                gate=gate,
                trace=trace,
                matched_sector=sec,
                batch_id="eval_batch",
                db=db
            )
        except Exception:
            pass

        gt_sector = item.get("ground_truth_sector")
        predicted_sector = cls_res.sector

        confusion_matrix[gt_sector][predicted_sector] += 1

        # Evaluate correctness
        is_correct = False
        if predicted_sector.lower() == gt_sector.lower() or (
            gt_sector == "Other / Unknown" and predicted_sector in ("Needs Review", "Other / Unknown")
        ):
            is_correct = True
            correct_classifications += 1
            per_sector_tp[gt_sector] += 1
        else:
            per_sector_fp[predicted_sector] += 1
            per_sector_fn[gt_sector] += 1

        if gate.status == "needs_review":
            needs_review_count += 1
            if predicted_sector.lower() == gt_sector.lower() or gt_sector == "Other / Unknown":
                review_suggestion_correct += 1

    total_latency_sec = time.time() - start_total_time
    avg_latency_ms = (total_latency_sec / total_samples) * 1000 if total_samples > 0 else 0.0

    # Calculate Overall Accuracy
    accuracy = correct_classifications / total_samples if total_samples > 0 else 0.0
    review_rate = (needs_review_count / total_samples) * 100 if total_samples > 0 else 0.0
    review_accuracy = (review_suggestion_correct / needs_review_count * 100) if needs_review_count > 0 else 100.0

    company_acc = (company_name_matches / total_samples) * 100 if total_samples > 0 else 0.0
    email_acc = (email_matches / total_samples) * 100 if total_samples > 0 else 0.0

    dup_recall = (dup_detected_count / dup_cases_count * 100) if dup_cases_count > 0 else 100.0

    # Per-Sector Metrics
    sector_metrics = {}
    all_sectors = sorted(list(set(list(per_sector_tp.keys()) + list(per_sector_fn.keys()))))
    for s in all_sectors:
        tp = per_sector_tp[s]
        fp = per_sector_fp[s]
        fn = per_sector_fn[s]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        sector_metrics[s] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn
        }

    # Print Summary Table
    print(f"\n--- OVERALL PERFORMANCE METRICS ({split_target.upper()} SET) ---")
    print(f"Overall Classification Accuracy: {accuracy * 100:.2f}% (Target: >= {min_accuracy * 100:.1f}%)")
    print(f"Manual Review Rate:              {review_rate:.1f}%")
    print(f"Review Suggestion Accuracy:      {review_accuracy:.1f}%")
    print(f"Company Extraction Accuracy:     {company_acc:.1f}%")
    print(f"Email Extraction Accuracy:       {email_acc:.1f}%")
    print(f"Duplicate Detection Recall:      {dup_recall:.1f}%")
    print(f"Average Latency:                 {avg_latency_ms:.2f} ms/email")
    print(f"Estimated Cost per 100 Emails:   $0.00 (Local fastembed & deterministic RAG engine)")

    print(f"\n--- PER-SECTOR PERFORMANCE (PRECISION / RECALL / F1) ---")
    print(f"{'Sector Name':<32} | {'Precision':<10} | {'Recall':<8} | {'F1-Score':<8}")
    print("-" * 65)
    for s, m in sector_metrics.items():
        print(f"{s:<32} | {m['precision']:<10.2f} | {m['recall']:<8.2f} | {m['f1']:<8.2f}")

    # Write Markdown Report
    report_path = "eval/evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(f"# Lead Segregation Evaluation Report\n\n")
        rf.write(f"**Split**: `{split_target}` | **Evaluated Samples**: `{total_samples}`\n\n")
        rf.write(f"## Key Executive Metrics\n\n")
        rf.write(f"| Metric | Result | Benchmark Target |\n")
        rf.write(f"|---|---|---|\n")
        rf.write(f"| Overall Classification Accuracy | **{accuracy * 100:.2f}%** | >= {min_accuracy * 100:.1f}% |\n")
        rf.write(f"| Manual Review Rate | **{review_rate:.1f}%** | < 25.0% |\n")
        rf.write(f"| Review Suggestion Accuracy | **{review_accuracy:.1f}%** | >= 80.0% |\n")
        rf.write(f"| Company Name Extraction Accuracy | **{company_acc:.1f}%** | >= 90.0% |\n")
        rf.write(f"| Email Extraction Accuracy | **{email_acc:.1f}%** | 100.0% |\n")
        rf.write(f"| Average Processing Latency | **{avg_latency_ms:.2f} ms** | < 500 ms |\n\n")

        rf.write(f"## Per-Sector Classification Breakdown\n\n")
        rf.write(f"| Sector | Precision | Recall | F1 Score |\n|---|---|---|---|\n")
        for s, m in sector_metrics.items():
            rf.write(f"| {s} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} |\n")

        rf.write(f"\n> [!NOTE]\n")
        rf.write(f"> Synthetic & template-driven dataset clearly labelled as development evaluation fixtures.\n")

    print(f"\nSaved detailed evaluation markdown report to: {report_path}")

    db.close()

    # CI Gate Check
    if accuracy < min_accuracy:
        print(f"\n[FAIL] Accuracy {accuracy * 100:.2f}% is below regression threshold {min_accuracy * 100:.1f}%!")
        sys.exit(1)
    else:
        print(f"\n[PASS] Accuracy {accuracy * 100:.2f}% meets or exceeds required CI threshold {min_accuracy * 100:.1f}%.")

    return {
        "accuracy": accuracy,
        "review_rate": review_rate,
        "avg_latency_ms": avg_latency_ms
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Lead Segregation Evaluation Benchmark")
    parser.add_argument("--data", default="eval/labelled_data/evaluation_dataset.json")
    parser.add_argument("--split", default="test", choices=["test", "tuning", "all"])
    parser.add_argument("--min-accuracy", type=float, default=0.80)
    args = parser.parse_args()

    run_evaluation(data_path=args.data, split_target=args.split, min_accuracy=args.min_accuracy)
