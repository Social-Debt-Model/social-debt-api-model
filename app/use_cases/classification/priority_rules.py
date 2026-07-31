import re

CAUSES = {
    "A": "Communication and shared understanding breakdowns",
    "B": "Coordination and workflow misalignment",
    "C": "Technical complexity, compatibility, and system constraints",
    "D": "Organizational and procedural workflow constraints",
    "E": "Collaboration and interpersonal tensions",
    "F": "Knowledge, documentation, and standards deficiencies",
    "G": "Resource, tooling, access, and validation dependencies",
    "H": "No identifiable sociotechnical cause",
}

VALID_CODES = set(CAUSES.keys())
UNKNOWN_CODE = "H"
CONFIDENCE_THRESHOLD = 0.70

LABEL_TO_CODE = {label.lower().strip(): code for code, label in CAUSES.items()}

VALIDATION_EVIDENCE_PATTERNS = [
    r"\btests?\b", r"\bci\b", r"continuous integration", r"perf dash", r"dashboard", r"coverage", r"\blogs?\b",
    r"monitoring", r"linter", r"gofmt", r"compile error", r"build error", r"minimal reproduction", r"reproduction",
    r"external tests?", r"local tests?", r"validation job", r"cluster", r"job failed", r"job failing",
    r"ran successfully", r"got a green", r"green build", r"red build",
]

DOCUMENTATION_EVIDENCE_PATTERNS = [
    r"documentation", r"\bdocs\b", r"tutorial", r"pr description", r"pull request description", r"release notes?",
    r"release-note", r"versionchanged", r"deprecation notes?", r"deprecation message", r"document .* behavior",
    r"document .* decision", r"wording", r"instructions", r"standards?", r"easy to understand", r"accurate .* document",
]

COMMUNICATION_EVIDENCE_PATTERNS = [
    r"misunderstood", r"i misunderstood", r"i get you now", r"not sure what you mean", r"what do you mean",
    r"unclear", r"confusing", r"ambiguous", r"clarif(?:y|ication)", r"correct(?:ed|ion) .* analysis",
    r"flawed reasoning", r"correct my analysis", r"reasoning .* flawed", r"i see now", r"i genuinely appreciate .* correct",
]

COORDINATION_EVIDENCE_PATTERNS = [
    r"split .* prs?", r"smaller prs?", r"separate pr", r"follow[- ]?up pr", r"merge order", r"review again",
    r"re-?approve", r"reapproval", r"what happens next", r"next steps", r"availability", r"available .* continue",
    r"consensus", r"same page", r"handoff", r"synchroni[sz]e", r"squashed .* commits?", r"force[- ]?pushed",
    r"resolved .* conflict", r"apply(?:ing|ied) .* comments",
]

PROCEDURAL_EVIDENCE_PATTERNS = [
    r"release branch", r"future release", r"milestones?", r"labels?", r"ticket flags?", r"patch needs improvement",
    r"needs tests", r"needs rebase", r"approval process", r"merge permission", r"triage", r"release process",
    r"upstream adoption", r"eks .* pick this up", r"todo list", r"critical .* todo",
]

INTERPERSONAL_EVIDENCE_PATTERNS = [
    r"unfair", r"dismissive", r"ignored", r"not being heard", r"low trust", r"toxic", r"code of conduct",
    r"interpersonal tension", r"frustrat(?:ed|ion) .* review",
]

TECHNICAL_EVIDENCE_PATTERNS = [
    r"\bconfiguration\b", r"\bconfig\b", r"\bcompatibility\b", r"\bimplementation\b", r"\bruntime\b", r"\bfeature gate\b",
    r"\bcontext cancellation\b", r"\bsecret\b", r"\blogger\b", r"\bselector\b", r"\bsyntax\b", r"\bpackage\b", r"\bclient-go\b",
    r"\bdefault behavior\b", r"\bprevious behavior\b", r"\bpreserve .* behavior\b", r"\bsystem behavior\b", r"\bdependency\b",
    r"\bdependencies\b", r"\barchitecture\b", r"\bedge case\b", r"\bsqlite\b", r"\bmysql\b", r"\boracle\b", r"\bpython 3\.10\b",
]

MINIMAL_H_PATTERNS = [
    r"^\s*(thanks|thank you|thx|ty|lgtm|done|fixed|ping|ptal)\s*[.!:]*\s*$",
    r"^\s*related issue\s*:?\s*/?url_reference\s*$",
    r"^\s*closes\s+/?url_reference\s*$",
    r"^\s*a github user is mentioned\.?\s*$",
    r"^\s*/(?:lgtm|approve|unhold|hold|retest|test|cc|assign|unassign)\s*$",
]

BOT_TEMPLATE_PATTERNS = [
    r"automated_bot_message", r"workflow_ci", r"ci_status_reference", r"flaky tests guide", r"retesting failed pr",
    r"pull-request has been approved", r"lgtm label has been added", r"this issue is currently awaiting triage",
]

SOCIAL_OR_MINIMAL_CONTEXT_PATTERNS = [
    r"\blgtm\b", r"\blooks good\b", r"\bsounds good\b", r"\bthank you\b", r"\bthanks\b", r"\bappreciate\b", r"\bnice work\b",
    r"\bgreat job\b", r"\bkeen to see\b", r"\bfine to me\b", r"\bgot it\b",
]

TECHNICAL_PROBLEM_PATTERNS = [
    r"\berror\b", r"\bfail(?:ed|ing)?\b", r"\bbroken\b", r"\bbug\b", r"\bissue\b", r"\bproblem\b", r"\bconstraint\b",
    r"\bincompatible\b", r"\bregression\b", r"\bdoes not work\b", r"\bcannot\b", r"\bcan't\b",
]

VALIDATION_PROBLEM_PATTERNS = [
    r"\bcannot\b", r"\bcan't\b", r"\bfail(?:ed|ing)?\b", r"\bflake\b", r"\bflaky\b", r"\bretry\b", r"\btimeout\b",
    r"\btrigger\b", r"\bmissing\b", r"\bred\b", r"\bgreen ci\b", r"\badded test case\b", r"\brun\b", r"\bran\b",
]

def contains_any(text, patterns):
    return any(re.search(pattern, str(text), flags=re.IGNORECASE) for pattern in patterns)

def get_rule_candidate(comment):
    text = re.sub(r"\s+", " ", str(comment or "")).strip()
    has_evidence = any([
        contains_any(text, VALIDATION_EVIDENCE_PATTERNS),
        contains_any(text, DOCUMENTATION_EVIDENCE_PATTERNS),
        contains_any(text, COMMUNICATION_EVIDENCE_PATTERNS),
        contains_any(text, COORDINATION_EVIDENCE_PATTERNS),
        contains_any(text, PROCEDURAL_EVIDENCE_PATTERNS),
        contains_any(text, INTERPERSONAL_EVIDENCE_PATTERNS),
        contains_any(text, TECHNICAL_EVIDENCE_PATTERNS),
    ])

    if contains_any(text, BOT_TEMPLATE_PATTERNS) and not has_evidence: return "H", 0.95, "H_bot_template_without_evidence"
    if contains_any(text, MINIMAL_H_PATTERNS) and not has_evidence: return "H", 0.95, "H_minimal_without_evidence"
    if contains_any(text, COMMUNICATION_EVIDENCE_PATTERNS): return "A", 0.90, "A_communication_evidence"
    if contains_any(text, DOCUMENTATION_EVIDENCE_PATTERNS): return "F", 0.88, "F_documentation_evidence"
    if contains_any(text, VALIDATION_EVIDENCE_PATTERNS): return "G", 0.88, "G_validation_tooling_evidence"
    if contains_any(text, INTERPERSONAL_EVIDENCE_PATTERNS): return "E", 0.88, "E_interpersonal_tension_evidence"
    if contains_any(text, PROCEDURAL_EVIDENCE_PATTERNS): return "D", 0.85, "D_procedural_workflow_evidence"
    if contains_any(text, COORDINATION_EVIDENCE_PATTERNS): return "B", 0.85, "B_coordination_workflow_evidence"
    if contains_any(text, TECHNICAL_EVIDENCE_PATTERNS): return "C", 0.82, "C_technical_evidence"
    return None, None, "none"

def strong_override_allowed(comment, rule_code):
    text = re.sub(r"\s+", " ", str(comment or "")).lower().strip()
    if contains_any(text, SOCIAL_OR_MINIMAL_CONTEXT_PATTERNS):
        if rule_code == "G": return contains_any(text, VALIDATION_EVIDENCE_PATTERNS) and contains_any(text, VALIDATION_PROBLEM_PATTERNS)
        if rule_code == "C": return contains_any(text, TECHNICAL_EVIDENCE_PATTERNS) and contains_any(text, TECHNICAL_PROBLEM_PATTERNS)
        if rule_code == "F": return contains_any(text, DOCUMENTATION_EVIDENCE_PATTERNS)
        return False
    if rule_code == "C": return contains_any(text, TECHNICAL_EVIDENCE_PATTERNS) and contains_any(text, TECHNICAL_PROBLEM_PATTERNS)
    if rule_code == "G": return contains_any(text, VALIDATION_EVIDENCE_PATTERNS) and contains_any(text, VALIDATION_PROBLEM_PATTERNS)
    if rule_code == "F": return contains_any(text, DOCUMENTATION_EVIDENCE_PATTERNS)
    return True

def apply_priority_rules(comment, llm_code, llm_conf):
    llm_code = llm_code if llm_code in VALID_CODES else UNKNOWN_CODE
    llm_conf = float(llm_conf or 0.0)

    rule_code, rule_conf, rule_name = get_rule_candidate(comment)
    if rule_code is None: return llm_code, llm_conf, "none"
    if rule_code == "H" and rule_name.startswith("H_"): return "H", max(llm_conf, rule_conf), rule_name
    
    if llm_code == "H" and rule_code != "H":
        if strong_override_allowed(comment, rule_code): return rule_code, max(llm_conf, rule_conf), rule_name + "_override_H"
        return llm_code, llm_conf, "override_rejected_keep_H"

    if llm_conf < CONFIDENCE_THRESHOLD and rule_code != llm_code:
        return rule_code, max(llm_conf, rule_conf), rule_name + "_low_conf_override"
    if rule_code == llm_code: return llm_code, max(llm_conf, rule_conf), rule_name + "_confirmed"
    
    return llm_code, llm_conf, "none_llm_kept"
