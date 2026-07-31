import re

HARD_EXACT_PATTERNS = [
    r"^/?html_details_block\.?$", r"^/?html_image_reference\.?$", r"^/?html_meta_comment\.?$",
    r"^/?code_block_attached\.?$", r"^/?diff_attached\.?$", r"^/?error_log_attached\.?$",
    r"^/?log_reference\.?$", r"^/?hash_reference\.?$", r"^/?url_reference\.?$",
    r"^/?benchmark_reference\.?$", r"^/?ci_status_reference\.?$", r"^/?workflow_ci\.?$",
    r"^/?workflow_review\.?$", r"^/?workflow_coordination\.?$", r"^/?approval_notification\.?$",
    r"^/?automated_cla_check\.?$", r"^/?automated_bot_message\.?$", r"^/?inline_code\.?$",
    r"^a github user is mentioned\.?$", r"^multiple github users are mentioned\.?$",
    r"^a github user is asked to review or check this\.?$", r"^multiple github users are asked to review or check this\.?$",
    r"^/[a-zA-Z0-9_-]+$", r"^/[a-zA-Z0-9_-]+\s+[a-zA-Z0-9_.-]+$",
    r"^[a-f0-9]{7,40}$", r"^\s*$", r"^\?+$", r"^!+$", r"^\)+$", r"^\(+$", r"^eyes:?$", r"^also$", r"^node$", r"^\d+$"
]

HARD_PHRASE_PATTERNS = [
    r"^landed in\s+/?hash_reference\.?$", r"^fixed in\s+/?hash_reference\.?$", r"^merged in\s+/?hash_reference\.?$", r"^closed by\s+/?hash_reference\.?$",
    r"the following test[s]? \*\*?failed\*\*?", r"full pr test history", r"your pr dashboard", r"rerun all failed tests", r"rerun all mandatory failed tests",
    r"please help us cut down on flakes", r"unknown cla label state", r"codecov .* report",
    r"^lgtm label has been added\.?\s*/?html_details_block\.?$", r"^approved label has been added\.?\s*/?html_details_block\.?$",
    r"^pull-request has been approved\.?\s*/?html_details_block\.?$", r"^pull request has been approved\.?\s*/?html_details_block\.?$",
    r"^[a-z0-9_-]+ label has been added\.?\s*/?html_details_block\.?$", r"^[a-z0-9_-]+ label has been removed\.?\s*/?html_details_block\.?$",
    r"new changes are detected\.?\s*lgtm label has been (added|removed)", r"new changes are detected\.?\s*lgtm label has been",
    r"label\(s\).*cannot be applied", r"the label .* cannot be applied", r"repository doesn't have them",
    r"only github organization members can add the label", r"you can only set the release note label", r"release-note-label-needed",
    r"no release-note block was detected", r"github didn't allow me to request pr reviews", r"failed to re-open pr", r"state cannot be changed",
    r"those labels are not set on the issue", r"there are no sig labels on this issue", r"adding label .* merge commits", r"release-note-edit must be used with a release note block",
    r"this request has been marked as needing help from a contributor", r"this request has been marked as suitable for new contributors",
    r"guidelines\s+please ensure that the issue body includes", r"instructions for interacting with me using pr comments",
    r"verify that this patch is reasonable to test", r"i will not automatically test new commits in this pr",
    r"^a github user is mentioned\.?\s*!cat image\s*/?url_reference\s*/?html_details_block\.?$",
    r"^multiple github users are mentioned\.?\s*!cat image\s*/?url_reference\s*/?html_details_block\.?$",
    r"!cat image\s*/?url_reference", r"this issue is currently awaiting triage", r"if a sig or subproject determines this is a relevant issue"
]

PLACEHOLDERS_TO_REMOVE = [
    "/html_details_block", "/html_image_reference", "/html_meta_comment", "/code_block_attached", "/diff_attached",
    "/error_log_attached", "/log_reference", "/hash_reference", "/url_reference", "/benchmark_reference",
    "/ci_status_reference", "/automated_cla_check", "/automated_bot_message", "/approval_notification",
    "/workflow_ci", "/workflow_review", "/workflow_coordination", "/inline_code", "/emoji_celebra", "/emoji_other"
]
GENERIC_USER_PLACEHOLDERS = [
    r"a github user is mentioned\.?", r"multiple github users are mentioned\.?",
    r"a github user is asked to review or check this\.?", r"multiple github users are asked to review or check this\.?"
]
LOW_VALUE_VISUAL_PATTERNS = [r"!cat image", r"!dog image", r"!gif", r"!meme"]
AUTOMATED_PREFIX_MARKERS = [
    "/automated_bot_message", "automated_bot_message", "/approval_notification", "approval_notification",
    "/automated_cla_check", "automated_cla_check", "/workflow_ci", "workflow_ci", "/workflow_review", "workflow_review",
    "/workflow_coordination", "workflow_coordination", "/ci_status_reference", "ci_status_reference"
]

OPERATIONAL_EXACT_PATTERNS = [
    r"^thanks\.?$", r"^thanks!$", r"^thank you\.?$", r"^ok\.?$", r"^okay\.?$", r"^yes\.?$", r"^yeah\.?$", r"^no worries\.?$",
    r"^sounds good\.?$", r"^looks good\.?$", r"^all good!?$", r"^acknowledged\.?$",
    r"^done\.?$", r"^updated\.?$", r"^fixed\.?$", r"^resolved\.?$", r"^addressed\.?$", r"^squashed\.?$", r"^rebased\.?$", r"^rebase\.?$",
    r"^rebase done\.?$", r"^force-pushed\.?$", r"^amended\.?$", r"^ptal\.?$", r"^lgtm\.?$", r"^approved\.?$", r"^approve, thanks!?$",
    r"^looks good to me\.?$", r"^this one is looking good\.?$", r"^ready for review\.?$", r"^ready for another pass\.?$",
    r"^i am reviewing this pr\.?$", r"^reviewing new commits\.?$", r"^ci is green.*$", r"^ci looks good.*$", r"^test was successful!?$",
    r"^tests? passed\.?$", r"^passes locally\.?$", r"^passed locally\.?$", r"^unrelated failure\.?$", r"^seems unrelated\.?$", r"^not a flaking test\.?$"
]

OPERATIONAL_PHRASE_PATTERNS = [
    r"^needs rebase\.?$", r"^please rebase\.?$", r"^rebased to fix conflict.*$", r"^rebased and removed merge commit.*$", r"^i have rebased.*$",
    r"^resolved trivial conflict.*$", r"^resolved conflict.*$", r"^only solved conflicts.*$", r"^merge conflict.*$", r"^done,? thanks.*$",
    r"^fixed now\.?$", r"^should be fixed now\.?$", r"^i have revised it\.?$", r"^i revised it\.?$", r"^i updated it\.?$", r"^i fixed it\.?$",
    r"^i pushed it\.?$", r"^squashed.*$", r"^amended the commit.*$", r"^force-pushed.*$", r"^comments addressed\.?$", r"^all comments have been addressed\.?$",
    r"^adjusted all comments.*$", r"^i think i addressed all the comments\.?$", r"^i have addressed all the comments\.?$",
    r"^i believe i have resolved all review comments\.?$", r"^i believe your comments have been addressed\.?$", r"^friendly ping.*$",
    r"^gentle ping.*$", r"^ping for review.*$", r"^pinging .* for review.*$", r"^please take a look\.?$", r"^can you take a look\.?$",
    r"^can you please take a look\.?$", r"^could you please take a look\.?$", r"^could you help review\.?$", r"^please review\.?$",
    r"^review,? thanks!?$", r"^ptal\.?$", r"^ptal,? thanks!?$", r"^any update\??$", r"^any further feedback\??$", r"^does anything else still need to be done\??$",
    r"^is this still active\??$", r"^can i work on this issue\??$", r"^can i fix\??$", r"^i want to work on this issue\.?$",
    r"^i would like to work on this\.?$", r"^i would like to work on this issue\.?$", r"^i'd like to work on this\.?$",
    r"^i'd like to work on this issue\.?$", r"^may i take this\??$", r"^may i take this issue\??$", r"^i will take this\.?$", r"^i will take this issue\.?$",
    r"^i will take up this issue\.?$", r"^i'll take this\.?$", r"^i'll take this issue\.?$", r"^i picked this up\.?$", r"^i picked up this issue\.?$",
    r"^i'm taking this\.?$", r"^i'm taking this issue\.?$", r"^i will take a look\.?$", r"^i'll take a look\.?$", r"^i'll give it a try\.?$",
    r"^i'll try\.?$", r"^i will try\.?$", r"^(ok|okay|sure|alright|fine),?\s+i (will|can) do it( tomorrow| later)?\.?$",
    r"^i (will|can) do it( tomorrow| later)?\.?$", r"^i'll do it( tomorrow| later)?\.?$",
    r'^based on the quotation:\s*".{1,150}"\s*(ok|okay|sure|alright|fine),?\s+i (will|can) do it( tomorrow| later)?\.?$',
    r'^based on the quotation:\s*".{1,150}"\s*i (will|can) do it( tomorrow| later)?\.?$',
    r'^based on the quotation:\s*".{1,150}"\s*i\'ll do it( tomorrow| later)?\.?$', r"^waiting for this.*$", r"^waiting for .* to be merged.*$",
    r"^this is ready for review\.?$", r"^ready to merge\.?$", r"^ready for merge\.?$", r"^ready to go\.?$", r"^this is good to go\.?$",
    r"^with .* merged, i think this is ready\.?$", r"^i think this is ready\.?$", r"^closed\.$", r"^closed this pr\.?$", r"^closing this issue\.?$",
    r"^closed in favor of.*$", r"^reopening\.?$", r"^i'll close this pr\.?$", r"^i will close this pr\.?$", r"^thanks for the update\.?$",
    r"^thanks for the information\.?$", r"^thanks for the review\.?$", r"^thanks for the feedback\.?$", r"^thanks for checking\.?$",
    r"^thanks for the clarification\.?$", r"^thank you for your guidance\.?$", r"^thank you for the review\.?$", r"^thank you for your feedback\.?$",
    r"^thank you for your comments\.?$", r"^thanks all\.?$", r"^thx all\.?$", r"^manually run the test job again\.?$", r"^re-running ci\.?$",
    r"^rerunning ci\.?$", r"^ci errors look legit\.?$", r"^(the )?ci is green now!?$", r"^test link:.*$", r"^passed in \d+.*$", r"^passed again.*$",
    r"^can the pipeline be triggered again\??.*$", r"^can the pipeline be re-triggered\??.*$", r"^could the pipeline be triggered again\??.*$",
    r"^could the pipeline be re-triggered\??.*$", r"^please trigger the pipeline again\.?.*$", r"^please re-trigger the pipeline\.?.*$",
    r"^please rerun the pipeline\.?.*$", r"^please rerun ci\.?.*$", r"^please rerun the ci\.?.*$", r"^can ci be triggered again\??.*$",
    r"^could ci be triggered again\??.*$", r"^can the checks be triggered again\??.*$", r"^could the checks be triggered again\??.*$",
    r"^please rerun the checks\.?.*$", r"^checks are going now\.?$"
]

def normalize_text(texto):
    return str(texto).strip().lower()

def matches_any_fullmatch(texto, patterns):
    return any(re.fullmatch(pattern, texto, flags=re.DOTALL) for pattern in patterns)

def matches_any_search(texto, patterns):
    return any(re.search(pattern, texto, flags=re.DOTALL) for pattern in patterns)

def starts_with_automated_marker(texto):
    texto = texto.strip().lower()
    return any(texto.startswith(marker) for marker in AUTOMATED_PREFIX_MARKERS)

def is_only_slash_commands(texto):
    lineas = [line.strip() for line in texto.splitlines() if line.strip()]
    if not lineas: return False
    return all(re.fullmatch(r"/[a-zA-Z0-9_-]+(\s+[a-zA-Z0-9_.-]+)?", line) for line in lineas)

def remove_low_value_tokens(texto):
    texto_limpio = texto
    for placeholder in PLACEHOLDERS_TO_REMOVE:
        texto_limpio = texto_limpio.replace(placeholder, " ")
    for pattern in GENERIC_USER_PLACEHOLDERS:
        texto_limpio = re.sub(pattern, " ", texto_limpio)
    for pattern in LOW_VALUE_VISUAL_PATTERNS:
        texto_limpio = re.sub(pattern, " ", texto_limpio)
    texto_limpio = re.sub(r"\s+", " ", texto_limpio).strip()
    return texto_limpio

def es_hard_noise(texto):
    texto = normalize_text(texto)
    if starts_with_automated_marker(texto): return True
    if matches_any_fullmatch(texto, HARD_EXACT_PATTERNS): return True
    if is_only_slash_commands(texto): return True
    if matches_any_search(texto, HARD_PHRASE_PATTERNS): return True
    texto_limpio = remove_low_value_tokens(texto)
    if len(texto_limpio) <= 3: return True
    return False

def es_operational_noise(texto):
    texto = normalize_text(texto)
    if es_hard_noise(texto): return False
    if matches_any_fullmatch(texto, OPERATIONAL_EXACT_PATTERNS): return True
    if matches_any_fullmatch(texto, OPERATIONAL_PHRASE_PATTERNS): return True
    return False

def get_noise_level(texto: str) -> str:
    """Returns 'hard_noise', 'operational_noise', or 'useful' for the given text."""
    if es_hard_noise(texto):
        return "hard_noise"
    if es_operational_noise(texto):
        return "operational_noise"
    return "useful"
