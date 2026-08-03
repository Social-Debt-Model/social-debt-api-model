import re
from pathlib import Path
from rdflib import Graph, RDF, OWL, Namespace

NS = Namespace("http://www.example.org/ontosocialdebt#")
CAUSE_TYPES = {
    "AdministrativeCause",
    "CommunicationCause",
    "CoordinationCause",
    "CollaborationCause",
    "CongruenceCause"
}

def normalize(text):
    if not text: return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def load_ontology(file_path: str = "app/infrastructure/ontologyv4.rdf"):
    g = Graph()
    g.parse(str(Path(file_path)))
    
    causes = []
    for subject, _, rdf_type in g.triples((None, RDF.type, None)):
        type_name = str(rdf_type).split("#")[-1]
        if type_name not in CAUSE_TYPES: continue
        
        ontology_uri = str(subject)
        ontology_id = ontology_uri.split("#")[-1]
        
        cause_id = next(g.objects(subject, NS.hasCauseID), None)
        cause_name = next(g.objects(subject, NS.hasCauseName), None)
        cause_desc = next(g.objects(subject, NS.hasCauseDescription), None)
        
        cause_id_str = str(cause_id) if cause_id else ontology_id
        cause_name_str = str(cause_name) if cause_name else ontology_id.replace("_", " ")
        cause_desc_str = str(cause_desc) if cause_desc else ""
        
        causes.append({
            "ontology_uri": ontology_uri,
            "ontology_id": ontology_id,
            "cause_id": cause_id_str,
            "cause_name": cause_name_str,
            "cause_description": cause_desc_str,
            "cause_type": type_name,
            "cause_name_clean": normalize(cause_name_str),
            "cause_description_clean": normalize(cause_desc_str)
        })
    return g, causes

global_g = None
ontology_causes = []
try:
    global_g, ontology_causes = load_ontology()
except Exception as e:
    print(f"Warning: Failed to load ontology: {e}")

def local_name(node):
    return str(node).split("#")[-1]

def enrich_microcause(cause_uri_str: str):
    if global_g is None:
        return {}
        
    cause_uri = None
    for s in global_g.subjects():
        if str(s) == cause_uri_str or str(s).endswith(f"#{cause_uri_str}"):
            cause_uri = s
            break
            
    if not cause_uri:
        return {}

    preventive = set()
    effects = set()
    corrective = set()
    indicators = set()
    metrics = set()
    risks = set()
    community_smells = set()

    preventive_props = [
        NS.hasAdministrativePreventiveStrategy, NS.hasCommunicationStrategy,
        NS.hasCoordinationStrategy, NS.hasCollaborationStrategy, NS.hasCongruenceStrategy,
    ]
    corrective_props = [
        NS.hasCorrectiveStrategy, NS.hasAdministrativeStrategy, NS.hasGroupStrategy,
        NS.hasIndividualStrategy, NS.hasProjectManagementStrategy, NS.hasTechnicalStrategy,
    ]
    indicator_props = [NS.isIndicatedByCause, NS.isMonitoredByIndicator]
    metric_props = [NS.isMeasuredByMetric]
    risk_props = [NS.leadsToRisk, NS.generatesRisk]
    community_smell_props = [NS.hasRelatedCommunitySmell, NS.hasCauseCommunitySmell]

    for prop in preventive_props:
        for obj in global_g.objects(cause_uri, prop):
            preventive.add(local_name(obj))

    for effect in global_g.objects(cause_uri, NS.generatesEffect):
        effects.add(local_name(effect))
        for prop in corrective_props:
            for strategy in global_g.objects(effect, prop):
                corrective.add(local_name(strategy))

    for prop in indicator_props:
        for obj in global_g.objects(cause_uri, prop):
            indicators.add(local_name(obj))

    for prop in metric_props:
        for obj in global_g.objects(cause_uri, prop):
            metrics.add(local_name(obj))

    for prop in risk_props:
        for obj in global_g.objects(cause_uri, prop):
            risks.add(local_name(obj))

    for prop in community_smell_props:
        for obj in global_g.objects(cause_uri, prop):
            community_smells.add(local_name(obj))

    return {
        "preventive_strategies": sorted(preventive),
        "effects": sorted(effects),
        "corrective_strategies": sorted(corrective),
        "indicators": sorted(indicators),
        "metrics": sorted(metrics),
        "risks": sorted(risks),
        "community_smells": sorted(community_smells)
    }
