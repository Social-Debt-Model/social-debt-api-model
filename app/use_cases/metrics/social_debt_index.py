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
    
    total_comments_by_issue = {issue_id: len(comments) for issue_id, comments in issues_data.items()}

    for issue_id, comments in issues_data.items():
        for c in comments:
            if c.get("is_noise", False) or c.get("code", "H") == "H":
                continue
            
            micro_names = [m.get("cause_name") for m in c.get("microcauses", [])]
            micro_scores = [m.get("similarity", 0.0) for m in c.get("microcauses", [])]
            micro_types = [m.get("cause_type") for m in c.get("microcauses", [])]

            smells = []
            risks = []
            for m in c.get("microcauses", []):
                for s in m.get("community_smells", []):
                    smells.extend([x.strip() for x in str(s).split('|') if x.strip()])
                for r in m.get("risks", []):
                    risks.extend([x.strip() for x in str(r).split('|') if x.strip()])
                
            smell_repr = str(sorted(list(set(smells)))) if smells else "[]"
            risk_repr = str(sorted(list(set(risks)))) if risks else "[]"

            rows.append({
                "issue_number": issue_id,
                "final_cause_for_analysis": c.get("code", "H"),
                "top_microcause_names_list": micro_names,
                "top_microcause_scores_list": micro_scores,
                "top_microcause_types_list": micro_types,
                "community_smells_repr": smell_repr,
                "risks_repr": risk_repr,
                "comment_body_clean_final": c.get("cleaned_text", "")
            })

    if not rows:
        return {}

    df = pd.DataFrame(rows)

    def aggregate_issue(group):
        micro_counter = Counter()
        type_counter = Counter()
        smell_counter = Counter()
        risk_counter = Counter()
        macro_counter = Counter()

        for _, row in group.iterrows():
            cause = row["final_cause_for_analysis"]
            if cause != "H":
                macro_counter[cause] += 1
            micro_names = row["top_microcause_names_list"]
            micro_scores = row["top_microcause_scores_list"]
            micro_types = row["top_microcause_types_list"]
            for name, score in zip(micro_names, micro_scores):
                micro_counter[name] += float(score)
            for m_type in micro_types:
                if m_type:
                    type_counter[m_type] += 1
            if row["community_smells_repr"] != "[]":
                smell_counter[row["community_smells_repr"]] += 1
            if row["risks_repr"] != "[]":
                risk_counter[row["risks_repr"]] += 1

        return pd.Series({
            "clean_comment_count": len(group),
            "dominant_macrocauses": macro_counter.most_common(5),
            "dominant_microcauses": micro_counter.most_common(5),
            "dominant_microcause_types": type_counter.most_common(5),
            "dominant_community_smells": smell_counter.most_common(5),
            "dominant_risks": risk_counter.most_common(5),
            "issue_text": "\n\n".join(group["comment_body_clean_final"].astype(str))
        })

    df_issue_adaptive = df.groupby("issue_number").apply(aggregate_issue, include_groups=False).reset_index()

    df_issue_adaptive["comment_count"] = df_issue_adaptive["issue_number"].map(total_comments_by_issue).fillna(0).astype(int)

    df_issue_adaptive["macro_diversity"] = df_issue_adaptive["dominant_macrocauses"].apply(count_items)
    df_issue_adaptive["micro_diversity"] = df_issue_adaptive["dominant_microcauses"].apply(count_items)
    df_issue_adaptive["smell_diversity"] = df_issue_adaptive["dominant_community_smells"].apply(count_items)
    df_issue_adaptive["risk_diversity"] = df_issue_adaptive["dominant_risks"].apply(count_items)
    df_issue_adaptive["top_macro_frequency"] = df_issue_adaptive["dominant_macrocauses"].apply(top_frequency)
    df_issue_adaptive["top_micro_score"] = df_issue_adaptive["dominant_microcauses"].apply(top_score)
    df_issue_adaptive["top_smell_frequency"] = df_issue_adaptive["dominant_community_smells"].apply(top_frequency)
    df_issue_adaptive["top_risk_frequency"] = df_issue_adaptive["dominant_risks"].apply(top_frequency)

    sdi_features = [
        "clean_comment_count", 
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
    
    if len(df_issue_adaptive) > 0:
        normalized_values = scaler.fit_transform(df_issue_adaptive[sdi_features])
        for idx, col in enumerate(sdi_features):
            df_issue_adaptive[f"{col}_norm"] = normalized_values[:, idx]

        sdi_variables = [
            "clean_comment_count_norm", 
            "macro_diversity_norm",
            "top_macro_frequency_norm",
            "top_micro_score_norm",
            "top_smell_frequency_norm",
            "top_risk_frequency_norm"
        ]

        df_issue_adaptive["social_debt_index"] = df_issue_adaptive[sdi_variables].mean(axis=1)

        q1 = df_issue_adaptive["social_debt_index"].quantile(0.33)
        q2 = df_issue_adaptive["social_debt_index"].quantile(0.66)
        
        def classify_sdi_level(score):
            if pd.isna(score): return "Unknown"
            if score <= q1: return "Low Social Debt"
            elif score <= q2: return "Medium Social Debt"
            else: return "High Social Debt"

        df_issue_adaptive["social_debt_level"] = df_issue_adaptive["social_debt_index"].apply(classify_sdi_level)
    else:
        df_issue_adaptive["social_debt_index"] = 0.0
        df_issue_adaptive["social_debt_level"] = "Unknown"

    results = {}
    for _, row in df_issue_adaptive.iterrows():
        iss_id = row["issue_number"]
        results[str(iss_id)] = {
            "social_debt_index": float(row.get("social_debt_index", 0.0)) if not pd.isna(row.get("social_debt_index")) else 0.0,
            "social_debt_level": row.get("social_debt_level", "Unknown"),
            "comment_count": int(row.get("comment_count", 0)),
            "clean_comment_count": int(row.get("clean_comment_count", 0)),
            "macro_diversity": int(row.get("macro_diversity", 0)),
            "micro_diversity": int(row.get("micro_diversity", 0)),
            "smell_diversity": int(row.get("smell_diversity", 0)),
            "risk_diversity": int(row.get("risk_diversity", 0)),
            "top_macro_frequency": int(row.get("top_macro_frequency", 0)),
            "top_micro_score": float(row.get("top_micro_score", 0.0)),
            "top_smell_frequency": int(row.get("top_smell_frequency", 0)),
            "top_risk_frequency": int(row.get("top_risk_frequency", 0)),
            "dominant_macrocauses": row.get("dominant_macrocauses", []),
            "dominant_microcauses": row.get("dominant_microcauses", []),
            "dominant_microcause_types": row.get("dominant_microcause_types", []),
            "dominant_community_smells": row.get("dominant_community_smells", []),
            "dominant_risks": row.get("dominant_risks", [])
        }
    return results