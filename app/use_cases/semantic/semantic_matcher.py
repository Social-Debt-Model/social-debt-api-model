import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from app.infrastructure.ontology_client import ontology_causes, enrich_microcause

try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
except ImportError:
    model = None

MACRO_TO_CANDIDATE_INDIVIDUALS = {
    "A": ["CO-001_LanguageBarriers", "CO-002_DelayedCommunication", "CO-003_UnclearOrAmbiguousCommunication", "CO-004_LackOfTimelyFeedbackOrResponse", "CO-005_MisinterpretationOfInformation"],
    "B": ["COO-001_CentralizedDecisionMaking", "COO-002_RestrictedInformationFlow", "COO-003_UnilateralTaskAssignment", "COO-004_FrequentLeadershipConflicts", "COO-006_MiscommunicationInTaskHandover", "COO-008_CoordinationMisalignmentForTechnicalValidation", "COO-009_TaskReworkDueToMisalignment", "CR-001_LackOfTaskDiscussion"],
    "C": ["COG-006_LackOfInterfaceClarification", "COG-007_TechnicalComplexityDueToDependencies", "COG-008_CompatibilityConstraints", "COG-010_PreservationOfPriorSystemBehavior", "COG-011_SystemConfigurationConstraints"],
    "D": ["CA-005_BlockageDueToApprovalRequirements", "CA-009_ConstraintDueToTicketStatusForReview", "CA-010_BlockageDueToTriageProcess", "CA-006_UnclearRolesAndResponsibilities", "CA-007_InefficientOrganizationalProcesses", "CA-001_LackOfCommunicationPlan", "CA-003_LackOfFeedbackChannels"],
    "E": ["COL-003_InsufficientPeerSupport", "COL-004_LackOfCollaborationOrTeamwork", "COL-006_LackOfTrustAmongTeamMembers", "CL-001_LowSocialization", "CO-006_PerceivedUnfairnessInInteraction", "COG-004_LackOfPeerAcknowledgement", "COL-005_LackOfKnowledgeSharing"],
    "F": ["CA-004_NoKnowledgeTransferPolicy", "ADM-003_LackOfStandardsOrBestPractices", "COG-009_LackOfTechnicalDocumentation"],
    "G": ["CA-008_LackOfResources", "CA-011_RequestForTechnicalValidationSupport", "CA-012_RepositoryAccessLimitation", "CA-013_InefficientOrInadequateTools"],
    "H": []
}

def get_candidates_for_macro(macro_code: str):
    allowed_ids = MACRO_TO_CANDIDATE_INDIVIDUALS.get(macro_code, [])
    if not allowed_ids:
        return ontology_causes
    return [c for c in ontology_causes if c["ontology_id"] in allowed_ids]

def match_microcauses(text: str, macro_code: str, top_k: int = 3):
    if not text or not ontology_causes or model is None:
        return []

    candidates = get_candidates_for_macro(macro_code)
    if not candidates:
        candidates = ontology_causes

    text_emb = model.encode([text])
    
    # Create representations: ID + Name + Description
    descriptions = [f"{c['cause_id']} {c['cause_name']} {c['cause_description']}" for c in candidates]
    if not descriptions:
        return []
        
    desc_embs = model.encode(descriptions)
    
    similarities = cosine_similarity(text_emb, desc_embs)[0]
    
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        sim = similarities[idx]
        c = candidates[idx]
        
        enrichment = enrich_microcause(c["ontology_uri"])
        
        micro_data = {
            "cause_id": c["cause_id"],
            "cause_name": c["cause_name"],
            "similarity": float(sim),
            "ontology_id": c["ontology_id"]
        }
        micro_data.update(enrichment)
        results.append(micro_data)
        
    return results
