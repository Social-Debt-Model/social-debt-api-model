import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from app.infrastructure.ontology_client import ontology_causes, enrich_microcause

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

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
        "CA-001_LackOfCommunicationPlan", "CA-003_LackOfFeedbackChannels",
        "CA-005_BlockageDueToApprovalRequirements", "CA-006_UnclearRolesAndResponsibilities",
        "CA-007_InefficientOrganizationalProcesses", "CA-009_ConstraintDueToTicketStatusForReview",
        "CA-010_BlockageDueToTriageProcess"
    ],
    "Collaboration and interpersonal tensions": [
        "COL-003_InsufficientPeerSupport", "COL-004_LackOfCollaborationOrTeamwork", 
        "COL-005_LackOfKnowledgeSharing", "COL-006_LackOfTrustAmongTeamMembers", 
        "CL-001_LowSocialization", "CO-006_PerceivedUnfairnessInInteraction", 
        "COG-004_LackOfPeerAcknowledgement"
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
    "CA-008_LackOfResources": "resources capacity availability people time budget bandwidth unavailable insufficient shortage",
    "CA-011_RequestForTechnicalValidationSupport": "validation support expert review maintainer approval confirmation technical authority external validation blocked progress cannot continue",
    "CA-012_RepositoryAccessLimitation": "repository access repo permission permissions fork branch pull request access denied cannot push cannot trigger ci restricted access",
    "CA-013_InefficientOrInadequateTools": "tool tooling inadequate tools ci logs buildbot automation infrastructure dashboard monitoring test runner flaky tooling limitation",
    "CO-001_LanguageBarriers": "language dialect terminology vocabulary translation wording naming non native speaker unclear term linguistic barrier",
    "CO-002_DelayedCommunication": "delayed communication late update late reply waiting information delay response delay slow communication asynchronous delay",
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

def classify_specific_causes_topk(macro_label, comment_text=None, top_k=3):
    macro_key = macro_label.strip().lower() if macro_label else ""
    candidate_ids = MACRO_TO_CANDIDATE_INDIVIDUALS.get(macro_label, [])
    
    candidates = [c for c in ontology_causes if c["ontology_id"] in candidate_ids]
    if not candidates:
        return {"top_candidates": []}
        
    macro_text = MACRO_CAUSE_DESCRIPTIONS.get(macro_key, str(macro_label))
    
    if comment_text:
        words = str(comment_text).split()
        short_comment = " ".join(words[:60])
        query_text = f"GitHub comment evidence:\\n{short_comment}\\n\\nMacro cause context:\\n{macro_text}"
    else:
        query_text = macro_text
        
    candidate_texts = []
    for c in candidates:
        keywords = CAUSE_KEYWORDS.get(c["ontology_id"], "")
        text = f"{c['cause_name']} {c['cause_description']} {keywords}"
        candidate_texts.append(text)
        
    query_embedding = model.encode(query_text, convert_to_tensor=True)
    candidate_embeddings = model.encode(candidate_texts, convert_to_tensor=True)
    
    scores = util.cos_sim(query_embedding, candidate_embeddings)[0].tolist()
    
    results = []
    for score, c in zip(scores, candidates):
        results.append({
            "ontology_id": c["ontology_id"],
            "cause_id": c["cause_id"],
            "specific_cause_name": c["cause_name"],
            "final_score": score
        })
        
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return {"top_candidates": results[:top_k]}
