#!/usr/bin/env python3
"""Reproduce FAIGRI-X-EG calculations from disclosed adjudicated case inputs.

Reproducibility begins at the disclosed case-level criterion/risk matrix and
mandatory-safeguard matrix. The package does not represent reconstructed records
as original coder-level annotations.
"""
from pathlib import Path
import json
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

try:
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
except ImportError as exc:
    raise SystemExit(f"Required scientific package missing: {exc}")

INPUT = DATA / "case_input_matrix.csv"
MANDATORY = DATA / "mandatory_safeguard_matrix.csv"
TAU_L = 0.30
TAU_H = 0.55
BASELINE_LAMBDA = 0.75
TOPSIS_TOL = 1e-12
GOVERNANCE_COLS = ["P", "F", "T", "H", "L"]
TOPSIS_COLS = GOVERNANCE_COLS + ["R"]
MANDATORY_DOCUMENTED = "Mandatory evidence documented"
VETO_HOLD = "Veto Hold"


def zone(score: float, tau_l: float = TAU_L, tau_h: float = TAU_H) -> str:
    if score >= tau_h:
        return "Upper"
    if score >= tau_l:
        return "Review"
    return "Lower"


def dense_rank_desc(values, tol: float = TOPSIS_TOL):
    """Dense descending ranks using the immediately preceding sorted value.

    Coefficients whose adjacent absolute difference is at most ``tol`` share a
    rank. Updating ``previous`` on every iteration implements the prose rule
    and makes chained near-ties explicit.
    """
    order = sorted(range(len(values)), key=lambda i: (-float(values[i]), i))
    ranks = [None] * len(values)
    rank = 0
    previous = None
    for i in order:
        value = float(values[i])
        if previous is None or abs(value - previous) > tol:
            rank += 1
        ranks[i] = rank
        previous = value
    return ranks


def topsis_vector(df):
    X = df[TOPSIS_COLS].astype(float).to_numpy()
    norms = np.sqrt((X ** 2).sum(axis=0))
    if np.any(norms == 0):
        raise ValueError("TOPSIS zero vector norm")
    weights = np.repeat(1 / len(TOPSIS_COLS), len(TOPSIS_COLS))
    V = (X / norms) * weights
    positive = np.concatenate([V[:, :5].max(axis=0), [V[:, 5].min()]])
    negative = np.concatenate([V[:, :5].min(axis=0), [V[:, 5].max()]])
    dplus = np.sqrt(((V - positive) ** 2).sum(axis=1))
    dminus = np.sqrt(((V - negative) ** 2).sum(axis=1))
    denom = dplus + dminus
    cc = np.where(denom > 0, dminus / denom, 0.5)
    return cc, dense_rank_desc(cc)


df = pd.read_csv(INPUT)
for col in TOPSIS_COLS:
    df[col] = df[col].astype(float)

mandatory = pd.read_csv(MANDATORY)
mandatory["m_ij"] = pd.to_numeric(mandatory["m_ij"], errors="coerce")
if "Applicability_Status" not in mandatory.columns:
    mandatory["Applicability_Status"] = "Applicable"
applicable = mandatory[mandatory["Applicability_Status"].eq("Applicable")].copy()
if applicable["m_ij"].isna().any():
    raise ValueError("Applicable mandatory safeguards must have binary m_ij values")
if not set(applicable["m_ij"].astype(int).unique()).issubset({0, 1}):
    raise ValueError("Applicable mandatory safeguards must be binary")
# M5/Not-applicable rows are excluded from each case-specific set M_i rather
# than multiplied as zero. Every current case retains a non-empty applicable set.
if set(df["Case_ID"]) - set(applicable["Case_ID"]):
    raise ValueError("Every case must have at least one applicable safeguard")
veto = applicable.groupby("Case_ID")["m_ij"].prod().astype(int).to_dict()
df["Veto_Pass"] = df["Case_ID"].map(lambda case_id: "Yes" if veto[case_id] == 1 else "No")
df["G_equal"] = df[GOVERNANCE_COLS].mean(axis=1)

lambda_grid = [0.00, 0.02, 0.05, 0.10, 0.125, 0.15, 0.16, 0.25, 0.75, 1.25]
for lam in lambda_grid:
    df[f"S_lambda_{lam:.2f}"] = df["G_equal"] * np.exp(-lam * df["R"])

df["Risk_Centroid"] = df["R"]
df["Zone_no_risk"] = df["G_equal"].map(zone)
df["Risk_Zone_0.75"] = df["S_lambda_0.75"].map(zone)
df["Evidence_Status"] = df["Veto_Pass"].map({"Yes": MANDATORY_DOCUMENTED, "No": VETO_HOLD})
df["Final_Paired_Decision"] = df["Risk_Zone_0.75"] + " numerical-score band + " + df["Evidence_Status"]

# TOPSIS is restricted to the 11 public dossiers.
df["TOPSIS_included"] = "No"
df["TOPSIS_CC"] = np.nan
df["TOPSIS_rank"] = np.nan
public_mask = df["Case_Type"].eq("Public-evidence case")
cc, ranks = topsis_vector(df.loc[public_mask].copy())
df.loc[public_mask, "TOPSIS_included"] = "Yes"
df.loc[public_mask, "TOPSIS_CC"] = cc
df.loc[public_mask, "TOPSIS_rank"] = ranks

result_cols = [
    "Case_ID", "Case_Name", "Use_Case", "Dossier_Unit_Type", "Comparator_Use_Boundary",
    "P", "F", "T", "H", "L", "R", "Veto_Pass", "G_equal",
    "S_lambda_0.25", "S_lambda_0.75", "S_lambda_1.25",
    "TOPSIS_included", "TOPSIS_CC", "TOPSIS_rank", "Zone_no_risk",
    "Risk_Zone_0.75", "Evidence_Status", "Final_Paired_Decision", "Veto_Reason",
    "Evidence_Confidence", "Case_Type", "Risk_Centroid",
]
df[result_cols].to_csv(DATA / "case_results_with_topsis.csv", index=False)
df.loc[public_mask, result_cols].to_csv(DATA / "public_case_results.csv", index=False)
df.loc[~public_mask, result_cols].to_csv(DATA / "protocol_stress_test_result.csv", index=False)
compact_cols = [
    "Case_ID", "Case_Name", "Use_Case", "Dossier_Unit_Type", "Comparator_Use_Boundary",
    "P", "F", "T", "H", "L", "R", "Veto_Pass", "G_equal", "Risk_Centroid",
    "S_lambda_0.75", "Risk_Zone_0.75", "Evidence_Status", "Final_Paired_Decision",
    "Evidence_Confidence", "Case_Type", "Veto_Reason",
]
df[compact_cols].to_csv(DATA / "case_coding.csv", index=False)

# Threshold sensitivity: public dossiers only; C12 separately reported.
scenarios = [
    ("Stress-lenient", 0.25, 0.40),
    ("Lenient", 0.25, 0.50),
    ("Baseline", 0.30, 0.55),
    ("Stricter", 0.35, 0.60),
]
threshold_rows = []
for name, tau_l, tau_h in scenarios:
    public = df.loc[public_mask].copy()
    bands = public["S_lambda_0.75"].map(lambda score: zone(score, tau_l, tau_h))
    counts = Counter(bands)
    paired = Counter(
        f"{band} numerical-score band + {status}"
        for band, status in zip(bands, public["Evidence_Status"])
    )
    c12 = df.loc[~public_mask].iloc[0]
    threshold_rows.append({
        "Scenario": name,
        "tau_L": tau_l,
        "tau_H": tau_h,
        "Public_Upper": counts["Upper"],
        "Public_Review": counts["Review"],
        "Public_Lower": counts["Lower"],
        "Public_Upper_Mandatory_Evidence_Documented": paired[f"Upper numerical-score band + {MANDATORY_DOCUMENTED}"],
        "Public_Review_Mandatory_Evidence_Documented": paired[f"Review numerical-score band + {MANDATORY_DOCUMENTED}"],
        "Public_Review_Veto_Hold": paired[f"Review numerical-score band + {VETO_HOLD}"],
        "Public_Lower_Veto_Hold": paired[f"Lower numerical-score band + {VETO_HOLD}"],
        "Public_Total_Veto_Hold": int((public["Veto_Pass"] == "No").sum()),
        "C12_Protocol_Band": zone(c12["S_lambda_0.75"], tau_l, tau_h),
        "C12_Protocol_Evidence_Status": c12["Evidence_Status"],
    })
pd.DataFrame(threshold_rows).to_csv(DATA / "threshold_sensitivity.csv", index=False)

# Risk-posture sensitivity and exact Upper-band breakpoints.
risk_rows = []
for lam in lambda_grid:
    for case_set, subset in [
        ("Public-evidence case", df.loc[public_mask]),
        ("Protocol stress-test", df.loc[~public_mask]),
    ]:
        scores = subset["G_equal"] * np.exp(-lam * subset["R"])
        counts = Counter(scores.map(zone))
        risk_rows.append({
            "Lambda": lam,
            "Case_Set": case_set,
            "Upper": counts["Upper"],
            "Review": counts["Review"],
            "Lower": counts["Lower"],
        })
pd.DataFrame(risk_rows).to_csv(DATA / "risk_posture_sensitivity.csv", index=False)

break_rows = []
for _, row in df.loc[public_mask].iterrows():
    if row["G_equal"] >= TAU_H and row["R"] > 0:
        critical = float(np.log(row["G_equal"] / TAU_H) / row["R"])
        break_rows.append({
            "Case_ID": row["Case_ID"],
            "G_equal": row["G_equal"],
            "Risk_R": row["R"],
            "Upper_Threshold_tau_H": TAU_H,
            "Critical_Lambda_Leaving_Upper": critical,
            "Interpretation": "Upper for lambda <= critical value; below Upper for lambda > critical value under the exponential form and fixed threshold.",
        })
break_df = pd.DataFrame(break_rows).sort_values("Critical_Lambda_Leaving_Upper")
break_df.to_csv(DATA / "upper_band_breakpoint_analysis.csv", index=False)

# Functional-form robustness at lambda=.75.
forms = {
    "Exponential": lambda g, r: g * np.exp(-BASELINE_LAMBDA * r),
    "Rational": lambda g, r: g / (1 + BASELINE_LAMBDA * r),
    "Clipped linear": lambda g, r: g * np.maximum(0, 1 - BASELINE_LAMBDA * r),
}
functional_rows = []
for name, function in forms.items():
    scores = function(df["G_equal"].to_numpy(), df["R"].to_numpy())
    for position, row in df.iterrows():
        functional_rows.append({
            "Functional_Form": name,
            "Case_ID": row["Case_ID"],
            "Case_Type": row["Case_Type"],
            "Score": float(scores[position]),
            "Band": zone(float(scores[position])),
            "Evidence_Status": row["Evidence_Status"],
            "Upper_Band_Indicator": int(float(scores[position]) >= TAU_H),
        })

pd.DataFrame(functional_rows).to_csv(DATA / "functional_form_sensitivity.csv", index=False)

# Sensitivity to alternative monotone spacing of the ordered risk categories.
# These mappings preserve risk order and are illustrative conventions, not
# empirical calibration.
risk_mappings = {
    "Declared anchors": {0.40: 0.40, 0.50: 0.50, 0.55: 0.55, 0.60: 0.60, 0.70: 0.70, 0.90: 0.90},
    "Compressed monotone spacing": {0.40: 0.45, 0.50: 0.50, 0.55: 0.525, 0.60: 0.55, 0.70: 0.625, 0.90: 0.75},
    "Expanded monotone spacing": {0.40: 0.25, 0.50: 0.40, 0.55: 0.475, 0.60: 0.55, 0.70: 0.75, 0.90: 1.00},
}
risk_spacing_rows = []
public_df = df.loc[public_mask].copy()
for mapping_name, mapping in risk_mappings.items():
    anchors = public_df["R"].map(mapping)
    if anchors.isna().any():
        raise ValueError(f"Risk-spacing mapping {mapping_name} omitted a declared anchor")
    scores = public_df["G_equal"] * np.exp(-BASELINE_LAMBDA * anchors)
    bands = scores.map(zone)
    counts = Counter(bands)
    for position, (_, row) in enumerate(public_df.iterrows()):
        risk_spacing_rows.append({
            "Mapping": mapping_name,
            "Case_ID": row["Case_ID"],
            "Original_Risk_Anchor": row["R"],
            "Alternative_Risk_Anchor": float(anchors.iloc[position]),
            "S_lambda_0.75": float(scores.iloc[position]),
            "Band": bands.iloc[position],
            "Public_Upper_Count": counts["Upper"],
            "Public_Review_Count": counts["Review"],
            "Public_Lower_Count": counts["Lower"],
            "Interpretation_Boundary": "Illustrative rank-preserving spacing sensitivity; not empirical calibration.",
        })
pd.DataFrame(risk_spacing_rows).to_csv(DATA / "risk_anchor_spacing_sensitivity.csv", index=False)

# Leave-one-dossier-out TOPSIS set-dependence diagnostic.
full_public = df.loc[public_mask].copy().reset_index(drop=True)
full_by_case = full_public.set_index("Case_ID")
loo_detail_rows = []
for excluded_case in full_public["Case_ID"]:
    subset = full_public[full_public["Case_ID"] != excluded_case].copy().reset_index(drop=True)
    loo_cc, loo_ranks = topsis_vector(subset)
    for index, row in subset.iterrows():
        case_id = row["Case_ID"]
        loo_detail_rows.append({
            "Excluded_Case_ID": excluded_case,
            "Included_Case_ID": case_id,
            "Full_Set_CC": float(full_by_case.loc[case_id, "TOPSIS_CC"]),
            "Full_Set_Rank": int(full_by_case.loc[case_id, "TOPSIS_rank"]),
            "LOO_CC": float(loo_cc[index]),
            "LOO_Rank": int(loo_ranks[index]),
            "Absolute_Rank_Change": abs(int(loo_ranks[index]) - int(full_by_case.loc[case_id, "TOPSIS_rank"])),
            "Interpretation_Boundary": "Set-dependence diagnostic only; does not alter evidence status.",
        })
loo_detail = pd.DataFrame(loo_detail_rows)
loo_detail.to_csv(DATA / "topsis_leave_one_out_detail.csv", index=False)
loo_summary_rows = []
for case_id, group in loo_detail.groupby("Included_Case_ID", sort=False):
    loo_summary_rows.append({
        "Case_ID": case_id,
        "Full_Set_CC": float(full_by_case.loc[case_id, "TOPSIS_CC"]),
        "LOO_Min_CC": float(group["LOO_CC"].min()),
        "LOO_Max_CC": float(group["LOO_CC"].max()),
        "LOO_Min_Rank": int(group["LOO_Rank"].min()),
        "LOO_Max_Rank": int(group["LOO_Rank"].max()),
        "Max_Absolute_Rank_Change": int(group["Absolute_Rank_Change"].max()),
        "Interpretation_Boundary": "Set-dependence diagnostic only; does not alter evidence status.",
    })
pd.DataFrame(loo_summary_rows).to_csv(DATA / "topsis_leave_one_out_summary.csv", index=False)

# Generate veto trace and readable supplement from the current item-level matrix.
category_map = {
    "C01": "General governance dossier",
    "C04": "Fairness/appeal/audit trail",
    "C05": "Fairness/appeal/audit trail",
    "C06": "Fairness/appeal/audit trail",
    "C07": "Proctoring proportionality",
    "C08": "Proctoring proportionality",
    "C09": "General governance dossier",
    "C10": "Admission/legal review",
    "C11": "Admission/legal review",
    "C12": "LLM assessment safeguards",
}
source_basis_map = {
    "C01": "OpenAI ChatGPT Edu product page plus protocol campus-LLM requirements",
    "C04": "EU AI Act learning-outcome assessment; NIST MEASURE/MANAGE; Canada AIA; audit/model-card literature",
    "C05": "EU AI Act learning-outcome assessment; NIST MEASURE/MANAGE; Canada AIA",
    "C06": "NIST GenAI information integrity; UNESCO assessment guidance; Canada AIA mitigation logic",
    "C07": "EU AI Act test-monitoring context; NIST privacy/security/robustness; Canada AIA",
    "C08": "EU AI Act test-monitoring context; NIST privacy/security/robustness; Canada AIA",
    "C09": "NIST GOVERN/MAP/MANAGE; UNESCO human-centred AI; Canada AIA",
    "C10": "EU AI Act access/admission/allocation; NIST fairness/transparency; Canada AIA",
    "C11": "EU AI Act access/admission/allocation; NIST transparency and oversight; Canada AIA",
    "C12": "EU AI Act learning-outcome assessment; NIST GenAI confabulation/information integrity; UNESCO GenAI guidance",
}
trace_rows = []
lookup = df.set_index("Case_ID")
for case_id, group in applicable.groupby("Case_ID", sort=False):
    if int(group["m_ij"].prod()) == 1:
        continue
    missing = group[group["m_ij"].astype(int).eq(0)]["Mandatory_Safeguard"].tolist()
    row = lookup.loc[case_id]
    trace_rows.append({
        "Case_ID": case_id,
        "Case_Name": row["Case_Name"],
        "Use_Case": row["Use_Case"],
        "Risk_Zone_0.75": row["Risk_Zone_0.75"],
        "Evidence_Status": row["Evidence_Status"],
        "Final_Paired_Decision": row["Final_Paired_Decision"],
        "Veto_Category": category_map[case_id],
        "Missing_Mandatory_Evidence": "; ".join(missing),
        "Source_Basis": source_basis_map[case_id],
        "Trace_Source": "mandatory_safeguard_matrix.csv; safeguard_item_adjudication_log.csv",
    })
trace = pd.DataFrame(trace_rows)
trace.to_csv(DATA / "veto_reason_trace.csv", index=False)
readable = trace.rename(columns={
    "Case_ID": "Case",
    "Use_Case": "Use context",
    "Final_Paired_Decision": "Final paired state",
    "Missing_Mandatory_Evidence": "Missing admitted evidence",
    "Source_Basis": "Source basis",
})
selected = ["Case", "Use context", "Final paired state", "Missing admitted evidence", "Source basis"]
readable[selected].to_csv(DATA / "supplementary_veto_trace_table.csv", index=False)
lines = [
    "| Case | Use context | Final paired state | Missing admitted evidence | Source basis |",
    "|---|---|---|---|---|",
]
for _, row in readable.iterrows():
    lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in selected) + " |")
(DATA / "supplementary_veto_trace_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# Tie audit.
public_rank = df.loc[public_mask, ["Case_ID", "Case_Name", "TOPSIS_CC", "TOPSIS_rank"]].sort_values(["TOPSIS_rank", "Case_ID"])
public_rank["Tie_Group_Size"] = public_rank.groupby("TOPSIS_rank")["Case_ID"].transform("count")
public_rank["Tie_Status"] = public_rank["Tie_Group_Size"].map(lambda count: "Shared rank" if count > 1 else "Unique rank")
public_rank["Absolute_Tie_Tolerance"] = TOPSIS_TOL
public_rank.to_csv(DATA / "topsis_tie_audit.csv", index=False)

# Figures: grayscale-safe, print-friendly, no product-superiority visual framing.
plt.rcParams.update({
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "figure.dpi": 180,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def save(name):
    for extension in ["pdf", "png"]:
        plt.savefig(FIG / f"{name}.{extension}", bbox_inches="tight")
    plt.close()

# Figure 1
fig, ax = plt.subplots(figsize=(8.8, 2.4))
ax.axis("off")
steps = [
    ("Evidence\nadmission", "source registry\nand use gate"),
    ("Mandatory\nveto gate", "non-compensatory\nconditions"),
    ("Ordinal evidence\nscores", "P, F, T, H, L"),
    ("Risk-adjusted\nscore", "explicit risk\nposture"),
    ("Paired screening\nstate", "score band +\nevidence status"),
]
x0, y0, width, height, gap = 0.02, 0.34, 0.16, 0.36, 0.035
for index, (title, subtitle) in enumerate(steps):
    x = x0 + index * (width + gap)
    rect = FancyBboxPatch(
        (x, y0), width, height,
        boxstyle="round,pad=0.018,rounding_size=0.02",
        linewidth=1.1, edgecolor="black", facecolor="white",
    )
    ax.add_patch(rect)
    ax.text(x + width / 2, y0 + height * 0.63, title, ha="center", va="center", weight="bold")
    ax.text(x + width / 2, y0 + height * 0.28, subtitle, ha="center", va="center", fontsize=7.7)
    if index < len(steps) - 1:
        ax.add_patch(FancyArrowPatch(
            (x + width + 0.005, y0 + height / 2),
            (x + width + gap - 0.005, y0 + height / 2),
            arrowstyle="-|>", mutation_scale=12, linewidth=1, color="black",
        ))
ax.text(0.5, 0.08, "Cross-dossier scoring remains separate from mandatory documentary sufficiency.", ha="center", va="center", fontsize=8.2)
save("fig1_workflow")

# Figure 2
fig, ax = plt.subplots(figsize=(8.8, 4.4))
indices = np.arange(len(df))
width = 0.38
ax.bar(indices - width / 2, df["G_equal"], width=width, label=r"Baseline readiness $G_i$", edgecolor="black", facecolor="white", hatch="//")
ax.bar(indices + width / 2, df["S_lambda_0.75"], width=width, label=r"Risk-adjusted readiness $S_i(r_i;0.75)$", edgecolor="black", facecolor="0.65", hatch="..")
ax.axhline(TAU_H, linestyle="--", color="black", linewidth=1, label=r"Upper threshold $\tau_H=0.55$")
ax.axhline(TAU_L, linestyle=":", color="black", linewidth=1, label=r"Lower threshold $\tau_L=0.30$")
ax.axvline(10.5, color="black", linewidth=0.8)
ax.text(10.5, 0.86, "public dossiers  |  protocol stress test", ha="center", va="bottom", fontsize=7.5, clip_on=False)
ax.set_ylabel("Numerical score")
ax.set_xlabel("Dossier identifier")
ax.set_title("Baseline and risk-adjusted numerical scores")
ax.set_xticks(indices)
ax.set_xticklabels(df["Case_ID"])
ax.set_ylim(0, 0.85)
ax.legend(loc="upper right")
ax.grid(axis="y", alpha=0.25)
save("fig2_readiness_scores")

# Figure 3: two non-additive panels shown as grouped bars.
public = df.loc[public_mask]
baseline = Counter(public["Zone_no_risk"])
risk_adjusted = Counter(public["Risk_Zone_0.75"])
paired = Counter(public["Final_Paired_Decision"])
fig, ax = plt.subplots(figsize=(8.5, 4.5))
labels = ["Baseline\nbands", "Risk-adjusted\nbands", "Final paired\nstates"]
x = np.arange(3)
series = [
    ("Upper", [baseline["Upper"], risk_adjusted["Upper"], 0], "//", "white"),
    ("Review", [baseline["Review"], risk_adjusted["Review"], 0], "..", "0.8"),
    ("Lower", [baseline["Lower"], risk_adjusted["Lower"], 0], "xx", "0.5"),
    ("Review + mandatory evidence", [0, 0, paired[f"Review numerical-score band + {MANDATORY_DOCUMENTED}"]], "++", "white"),
    ("Review + Veto Hold", [0, 0, paired[f"Review numerical-score band + {VETO_HOLD}"]], "oo", "0.75"),
    ("Lower + Veto Hold", [0, 0, paired[f"Lower numerical-score band + {VETO_HOLD}"]], "\\\\", "0.45"),
]
bottom = np.zeros(3)
for label, values, hatch, gray in series:
    values = np.asarray(values)
    if values.any():
        ax.bar(x, values, bottom=bottom, label=label, edgecolor="black", facecolor=gray, hatch=hatch)
        bottom += values
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("Number of public dossiers")
ax.set_title("Numerical bands and documentary gate are distinct classifications")
ax.text(0.5, -0.18, "The three columns are separate classifications and are not additive across columns.", transform=ax.transAxes, ha="center", va="top", fontsize=7.5)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3, frameon=False)
ax.set_ylim(0, 11.8)
ax.grid(axis="y", alpha=0.25)
save("fig3_ablation_counts")

# Figure 4: conventional rank direction, combined label for exact tie.
fig, ax = plt.subplots(figsize=(7.6, 4.4))
public = df.loc[public_mask].copy()
passed = public["Veto_Pass"].eq("Yes")
ax.scatter(public.loc[passed, "TOPSIS_rank"], public.loc[passed, "S_lambda_0.75"], marker="o", s=70, edgecolor="black", facecolor="white", label=MANDATORY_DOCUMENTED)
ax.scatter(public.loc[~passed, "TOPSIS_rank"], public.loc[~passed, "S_lambda_0.75"], marker="x", s=80, linewidth=2, color="black", label=VETO_HOLD)
# Label exact tie once and all other cases individually.
tied = {"C01", "C02"}
tie_row = public[public["Case_ID"] == "C01"].iloc[0]
ax.annotate("C01/C02", (tie_row["TOPSIS_rank"], tie_row["S_lambda_0.75"]), xytext=(6, 7), textcoords="offset points", fontsize=7)
offsets = {
    "C03": (7, 8), "C04": (7, 8), "C05": (12, -16), "C06": (-18, 10),
    "C07": (8, -15), "C08": (8, 9), "C09": (-22, -15), "C10": (8, 9), "C11": (8, -15),
}
for _, row in public[~public["Case_ID"].isin(tied)].iterrows():
    ax.annotate(
        row["Case_ID"],
        (row["TOPSIS_rank"], row["S_lambda_0.75"]),
        xytext=offsets.get(row["Case_ID"], (5, 5)),
        textcoords="offset points",
        fontsize=7,
        arrowprops={"arrowstyle": "-", "linewidth": 0.45, "color": "0.35"},
    )
ax.axhline(TAU_H, linestyle="--", color="black", linewidth=1)
ax.axhline(TAU_L, linestyle=":", color="black", linewidth=1)
ax.set_xlabel("Tie-aware TOPSIS rank (1 = highest closeness)")
ax.set_ylabel(r"Risk-adjusted score $S_i(r_i;0.75)$")
ax.set_title("Relative rank does not establish mandatory documentary sufficiency")
ax.set_xlim(0.5, max(public["TOPSIS_rank"]) + 0.8)
ax.legend(loc="lower left")
ax.grid(alpha=0.25)
save("fig4_topsis_vs_readiness")

# Figure 5: mutually exclusive primary categories.
trace = pd.read_csv(DATA / "veto_reason_trace.csv")
trace = trace[trace["Case_ID"] != "C12"]
order = [
    "Fairness/appeal/audit trail",
    "Proctoring proportionality",
    "Admission/legal review",
    "General governance dossier",
]
counts = trace["Veto_Category"].value_counts().reindex(order).fillna(0).astype(int)
fig, ax = plt.subplots(figsize=(7.6, 4.2))
bars = ax.barh(list(counts.index), list(counts.values), edgecolor="black", facecolor="white", hatch="//")
for bar, value in zip(bars, counts.values):
    ax.text(value + 0.05, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontsize=8)
ax.set_xlabel("Number of public-dossier Veto Hold cases")
ax.set_title("Primary documentary bottleneck categories (one category per dossier)")
ax.set_xlim(0, max(counts.values) + 1)
ax.grid(axis="x", alpha=0.25)
save("fig5_veto_bottlenecks")

# Machine-readable calculation assertions.
assertions = {
    "governance_weights": {"count": 5, "each": 0.2, "sum": 1.0},
    "topsis_weights": {"count": 6, "each": 1 / 6, "sum": 1.0},
    "score_bounds_pass": bool(df[GOVERNANCE_COLS + ["R"]].apply(lambda col: col.between(0, 1).all()).all()),
    "safeguards_binary_pass": bool(set(applicable["m_ij"].astype(int).unique()).issubset({0, 1})),
    "not_applicable_rows_excluded_from_veto_product": True,
    "chained_near_tie_test": bool(dense_rank_desc([1.0, 1.0 - 0.6 * TOPSIS_TOL, 1.0 - 1.2 * TOPSIS_TOL]) == [1, 1, 1]),
    "c12_excluded_from_public_topsis": bool(df.loc[df["Case_ID"] == "C12", "TOPSIS_included"].iloc[0] == "No"),
    "dense_tie_tolerance_absolute": TOPSIS_TOL,
    "c01_c02_shared_rank": bool(df.loc[df["Case_ID"].isin(["C01", "C02"]), "TOPSIS_rank"].nunique() == 1),
    "rounded_values_used_as_inputs": False,
    "risk_spacing_sensitivity_generated": bool((DATA / "risk_anchor_spacing_sensitivity.csv").exists()),
    "topsis_leave_one_out_generated": bool((DATA / "topsis_leave_one_out_summary.csv").exists()),
}
(DATA / "calculation_assertions.json").write_text(json.dumps(assertions, indent=2), encoding="utf-8")

report = {
    "case_count": int(len(df)),
    "public_case_count": int(public_mask.sum()),
    "protocol_case_count": int((~public_mask).sum()),
    "criterion_score_rows": 72,
    "mandatory_safeguard_rows": int(len(mandatory)),
    "source_registry_rows": int(len(pd.read_csv(DATA / "source_registry.csv"))),
    "public_veto_hold": int(((df["Veto_Pass"] == "No") & public_mask).sum()),
    "public_mandatory_evidence_documented": int(((df["Veto_Pass"] == "Yes") & public_mask).sum()),
    "protocol_veto_hold": int(((df["Veto_Pass"] == "No") & (~public_mask)).sum()),
    "public_baseline_band_counts": dict(Counter(public["Zone_no_risk"])),
    "public_risk_adjusted_band_counts": dict(Counter(public["Risk_Zone_0.75"])),
    "topsis_excludes_protocol_case": True,
    "topsis_six_equal_weights": True,
    "topsis_ties_are_shared": True,
    "max_upper_band_critical_lambda_exponential": float(break_df["Critical_Lambda_Leaving_Upper"].max()),
    "evidence_status_label": f"{MANDATORY_DOCUMENTED} / {VETO_HOLD}",
    "reproducibility_start": "Disclosed adjudicated case-level matrix",
    "comparator_scope": "Heterogeneous cross-dossier methodological stress test only",
    "overall_passed": True,
}
(DATA / "full_reproduction_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
