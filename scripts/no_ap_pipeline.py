#!/usr/bin/env python3
"""
Full end-to-end no-AP pipeline:
1. Parse raw responses → extract AP + LTL
2. Evaluate AP extraction (Jaccard/Levenshtein/P/R/F1) vs GT
3. Substitute GT variables into predicted LTL based on description similarity
4. Save substituted summary → feed into semantic_checker.py
"""

import re
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score
from Levenshtein import distance as levenshtein_distance
from pathlib import Path
from scipy.optimize import linear_sum_assignment

def build_substitution_map(pred_map, gt_map, verbose=False):
    """
    One-to-one matching: pred description → GT description
    using Jaccard similarity (word overlap) as the score.
    Uses Hungarian algorithm to find optimal assignment.
    """
    pred_items = list(pred_map.items())  # [(desc, var), ...]
    gt_items   = list(gt_map.items())    # [(desc, letter), ...]

    if not pred_items or not gt_items:
        return {}, []

    # Build similarity matrix (pred × gt)
    n_pred = len(pred_items)
    n_gt   = len(gt_items)
    sim_matrix = np.zeros((n_pred, n_gt))

    for i, (pred_desc, _) in enumerate(pred_items):
        for j, (gt_desc, _) in enumerate(gt_items):
            sim_matrix[i, j] = jaccard(pred_desc, gt_desc)

    # Hungarian algorithm on cost matrix (1 - similarity)
    cost_matrix = 1 - sim_matrix
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    var_to_gt  = {}
    match_info = []

    # assigned pairs
    assigned_gt = set()
    for i, j in zip(row_ind, col_ind):
        pred_desc, pred_var = pred_items[i]
        gt_desc,   gt_letter = gt_items[j]
        sim  = sim_matrix[i, j]
        var_to_gt[pred_var] = gt_letter
        assigned_gt.add(j)
        match_info.append(
            f"{pred_var}('{pred_desc}') → {gt_letter}"
            f"('{gt_desc}') [jaccard={sim:.2f}]"
        )

    # unmatched pred vars — assign their pred_var as-is (no substitution)
    for i, (pred_desc, pred_var) in enumerate(pred_items):
        if i not in row_ind:
            var_to_gt[pred_var] = pred_var
            match_info.append(f"{pred_var} → UNMATCHED")

    if verbose:
        for m in match_info:
            print(f"  {m}")

    return var_to_gt, match_info

# ══════════════════════════════════════════════════════════════
# 1. PARSING
# ══════════════════════════════════════════════════════════════

LTL_KEYWORDS = {"G","F","X","U","S","Y","O","H","TRUE","FALSE","true","false"}

def parse_ap_block(response_text):
    """
    Parse lines of format:  var : "description"
    Returns dict: {description_lowercase: variable}
    Handles both GT format (desc: var) and LLM format (var : "desc")
    """
    mappings = {}
    if not response_text or str(response_text).strip() in ("nan",""):
        return mappings

    text = str(response_text)

    # Try to isolate AP block (before formulaToFind)
    ap_section = re.split(r'formulaToFind', text, maxsplit=1)[0]

    for line in re.split(r'[\n;]', ap_section):
        line = line.strip().strip('*').strip('#').strip()
        if not line or ':' not in line:
            continue
        # skip markdown headers and code fences
        if line.startswith('```') or line.startswith('##') or line.startswith('//'):
            continue

        parts = line.split(':', 1)
        left  = parts[0].strip().strip('"').strip("'")
        right = parts[1].strip().strip('"').strip("'").lower()

        # Detect format: if left matches [a-zA-Z][a-zA-Z0-9]* it's var : desc
        if re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', left):
            var, desc = left, right
        else:
            # desc : var  (GT format)
            desc = left.replace('_', ' ').lower()
            var  = right.strip()

        if var and desc:
            mappings[desc] = var

    return mappings


def parse_gt_ap(ap_string):
    """
    Parse GT format: 'user_authentication_attempt: q, access_granted: p'
    Returns {description: variable_letter}
    """
    mappings = {}
    if not ap_string or str(ap_string).strip() in ("nan",""):
        return mappings
    for part in str(ap_string).split(","):
        part = part.strip()
        if ":" in part:
            desc, var = part.split(":", 1)
            mappings[desc.strip().replace("_"," ").lower()] = var.strip()
    return mappings


def extract_ltl_from_response(response_text):
    """Extract formulaToFind line and convert AST to standard LTL."""
    if not response_text or str(response_text).strip() in ("nan",""):
        return ""
    # use refined response if present
    text = str(response_text)
    match = re.search(r'formulaToFind\s*=\s*(.+?)(?:\n|$)', text, re.DOTALL)
    if not match:
        return ""
    ast = match.group(1).strip().rstrip('`').strip()
    return _convert_ast_to_ltl(ast)


def _convert_ast_to_ltl(ast):
    ltl = ast
    ltl = re.sub(r'AtomicProposition\s*\(\s*["\']([^"\']+)["\']\s*\)', r'\1', ltl)
    ltl = re.sub(r'Eventually\s*\(', 'F(', ltl)
    ltl = re.sub(r'Always\s*\(', 'G(', ltl)
    ltl = re.sub(r'Next\s*\(', 'X(', ltl)
    ltl = re.sub(r'LNot\s*\(', '!(', ltl)
    ltl = _replace_binary_op(ltl, 'LImplies', '->')
    ltl = _replace_binary_op(ltl, 'LAnd', '&')
    ltl = _replace_binary_op(ltl, 'LOr', '|')
    ltl = _replace_binary_op(ltl, 'LEquiv', '<->')
    ltl = _replace_binary_op(ltl, 'Until', 'U')
    ltl = _replace_binary_op(ltl, 'Since', 'S')
    return ltl.strip()


def _replace_binary_op(formula, func_name, op_symbol):
    result = formula
    while func_name + '(' in result:
        idx   = result.find(func_name + '(')
        start = idx + len(func_name) + 1
        depth, i = 1, start
        while i < len(result) and depth > 0:
            if result[i] == '(':   depth += 1
            elif result[i] == ')': depth -= 1
            i += 1
        inner     = result[start:i-1]
        comma_idx = _top_comma(inner)
        if comma_idx == -1:
            break
        arg1 = inner[:comma_idx].strip()
        arg2 = inner[comma_idx+1:].strip()
        result = result[:idx] + f'({arg1} {op_symbol} {arg2})' + result[i:]
    return result


def _top_comma(s):
    depth = 0
    for i, c in enumerate(s):
        if c == '(':   depth += 1
        elif c == ')': depth -= 1
        elif c == ',' and depth == 0:
            return i
    return -1


# ══════════════════════════════════════════════════════════════
# 2. AP EVALUATION (Jaccard + Levenshtein + P/R/F1)
#    Compare on DESCRIPTIONS (right side), not variable names
# ══════════════════════════════════════════════════════════════

def jaccard(a, b):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    return len(sa & sb) / len(sa | sb) if sa | sb else 0


def evaluate_ap(gt_map, pred_map):
    """
    gt_map:   {description: letter}  e.g. {'user authentication attempt': 'q'}
    pred_map: {description: var}     e.g. {'authentication attempt holds': 'auth'}

    Match on descriptions using best Jaccard.
    Returns dict of metrics.
    """
    gt_descs   = list(gt_map.keys())
    pred_descs = list(pred_map.keys())

    # ── Jaccard (avg best match per GT desc) ──
    jac_scores = []
    lev_scores = []
    for g in gt_descs:
        if pred_descs:
            best_jac = max(jaccard(g, p) for p in pred_descs)
            best_lev = min(levenshtein_distance(g, p) for p in pred_descs)
        else:
            best_jac, best_lev = 0, 999
        jac_scores.append(best_jac)
        lev_scores.append(best_lev)

    avg_jaccard     = np.mean(jac_scores) if jac_scores else 0
    avg_levenshtein = np.mean(lev_scores) if lev_scores else 999

    # ── Precision / Recall / F1 at set level ──
    # A predicted desc is matched if best Jaccard to any GT desc > 0.3
    THRESHOLD = 0.3
    all_descs   = list(set(gt_descs) | set(pred_descs))
    gt_labels   = [1 if d in gt_descs   else 0 for d in all_descs]
    pred_labels = [1 if d in pred_descs else 0 for d in all_descs]

    p  = precision_score(gt_labels, pred_labels, zero_division=0)
    r  = recall_score   (gt_labels, pred_labels, zero_division=0)
    f1 = f1_score       (gt_labels, pred_labels, zero_division=0)

    return {
        "gt_count"      : len(gt_descs),
        "pred_count"    : len(pred_descs),
        "Precision"     : round(p  * 100, 2),
        "Recall"        : round(r  * 100, 2),
        "F1"            : round(f1 * 100, 2),
        "Jaccard"       : round(avg_jaccard, 3),
        "Levenshtein"   : round(avg_levenshtein, 2),
    }


# ══════════════════════════════════════════════════════════════
# 3. VARIABLE SUBSTITUTION
#    Match pred description → GT description → GT letter
#    Replace pred var with GT letter in LTL formula
# ══════════════════════════════════════════════════════════════

def build_substitution_map(pred_map, gt_map, verbose=False):
    """
    For each predicted (desc→var), find closest GT description,
    get its GT letter. Return {pred_var: gt_letter} and match info.
    """
    var_to_gt  = {}
    match_info = []

    for pred_desc, pred_var in pred_map.items():
        best_gt_desc, best_gt_letter, best_dist = None, pred_var, float("inf")

        for gt_desc, gt_letter in gt_map.items():
            dist = levenshtein_distance(pred_desc, gt_desc)
            if dist < best_dist:
                best_dist      = dist
                best_gt_desc   = gt_desc
                best_gt_letter = gt_letter

        var_to_gt[pred_var] = best_gt_letter
        match_info.append(
            f"{pred_var}('{pred_desc}') → {best_gt_letter}"
            f"('{best_gt_desc}') [dist={best_dist}]"
        )

    if verbose:
        print("  " + " | ".join(match_info))

    return var_to_gt, match_info


def substitute_in_formula(ltl_formula, var_to_gt):
    """Replace pred vars with GT letters in formula."""
    result = str(ltl_formula)
    for pred_var, gt_letter in sorted(var_to_gt.items(),
                                      key=lambda x: len(x[0]), reverse=True):
        result = re.sub(rf'\b{re.escape(pred_var)}\b', gt_letter, result)
    return result


# ══════════════════════════════════════════════════════════════
# 4. MAIN PIPELINE
# ══════════════════════════════════════════════════════════════

def run_pipeline(input_csv, verbose=True):
    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} rows from {input_csv}")
    print(f"Columns: {df.columns.tolist()}")

    # detect which response column to use
    has_refined = "Refined Response" in df.columns

    ap_rows      = []   # for AP evaluation
    summary_rows = {}   # for substituted LTL summary
    review_rows  = []   # for manual review

    for _, row in df.iterrows():
        nl       = row["Natural Language"]
        gt_ltl   = row["Ground Truth"]
        gt_ap    = row.get("Atomic Proposition", "")
        model    = row["Model"]
        approach = row["Approach"]
        col_name = f"{model}_{approach}"

        # pick best response
        refined = str(row.get("Refined Response","")).strip()
        initial = str(row.get("Initial Response","")).strip()
        response = (refined if refined not in ("nan","","None") 
                    and has_refined else initial)

        # ── parse ──
        gt_map   = parse_gt_ap(gt_ap)
        pred_map = parse_ap_block(response)
        ltl_raw  = extract_ltl_from_response(response)

        # ── AP evaluation ──
        ap_metrics = evaluate_ap(gt_map, pred_map)
        ap_rows.append({
            "Model"            : model,
            "Approach"         : approach,
            "Natural Language" : nl[:70],
            "GT AP"            : gt_ap,
            "Predicted AP"     : str(pred_map),
            **ap_metrics,
        })

        # ── variable substitution ──
        var_to_gt, match_info = build_substitution_map(pred_map, gt_map, verbose)
        ltl_subst = substitute_in_formula(ltl_raw, var_to_gt)

        # ── review row ──
        review_rows.append({
            "Natural Language"    : nl[:70],
            "Model/Approach"      : col_name,
            "GT LTL"             : gt_ltl,
            "GT AP"              : gt_ap,
            "Predicted AP (raw)" : str(pred_map),
            "LTL raw"            : ltl_raw,
            "Var Matches"        : " | ".join(match_info),
            "LTL substituted"    : ltl_subst,
        })

        # ── build summary ──
        if nl not in summary_rows:
            summary_rows[nl] = {
                "Natural Language": nl,
                "Ground Truth":     gt_ltl,
            }
        summary_rows[nl][col_name] = ltl_subst

    # ── DataFrames ──
    ap_detailed = pd.DataFrame(ap_rows)
    review_df   = pd.DataFrame(review_rows)
    summary_df  = pd.DataFrame(list(summary_rows.values()))

    # ── AP aggregated ──
    ap_agg = (
        ap_detailed
        .groupby(["Model","Approach"])
        .agg(
            Samples         = ("Natural Language", "count"),
            Precision       = ("Precision",    "mean"),
            Recall          = ("Recall",       "mean"),
            F1              = ("F1",           "mean"),
            Jaccard         = ("Jaccard",      "mean"),
            Levenshtein     = ("Levenshtein",  "mean"),
            avg_GT_APs      = ("gt_count",     "mean"),
            avg_Pred_APs    = ("pred_count",   "mean"),
        )
        .round(2)
        .reset_index()
    )

    return ap_detailed, ap_agg, review_df, summary_df


# ══════════════════════════════════════════════════════════════
# 5. RUN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    input_csv = sys.argv[1] if len(sys.argv) > 1 else "nl2ltl_raw_responses.csv"

    ap_detailed, ap_agg, review_df, summary_df = run_pipeline(input_csv, verbose=True)

    print("\n=== AP EXTRACTION RESULTS ===")
    print(ap_agg.to_string(index=False))

    print("\n=== SUBSTITUTED SUMMARY (first 3 rows) ===")
    print(summary_df.head(3).to_string())

    # save
    ap_detailed.to_csv("no_ap_ap_detailed.csv",   index=False)
    ap_agg.to_csv     ("no_ap_ap_aggregated.csv",  index=False)
    review_df.to_csv  ("no_ap_review.csv",         index=False)
    summary_df.to_csv ("no_ap_substituted_summary.csv", index=False)

    print("\nSaved:")
    print("  no_ap_ap_detailed.csv")
    print("  no_ap_ap_aggregated.csv")
    print("  no_ap_review.csv          ← manual review before semantic check")
    print("  no_ap_substituted_summary.csv  ← feed into semantic_checker.py")