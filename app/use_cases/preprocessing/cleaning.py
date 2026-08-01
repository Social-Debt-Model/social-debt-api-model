import os
import re
from pathlib import Path
import pandas as pd
import unicodedata
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

INLINE_RE = re.compile('`([^`\\n]+)`')
INLINE_CODE_NO_BACKTICKS_RE = re.compile('(?m)^\\s*["\\\']?\\s*(?:(?:private|public|protected|readonly|const|let|var|def|class|return|import|from)\\b|[A-Za-z_][A-Za-z0-9_]*\\s*[:=]\\s*[^,\\n]+|.*//.*).*$')
CODE_BLOCK_TAG = '/Code_block_attached.'
DIFF_BLOCK_TAG = '/Diff_attached.'
ERROR_BLOCK_TAG = '/Error_log_attached.'
USER_MENTION_SINGLE = 'A GitHub user is mentioned.'
USER_MENTION_MULTI = 'Multiple GitHub users are mentioned.'
USER_REVIEW_SINGLE = 'A GitHub user is asked to review or check this.'
USER_REVIEW_MULTI = 'Multiple GitHub users are asked to review or check this.'
USER_LEADING_SINGLE = 'A GitHub user is mentioned.'
USER_LEADING_MULTI = 'Multiple GitHub users are mentioned.'
TEAM_MENTION_SINGLE = 'A team from a GitHub organization is mentioned.'
TEAM_MENTION_MULTI = 'Multiple teams from GitHub organizations are mentioned.'
TEAM_REVIEW_SINGLE = 'A team from a GitHub organization is asked to review or check the comment.'
TEAM_REVIEW_MULTI = 'Multiple teams from GitHub organizations are asked to review or check the comment.'
TEAM_LEADING_SINGLE = 'A team from a GitHub organization is mentioned.'
TEAM_LEADING_MULTI = 'Multiple teams from GitHub organizations are mentioned.'
BOT_TAG = '/automated_bot_message'
FENCED_BLOCK_RE = re.compile('```([A-Za-z0-9_+\\-]*)\\s*\\n(.*?)\\n\\s*```', re.DOTALL)
ERROR_SIGNALS = re.compile('\n    (?im)\n    ^(?:ERROR|FAIL|FAILED|FATAL)[:\\s]                # log lines starting with ERROR/FAIL/FAILED/FATAL\n    |Traceback \\(most recent call last\\)            # Python traceback\n    |={6,}\\s*\\n(?:FAIL|ERROR):                      # test separators followed by FAIL/ERROR\n    |FAILED \\(errors=\\d+                            # unittest summary\n    |\\b\\d+\\s+(?:test|tests)\\s+failed\\b           # summary like "3 tests failed"\n    |panic:\\s+runtime\\s+error                       # Go panic\n    |^\\s*[A-Za-z_][A-Za-z0-9_]*Error:                # ValueError:, TypeError:, AssertionError:\n    |^\\s*Exception:                                  # generic exception line\n    |^\\s*Caused by:                                  # Java style stack trace\n    |\\bexit code\\s+\\d+\\b                          # exit code 1\n    ', re.VERBOSE)
ERROR_LOG_STRONG_RE = ERROR_SIGNALS
PROGRAMMING_LANGS = {'python', 'py', 'javascript', 'js', 'typescript', 'ts', 'java', 'c', 'cpp', 'c++', 'csharp', 'cs', 'go', 'ruby', 'rb', 'php', 'swift', 'kotlin', 'scala', 'rust', 'r', 'sql', 'bash', 'shell', 'sh', 'zsh', 'powershell', 'ps1', 'html', 'css', 'scss', 'sass', 'xml', 'json', 'yaml', 'yml', 'dockerfile', 'makefile', 'gradle'}
DIFF_GIT_RE = re.compile('(?m)^\\s*diff --git\\b')
DIFF_HUNK_RE = re.compile('(?m)^\\s*@@\\s*-\\d+(?:,\\d+)?\\s+\\+\\d+(?:,\\d+)?\\s*@@')
DIFF_FILE_OLD_RE = re.compile('(?m)^\\s*---\\s+[ab]/.+')
DIFF_FILE_NEW_RE = re.compile('(?m)^\\s*\\+\\+\\+\\s+[ab]/.+')
DIFF_INDEX_RE = re.compile('(?m)^\\s*index\\s+[0-9a-f]+\\.\\.[0-9a-f]+\\s+\\d+')
CODE_BLOCK_TAG = '/Code_block_attached.'
DIFF_BLOCK_TAG = '/Diff_attached.'
ERROR_BLOCK_TAG = '/Error_log_attached.'
USER_MENTION_SINGLE = 'A GitHub user is mentioned.'
USER_MENTION_MULTI = 'Multiple GitHub users are mentioned.'
USER_REVIEW_SINGLE = 'A GitHub user is asked to review or check this.'
USER_REVIEW_MULTI = 'Multiple GitHub users are asked to review or check this.'
USER_LEADING_SINGLE = 'A GitHub user is mentioned.'
USER_LEADING_MULTI = 'Multiple GitHub users are mentioned.'
TEAM_MENTION_SINGLE = 'A team from a GitHub organization is mentioned.'
TEAM_MENTION_MULTI = 'Multiple teams from GitHub organizations are mentioned.'
TEAM_REVIEW_SINGLE = 'A team from a GitHub organization is asked to review or check the comment.'
TEAM_REVIEW_MULTI = 'Multiple teams from GitHub organizations are asked to review or check the comment.'
TEAM_LEADING_SINGLE = 'A team from a GitHub organization is mentioned.'
TEAM_LEADING_MULTI = 'Multiple teams from GitHub organizations are mentioned.'
TEAM_MENTION_RE = re.compile('(?<!\\w)@([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)')
USER_MENTION_RE = re.compile('(?<!\\w)@([A-Za-z0-9_.-]+)\\b')
REVIEW_CUES_RE = re.compile('(?i)\\b(please review|can you review|could you review|please take a look|take a look|can you check|could you check|check this|ptal)\\b')
ONLY_USER_MENTIONS_RE = re.compile('^\\s*(?:@[A-Za-z0-9_.-]+\\s*)+$')
ONLY_TEAM_MENTIONS_RE = re.compile('^\\s*(?:@[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\\s*)+$')
GREETING_USER_RE = re.compile('^\\s*(Hi|Hello|Hey)\\s+@([A-Za-z0-9_.-]+)\\s*([.!?]?)\\s*$', re.IGNORECASE)
GREETING_MULTI_USER_RE = re.compile('^\\s*(Hi|Hello|Hey)\\s+(?:@[A-Za-z0-9_.-]+\\s*){2,}([.!?]?)\\s*$', re.IGNORECASE)
GREETING_THANKS_MULTI_USER_RE = re.compile('^\\s*(Hi|Hello|Hey)\\s+((?:@[A-Za-z0-9_.-]+\\s*(?:,|\\band\\b)?\\s*){2,})([!?\\.]*)\\s*(.*)$', re.IGNORECASE | re.DOTALL)
GREETING_THANKS_SINGLE_USER_RE = re.compile('^\\s*(Hi|Hello|Hey)\\s+(@[A-Za-z0-9_.-]+)([!?\\.]*)\\s*(.*)$', re.IGNORECASE | re.DOTALL)
LEADING_USER_MENTIONS_RE = re.compile('^\\s*((?:@[A-Za-z0-9_.-]+\\s*)+)(.+)$', re.DOTALL)
LEADING_TEAM_MENTIONS_RE = re.compile('^\\s*((?:@[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\\s*)+)(.+)$', re.DOTALL)
THANKS_SINGLE_USER_RE = re.compile('(?i)^\\s*(thanks|thank you)[,\\s]+@[A-Za-z0-9_.-]+\\s*[.!?]?\\s*$')
THANKS_MULTI_USERS_RE = re.compile('(?i)^\\s*(thanks|thank you)[,\\s]+(?:@[A-Za-z0-9_.-]+\\s*(?:,|\\band\\b)?\\s*){2,}[.!?]?\\s*$')
THANKS_LEADING_MULTI_USERS_RE = re.compile('(?i)^\\s*(thanks|thank you)[,\\s]+((?:@[A-Za-z0-9_.-]+\\s*(?:,|\\band\\b)?\\s*){2,})([.!?]?\\s*)(.*)$')
THANKS_LEADING_SINGLE_USER_RE = re.compile('(?i)^\\s*(thanks|thank you)[,\\s]+(@[A-Za-z0-9_.-]+)([.!?]?\\s*)(.*)$')
MEETING_WITH_MULTI_USERS_RE = re.compile('(?i)^(.*?\\b(?:meeting|call|discussion|sync|chat)\\s+with)\\s+((?:@[A-Za-z0-9_.-]+\\s*(?:,|\\band\\b)?\\s*){2,})(\\s*[:.-]?\\s*)(.*)$', re.DOTALL)
MEETING_WITH_SINGLE_USER_RE = re.compile('(?i)^(.*?\\b(?:meeting|call|discussion|sync|chat)\\s+with)\\s+(@[A-Za-z0-9_.-]+)(\\s*[:.-]?\\s*)(.*)$', re.DOTALL)
QUOTE_PREFIX_RE = re.compile('^\\s*((?:>\\s*)+)(.*)$')
QUESTION_START_RE = re.compile('(?i)^\\s*(would|could|can|should|do|does|is|are|what|why|how)\\b')
REQUEST_START_RE = re.compile('(?i)^\\s*(please\\b|can you\\b|could you\\b|would you\\b|take a look\\b|check\\b|review\\b|have a look\\b)')
PROPOSAL_START_RE = re.compile('(?i)^\\s*(would it make sense to|does it make sense to|maybe we should|perhaps we should|it might make sense to)\\b')
THOUGHT_OPINION_RE = re.compile('(?i)^\\s*(what do you think|thoughts\\??)\\s*$')
OPINION_THEN_FEEDBACK_RE = re.compile('(?is)^\\s*(i think|i believe|in my opinion|imo)\\b.*\\b(what do you think\\??|thoughts\\??)\\s*$')
ENDS_WITH_FEEDBACK_RE = re.compile('(?is)^(.*?)[,;:\\s-]*(what do you think\\??|thoughts\\??)\\s*$')
COMMIT_LINE_REFERENCE_RE = re.compile('(?i)\\bLine\\s+\\d+\\s+in\\s+\\[?/hash_reference\\]?\\([^)]+\\)')
CC_USER_MENTION_RE = re.compile('(?i)(?<!\\w)/?cc\\s+@[A-Za-z0-9_.-]+(?:\\s+as well)?')
APPROVAL_NOTIFICATION_RE = re.compile('(?is)\\[APPROVALNOTIFIER\\].*?\\bAPPROVED\\b(?:\\*\\*)?')
SUGGESTION_RE = re.compile('(?im)^\\s*#{0,6}\\s*suggestion\\s*$')
SLASH_TAXONOMY = {'/assign': '/workflow_coordination', '/unassign': '/workflow_coordination', '/cc': '/workflow_coordination', '/sig': '/workflow_coordination', '/wg': '/workflow_coordination', '/label': '/workflow_coordination', '/remove-label': '/workflow_coordination', '/milestone': '/workflow_coordination', '/priority': '/workflow_coordination', '/remove-priority': '/workflow_coordination', '/kind': '/workflow_coordination', '/remove-kind': '/workflow_coordination', '/triage': '/workflow_coordination', '/test': '/workflow_ci', '/retest': '/workflow_ci', '/retest-required': '/workflow_ci', '/ok-to-test': '/workflow_ci', '/skip': '/workflow_ci', '/approve': '/workflow_review', '/lgtm': '/workflow_review', '/hold': '/workflow_blocking', '/close': '/workflow_blocking', '/reopen': '/workflow_blocking'}
KNOWN_SLASH_COMMANDS = 'assign|unassign|cc|sig|wg|label|remove-label|milestone|priority|remove-priority|kind|remove-kind|triage|test|retest|retest-required|ok-to-test|skip|approve|lgtm|hold|close|reopen'
SLASH_CMD_RE = re.compile(f'(?m)(?<!\\S)(/(?:{KNOWN_SLASH_COMMANDS}))\\b')
SLASH_ONLY_RE = re.compile(f'^\\s*(?:(?:/(?:{KNOWN_SLASH_COMMANDS}))(?:\\s+[@\\w.\\-/]+)*\\s*)+$')
PLAIN_CC_ONLY_RE = re.compile('(?im)^\\s*cc\\s+@?[\\w.\\-]+(?:\\s+@?[\\w.\\-]+)*\\s*$')
PLAIN_CC_LEADING_RE = re.compile('(?im)^\\s*cc\\s+@?[\\w.\\-]+(?:\\s+@?[\\w.\\-]+)*(.*)$')
BOT_PATTERN = re.compile('(?i)\\[bot\\]|ci[\\-_]robot|triage[\\-_]robot|dependabot|renovate|greenkeeper|codecov|coveralls|mergify|stale\\[bot\\]|allcontributors|nodejs-github-bot|welcome[\\-_]bot|onboarding[\\-_]bot|approval[\\-_]bot|review[\\-_]bot|flaky[\\-_]bot|retest[\\-_]bot')
TRIAGE_BOT_RE = re.compile('(?i)triage[\\-_]robot|triage[\\-_]bot')
APPROVAL_BOT_RE = re.compile('(?i)approval[\\-_]bot|review[\\-_]bot|mergify')
RETEST_FLAKY_BOT_RE = re.compile('(?i)flaky[\\-_]bot|retest[\\-_]bot|ci[\\-_]robot|codecov|coveralls')
ONBOARDING_BOT_RE = re.compile('(?i)welcome[\\-_]bot|onboarding[\\-_]bot|allcontributors')
QUOTED_FENCED_BLOCK_RE = re.compile('(^\\s*>\\s*```([A-Za-z0-9_+\\-]*)[ \\t]*\\n(?:^\\s*>\\s?.*\\n)*?^\\s*>\\s*```)', re.MULTILINE)
EMO_RISA_TAG = '/emoji_risa'
EMO_SONRISA_TAG = '/emoji_sonrisa'
EMO_AMOR_TAG = '/emoji_amor'
EMO_CELEBRA_TAG = '/emoji_celebra'
EMO_APROBACION_TAG = '/emoji_aprobacion'
EMO_RECHAZA_TAG = '/emoji_rechaza'
EMO_TRISTEZA_TAG = '/emoji_tristeza'
EMO_RABIA_TAG = '/emoji_rabia'
EMO_ASCO_TAG = '/emoji_asco'
EMO_MIEDO_TAG = '/emoji_miedo'
EMO_SORPRESA_TAG = '/emoji_sorpresa'
EMO_CONFUSION_TAG = '/emoji_confusion'
EMO_SARCASMO_TAG = '/emoji_sarcasmo'
EMO_CALMA_TAG = '/emoji_calma'
EMO_INTENSO_TAG = '/emoji_intenso'
EMO_ATENCION_TAG = '/emoji_atencion'
EMO_ESPERANZA_TAG = '/emoji_esperanza'
FLAG_TAG = '/emoji_flag_reference'
EMO_OTHER_TAG = '/emoji_other'
ASCII_EMOTICON_MAP = {"(:-D|:D|=D|xD|XD|XDD|:\\'D)": EMO_RISA_TAG, '(:-\\)|:\\)|=\\)|\\^\\^)': EMO_SONRISA_TAG, '(<3)': EMO_AMOR_TAG, "(:-\\(|:\\(|:\\'\\(|T_T|;_;)": EMO_TRISTEZA_TAG, '(>:\\(|D:<)': EMO_RABIA_TAG, '(:-O|:O|O_O|o_O)': EMO_SORPRESA_TAG, '(:-/|:/|:\\\\\\\\|o\\.O|O\\.o)': EMO_CONFUSION_TAG, '(;-\\)|;\\)|:-P|:P|:-p|:p|XP)': EMO_SARCASMO_TAG}
GITHUB_EMOJI_SHORTCODE_MAP = {':eyes:': EMO_ATENCION_TAG}
UNICODE_EMOJI_MAP = {'😂': EMO_RISA_TAG, '🤣': EMO_RISA_TAG, '😄': EMO_RISA_TAG, '😆': EMO_RISA_TAG, '😁': EMO_RISA_TAG, '😹': EMO_RISA_TAG, '🙂': EMO_SONRISA_TAG, '😊': EMO_SONRISA_TAG, '☺️': EMO_SONRISA_TAG, '😇': EMO_SONRISA_TAG, '😍': EMO_AMOR_TAG, '🥰': EMO_AMOR_TAG, '😘': EMO_AMOR_TAG, '💚': EMO_AMOR_TAG, '❤️': EMO_AMOR_TAG, '❤': EMO_AMOR_TAG, '🎉': EMO_CELEBRA_TAG, '🎊': EMO_CELEBRA_TAG, '🏅': EMO_CELEBRA_TAG, '🎁': EMO_CELEBRA_TAG, '👏': EMO_CELEBRA_TAG, '✨': EMO_CELEBRA_TAG, '👍': EMO_APROBACION_TAG, '✅': EMO_APROBACION_TAG, '👎': EMO_RECHAZA_TAG, '❌': EMO_RECHAZA_TAG, '😢': EMO_TRISTEZA_TAG, '😞': EMO_TRISTEZA_TAG, '😡': EMO_RABIA_TAG, '👹': EMO_ASCO_TAG, '🤔': EMO_CONFUSION_TAG, '😕': EMO_CONFUSION_TAG, '😐': EMO_CONFUSION_TAG, '🤦': EMO_CONFUSION_TAG, '🤦\u200d♀️': EMO_CONFUSION_TAG, '😌': EMO_CALMA_TAG, '🙇': EMO_CALMA_TAG, '😉': EMO_SARCASMO_TAG, '😅': EMO_SARCASMO_TAG, '👀': EMO_ATENCION_TAG, '👋': EMO_APROBACION_TAG, '🙏': EMO_ESPERANZA_TAG}
FLAG_RE = re.compile('[\\U0001F1E6-\\U0001F1FF]{2}')
EMOJI_CLUSTER_RE = re.compile('((?:[\\U0001F1E6-\\U0001F1FF]{2})|(?:[\\U0001F300-\\U0001FAFF\\U00002600-\\U000027BF](?:\\uFE0F)?(?:[\\U0001F3FB-\\U0001F3FF])?(?:\\u200D[\\U0001F300-\\U0001FAFF\\U00002600-\\U000027BF](?:\\uFE0F)?(?:[\\U0001F3FB-\\U0001F3FF])?)*))')
ISSUE_REF_TAG = '/issue_reference'
REPO_ISSUE_REF_TAG = '/repo_issue_reference'
HASH_TAG = '/hash_reference'
LOG_TAG = '/log_reference'
BENCHMARK_TAG = '/benchmark_reference'
REPO_ISSUE_REF_RE = re.compile('\\b[\\w.-]+/[\\w.-]+#\\d+\\b')
ISSUE_REF_RE = re.compile('(?<![\\w/])#\\d+\\b')
FULL_HASH_RE = re.compile('\\b[0-9a-f]{40}\\b', re.IGNORECASE)
SHORT_HASH_RE = re.compile('\\b[0-9a-f]{7,12}\\b', re.IGNORECASE)
GIT_TREE_HASH_RE = re.compile('(?im)^\\s*index\\s+[0-9a-f]+\\.\\.[0-9a-f]+\\s+\\d+\\s*$')
LOG_LINE_RE = re.compile('(?im)^\\s*(?:\\[[^\\]]+\\]\\s*)?(?:INFO|DEBUG|WARN|WARNING|ERROR|TRACE|FATAL)\\b.*$\n    |^\\s*at\\s+.+$\n    |^\\s*File\\s+"[^"]+",\\s+line\\s+\\d+.*$\n    |^\\s*Caused by:.*$\n    ', re.VERBOSE)
BENCHMARK_RE = re.compile('(?im)^\\s*.*(?:\n        \\b\\d+(?:\\.\\d+)?\\s*(?:ns/op|µs/op|us/op|ms/op|s/op)\\b|\n        \\b\\d+(?:\\.\\d+)?\\s*(?:ops/sec|op/s|iter/s|iterations/s)\\b|\n        \\bbenchmark\\b|\n        \\bthroughput\\b|\n        \\blatency\\b\n    ).*$', re.VERBOSE)
WIP_SIGNAL_RE = re.compile('(?i)\\bWIP\\b')
REVIEW_SIGNAL_RE = re.compile('(?i)\\b(PTAL|review required|please review|can you review|could you review|take a look|can you check|could you check|pinging)\\b')
AGREEMENT_SIGNAL_RE = re.compile('(?i)(?<!\\w)\\+1(?!\\w)|\\bIIUC\\b')
UNCERTAINTY_SIGNAL_RE = re.compile("(?i)\\b(I am not sure|I\\'m not sure|not sure|maybe|perhaps|I think|IIUC|do you mean|could it be)\\b")
FRUSTRATION_SIGNAL_RE = re.compile('(?i)\\b(frustrating|exhausting|annoying|painful|blocked|stuck|this is hard|this is difficult)\\b')
HELP_REQUEST_SIGNAL_RE = re.compile('(?i)\\b(can you help|could you help|need help|any help|could someone help|help me understand)\\b')
URGENCY_SIGNAL_RE = re.compile('(?i)\\b(asap|urgent|urgently|blocking|time-sensitive|high priority)\\b')
POLITENESS_SIGNAL_RE = re.compile('(?i)\\b(thanks|thank you|please|appreciate it|much appreciated|sorry)\\b')
DISAGREEMENT_SIGNAL_RE = re.compile("(?i)\\b(I disagree|I don\\'t think|this is not correct|I don\\'t agree|not convinced|I\\'m not convinced|I think this is wrong)\\b")
URL_TAG = '/url_reference'
MARKDOWN_LINK_RE = re.compile('\\[([^\\]]+)\\]\\((https?://[^\\s)]+|www\\.[^\\s)]+)\\)')
GENERIC_MARKDOWN_LINK_RE = re.compile('\\[([^\\]]+)\\]\\(([^)\\s]+)\\)')
BROKEN_MARKDOWN_LINK_RE = re.compile('\\[([^\\]]+)\\]\\((https?:/[^\\s)]+)\\)')
RAW_URL_RE = re.compile('(?i)\\b(?:https?://|www\\.)[^\\s<>()\\[\\]{}"\']+')
BROKEN_HTTP_RE = re.compile('(?i)\\bhttps?:/[^\\s<>()\\[\\]{}"\']+')
HTML_DETAILS_TAG = '/html_details_block'
HTML_IMAGE_TAG = '/html_image_reference'
HTML_LINK_TAG = '/html_link_reference'
HTML_META_TAG = '/html_meta_comment'
VISUAL_ARTIFACT_TAG = '/visual_artifact_reference'
HTML_DETAILS_RE = re.compile('(?is)<details\\b.*?>.*?</details>')
HTML_IMG_RE = re.compile('(?is)<img\\b[^>]*>')
HTML_A_RE = re.compile('(?is)<a\\b[^>]*href\\s*=\\s*["\\\']?[^"\\\'>\\s]+[^>]*>(.*?)</a>')
HTML_META_COMMENT_RE = re.compile('(?is)<!--\\s*.*?\\s*-->')
VISUAL_ARTIFACT_RE = re.compile('(?im)^\\s*Visible:\\s*\\d+%\\s*-\\s*\\d+%\\s*$')
CLA_CHECK_TAG = '/automated_cla_check'
CLA_CHECK_RE = re.compile('(?is)The committers listed above are authorized under a signed CLA\\..*?(?=\\n|$)')
GENERIC_HTML_TAG_RE = re.compile('(?is)</?(?:details|summary|sub|sup|br|hr|p|div|span|table|tr|td|th|thead|tbody|img|a|ul|li|ol)\\b[^>]*>')
CI_STATUS_TAG = '/ci_status_reference'
COVERAGE_REPORT_TAG = '/coverage_report_reference'
CI_STATUS_LINE_RE = re.compile('(?im)^\\s*(?:CI|V8 CI|CITGM):\\s*.+$')
CODECOV_STATUS_LINE_RE = re.compile('(?im)^\\s*Codecov\\b.*$')
COVERALLS_STATUS_LINE_RE = re.compile('(?im)^\\s*Coveralls\\b.*$')
SOURCE_COL = 'comment_body_raw'
AUTHOR_COL = 'comment_author'
FINAL_TARGET_COL = 'comment_body_clean_final'
RAW_URL_TARGET_COL = 'comment_body_raw_urls_only'
RAW_URL_FLAG_COL = 'has_raw_url'
MARKDOWN_TARGET_COL = 'comment_body_markdown_links_only'
MARKDOWN_FLAG_COL = 'has_markdown_link'
COMBINED_URL_TARGET_COL = 'comment_body_clean_final_urls'
CI_TARGET_COL = 'comment_body_ci_reports_only'
EMOTION_TARGET_COL = 'comment_body_emotions_clean'
HTML_TARGET_COL = 'comment_body_html_artifacts_only'
HTML_FLAG_COL = 'has_html_markup'
VISUAL_ARTIFACT_FLAG_COL = 'has_visual_artifact'
TECH_REF_TARGET_COL = 'comment_body_technical_refs_only'
HAS_ISSUE_REF_COL = 'has_issue_ref'
HAS_HASH_REF_COL = 'has_hash_reference'
HAS_LOG_REF_COL = 'has_log_reference'
HAS_BENCHMARK_REF_COL = 'has_benchmark_reference'
HAS_WIP_SIGNAL_COL = 'has_wip_signal'
HAS_REVIEW_SIGNAL_COL = 'has_review_signal'
HAS_AGREEMENT_SIGNAL_COL = 'has_agreement_signal'
HAS_UNCERTAINTY_SIGNAL_COL = 'has_uncertainty_signal'
HAS_FRUSTRATION_SIGNAL_COL = 'has_frustration_signal'
HAS_HELP_REQUEST_SIGNAL_COL = 'has_help_request_signal'
HAS_URGENCY_SIGNAL_COL = 'has_urgency_signal'
HAS_POLITENESS_SIGNAL_COL = 'has_politeness_signal'
HAS_DISAGREEMENT_SIGNAL_COL = 'has_disagreement_signal'
SOURCE_COL = 'comment_body_raw'
FINAL_TARGET_COL = 'comment_body_clean_final'
CHANGED_COL = 'clean_changed'
LAST_COLUMN = 'comment_body_clean_final'

def clean_inline_code(text):
    if not isinstance(text, str):
        return ''
    return INLINE_RE.sub('/inline_code', text)

def clean_inline_code_without_backticks(text):
    if not isinstance(text, str):
        return ''
    return INLINE_CODE_NO_BACKTICKS_RE.sub('/inline_code', text)

def classify_fenced_block(lang, body):
    lang = (lang or '').strip().lower()
    if lang == 'diff':
        return DIFF_BLOCK_TAG
    diff_signals = 0
    if DIFF_GIT_RE.search(body):
        diff_signals += 1
    if DIFF_HUNK_RE.search(body):
        diff_signals += 1
    if DIFF_FILE_OLD_RE.search(body):
        diff_signals += 1
    if DIFF_FILE_NEW_RE.search(body):
        diff_signals += 1
    if DIFF_INDEX_RE.search(body):
        diff_signals += 1
    if diff_signals >= 2:
        return DIFF_BLOCK_TAG
    if lang and lang in PROGRAMMING_LANGS:
        return CODE_BLOCK_TAG
    if ERROR_SIGNALS.search(body):
        return ERROR_BLOCK_TAG
    return CODE_BLOCK_TAG

def _line_quote_level(line):
    m = re.match('^\\s*(>[>\\s]*)', line)
    return m.group(1).count('>') if m else 0

def _strip_all_quote_prefixes(line):
    s = line
    while re.match('^\\s*>\\s?', s):
        s = re.sub('^\\s*>\\s?', '', s)
    return s.rstrip()

def _is_low_value_quote(text):
    if not isinstance(text, str):
        return True
    t = re.sub('\\s+', ' ', text).strip()
    if len(t) < 8:
        return True
    if re.fullmatch('[\\W_]+', t):
        return True
    if re.search('(?i)gibberish|giberrish|random characters', t):
        return True
    if len(re.findall('[A-Za-zÀ-ÿ]', t)) < 3:
        return True
    return False

def _is_technical_quote(text):
    if not isinstance(text, str):
        return False
    technical_tags = [CODE_BLOCK_TAG, DIFF_BLOCK_TAG, ERROR_BLOCK_TAG]
    return any((tag in text for tag in technical_tags))

def _is_complex_quote(text):
    if not isinstance(text, str):
        return False
    return '\n' in text or _is_technical_quote(text)

def _render_quote_context(quote_text, response=None):
    if not isinstance(quote_text, str) or not quote_text.strip():
        return response or ''
    quote_text = quote_text.strip()
    response = '' if response is None else response.strip()
    if _is_complex_quote(quote_text):
        prefix = f'based on the quotation:\n{quote_text}'
    else:
        q = "'" if '"' in quote_text else '"'
        prefix = f'based on the quotation: {q}{quote_text}{q}'
    if response:
        return f'{prefix}\n\n{response}'
    return prefix

def _split_quoted_segments(seg_lines):
    segments = []
    current = []
    in_fenced = False
    for raw in seg_lines:
        line = raw.rstrip('\n')
        content = re.sub('^\\s*>\\s?', '', line)
        if content.strip().startswith('```'):
            if not in_fenced:
                if current:
                    segments.append(('text', current))
                    current = []
                in_fenced = True
                current.append(content)
            else:
                current.append(content)
                segments.append(('fenced', current))
                current = []
                in_fenced = False
            continue
        current.append(content)
    if current:
        segments.append(('fenced' if in_fenced else 'text', current))
    return segments

def _process_quote_block(seg_lines):
    parts = []
    buffer = []

    def flush_buffer():
        nonlocal buffer, parts
        if not buffer:
            return
        cleaned = []
        for line in buffer:
            content = re.sub('^\\s*(?:>\\s*)+', '', line.rstrip('\n')).strip()
            if not content:
                if cleaned and cleaned[-1] != '':
                    cleaned.append('')
                continue
            cleaned.append(content)
        while cleaned and cleaned[0] == '':
            cleaned.pop(0)
        while cleaned and cleaned[-1] == '':
            cleaned.pop()
        if cleaned:
            parts.append('\n'.join(cleaned))
        buffer = []
    i = 0
    while i < len(seg_lines):
        raw = seg_lines[i].rstrip('\n')
        stripped = re.sub('^\\s*(?:>\\s*)+', '', raw)
        if stripped.strip().startswith('```'):
            flush_buffer()
            fenced_lines = [stripped]
            i += 1
            while i < len(seg_lines):
                nxt = seg_lines[i].rstrip('\n')
                nxt_stripped = re.sub('^\\s*(?:>\\s*)+', '', nxt)
                fenced_lines.append(nxt_stripped)
                if nxt_stripped.strip().startswith('```'):
                    break
                i += 1
            block_text = '\n'.join(fenced_lines).strip()
            cleaned_block = replace_fenced_blocks(block_text).strip()
            if cleaned_block:
                parts.append(cleaned_block)
            i += 1
            continue
        buffer.append(raw)
        i += 1
    flush_buffer()
    return '\n\n'.join((p for p in parts if p)).strip()

def _extract_quotes(text):
    """
    Reglas:
    - cada línea con >   -> based on the quotation: "..."
    - cada línea con >>+ -> (citing: "...")
    - líneas vacías citadas se conservan
    - menciones dentro de la cita se anonimizarán, pero no se reescriben discursivamente
    """
    if not isinstance(text, str) or not text.strip():
        return ([], '')
    lines = text.splitlines()
    quote_list = []
    result_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not re.match('^\\s*>', line):
            result_lines.append(line)
            i += 1
            continue
        level = _line_quote_level(line)
        content = _strip_all_quote_prefixes(line).strip()
        if not content:
            result_lines.append('')
            i += 1
            continue
        if content.startswith('```'):
            fenced_lines = [content]
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not re.match('^\\s*>', nxt):
                    break
                nxt_content = _strip_all_quote_prefixes(nxt).rstrip()
                fenced_lines.append(nxt_content)
                if nxt_content.strip().startswith('```') and len(fenced_lines) > 1:
                    break
                i += 1
            block_text = '\n'.join(fenced_lines).strip()
            if 'replace_fenced_blocks' in globals():
                cleaned_block = replace_fenced_blocks(block_text).strip()
                if not cleaned_block:
                    cleaned_block = CODE_BLOCK_TAG
            else:
                cleaned_block = CODE_BLOCK_TAG
            if level == 1:
                result_lines.append(f'based on the quotation: {cleaned_block}')
            else:
                q = "'" if '"' in cleaned_block else '"'
                result_lines.append(f'(citing: {q}{cleaned_block}{q})')
            quote_list.append(cleaned_block)
            i += 1
            continue
        content = _anonymize_inline_mentions(content)
        q = "'" if '"' in content else '"'
        if level == 1:
            result_lines.append(f'based on the quotation: {q}{content}{q}')
        else:
            result_lines.append(f'(citing: {q}{content}{q})')
        quote_list.append(content)
        i += 1
    return (quote_list, '\n'.join(result_lines).strip())

def _team_spans(text):
    return [m.span() for m in TEAM_MENTION_RE.finditer(text)] if isinstance(text, str) else []

def count_team_mentions(text):
    if not isinstance(text, str):
        return 0
    return len(list(TEAM_MENTION_RE.finditer(text)))

def count_user_mentions(text):
    if not isinstance(text, str):
        return 0
    spans = _team_spans(text)
    count = 0
    for m in USER_MENTION_RE.finditer(text):
        s, e = m.span()
        inside_team = any((s >= ts and e <= te for ts, te in spans))
        if not inside_team:
            count += 1
    return count

def _leading_user_mentions_info(text):
    if not isinstance(text, str):
        return (0, '')
    m = re.match('^\\s*((?:@[A-Za-z0-9_.-]+\\s*)+)(.*)$', text, re.DOTALL)
    if not m:
        return (0, text)
    lead = m.group(1)
    rest = m.group(2)
    n = len(re.findall('@[A-Za-z0-9_.-]+', lead))
    return (n, rest)

def _normalize_after_prefix(text):
    text = re.sub('^[\\s,;:.-]+', '', text)
    text = re.sub('\\s+', ' ', text).strip()
    return text

def _extract_quote_info(line):
    """
    Returns
    -------
    depth : int
        Number of quote markers at the beginning of the line.
    content : str
        Line content without the leading Markdown quote markers.
    """
    if not isinstance(line, str):
        return (0, line)
    m = QUOTE_PREFIX_RE.match(line)
    if not m:
        return (0, line)
    prefix = m.group(1)
    content = m.group(2).strip()
    depth = prefix.count('>')
    return (depth, content)

def _anonymize_inline_mentions(text):
    text = COMMIT_LINE_REFERENCE_RE.sub('/commit_line_reference', text)
    text = TEAM_MENTION_RE.sub('a team from a GitHub organization', text)
    text = USER_MENTION_RE.sub('a GitHub user', text)
    return text

def clean_approval_notifications(text):
    if not isinstance(text, str):
        return ''
    return APPROVAL_NOTIFICATION_RE.sub('/approval_notification', text)

def clean_code_suggestions(text):
    if not isinstance(text, str):
        return ''
    return SUGGESTION_RE.sub('/code_suggestion', text)

def clean_cc_user_mentions(text):
    if not isinstance(text, str):
        return ''
    return CC_USER_MENTION_RE.sub(USER_MENTION_SINGLE, text)

def _rewrite_greeting_with_mentions(greeting, is_multi, trailing_text):
    greeting = greeting.capitalize().strip()
    trailing_text = trailing_text.strip()
    mention_text = USER_MENTION_MULTI if is_multi else USER_MENTION_SINGLE
    if not trailing_text:
        return f'{greeting}. {mention_text}'
    trailing_text = _anonymize_inline_mentions(trailing_text)
    if re.match('(?i)^thank you\\b', trailing_text):
        return f'{greeting}. {mention_text} The comment thanks them for their work so far.'
    return f'{greeting}. {mention_text} {trailing_text}'

def _rewrite_user_leading_context(rest, lead_n, has_review):
    rest = _normalize_after_prefix(rest)
    if not rest:
        return USER_LEADING_SINGLE if lead_n == 1 else USER_LEADING_MULTI
    rest_clean = rest.strip()
    rest_lower = rest_clean.lower()
    if THOUGHT_OPINION_RE.fullmatch(rest_clean):
        return f"{USER_LEADING_SINGLE} The message asks for that user's opinion." if lead_n == 1 else f'{USER_LEADING_MULTI} The message asks for their opinion.'
    if OPINION_THEN_FEEDBACK_RE.match(rest_clean):
        m = ENDS_WITH_FEEDBACK_RE.match(rest_clean)
        main_part = m.group(1).strip() if m else rest_clean
        return f"{USER_LEADING_SINGLE} {main_part} The message then asks for that user's opinion." if lead_n == 1 else f'{USER_LEADING_MULTI} {main_part} The message then asks for their opinion.'
    if has_review:
        cleaned = re.sub('(?i)^(please review|can you review|could you review|please take a look|take a look|can you check|could you check|check this|ptal)\\b[\\s,:-]*', '', rest_clean).strip()
        return USER_REVIEW_SINGLE + (f' {cleaned}' if cleaned else '') if lead_n == 1 else USER_REVIEW_MULTI + (f' {cleaned}' if cleaned else '')
    if PROPOSAL_START_RE.match(rest_clean):
        if rest_lower.startswith('would it make sense to'):
            tail = rest_clean[len('would it make sense to'):].strip()
            return f'{USER_LEADING_SINGLE} It asks whether it would make sense to {tail}' if lead_n == 1 else f'{USER_LEADING_MULTI} It asks whether it would make sense to {tail}'
        return f'{USER_LEADING_SINGLE} It asks whether {rest_clean}' if lead_n == 1 else f'{USER_LEADING_MULTI} It asks whether {rest_clean}'
    if QUESTION_START_RE.match(rest_clean):
        return f'{USER_LEADING_SINGLE} It asks: {rest_clean}' if lead_n == 1 else f'{USER_LEADING_MULTI} It asks: {rest_clean}'
    if REQUEST_START_RE.match(rest_clean):
        cleaned_request_rest = re.sub('(?i)^(please|can you|could you|would you|take a look|check|review|have a look)\\b[\\s,:-]*', '', rest_clean).strip()
        return USER_REVIEW_SINGLE + (f' {cleaned_request_rest}' if cleaned_request_rest else '') if lead_n == 1 else USER_REVIEW_MULTI + (f' {cleaned_request_rest}' if cleaned_request_rest else '')
    return f'{USER_LEADING_SINGLE} {rest_clean}' if lead_n == 1 else f'{USER_LEADING_MULTI} {rest_clean}'

def _rewrite_team_leading_context(rest, team_count, has_review):
    rest = _normalize_after_prefix(rest)
    if not rest:
        return TEAM_LEADING_SINGLE if team_count == 1 else TEAM_LEADING_MULTI
    rest_clean = rest.strip()
    if has_review:
        return f'{TEAM_REVIEW_SINGLE} {rest_clean}' if team_count == 1 else f'{TEAM_REVIEW_MULTI} {rest_clean}'
    if PROPOSAL_START_RE.match(rest_clean):
        return f'{TEAM_LEADING_SINGLE} It asks whether {rest_clean}' if team_count == 1 else f'{TEAM_LEADING_MULTI} It asks whether {rest_clean}'
    if QUESTION_START_RE.match(rest_clean):
        return f'{TEAM_LEADING_SINGLE} It asks: {rest_clean}' if team_count == 1 else f'{TEAM_LEADING_MULTI} It asks: {rest_clean}'
    if REQUEST_START_RE.match(rest_clean):
        return f'{TEAM_REVIEW_SINGLE} {rest_clean}' if team_count == 1 else f'{TEAM_REVIEW_MULTI} {rest_clean}'
    return f'{TEAM_LEADING_SINGLE} {rest_clean}' if team_count == 1 else f'{TEAM_LEADING_MULTI} {rest_clean}'

def _clean_quote_line(line):
    depth, content = _extract_quote_info(line)
    if depth == 0:
        return line
    if not content:
        return ''
    quote_intro = 'Based on the quotation, '
    if ONLY_TEAM_MENTIONS_RE.fullmatch(stripped):
        team_count = count_team_mentions(stripped)
        return TEAM_MENTION_SINGLE if team_count == 1 else TEAM_MENTION_MULTI
    if ONLY_USER_MENTIONS_RE.fullmatch(stripped):
        user_count = count_user_mentions(stripped)
        return USER_MENTION_SINGLE if user_count == 1 else USER_MENTION_MULTI
    team_count = count_team_mentions(stripped)
    user_count = count_user_mentions(stripped)
    m_team = LEADING_TEAM_MENTIONS_RE.match(content)
    if m_team and count_team_mentions(content) > 0 and (count_user_mentions(content) == 0):
        rest = _normalize_after_prefix(m_team.group(2))
        if rest:
            return quote_intro + f'{TEAM_LEADING_SINGLE} {rest}'
        return quote_intro + TEAM_MENTION_SINGLE
    m_user = LEADING_USER_MENTIONS_RE.match(content)
    if m_user and count_user_mentions(content) > 0 and (count_team_mentions(content) == 0):
        lead_n, rest = _leading_user_mentions_info(content)
        rewritten = _rewrite_user_leading_context(rest, lead_n, bool(REVIEW_CUES_RE.search(content)))
        return quote_intro + rewritten
    content = _anonymize_inline_mentions(content)
    return quote_intro + content

def clean_mentions(text):
    if not isinstance(text, str) or not text.strip():
        return ''
    stripped = text.strip()
    depth, _ = _extract_quote_info(stripped)
    if depth > 0:
        return _clean_quote_line(stripped)
    if ONLY_TEAM_MENTIONS_RE.fullmatch(stripped):
        team_count = count_team_mentions(stripped)
        return TEAM_MENTION_SINGLE if team_count == 1 else TEAM_MENTION_MULTI
    if ONLY_USER_MENTIONS_RE.fullmatch(stripped):
        user_count = count_user_mentions(stripped)
        return USER_MENTION_SINGLE if user_count == 1 else USER_MENTION_MULTI
    if THANKS_SINGLE_USER_RE.fullmatch(stripped):
        return 'The comment thanks a GitHub user.'
    if THANKS_MULTI_USERS_RE.fullmatch(stripped):
        return 'The comment thanks multiple GitHub users.'
    m_thanks_multi = THANKS_LEADING_MULTI_USERS_RE.match(stripped)
    if m_thanks_multi:
        rest = m_thanks_multi.group(4).strip()
        if rest:
            return f'The comment thanks multiple GitHub users. {rest}'
        return 'The comment thanks multiple GitHub users.'
    m_thanks_single = THANKS_LEADING_SINGLE_USER_RE.match(stripped)
    if m_thanks_single:
        rest = m_thanks_single.group(4).strip()
        if rest:
            return f'The comment thanks a GitHub user. {rest}'
        return 'The comment thanks a GitHub user.'
    m_meeting_multi = MEETING_WITH_MULTI_USERS_RE.match(stripped)
    if m_meeting_multi:
        prefix = m_meeting_multi.group(1).strip()
        sep = m_meeting_multi.group(3) or ''
        rest = m_meeting_multi.group(4).strip()
        rewritten = f'{prefix} multiple GitHub users'
        if sep:
            rewritten += sep.rstrip()
        if rest:
            rewritten += f' {rest}'
        return rewritten
    m_meeting_single = MEETING_WITH_SINGLE_USER_RE.match(stripped)
    if m_meeting_single:
        prefix = m_meeting_single.group(1).strip()
        sep = m_meeting_single.group(3) or ''
        rest = m_meeting_single.group(4).strip()
        rewritten = f'{prefix} a GitHub user'
        if sep:
            rewritten += sep.rstrip()
        if rest:
            rewritten += f' {rest}'
        return rewritten
    m_greet_thanks_multi = GREETING_THANKS_MULTI_USER_RE.match(stripped)
    if m_greet_thanks_multi:
        greeting = m_greet_thanks_multi.group(1)
        trailing_text = m_greet_thanks_multi.group(4)
        return _rewrite_greeting_with_mentions(greeting, is_multi=True, trailing_text=trailing_text)
    m_greet_thanks_single = GREETING_THANKS_SINGLE_USER_RE.match(stripped)
    if m_greet_thanks_single:
        greeting = m_greet_thanks_single.group(1)
        trailing_text = m_greet_thanks_single.group(4)
        return _rewrite_greeting_with_mentions(greeting, is_multi=False, trailing_text=trailing_text)
    m_greet_single = GREETING_USER_RE.fullmatch(stripped)
    if m_greet_single:
        greeting = m_greet_single.group(1).capitalize()
        return f'{greeting}. {USER_MENTION_SINGLE}'
    m_greet_multi = GREETING_MULTI_USER_RE.fullmatch(stripped)
    if m_greet_multi:
        greeting = m_greet_multi.group(1).capitalize()
        return f'{greeting}. {USER_MENTION_MULTI}'
    team_count = count_team_mentions(stripped)
    user_count = count_user_mentions(stripped)
    has_review = bool(REVIEW_CUES_RE.search(stripped))
    m_team = LEADING_TEAM_MENTIONS_RE.match(stripped)
    if m_team and team_count > 0 and (user_count == 0):
        return _rewrite_team_leading_context(m_team.group(2), team_count, has_review)
    m_user = LEADING_USER_MENTIONS_RE.match(stripped)
    if m_user and user_count > 0 and (team_count == 0):
        lead_n, rest_raw = _leading_user_mentions_info(stripped)
        return _rewrite_user_leading_context(rest_raw, lead_n, has_review)
    return _anonymize_inline_mentions(stripped)

def clean_mentions_by_paragraph(text):
    if not isinstance(text, str) or not text.strip():
        return ''
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        if not line.strip():
            cleaned_lines.append('')
            continue
        cleaned = clean_mentions(line)
        if cleaned:
            cleaned_lines.append(cleaned)
    return '\n'.join(cleaned_lines).strip()

def normalize_comment_text(text):
    if not isinstance(text, str) or not text.strip():
        return ''
    _, text = _extract_quotes(text)
    text = clean_mentions_by_paragraph(text)
    return text
    final_text = normalize_comment_text(text)

def extract_slash_commands(text):
    if not isinstance(text, str):
        return []
    return SLASH_CMD_RE.findall(text)

def classify_slash_commands(text):
    cmds = extract_slash_commands(text)
    types = []
    for cmd in cmds:
        types.append(SLASH_TAXONOMY.get(cmd, '/workflow_other'))
    return sorted(set(types))

def is_slash_only(text):
    if not isinstance(text, str) or not text.strip():
        return False
    return bool(SLASH_ONLY_RE.fullmatch(text.strip()))

def replace_plain_cc(text):
    if not isinstance(text, str) or not text.strip():
        return ''
    stripped = text.strip()
    if PLAIN_CC_ONLY_RE.fullmatch(stripped):
        return '/workflow_coordination'
    m = PLAIN_CC_LEADING_RE.match(stripped)
    if m:
        rest = re.sub('^[,;:.-]+\\s*', '', m.group(1).strip())
        return rest if rest else '/workflow_coordination'
    return text

def clean_workflow_commands(text):
    if not isinstance(text, str) or not text.strip():
        return ''
    stripped = text.strip()
    cmd_types = classify_slash_commands(stripped)
    stripped = replace_plain_cc(stripped)
    if stripped == '/workflow_coordination':
        return stripped
    if not cmd_types:
        return stripped
    if is_slash_only(text):
        return ' '.join(cmd_types)
    cleaned = re.sub(f'(?<!\\S)/(?:{KNOWN_SLASH_COMMANDS})\\b', '', stripped)
    cleaned = re.sub('[ \\t]+', ' ', cleaned).strip()
    cleaned = re.sub('^[,;:.-]+\\s*', '', cleaned)
    cleaned = re.sub('\\s+([,;:.!?])', '\\1', cleaned)
    return cleaned if cleaned else ' '.join(cmd_types)

def classify_bot_or_automation(author, text=''):
    author = '' if author is None else str(author)
    text = '' if text is None else str(text)
    hay = f'{author} {text}'
    if not BOT_PATTERN.search(hay):
        return ''
    if TRIAGE_BOT_RE.search(hay):
        return 'triage_bot'
    if APPROVAL_BOT_RE.search(hay):
        return 'approval_notifier'
    if RETEST_FLAKY_BOT_RE.search(hay):
        return 'retest_flaky_bot'
    if ONBOARDING_BOT_RE.search(hay):
        return 'onboarding_bot'
    return 'other_bot'

def is_bot_or_automation(author, text=''):
    return bool(classify_bot_or_automation(author, text))

def _looks_like_pure_ci_or_coverage_message(text):
    if not isinstance(text, str):
        return False
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    if not lines:
        return False
    return all((CI_STATUS_LINE_RE.match(ln) or CODECOV_STATUS_LINE_RE.match(ln) or COVERALLS_STATUS_LINE_RE.match(ln) for ln in lines))

def clean_bot_messages(text, author=''):
    if not isinstance(text, str):
        return ''
    bot_type = classify_bot_or_automation(author, text)
    if not bot_type:
        return text
    stripped = text.strip()
    if _looks_like_pure_ci_or_coverage_message(stripped):
        return stripped
    return f'{BOT_TAG} {stripped}'.strip() if stripped else BOT_TAG

def _strip_quote_prefixes_from_block(block_text):
    lines = block_text.splitlines()
    cleaned = [re.sub('^\\s*>\\s?', '', line) for line in lines]
    return '\n'.join(cleaned)

def _replace_single_fenced_block(block_text):
    match = FENCED_BLOCK_RE.search(block_text)
    if not match:
        return block_text
    lang = (match.group(1) or '').strip()
    body = match.group(2) or ''
    label = classify_fenced_block(lang, body)
    return f'\n{label}\n'

def replace_fenced_blocks(text):
    if not isinstance(text, str):
        return ''

    def quoted_repl(match):
        quoted_block = match.group(1)
        cleaned_block = _strip_quote_prefixes_from_block(quoted_block)
        return _replace_single_fenced_block(cleaned_block)

    def fenced_repl(match):
        lang = (match.group(1) or '').strip()
        body = match.group(2) or ''
        label = classify_fenced_block(lang, body)
        return f'\n{label}\n'
    text = QUOTED_FENCED_BLOCK_RE.sub(quoted_repl, text)
    text = FENCED_BLOCK_RE.sub(fenced_repl, text)
    return text

def replace_diff_structures(text):
    if not isinstance(text, str):
        return ''
    diff_signals = 0
    if DIFF_GIT_RE.search(text):
        diff_signals += 1
    if DIFF_HUNK_RE.search(text):
        diff_signals += 1
    if DIFF_FILE_OLD_RE.search(text):
        diff_signals += 1
    if DIFF_FILE_NEW_RE.search(text):
        diff_signals += 1
    if DIFF_INDEX_RE.search(text):
        diff_signals += 1
    if diff_signals >= 2:
        return DIFF_BLOCK_TAG
    return text

def replace_error_logs(text):
    if not isinstance(text, str):
        return ''
    if ERROR_LOG_STRONG_RE.search(text):
        return ERROR_BLOCK_TAG
    return text

def _classify_emoji_cluster(cluster):
    if FLAG_RE.fullmatch(cluster):
        return FLAG_TAG
    if cluster in UNICODE_EMOJI_MAP:
        return UNICODE_EMOJI_MAP[cluster]
    found_tags = []
    for emo, tag in UNICODE_EMOJI_MAP.items():
        if emo in cluster:
            found_tags.append(tag)
    if found_tags:
        priority = [EMO_AMOR_TAG, EMO_RISA_TAG, EMO_CELEBRA_TAG, EMO_APROBACION_TAG, EMO_RECHAZA_TAG, EMO_TRISTEZA_TAG, EMO_RABIA_TAG, EMO_ASCO_TAG, EMO_MIEDO_TAG, EMO_SORPRESA_TAG, EMO_CONFUSION_TAG, EMO_SARCASMO_TAG, EMO_CALMA_TAG, EMO_INTENSO_TAG, EMO_ATENCION_TAG, EMO_ESPERANZA_TAG]
        for candidate in priority:
            if candidate in found_tags:
                return candidate
    return EMO_OTHER_TAG

def replace_emoticons_and_emojis(text):
    if not isinstance(text, str):
        return ''
    text = unicodedata.normalize('NFKC', text)
    for shortcode, tag in GITHUB_EMOJI_SHORTCODE_MAP.items():
        text = re.sub(re.escape(shortcode), f' {tag} ', text, flags=re.IGNORECASE)
    for emo in sorted(UNICODE_EMOJI_MAP, key=len, reverse=True):
        text = text.replace(emo, f' {UNICODE_EMOJI_MAP[emo]} ')
    for pattern, tag in ASCII_EMOTICON_MAP.items():
        text = re.sub(pattern, f' {tag} ', text)

    def emoji_repl(match):
        cluster = match.group(0)
        return f' {_classify_emoji_cluster(cluster)} '
    text = EMOJI_CLUSTER_RE.sub(emoji_repl, text)
    text = re.sub('\\s+', ' ', text)
    return text.strip()

def has_emoticon_or_emoji(text):
    if not isinstance(text, str):
        return False
    norm = unicodedata.normalize('NFKC', text)
    for shortcode in GITHUB_EMOJI_SHORTCODE_MAP:
        if re.search(re.escape(shortcode), norm, flags=re.IGNORECASE):
            return True
    for pattern in ASCII_EMOTICON_MAP:
        if re.search(pattern, norm):
            return True
    return bool(EMOJI_CLUSTER_RE.search(norm))

def count_emoticon_or_emoji(text):
    if not isinstance(text, str):
        return 0
    norm = unicodedata.normalize('NFKC', text)
    count = 0
    for shortcode in GITHUB_EMOJI_SHORTCODE_MAP:
        count += len(re.findall(re.escape(shortcode), norm, flags=re.IGNORECASE))
    for pattern in ASCII_EMOTICON_MAP:
        count += len(re.findall(pattern, norm))
    count += len(EMOJI_CLUSTER_RE.findall(norm))
    return count

def detect_emotion_types(text):
    if not isinstance(text, str):
        return []
    norm = unicodedata.normalize('NFKC', text)
    found = set()
    for shortcode, tag in GITHUB_EMOJI_SHORTCODE_MAP.items():
        if re.search(re.escape(shortcode), norm, flags=re.IGNORECASE):
            found.add(tag)
    for pattern, tag in ASCII_EMOTICON_MAP.items():
        if re.search(pattern, norm):
            found.add(tag)
    for match in EMOJI_CLUSTER_RE.finditer(norm):
        found.add(_classify_emoji_cluster(match.group(0)))
    return sorted(found)

def has_issue_ref(text):
    if not isinstance(text, str):
        return False
    return bool(ISSUE_REF_RE.search(text) or REPO_ISSUE_REF_RE.search(text))

def has_hash_reference(text):
    if not isinstance(text, str):
        return False
    return bool(FULL_HASH_RE.search(text) or GIT_TREE_HASH_RE.search(text))

def has_log_reference(text):
    if not isinstance(text, str):
        return False
    return bool(LOG_LINE_RE.search(text))

def has_benchmark_reference(text):
    if not isinstance(text, str):
        return False
    return bool(BENCHMARK_RE.search(text))

def replace_technical_references(text):
    if not isinstance(text, str):
        return ''
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if BENCHMARK_RE.match(stripped):
            cleaned_lines.append(BENCHMARK_TAG)
            continue
        if LOG_LINE_RE.match(stripped):
            cleaned_lines.append(LOG_TAG)
            continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)
    text = REPO_ISSUE_REF_RE.sub(REPO_ISSUE_REF_TAG, text)
    text = ISSUE_REF_RE.sub(ISSUE_REF_TAG, text)
    text = GIT_TREE_HASH_RE.sub(HASH_TAG, text)
    text = FULL_HASH_RE.sub(HASH_TAG, text)
    text = SHORT_HASH_RE.sub(HASH_TAG, text)
    text = re.sub('[ \\t]+', ' ', text)
    return text.strip()

def normalize_linebreaks_and_tabs(text):
    if not isinstance(text, str):
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\t', ' ')
    text = re.sub('[ \\t]+', ' ', text)
    text = re.sub(' *\\n *', '\n', text)
    text = re.sub('\\n{3,}', '\n\n', text)
    return text

def normalize_text(text):
    if not isinstance(text, str):
        return ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\t', ' ')
    text = re.sub('[ \\t]+', ' ', text)
    text = re.sub(' *\\n *', '\n', text)
    text = re.sub('\\n{3,}', '\n\n', text)
    return text.strip()

def clean_code_related_text(text):
    if not isinstance(text, str) or not text.strip():
        return ''
    text = clean_inline_code(text)
    text = replace_fenced_blocks(text)
    text = replace_diff_structures(text)
    text = replace_error_logs(text)
    text = normalize_text(text)
    return text

def clean_comment_text(text, author=''):
    if not isinstance(text, str) or not text.strip():
        return ''
    text = COMMIT_LINE_REFERENCE_RE.sub('/commit_line_reference', text)
    text = clean_bot_messages(text, author)
    text = normalize_linebreaks_and_tabs(text)
    text = clean_urls(text)
    text = replace_html_and_visual_artifacts(text)
    text = replace_ci_and_coverage_reports(text)
    text = replace_technical_references(text)
    text = clean_inline_code(text)
    text = clean_inline_code_without_backticks(text)
    text = clean_code_suggestions(text)
    text = clean_code_related_text(text)
    _, text = _extract_quotes(text)
    text = clean_approval_notifications(text)
    text = clean_cc_user_mentions(text)
    text = clean_workflow_commands(text)
    text = replace_emoticons_and_emojis(text)
    text = clean_mentions_by_paragraph(text)
    text = _anonymize_inline_mentions(text)
    text = normalize_text(text)
    return text

def has_wip_signal(text):
    return bool(WIP_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_review_signal(text):
    return bool(REVIEW_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_agreement_signal(text):
    return bool(AGREEMENT_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_uncertainty_signal(text):
    return bool(UNCERTAINTY_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_frustration_signal(text):
    return bool(FRUSTRATION_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_help_request_signal(text):
    return bool(HELP_REQUEST_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_urgency_signal(text):
    return bool(URGENCY_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_politeness_signal(text):
    return bool(POLITENESS_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def has_disagreement_signal(text):
    return bool(DISAGREEMENT_SIGNAL_RE.search(text)) if isinstance(text, str) else False

def split_trailing_punctuation(url):
    trailing = ''
    while url and url[-1] in '.,;:!?)]}':
        trailing = url[-1] + trailing
        url = url[:-1]
    return (url, trailing)

def _markdown_anchor_with_url(anchor):
    anchor = re.sub('\\s+', ' ', anchor).strip()
    if not anchor:
        return URL_TAG
    return f'{anchor} {URL_TAG}'

def replace_markdown_links(text):
    if not isinstance(text, str):
        return ''

    def repl(match):
        anchor = match.group(1)
        return _markdown_anchor_with_url(anchor)
    return MARKDOWN_LINK_RE.sub(repl, text)

def replace_broken_markdown_links(text):
    if not isinstance(text, str):
        return ''

    def repl(match):
        anchor = match.group(1)
        return _markdown_anchor_with_url(anchor)
    return BROKEN_MARKDOWN_LINK_RE.sub(repl, text)

def replace_generic_markdown_links(text):
    if not isinstance(text, str):
        return ''

    def repl(match):
        anchor = match.group(1).strip()
        return _markdown_anchor_with_url(anchor)
    return GENERIC_MARKDOWN_LINK_RE.sub(repl, text)

    def repl(match):
        anchor = match.group(1)
        return _markdown_anchor_with_url(anchor)
    return BROKEN_MARKDOWN_LINK_RE.sub(repl, text)

def replace_raw_urls(text):
    if not isinstance(text, str):
        return ''

    def repl(match):
        url = match.group(0)
        core, trailing = split_trailing_punctuation(url)
        return f' {URL_TAG}{trailing} '
    text = RAW_URL_RE.sub(repl, text)
    text = BROKEN_HTTP_RE.sub(repl, text)
    text = re.sub('[ \\t]+', ' ', text)
    return text.strip()

def has_raw_url(text):
    if not isinstance(text, str):
        return False
    return bool(RAW_URL_RE.search(text) or BROKEN_HTTP_RE.search(text))

def has_markdown_link(text):
    if not isinstance(text, str):
        return False
    return bool(MARKDOWN_LINK_RE.search(text) or BROKEN_MARKDOWN_LINK_RE.search(text))

def clean_urls(text):
    if not isinstance(text, str):
        return ''
    text = replace_markdown_links(text)
    text = replace_broken_markdown_links(text)
    text = replace_generic_markdown_links(text)
    text = replace_raw_urls(text)
    return text

def has_html_markup(text):
    if not isinstance(text, str):
        return False
    return bool(HTML_DETAILS_RE.search(text) or HTML_IMG_RE.search(text) or HTML_A_RE.search(text) or HTML_META_COMMENT_RE.search(text) or GENERIC_HTML_TAG_RE.search(text))

def has_visual_artifact(text):
    if not isinstance(text, str):
        return False
    return bool(VISUAL_ARTIFACT_RE.search(text))

def replace_html_and_visual_artifacts(text):
    if not isinstance(text, str):
        return ''
    text = HTML_DETAILS_RE.sub(f' {HTML_DETAILS_TAG} ', text)
    text = HTML_IMG_RE.sub(f' {HTML_IMAGE_TAG} ', text)
    text = CLA_CHECK_RE.sub(f' {CLA_CHECK_TAG} ', text)

    def repl_a(match):
        anchor_text = re.sub('\\s+', ' ', match.group(1)).strip()
        if anchor_text:
            return f'{anchor_text} {HTML_LINK_TAG}'
        return HTML_LINK_TAG
    text = HTML_A_RE.sub(repl_a, text)
    text = HTML_META_COMMENT_RE.sub(f' {HTML_META_TAG} ', text)
    text = VISUAL_ARTIFACT_RE.sub(VISUAL_ARTIFACT_TAG, text)
    text = GENERIC_HTML_TAG_RE.sub(' ', text)
    text = re.sub('[ \\t]+', ' ', text)
    text = re.sub(' *\\n *', '\n', text)
    return text.strip()

def has_ci_status_line(text):
    if not isinstance(text, str):
        return False
    return bool(CI_STATUS_LINE_RE.search(text))

def has_codecov_report(text):
    if not isinstance(text, str):
        return False
    return bool(CODECOV_STATUS_LINE_RE.search(text))

def has_coverage_report(text):
    if not isinstance(text, str):
        return False
    return bool(COVERALLS_STATUS_LINE_RE.search(text))

def replace_ci_and_coverage_reports(text):
    if not isinstance(text, str):
        return ''
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if CI_STATUS_LINE_RE.match(stripped):
            cleaned_lines.append(CI_STATUS_TAG)
            continue
        if CODECOV_STATUS_LINE_RE.match(stripped) or COVERALLS_STATUS_LINE_RE.match(stripped):
            cleaned_lines.append(COVERAGE_REPORT_TAG)
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)