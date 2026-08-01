import pandas as pd
from collections import Counter
from sklearn.preprocessing import MinMaxScaler

def count_items(x):
    if isinstance(x, list): return len(x)
    return 0

def top_frequency(x):
    if isinstance(x, list) and len(x) > 0: return x[0][1]
    return 0
def top_score(x):
    if isinstance(x, list) and len(x) > 0: return x[0][1]
    return 0

def calculate_batch_sdi(issues_data: dict) -> dict:
    rows = []
    for issue_id, comments in issues_data.items():
        for c in comments:
            # DO NOT SKIP NOISE! We need them for the total comment count!
            
            # Extract microcauses
            micro_names = [m.get("cause_name") for m in c.get("microcauses", [])]
            micro_scores = [m.get("similarity", 0.0) for m in c.get("microcauses", [])]

            # Extract smells and risks
            smells = []
            risks = []
            for m in c.get("microcauses", []):
                smells.extend(m.get("community_smells", []))
                risks.extend(m.get("risks", []))

            rows.append({
                "issue_number": issue_id,
                "final_cause_for_analysis": c.get("code", "H"),
                "top_microcause_names_list": micro_names,
                "top_microcause_scores_list": micro_scores,
                "community_smells_list": smells,
                "risks_list": risks,
                "comment_body_clean_final": c.get("cleaned_text", "")
            })

    if not rows:
        return {}

    df = pd.DataFrame(rows)

    def aggregate_issue(group):
        micro_counter = Counter()
        smell_counter = Counter()
        risk_counter = Counter()
        macro_counter = Counter()

        for _, row in group.iterrows():
            macro_counter[row["final_cause_for_analysis"]] += 1
            micro_names = row["top_microcause_names_list"]
            micro_scores = row["top_microcause_scores_list"]
            for name, score in zip(micro_names, micro_scores):
                micro_counter[name] += float(score)
            for smell in row["community_smells_list"]:
                smell_counter[smell] += 1
            for risk in row["risks_list"]:
                risk_counter[risk] += 1

        return pd.Series({
            "comment_count": len(group),
            "dominant_macrocauses": macro_counter.most_common(5),
            "dominant_microcauses": micro_counter.most_common(5),
            "dominant_community_smells": smell_counter.most_common(5),
            "dominant_risks": risk_counter.most_common(5),
            "issue_text": "\n\n".join(group["comment_body_clean_final"].astype(str))
        })

    # FutureWarning fix for pandas
    df_issue_adaptive = df.groupby("issue_number").apply(aggregate_issue, include_groups=False).reset_index()

    # Calculate diversity and frequencies
    df_issue_adaptive["macro_diversity"] = df_issue_adaptive["dominant_macrocauses"].apply(count_items)
    df_issue_adaptive["micro_diversity"] = df_issue_adaptive["dominant_microcauses"].apply(count_items)
    df_issue_adaptive["smell_diversity"] = df_issue_adaptive["dominant_community_smells"].apply(count_items)
    df_issue_adaptive["risk_diversity"] = df_issue_adaptive["dominant_risks"].apply(count_items)
    df_issue_adaptive["top_macro_frequency"] = df_issue_adaptive["dominant_macrocauses"].apply(top_frequency)
    df_issue_adaptive["top_micro_score"] = df_issue_adaptive["dominant_microcauses"].apply(top_score)
    df_issue_adaptive["top_smell_frequency"] = df_issue_adaptive["dominant_community_smells"].apply(top_frequency)
    df_issue_adaptive["top_risk_frequency"] = df_issue_adaptive["dominant_risks"].apply(top_frequency)

    sdi_features = [
        "comment_count",
        "macro_diversity",
        "micro_diversity",
        "smell_diversity",
        "risk_diversity",
        "top_macro_frequency",
        "top_micro_score",
        "top_smell_frequency",
        "top_risk_frequency"
    ]

    scaler = MinMaxScaler()
    normalized_values = scaler.fit_transform(df_issue_adaptive[sdi_features])
    df_sdi_norm = pd.DataFrame(normalized_values, columns=[f"{col}_norm" for col in sdi_features])

    df_issue_adaptive = pd.concat([df_issue_adaptive.reset_index(drop=True), df_sdi_norm], axis=1)

    sdi_variables = [
        "comment_count_norm",
        "macro_diversity_norm",
        "top_macro_frequency_norm",
        "top_micro_score_norm",
        "top_smell_frequency_norm",
        "top_risk_frequency_norm"
    ]

    df_issue_adaptive["social_debt_index"] = df_issue_adaptive[sdi_variables].mean(axis=1)

    def classify_sdi_level(score, q1, q2):
        if pd.isna(score): return "Unknown"
        if score <= q1: return "Low Social Debt"
        elif score <= q2: return "Medium Social Debt"
        else: return "High Social Debt"

    if len(df_issue_adaptive) > 0:
        q1 = df_issue_adaptive["social_debt_index"].quantile(0.33)
        q2 = df_issue_adaptive["social_debt_index"].quantile(0.66)
        df_issue_adaptive["social_debt_level"] = df_issue_adaptive["social_debt_index"].apply(lambda x: classify_sdi_level(x, q1, q2))
    else:
        df_issue_adaptive["social_debt_level"] = "Unknown"

    results = {}
    for _, row in df_issue_adaptive.iterrows():
        iss_id = row["issue_number"]
        results[str(iss_id)] = {
            "social_debt_index": float(row["social_debt_index"]) if not pd.isna(row["social_debt_index"]) else 0.0,
            "social_debt_level": row.get("social_debt_level", "Unknown"),
            "comment_count": int(row["comment_count"]),
            "macro_diversity": int(row["macro_diversity"]),
            "micro_diversity": int(row["micro_diversity"]),
            "smell_diversity": int(row["smell_diversity"]),
            "risk_diversity": int(row["risk_diversity"]),
            "top_macro_frequency": int(row["top_macro_frequency"]),
            "top_micro_score": float(row["top_micro_score"]),
            "top_smell_frequency": int(row["top_smell_frequency"]),
            "top_risk_frequency": int(row["top_risk_frequency"]),
            "dominant_macrocauses": row["dominant_macrocauses"],
            "dominant_microcauses": row["dominant_microcauses"],
            "dominant_community_smells": row["dominant_community_smells"],
            "dominant_risks": row["dominant_risks"]
        }
    return results
