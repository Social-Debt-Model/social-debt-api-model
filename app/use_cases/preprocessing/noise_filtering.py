import re

HARD_NOISE_EXACT_PATTERNS = [
    r"^/?html_details_block$",
    r"^/?hash_reference$",
    r"^/?benchmark_reference$",
    r"^/?ci_status_reference$",
    r"^/?workflow_ci$",
    r"^/?workflow_review$",
    r"^/?workflow_coordination$",
    r"^/?approval_notification$",
    r"^/?automated_bot_message$",
    r"^/?inline_code$",
    r"^/[a-zA-Z0-9_-]+$",
    r"^[a-f0-9]{7,40}$",
    r"^\s*$"
]

HARD_NOISE_PHRASE_PATTERNS = [
    r"^landed in\s+/?hash_reference$",
    r"^fixed in\s+/?hash_reference$",
    r"^merged in\s+/?hash_reference$",
    r"^closed by\s+/?hash_reference$"
]

SOFT_NOISE_PATTERNS = [
    r"needs rebase",
    r"please rebase",
    r"awaiting triage",
    r"pull request has been approved",
    r"approved",
    r"lgtm",
    r"label has been added",
    r"label has been removed",
    r"new changes are detected",
    r"new commits were pushed",
    r"cannot trigger testing",
    r"trusted user",
    r"merge conflict",
    r"ready for merge",
    r"retesting failed",
    r"assigned",
    r"closed successfully",
    r"reopened",
    r"milestone",
    r"review requested"
]

def es_hard_noise(texto):
    texto = str(texto).strip().lower()
    for patron in HARD_NOISE_EXACT_PATTERNS:
        if re.search(patron, texto):
            return True
    for patron in HARD_NOISE_PHRASE_PATTERNS:
        if re.search(patron, texto):
            return True
    return False

def es_soft_noise(texto):
    texto = str(texto).strip().lower()
    for patron in SOFT_NOISE_PATTERNS:
        if re.search(patron, texto):
            return True
    return False
