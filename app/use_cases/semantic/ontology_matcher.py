import re
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from app.infrastructure.ontology_client import ontology_causes

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

DEFAULT_THRESHOLD = 0.28
DEFAULT_TOP_K = 3
DEFAULT_ALPHA = 0.10
DEFAULT_LEXICAL_WEIGHT = 0.20
MAX_SCORE_GAP = 0.18

GENERIC_CAUSE_PENALTY = {
    "CL-001_LowSocialization": 0.020,
    "COL-004_LackOfCollaborationOrTeamwork": 0.020,
    "COG-007_TechnicalComplexityDueToDependencies": 0.015,
    "CO-003_UnclearOrAmbiguousCommunication": 0.015,
    "CA-005_BlockageDueToApprovalRequirements": 0.015,
}

LEXICAL_SIGNALS = {
    "CO-001_LanguageBarriers":["language","translation","terminology","wording","vocabulary","non native","mother tongue","dialect","term"],
    "CO-002_DelayedCommunication":["late","delay","delayed","waiting","no update","slow response","sorry for the delay"],
    "CO-003_UnclearOrAmbiguousCommunication":["unclear","ambiguous","confusing","not clear","clarify","clarification","what do you mean","don't understand"],
    "CO-005_MisinterpretationOfInformation":["misunderstood","misinterpret","wrong understanding","incorrect assumption"],
    "COG-007_TechnicalComplexityDueToDependencies":["dependency","dependencies","depends on","component","module","integration","external system"],
    "COG-008_CompatibilityConstraints":["compatibility","backward compatibility","backwards compatible","version mismatch","legacy","api version","browser","database"],
    "COG-011_SystemConfigurationConstraints":["configuration","config","environment","settings","deployment","runtime","variable"],
    "CA-011_RequestForTechnicalValidationSupport":["validate","validation","review","expert review","maintainer","confirm"],
    "CA-012_RepositoryAccessLimitation":["repository access","access denied","permission","cannot push","cannot trigger","fork"],
    "CA-013_InefficientOrInadequateTools":["ci","tool","tooling","dashboard","logs","buildbot","automation","flaky","test failed","job failed"],
    "CA-005_BlockageDueToApprovalRequirements":["approval","approve","approved","waiting approval","cannot merge","required review"],
    "CA-007_InefficientOrganizationalProcesses":["process","workflow","bureaucracy","release process","slow process"],
    "CA-009_ConstraintDueToTicketStatusForReview":["needs review","ticket","review status","needs tests","needs improvement"],
    "COO-002_RestrictedInformationFlow":["restricted information","hidden information","information access","not visible"],
    "COO-006_MiscommunicationInTaskHandover":["handover","handoff","transfer","passed to","take over"],
    "COO-008_CoordinationMisalignmentForTechnicalValidation":["technical validation","validation responsibility","validation timing","approval criteria"],
    "COO-009_TaskReworkDueToMisalignment":["rework","redo","repeat","revert","reimplemented","change requests","rebase"],
    "CR-001_LackOfTaskDiscussion":["needs discussion","task discussion","requirements discussion"],
    "CL-001_LowSocialization":["little interaction","rarely interact","low engagement","few discussions"],
    "COL-003_InsufficientPeerSupport":["need help","help me","assistance","guidance","mentor"],
    "COL-004_LackOfCollaborationOrTeamwork":["collaboration","work together","shared decision","joint work","working alone"],
    "COL-005_LackOfKnowledgeSharing":["knowledge sharing","share knowledge","knowledge transfer","lessons learned"],
    "COL-006_LackOfTrustAmongTeamMembers":["trust","distrust","hostile","skeptical","good faith"],
    "CO-006_PerceivedUnfairnessInInteraction":["unfair","not fair","bias","biased","double standard","favoritism"],
    "COG-004_LackOfPeerAcknowledgement":["credit","recognition","acknowledge","not recognized","appreciation","thank you"],
}

LANGUAGE_TERMS = {
    "language", "translation", "translate", "translator", "english", "spanish",
    "french", "german", "polish", "chinese", "japanese", "italian", "portuguese",
    "dialect", "terminology", "vocabulary", "non native", "non-native",
    "mother tongue", "linguistic", "multilingual"
}

MACRO_TO_CANDIDATE_INDIVIDUALS = {
    "Communication and shared understanding breakdowns": [
        "CO-001_LanguageBarriers", "CO-002_DelayedCommunication", 
        "CO-003_UnclearOrAmbiguousCommunication", "CO-004_LackOfTimelyFeedbackOrResponse", 
        "CO-005_MisinterpretationOfInformation"
    ],
    "Coordination and workflow misalignment": [
        "COO-001_CentralizedDecisionMaking", "COO-002_RestrictedInformationFlow", 
        "COO-003_UnilateralTaskAssignment", "COO-004_FrequentLeadershipConflicts", 
        "COO-006_MiscommunicationInTaskHandover", "COO-008_CoordinationMisalignmentForTechnicalValidation", 
        "COO-009_TaskReworkDueToMisalignment", "CR-001_LackOfTaskDiscussion"
    ],
    "Technical complexity, compatibility, and system constraints": [
        "COG-006_LackOfInterfaceClarification", "COG-007_TechnicalComplexityDueToDependencies", 
        "COG-008_CompatibilityConstraints", "COG-010_PreservationOfPriorSystemBehavior", 
        "COG-011_SystemConfigurationConstraints"
    ],
    "Organizational and procedural workflow constraints": [
        "CA-005_BlockageDueToApprovalRequirements", "CA-009_ConstraintDueToTicketStatusForReview", 
        "CA-010_BlockageDueToTriageProcess", "CA-006_UnclearRolesAndResponsibilities", 
        "CA-007_InefficientOrganizationalProcesses", "CA-001_LackOfCommunicationPlan", 
        "CA-003_LackOfFeedbackChannels"
    ],
    "Collaboration and interpersonal tensions": [
        "COL-003_InsufficientPeerSupport", "COL-004_LackOfCollaborationOrTeamwork", 
        "COL-006_LackOfTrustAmongTeamMembers", "CL-001_LowSocialization", 
        "CO-006_PerceivedUnfairnessInInteraction", "COG-004_LackOfPeerAcknowledgement", 
        "COL-005_LackOfKnowledgeSharing"
    ],
    "Knowledge, documentation, and standards deficiencies": [
        "CA-004_NoKnowledgeTransferPolicy", "ADM-003_LackOfStandardsOrBestPractices", 
        "COG-009_LackOfTechnicalDocumentation"
    ],
    "Resource, tooling, access, and validation dependencies": [
        "CA-008_LackOfResources", "CA-011_RequestForTechnicalValidationSupport", 
        "CA-012_RepositoryAccessLimitation", "CA-013_InefficientOrInadequateTools"
    ]
}

CAUSE_KEYWORDS = {
    "CO-001_LanguageBarriers": "language terminology non native idiom expression grammar dictionary translation meaning linguistic misunderstanding",
    "CO-002_DelayedCommunication": "delay response delay slow communication asynchronous delay",
    "CO-003_UnclearOrAmbiguousCommunication": "unclear ambiguous incomplete imprecise vague confusing lack context clarification not clear not sure what mean unclear instruction",
    "CO-004_LackOfTimelyFeedbackOrResponse": "feedback response reply no response unanswered follow up waiting review feedback missing response timely feedback",
    "CO-005_MisinterpretationOfInformation": "misinterpretation misunderstood wrong understanding interpreted differently intended meaning incorrect assumption misunderstood requirement",
    "CA-004_NoKnowledgeTransferPolicy": "knowledge transfer policy knowledge retention handover policy onboarding policy knowledge management no transfer process",
    "ADM-003_LackOfStandardsOrBestPractices": "standards best practices guidelines conventions procedures coding standards review practices governance criteria consistency",
    "COG-009_LackOfTechnicalDocumentation": "technical documentation architecture component specification interface definition dependency information configuration details technical design decisions",
    "CA-001_LackOfCommunicationPlan": "communication plan communication policy planned communication channels communication responsibilities communication process",
    "CA-003_LackOfFeedbackChannels": "feedback channels feedback loop feedback mechanism accessible feedback channel open communication early issue detection",
    "CA-005_BlockageDueToApprovalRequirements": "approval required approve blocked waiting approval merge permission authorization approval gate cannot proceed",
    "CA-006_UnclearRolesAndResponsibilities": "unclear roles unclear responsibilities ownership responsibility owner accountable role ambiguity who owns who responsible",
    "CA-007_InefficientOrganizationalProcesses": "inefficient process organizational process bureaucracy procedural delay process inefficiency administrative workflow slow process",
    "CA-009_ConstraintDueToTicketStatusForReview": "ticket status review status needs review needs tests needs improvement patch status blocked by status",
    "CA-010_BlockageDueToTriageProcess": "triage process awaiting triage accepted needs triage priority label triage blocked workflow",
    "COG-006_LackOfInterfaceClarification": "interface clarification contract inputs outputs responsibilities component interaction api contract integration specification interface definition",
    "COG-007_TechnicalComplexityDueToDependencies": "dependencies dependency component module service tool external system technical complexity integration dependency chain coupling",
    "COG-008_CompatibilityConstraints": "compatibility backward compatibility backwards compatible api version platform database browser external component environment legacy behavior",
    "COG-010_PreservationOfPriorSystemBehavior": "preserve behavior prior behavior existing behavior expected functionality backward compatibility regression behavior change preserve expected behavior",
    "COG-011_SystemConfigurationConstraints": "configuration settings environment differences system behavior infrastructure dependency deployment configuration environment specific behavior config",
    "COO-001_CentralizedDecisionMaking": "centralized decision making leaders small group decision authority limited autonomy distributed coordination decision centralization",
    "COO-002_RestrictedInformationFlow": "restricted information flow limited information distribution information access visibility select members hidden information coordination",
    "COO-003_UnilateralTaskAssignment": "unilateral task assignment reassigned without consultation assigned without discussion task ownership imposed assignment",
    "COO-004_FrequentLeadershipConflicts": "leadership conflict leadership disputes disagreement leaders key positions project planning friction leadership tension",
    "COO-006_MiscommunicationInTaskHandover": "handover task handover ownership transfer responsibility transfer transition work item transfer incomplete handoff missing information during handover communication breakdown during handover coordination during handover",
    "COO-008_CoordinationMisalignmentForTechnicalValidation": "technical validation coordination validation timing validation criteria validation procedure validation responsibility misalignment",
    "COO-009_TaskReworkDueToMisalignment": "task execution inconsistent agreements misaligned expectations coordination decisions rework revise repeated work inconsistent responsibilities",
    "CR-001_LackOfTaskDiscussion": "task discussion requirements discussion responsibilities discussion implementation approach",
    "COL-003_InsufficientPeerSupport": "peer support help assistance support from peers teammate support insufficient support blocked without help",
    "COL-004_LackOfCollaborationOrTeamwork": "collaboration collaborative work isolated contributors independent work silos knowledge exchange joint activities shared decision making collaborative problem solving",
    "COL-005_LackOfKnowledgeSharing": "knowledge sharing exchange knowledge experience lessons learned technical information collective understanding sharing expertise",
    "COL-006_LackOfTrustAmongTeamMembers": "trust distrust reliability confidence skeptical hostile passive aggressive aggressive good faith bad faith intentions competence",
    "CL-001_LowSocialization": "rare interaction little interaction few discussions isolated contributors weak social ties low engagement minimal participation lack of regular communication",
    "CO-006_PerceivedUnfairnessInInteraction": "unfair unfairness unequal treatment bias biased double standard exclusion favoritism not fair unfair process",
    "COG-004_LackOfPeerAcknowledgement": "recognition acknowledgement appreciation credit credited contribution contributions effort achievements ideas not valued not recognized",
    "CA-008_LackOfResources": "lack of resources low bandwidth not enough time understaffed resource constraint capacity limit",
    "CA-011_RequestForTechnicalValidationSupport": "request technical validation need review request maintainer review ask for validation approval request validate changes",
    "CA-012_RepositoryAccessLimitation": "repository access access rights permission denied lack write access read only github permissions cannot merge",
    "CA-013_InefficientOrInadequateTools": "inefficient tools tooling issues broken tools pipeline failure ci problems bad tools infrastructure failure"
}

MACRO_CAUSE_DESCRIPTIONS = {
    "communication and shared understanding breakdowns": "Communication and shared understanding breakdowns. This category refers to language barriers, delayed communication, unclear or ambiguous messages, missing feedback, lack of timely responses, and misinterpretation of shared information.",
    "coordination and workflow misalignment": "Coordination and workflow misalignment. This category refers to centralized decisions, restricted information flow, unilateral task assignment, leadership conflicts, lack of cross-team meetings, poor task handover, validation coordination problems, task execution based on inconsistent agreements, and lack of task discussion.",
    "technical complexity, compatibility, and system constraints": "Technical complexity, compatibility, and system constraints. This category refers to unclear interfaces, technical dependencies, compatibility constraints, preservation of prior system behavior, configuration settings, environment differences, and system-specific constraints.",
    "organizational and procedural workflow constraints": "Organizational and procedural workflow constraints. This category refers to approval requirements, ticket status constraints, triage bottlenecks, unclear roles, inefficient organizational processes, lack of communication planning, and missing feedback channels.",
    "collaboration and interpersonal tensions": "Collaboration and interpersonal tensions. This category refers to interpersonal friction, weak mutual support, limited joint work, reduced knowledge exchange, low trust, perceived unfairness, poor recognition of contributions, and reduced social participation among contributors.",
    "knowledge, documentation, and standards deficiencies": "Knowledge, documentation, and standards deficiencies. This category refers to lack of knowledge transfer policies, missing project or process documentation, lack of standards or best practices, and missing technical documentation about architecture, interfaces, dependencies, or technical decisions.",
    "resource, tooling, access, and validation dependencies": "Resource, tooling, access, and validation dependencies. This category refers to lack of resources, dependency on technical validation support, repository access limitations, inefficient or inadequate tools, and collaboration constraints due to repository access."
}

def normalize(text):
    if pd.isna(text): return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize_for_match(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def build_macro_semantic_text(macro_label):
    macro_clean = normalize(macro_label)
    if macro_clean in MACRO_CAUSE_DESCRIPTIONS:
        return MACRO_CAUSE_DESCRIPTIONS[macro_clean]
    return str(macro_label)

def clean_comment_for_embedding(text, max_words=120):
    if text is None or pd.isna(text): return ""
    text = str(text)
    
    # Tweak: Homologación de formato de Excel del Colab
    # Tweak: homologar mayuscula y multiples repeticiones juntas exactamente como en el notebook del cliente
    text = text.replace("_x000d_", "_x000D_")
    text = re.sub(r'(_x000D_)+', '_x000D_', text)
    
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"/url_reference", " ", text)
    text = re.sub(r"/hash_reference", " ", text)
    text = re.sub(r"/html_details_block", " ", text)
    text = re.sub(r"/html_image_reference", " ", text)
    text = re.sub(r"/inline_code", " inline_code ", text)
    text = re.sub(r"/code_block_attached", " code_block ", text)
    text = re.sub(r"/diff_attached", " diff_block ", text)
    text = re.sub(r"A GitHub user is mentioned", " ", text, flags=re.I)
    text = re.sub(r"based on the quotation:", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    return " ".join(words[:max_words])

def build_candidate_cause_text(candidate_row):
    ontology_id = candidate_row["ontology_id"]
    keywords = CAUSE_KEYWORDS.get(ontology_id, "")
    return " ".join([str(candidate_row["cause_name"]), str(candidate_row["cause_description"]), keywords])

def lexical_signal_score(comment_text, ontology_id):
    if comment_text is None: return 0.0
    text = normalize_for_match(comment_text)
    signals = LEXICAL_SIGNALS.get(ontology_id, [])
    if len(signals) == 0: return 0.0
    hits = 0
    for signal in signals:
        signal = normalize_for_match(signal)
        if signal in text: hits += 1
    if hits == 0: return 0.0
    return min(1.0, hits / 3)

def has_explicit_language_signal(comment_text):
    if comment_text is None: return False
    text = normalize_for_match(comment_text)
    return any(term in text for term in LANGUAGE_TERMS)

def classify_specific_causes_topk(
    macro_label,
    comment_text=None,
    threshold=DEFAULT_THRESHOLD,
    top_k=DEFAULT_TOP_K,
    alpha=DEFAULT_ALPHA,
    lexical_weight=DEFAULT_LEXICAL_WEIGHT,
):
    candidate_ids = MACRO_TO_CANDIDATE_INDIVIDUALS.get(macro_label, [])
    candidates = [c for c in ontology_causes if c["ontology_id"] in candidate_ids]
    
    if not candidates:
        return {"top_candidates": []}

    macro_semantic_text = build_macro_semantic_text(macro_label)
    comment_semantic_text = clean_comment_for_embedding(comment_text, max_words=120)

    if comment_semantic_text.strip() == "":
        comment_semantic_text = macro_semantic_text

    candidate_texts = []
    for c in candidates:
        candidate_texts.append(build_candidate_cause_text(c))

    macro_embedding = model.encode(macro_semantic_text, convert_to_tensor=True)
    comment_embedding = model.encode(comment_semantic_text, convert_to_tensor=True)
    candidate_embeddings = model.encode(candidate_texts, convert_to_tensor=True)

    scores_macro = util.cos_sim(macro_embedding, candidate_embeddings)[0]
    scores_comment = util.cos_sim(comment_embedding, candidate_embeddings)[0]

    has_language_signal = has_explicit_language_signal(comment_text)

    all_candidates = []
    for i in range(len(candidates)):
        c = candidates[i]
        ontology_id = c["ontology_id"]

        macro_score = float(scores_macro[i].item())
        comment_score = float(scores_comment[i].item())

        base_score = alpha * macro_score + (1 - alpha) * comment_score
        lex_bonus = lexical_weight * lexical_signal_score(comment_text, ontology_id)
        penalty = GENERIC_CAUSE_PENALTY.get(ontology_id, 0.0)

        if ontology_id == "CO-001_LanguageBarriers" and not has_language_signal:
            penalty += 0.10

        final_score = base_score + lex_bonus - penalty
        final_score = max(0.0, min(1.0, final_score))

        all_candidates.append({
            "ontology_id": ontology_id,
            "cause_id": c["cause_id"],
            "specific_cause_name": c["cause_name"],
            "final_score": final_score
        })

    all_candidates = sorted(all_candidates, key=lambda x: x["final_score"], reverse=True)

    selected = [c for c in all_candidates if c["final_score"] >= threshold]
    
    if len(selected) == 0:
        selected = [all_candidates[0]]

    if len(selected) > 1:
        best_score = selected[0]["final_score"]
        selected = [c for c in selected if (best_score - c["final_score"]) <= MAX_SCORE_GAP]

    selected = selected[:top_k]

    if len(selected) == 0:
        selected = [all_candidates[0]]

    return {"top_candidates": selected}
