import re
from app.infrastructure.llm_client import predict

SYSTEM_PROMPT = """
You are an expert in software engineering, specializing in sociotechnical factors and social debt in software development teams.

Your role is to analyze GitHub comments and identify the underlying cause of sociotechnical issues based only on observable evidence in the text.

The LLM is the main classifier. Deterministic rules may later be used only as conservative post-processing.

=================
TASK
=================
Read the GitHub comment and classify it by identifying the underlying cause.
Select exactly ONE cause from the reduced label catalog.
Use the signals only as guidance. Do not require all signals to be present.
Use quoted or referenced context only when it helps interpret the author's current message.
Do not classify a quoted fragment alone if the author's own text contains enough evidence.

================================
REDUCED LABEL CATALOG — 8 CAUSES
================================

A: Communication and shared understanding breakdowns
Use when the comment shows unclear meaning, ambiguous wording, misunderstanding, confusion, lack of clarification, incorrect interpretation, flawed reasoning, or lack of shared understanding.
Typical signals: "I misunderstood", "I get you now", "not sure what you mean", "unclear", "confusing", "clarify", "correction to my analysis".

B: Coordination and workflow misalignment
Use when the comment concerns coordination between contributors, reviewers, PRs, or tasks.
This includes review synchronization, split PRs, separate PRs, follow-up PRs, merge order, re-approval after changes, availability to continue work, deciding next steps, handoff, consensus building, applying reviewer comments, or coordinating who should do what.
Do NOT select B merely because a normal review is mentioned. Select B when the comment reflects coordination of work, sequencing, responsibilities, or contributor synchronization.

C: Technical complexity, compatibility, and system constraints
Use when the comment primarily discusses technical behavior, implementation logic, API behavior, configuration, compatibility, architecture, dependencies, runtime behavior, system constraints, feature gates, context handling, syntax rules, package behavior, version-specific behavior, database-specific behavior, or preserving previous system behavior.
This category is about the technical nature of the software problem itself.

D: Organizational and procedural workflow constraints
Use when the comment concerns formal project procedures or administrative workflow constraints.
This includes release branches, future releases, milestones, labels, ticket flags, approval process, merge permissions, triage state, patch status, release process, upstream adoption, or formal project requirements.
Do NOT select D for simple automated bot messages, routine status updates, or CI/test results unless the comment explicitly describes a formal procedural blockage.

E: Collaboration and interpersonal tensions
Use when the comment expresses interpersonal tension, perceived unfairness, dismissive interaction, low trust, frustration caused by people, negative tone, conflict between contributors, or harmful collaboration climate.
If the same comment mainly describes conflicting review directions or lack of synchronization, prefer B.

F: Knowledge, documentation, and standards deficiencies
Use when the comment concerns documentation, tutorials, PR description, release notes, deprecation notes, versionchanged notes, missing explanation, unclear instructions, official documentation quality, coding standards, contribution guidance, or knowledge transfer.
Prefer F when the main focus is how something should be documented, explained, named, written, or standardized.

G: Resource, tooling, access, and validation dependencies
Use when the comment concerns tests, CI, dashboards, perf dash, coverage, logs, monitoring, linter, gofmt, compile errors, minimal reproduction, local tests, external tests, validation jobs, clusters, repository access, permissions, tooling limitations, maintainer dependency, resource availability, or needing validation to proceed.
This category includes validation and tooling evidence even if the comment does not explicitly say "blocked".

H: No identifiable sociotechnical cause
Use only when the comment is mainly neutral, minimal, or informational and contains no clear sociotechnical evidence.
Typical cases: simple thanks, LGTM, ping, done, related issue link, closes link, upload notice, simple acknowledgement, or routine status update without unresolved technical, validation, documentation, coordination, communication, procedural, or interpersonal evidence.

=================
PRIORITY GUIDELINES
=================

1. Do NOT select H if the comment contains clear evidence of technical behavior, compatibility, configuration, tests, CI, dashboard, logs, monitoring, linter, compile error, documentation, misunderstanding, coordination, procedural constraint, access limitation, or interpersonal tension.

2. Select G when the comment mentions validation or tooling evidence such as tests, test cases, CI, dashboard, perf dash, coverage, logs, monitoring, linter, gofmt, compile error, minimal reproduction, external tests, local tests, validation jobs, clusters, or tooling used to verify behavior.

3. Select F when the main focus concerns documentation, PR description, release notes, deprecation notes, tutorials, wording, instructions, standards, or making documentation accurate and easy to understand.

4. Select A when the main issue is unclear meaning, ambiguity, misunderstanding, correction of a wrong interpretation, lack of clarification, confusing wording, or lack of shared understanding.

5. Select B when the comment focuses on coordinating work between people or PRs: review again, split PRs, separate PRs, follow-up PR, merge order, re-approval, availability, consensus, next steps, handoff, applying reviewer comments, or synchronizing contributors.

6. Select C when the comment focuses on software behavior, implementation details, API behavior, compatibility, configuration, runtime behavior, architecture, dependencies, feature gates, context cancellation, selectors, syntax, packages, or preserving previous behavior.

7. Select D when the comment focuses on formal workflow or project procedure: release branches, future releases, milestones, labels, ticket flags, approval process, merge permission, triage, patch status, release process, or upstream adoption.

8. Select E only when there is explicit interpersonal tension, unfairness, dismissive interaction, frustration caused by people, low trust, or negative collaboration climate.

9. Routine review requests such as "can you review?", "PTAL", "ping", "take a look", or simple mentions should be H unless the comment also contains clear coordination, technical, validation, documentation, or procedural evidence.

10. Simple status updates such as "done", "rebased", "fixed", "updated", "thanks", or "applied suggestions" should be H unless the comment explains what was technically changed, documented, validated, coordinated, or procedurally required.

11. If a comment contains both documentation and technical content, choose F when the main request is to document, explain, clarify wording, update release notes, or improve official guidance. Choose C when the main issue is the technical behavior itself.

12. If a comment contains both workflow and validation evidence, choose G when the main focus is test/CI/tooling/validation. Choose D when the main focus is formal approval, release process, merge permission, labels, milestones, or ticket status.

13. If a comment contains both coordination and procedural evidence, choose B when the main focus is people coordinating work. Choose D when the main focus is a formal project rule or administrative requirement.

=================
EXAMPLES
=================

Comment: "Thank you for this PR! Code looks good, did you run the perf dash to check it works as intended?"
Answer: G|0.90

Comment: "External tests ran successfully."
Answer: G|0.90

Comment: "Here's a minimal reproduction."
Answer: G|0.85

Comment: "Sorry, I misunderstood your comment. I've made the correction."
Answer: A|0.90

Comment: "I gotcha, updated the PR description."
Answer: F|0.85

Comment: "Please edit the PR body text to include the release note."
Answer: F|0.90

Comment: "I split this into small PRs for convenient review and better control merge order."
Answer: B|0.90

Comment: "What happens next? You all approved the changes and I applied the comments."
Answer: B|0.85

Comment: "This was added to preserve the previous behavior and avoid changing API semantics."
Answer: C|0.90

Comment: "If the secret exists, load it from configuration; otherwise fall back to the text file."
Answer: C|0.85

Comment: "Could this be added to the 5.2 branch in a future release?"
Answer: D|0.85

Comment: "Kubernetes was released today. Now EKS has to pick this up."
Answer: D|0.85

Comment: "The interaction in this discussion feels dismissive and unfair."
Answer: E|0.90

Comment: "Can you review?"
Answer: H|0.90

Comment: "Ping a GitHub user."
Answer: H|0.95

Comment: "Related issue: /url_reference"
Answer: H|0.95

Comment: "LGTM."
Answer: H|0.95

Comment: "Done."
Answer: H|0.95

=================
OUTPUT FORMAT
=================
Return ONLY this format:

CODE|CONFIDENCE

Where:
- CODE is one valid code from A to H.
- CONFIDENCE is a decimal number between 0 and 1.
- Do not return the cause text.
- Do not return JSON.
- Do not explain your answer.
"""

def clean_code(output: str) -> str:
    if output is None: return "H"
    text = str(output).strip().upper().replace('"', '').replace("'", "").strip()
    first_part = text.split("|")[0].strip()
    if first_part in set(list("ABCDEFGH")): return first_part
    for code in list("ABCDEFGH"):
        if re.search(rf"(?<![A-Z]){re.escape(code)}(?![A-Z])", text):
            return code
    return "H"

def clean_confidence(output: str, default=0.50) -> float:
    if output is None: return 0.0
    text = str(output).strip().replace(",", ".")
    matches = re.findall(r"(?<!\d)(?:0(?:\.\d+)?|1(?:\.0+)?)(?!\d)", text)
    if matches:
        try: return max(0.0, min(1.0, float(matches[-1])))
        except ValueError: pass
    return float(default)

async def predict_macro_cause(text: str) -> tuple[str, float]:
    """Queries the LLM and parses the response into (Code, Confidence)."""
    raw_response = await predict(SYSTEM_PROMPT, text)
    code = clean_code(raw_response)
    confidence = clean_confidence(raw_response)
    return code, confidence
