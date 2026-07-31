import re

# =================
# TAGS
# =================
CODE_BLOCK_TAG = "/Code_block_attached."
DIFF_BLOCK_TAG = "/Diff_attached."
ERROR_BLOCK_TAG = "/Error_log_attached."

USER_MENTION_SINGLE = "A GitHub user is mentioned."
USER_MENTION_MULTI = "Multiple GitHub users are mentioned."
USER_REVIEW_SINGLE = "A GitHub user is asked to review or check this."
USER_REVIEW_MULTI = "Multiple GitHub users are asked to review or check this."

USER_LEADING_SINGLE = "A GitHub user is mentioned."
USER_LEADING_MULTI = "Multiple GitHub users are mentioned."

TEAM_MENTION_SINGLE = "A team from a GitHub organization is mentioned."
TEAM_MENTION_MULTI = "Multiple teams from GitHub organizations are mentioned."
TEAM_REVIEW_SINGLE = "A team from a GitHub organization is asked to review or check the comment."
TEAM_REVIEW_MULTI = "Multiple teams from GitHub organizations are asked to review or check the comment."

TEAM_LEADING_SINGLE = "A team from a GitHub organization is mentioned."
TEAM_LEADING_MULTI = "Multiple teams from GitHub organizations are mentioned."

BOT_TAG = "/automated_bot_message"

# =================
# REGEX
# =================
INLINE_RE = re.compile(r'`([^`\n]+)`')
INLINE_CODE_NO_BACKTICKS_RE = re.compile(
    r'(?m)^\s*["\']?\s*(?:'
    r'(?:private|public|protected|readonly|const|let|var|def|class|return|import|from)\b'
    r'|[A-Za-z_][A-Za-z0-9_]*\s*[:=]\s*[^,\n]+'
    r'|.*//.*'
    r')'
    r'.*$'
)

FENCED_BLOCK_RE = re.compile(r'```([A-Za-z0-9_+\-]*)\s*\n(.*?)\n\s*```', re.DOTALL)
ERROR_SIGNALS = re.compile(
    r"""(?im)^(?:ERROR|FAIL|FAILED|FATAL)[:\s]|Traceback \(most recent call last\)|={6,}\s*\n(?:FAIL|ERROR):|FAILED \(errors=\d+|\b\d+\s+(?:test|tests)\s+failed\b|panic:\s+runtime\s+error|^\s*[A-Za-z_][A-Za-z0-9_]*Error:|^\s*Exception:|^\s*Caused by:|\bexit code\s+\d+\b""",
    re.VERBOSE
)
PROGRAMMING_LANGS = {
    "python", "py", "javascript", "js", "typescript", "ts",
    "java", "c", "cpp", "c++", "csharp", "cs", "go", "ruby", "rb",
    "php", "swift", "kotlin", "scala", "rust", "r", "sql",
    "bash", "shell", "sh", "zsh", "powershell", "ps1",
    "html", "css", "scss", "sass", "xml", "json", "yaml", "yml",
    "dockerfile", "makefile", "gradle"
}
DIFF_GIT_RE = re.compile(r'(?m)^\s*diff --git\b')
DIFF_HUNK_RE = re.compile(r'(?m)^\s*@@\s*-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s*@@')
DIFF_FILE_OLD_RE = re.compile(r'(?m)^\s*---\s+[ab]/.+')
DIFF_FILE_NEW_RE = re.compile(r'(?m)^\s*\+\+\+\s+[ab]/.+')
DIFF_INDEX_RE = re.compile(r'(?m)^\s*index\s+[0-9a-f]+\.\.[0-9a-f]+\s+\d+')

TEAM_MENTION_RE = re.compile(r'(?<!\w)@([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)')
USER_MENTION_RE = re.compile(r'(?<!\w)@([A-Za-z0-9_.-]+)\b')
COMMIT_LINE_REFERENCE_RE = re.compile(r'(?i)\bLine\s+\d+\s+in\s+\[?/hash_reference\]?\([^)]+\)')
CC_USER_MENTION_RE = re.compile(r'(?i)(?<!\w)/?cc\s+@[A-Za-z0-9_.-]+(?:\s+as well)?')
APPROVAL_NOTIFICATION_RE = re.compile(r'(?is)\[APPROVALNOTIFIER\].*?\bAPPROVED\b(?:\*\*)?')
SUGGESTION_RE = re.compile(r'(?im)^\s*#{0,6}\s*suggestion\s*$')

def clean_inline_code(text):
    if not isinstance(text, str): return ""
    return INLINE_RE.sub("/inline_code", text)

def clean_inline_code_without_backticks(text):
    if not isinstance(text, str): return ""
    return INLINE_CODE_NO_BACKTICKS_RE.sub("/inline_code", text)

def classify_fenced_block(lang, body):
    lang = (lang or "").strip().lower()
    if lang == "diff": return DIFF_BLOCK_TAG
    diff_signals = 0
    if DIFF_GIT_RE.search(body): diff_signals += 1
    if DIFF_HUNK_RE.search(body): diff_signals += 1
    if DIFF_FILE_OLD_RE.search(body): diff_signals += 1
    if DIFF_FILE_NEW_RE.search(body): diff_signals += 1
    if DIFF_INDEX_RE.search(body): diff_signals += 1
    if diff_signals >= 2: return DIFF_BLOCK_TAG
    if lang and lang in PROGRAMMING_LANGS: return CODE_BLOCK_TAG
    if ERROR_SIGNALS.search(body): return ERROR_BLOCK_TAG
    return CODE_BLOCK_TAG

def replace_fenced_blocks(text):
    if not isinstance(text, str): return ""
    def repl(m):
        return classify_fenced_block(m.group(1), m.group(2))
    return FENCED_BLOCK_RE.sub(repl, text)

def clean_approval_notifications(text):
    if not isinstance(text, str): return ""
    return APPROVAL_NOTIFICATION_RE.sub("/approval_notification", text)

def clean_code_suggestions(text):
    if not isinstance(text, str): return ""
    return SUGGESTION_RE.sub("/code_suggestion", text)

def clean_cc_user_mentions(text):
    if not isinstance(text, str): return ""
    return CC_USER_MENTION_RE.sub(USER_MENTION_SINGLE, text)

def _anonymize_inline_mentions(text):
    text = COMMIT_LINE_REFERENCE_RE.sub("/commit_line_reference", text)
    text = TEAM_MENTION_RE.sub("a team from a GitHub organization", text)
    text = USER_MENTION_RE.sub("a GitHub user", text)
    return text

def clean_comment(text: str) -> str:
    """Orchestrates the full cleaning pipeline for a single comment."""
    if not isinstance(text, str): return ""
    
    text = clean_inline_code(text)
    text = clean_inline_code_without_backticks(text)
    text = replace_fenced_blocks(text)
    text = clean_approval_notifications(text)
    text = clean_code_suggestions(text)
    text = clean_cc_user_mentions(text)
    text = _anonymize_inline_mentions(text)
    
    # We strip and clean redundant spaces at the end
    text = re.sub(r'\s+', ' ', text).strip()
    return text
