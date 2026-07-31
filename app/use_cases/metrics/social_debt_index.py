import math

MACRO_WEIGHTS = {
    "A": 0.15, "B": 0.15, "C": 0.20, "D": 0.10,
    "E": 0.20, "F": 0.10, "G": 0.10, "H": 0.0
}

MACRO_RISK_FACTORS = {
    "A": 1.5, "B": 1.2, "C": 1.8, "D": 1.1,
    "E": 2.0, "F": 1.2, "G": 1.3, "H": 1.0
}

def calculate_shannon_entropy(probabilities):
    entropy = 0
    for p in probabilities:
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def calculate_issue_metrics(comments):
    """
    comments is a list of dicts with:
    - code: str (macro cause A-H)
    - is_noise: bool
    """
    total_comments = len(comments)
    if total_comments == 0:
        return {"sdi_score": 0.0, "sdi_status": "Low", "macro_diversity": 0.0}

    valid_comments = [c for c in comments if not c.get('is_noise', False) and c.get('code') != 'H']
    noise_comments = [c for c in comments if c.get('is_noise', False)]
    h_comments = [c for c in comments if not c.get('is_noise', False) and c.get('code') == 'H']

    N = len(valid_comments)
    total_relevant = N + len(h_comments)

    if total_relevant == 0:
        return {"sdi_score": 0.0, "sdi_status": "Low", "macro_diversity": 0.0, "noise_ratio": len(noise_comments)/total_comments}

    macro_counts = {k: 0 for k in MACRO_WEIGHTS.keys()}
    for c in valid_comments:
        code = c.get('code')
        if code in macro_counts:
            macro_counts[code] += 1
    
    probabilities = [count / total_relevant for count in macro_counts.values()]
    macro_diversity = calculate_shannon_entropy(probabilities)

    max_entropy = math.log2(7) if len([c for c in macro_counts if c != 'H']) > 0 else 1
    normalized_diversity = macro_diversity / max_entropy if max_entropy > 0 else 0

    base_debt_score = sum((macro_counts[code] / total_relevant) * MACRO_WEIGHTS[code] * MACRO_RISK_FACTORS[code] 
                          for code in macro_counts if code != 'H')

    volume_penalty = math.log1p(total_comments) * 0.1
    noise_ratio = len(noise_comments) / total_comments
    noise_penalty = noise_ratio * 0.05
    
    sdi = (base_debt_score * (1 + normalized_diversity)) + volume_penalty + noise_penalty
    sdi = min(1.0, max(0.0, sdi))

    if sdi < 0.33:
        status = "Low"
    elif sdi < 0.66:
        status = "Medium"
    else:
        status = "High"

    return {
        "sdi_score": round(sdi, 4),
        "sdi_status": status,
        "macro_diversity": round(macro_diversity, 4),
        "normalized_diversity": round(normalized_diversity, 4),
        "total_comments": total_comments,
        "valid_comments": N,
        "noise_ratio": round(noise_ratio, 4)
    }
