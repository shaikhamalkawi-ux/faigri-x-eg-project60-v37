#!/usr/bin/env python3
"""Build and verify the bounded UK ATRS education-relevant public benchmark.

This script does not scrape the web. It verifies the manually extracted, page-level
public-record trace and regenerates the derived matrix, summaries, report, and figure.
The registry and trace CSV files are the admitted manual source-extraction inputs.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

DIMENSIONS = {
    "P": "Privacy and data governance",
    "F": "Fairness and accessibility",
    "T": "Transparency and limitations",
    "H": "Human review and appeal",
    "L": "Accountability and risk",
}
STATUSES = ("Direct", "Partial", "None")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root)
    data_dir = root / "external_evidence" / "uk_atrs"
    audit_dir = root / "audit"
    figure_dir = root / "figures"
    audit_dir.mkdir(exist_ok=True)
    figure_dir.mkdir(exist_ok=True)

    registry = read_csv(data_dir / "uk_atrs_education_benchmark_registry.csv")
    trace = read_csv(data_dir / "uk_atrs_documentary_coverage_trace.csv")

    assert len(registry) == 8, f"Expected 8 records, found {len(registry)}"
    ids = [r["id"] for r in registry]
    assert len(set(ids)) == 8, "Record IDs must be unique"
    assert len(trace) == 40, f"Expected 40 record-dimension rows, found {len(trace)}"

    keys = [(r["Record_ID"], r["Dimension_Code"]) for r in trace]
    assert len(set(keys)) == 40, "Trace keys must be unique"
    assert set(k[0] for k in keys) == set(ids), "Trace and registry IDs differ"
    assert set(k[1] for k in keys) == set(DIMENSIONS), "Expected P/F/T/H/L dimensions"
    assert all(r["Coverage_Status"] in STATUSES for r in trace), "Invalid coverage status"
    assert all(r["Evidence_Paraphrase"].strip() for r in trace), "Every trace row needs evidence text"
    assert all(r["ATRS_Sections"].strip() for r in trace), "Every trace row needs ATRS sections"

    reg_by_id = {r["id"]: r for r in registry}
    trace_by_key = {(r["Record_ID"], r["Dimension_Code"]): r for r in trace}

    matrix: list[dict] = []
    for rid in ids:
        reg = reg_by_id[rid]
        statuses = {d: trace_by_key[(rid, d)]["Coverage_Status"] for d in DIMENSIONS}
        direct = sum(v == "Direct" for v in statuses.values())
        partial = sum(v == "Partial" for v in statuses.values())
        none = sum(v == "None" for v in statuses.values())
        assert direct + partial + none == 5
        matrix.append({
            "Record_ID": rid,
            "Title": reg["title"],
            "Organisation": reg["org"],
            "Phase": reg["phase"],
            "Decision_Role": reg["decision_role"],
            "P_Privacy_Data": statuses["P"],
            "F_Fairness_Accessibility": statuses["F"],
            "T_Transparency_Limitations": statuses["T"],
            "H_Human_Review_Appeal": statuses["H"],
            "L_Accountability_Risk": statuses["L"],
            "Direct_Count": direct,
            "Partial_Count": partial,
            "None_Count": none,
            "All_Five_Direct": int(direct == 5),
        })

    matrix_fields = list(matrix[0].keys())
    write_csv(data_dir / "uk_atrs_documentary_coverage_matrix.csv", matrix, matrix_fields)

    by_dimension: list[dict] = []
    for code, label in DIMENSIONS.items():
        vals = [trace_by_key[(rid, code)]["Coverage_Status"] for rid in ids]
        counts = Counter(vals)
        by_dimension.append({
            "Dimension_Code": code,
            "Dimension": label,
            "Direct": counts["Direct"],
            "Partial": counts["Partial"],
            "None": counts["None"],
            "N": len(vals),
        })
    write_csv(
        data_dir / "uk_atrs_summary_by_dimension.csv",
        by_dimension,
        ["Dimension_Code", "Dimension", "Direct", "Partial", "None", "N"],
    )

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in matrix:
        grouped[row["Phase"]].append(row)
    by_phase: list[dict] = []
    for phase in sorted(grouped):
        rows = grouped[phase]
        by_phase.append({
            "Phase": phase,
            "Records": len(rows),
            "Mean_Direct_Count": round(sum(int(r["Direct_Count"]) for r in rows) / len(rows), 3),
            "All_Five_Direct": sum(int(r["All_Five_Direct"]) for r in rows),
            "Mean_Partial_Count": round(sum(int(r["Partial_Count"]) for r in rows) / len(rows), 3),
        })
    write_csv(
        data_dir / "uk_atrs_summary_by_phase.csv",
        by_phase,
        ["Phase", "Records", "Mean_Direct_Count", "All_Five_Direct", "Mean_Partial_Count"],
    )

    direct_total = sum(int(r["Direct_Count"]) for r in matrix)
    partial_total = sum(int(r["Partial_Count"]) for r in matrix)
    none_total = sum(int(r["None_Count"]) for r in matrix)
    all_direct = sum(int(r["All_Five_Direct"]) for r in matrix)
    production = [r for r in matrix if r["Phase"] == "Production"]

    assert direct_total == 31, direct_total
    assert partial_total == 9, partial_total
    assert none_total == 0, none_total
    assert all_direct == 2, all_direct
    assert len(production) == 4
    assert sum(int(r["All_Five_Direct"]) for r in production) == 0

    report = {
        "audit_name": "UK ATRS education-relevant public documentary benchmark",
        "source_scope": "Purposive eight-record subset from the official GOV.UK ATRS repository",
        "extraction_date": "2026-07-22",
        "registry_records": len(registry),
        "record_dimension_cells": len(trace),
        "coverage_totals": {"Direct": direct_total, "Partial": partial_total, "None": none_total},
        "all_five_direct_records": all_direct,
        "production_records": len(production),
        "production_all_five_direct": sum(int(r["All_Five_Direct"]) for r in production),
        "dimension_summary": by_dimension,
        "phase_summary": by_phase,
        "admission_decision": "Admitted for bounded cross-framework documentary-coverage analysis",
        "excluded_claims": [
            "No external outcome validation",
            "No score calibration or weight derivation",
            "No inference about population prevalence",
            "No causal or inferential comparison by deployment phase",
            "No claim that public documentation proves implementation effectiveness",
        ],
        "single_analyst_boundary": "Coverage states are single-analyst public-document coding; no intercoder reliability is claimed.",
        "overall_passed": True,
    }
    (audit_dir / "uk_atrs_public_benchmark_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    report_md = "# UK ATRS Public Documentary Benchmark\n\n"
    report_md += (
        "This audit uses a purposive eight-record education-relevant subset of the official "
        "UK Algorithmic Transparency Recording Standard repository. It is a public-document "
        "coverage benchmark, not an outcome-validation study.\n\n"
    )
    report_md += (
        f"- Records: {len(registry)}\n"
        f"- Record-dimension cells: {len(trace)}\n"
        f"- Direct: {direct_total}\n"
        f"- Partial: {partial_total}\n"
        f"- None: {none_total}\n"
        f"- All five dimensions direct: {all_direct}\n"
        f"- Production records: {len(production)}\n"
        f"- Production records with all five direct: "
        f"{sum(int(r['All_Five_Direct']) for r in production)}\n\n"
    )
    report_md += (
        "## Admission decision\n\n"
        "Admitted only for bounded cross-framework documentary-coverage analysis. "
        "The dataset is not used to change FAIGRI-X-EG scores, weights, risk anchors, "
        "thresholds, veto decisions, or ranks.\n\n"
    )
    report_md += (
        "## Interpretation boundary\n\n"
        "The coding records whether the official ATRS page contains direct, partial, "
        "or no public documentary evidence for five broad governance constructs. "
        "It does not verify implementation, effectiveness, legality, fairness, or safety "
        "in practice. The selected set is purposive and single-analyst coded.\n"
    )
    (audit_dir / "UK_ATRS_PUBLIC_BENCHMARK.md").write_text(report_md, encoding="utf-8")

    # Figure: hatching makes groups distinguishable if printed in grayscale.
    labels = [r["Dimension_Code"] for r in by_dimension]
    direct = [int(r["Direct"]) for r in by_dimension]
    partial = [int(r["Partial"]) for r in by_dimension]
    none = [int(r["None"]) for r in by_dimension]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    ax.bar(x, direct, label="Direct", hatch="///", edgecolor="black")
    ax.bar(x, partial, bottom=direct, label="Partial", hatch="...", edgecolor="black")
    bottom2 = [a + b for a, b in zip(direct, partial)]
    ax.bar(x, none, bottom=bottom2, label="None", hatch="xx", edgecolor="black")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Records (n = 8)")
    ax.set_xlabel("Documentary dimension")
    ax.set_ylim(0, 8.7)
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    ax.spines[["top", "right"]].set_visible(False)
    for i, (d, p, n) in enumerate(zip(direct, partial, none)):
        ax.text(i, d / 2, str(d), ha="center", va="center", fontsize=9)
        if p:
            ax.text(i, d + p / 2, str(p), ha="center", va="center", fontsize=9)
        if n:
            ax.text(i, d + p + n / 2, str(n), ha="center", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(figure_dir / "fig6_uk_atrs_documentary_coverage.pdf", bbox_inches="tight")
    fig.savefig(figure_dir / "fig6_uk_atrs_documentary_coverage.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
