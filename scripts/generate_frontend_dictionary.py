import json
from rdflib import Graph, Namespace

def generate_dict():
    g = Graph()
    g.parse('app/infrastructure/ontologyv4.rdf')
    NS = Namespace('http://www.example.org/ontosocialdebt#')
    
    frontend_dict = {
        "macro_causes": {
            "A": "Communication and shared understanding breakdowns",
            "B": "Coordination and workflow misalignment",
            "C": "Technical complexity, compatibility, and system constraints",
            "D": "Organizational and procedural workflow constraints",
            "E": "Collaboration and interpersonal tensions",
            "F": "Knowledge, documentation, and standards deficiencies",
            "G": "Resource, tooling, access, and validation dependencies",
            "H": "No identificable (Noise)"
        },
        "micro_causes": {},
        "strategies": {},
        "effects": {},
        "indicators": {},
        "metrics": {},
        "risks": {}
    }
    
    def local_name(node):
        return str(node).split('#')[-1]
        
    for s in g.subjects():
        s_id = local_name(s)
        
        # Strategies (Preventive & Corrective)
        strat_desc = next(g.objects(s, NS.hasStrategyDescription), None)
        strat_name = next(g.objects(s, NS.hasStrategyName), None)
        if strat_name or strat_desc:
            frontend_dict["strategies"][s_id] = {
                "name": str(strat_name) if strat_name else s_id,
                "description": str(strat_desc) if strat_desc else ""
            }
            
        # Effects
        eff_desc = next(g.objects(s, NS.hasEffectDescription), None)
        eff_name = next(g.objects(s, NS.hasEffectName), None)
        if eff_name or eff_desc:
            frontend_dict["effects"][s_id] = {
                "name": str(eff_name) if eff_name else s_id,
                "description": str(eff_desc) if eff_desc else ""
            }
            
        # Risks
        risk_desc = next(g.objects(s, NS.hasRiskDescription), None)
        risk_name = next(g.objects(s, NS.hasRiskName), None)
        if risk_name or risk_desc:
            frontend_dict["risks"][s_id] = {
                "name": str(risk_name) if risk_name else s_id,
                "description": str(risk_desc) if risk_desc else ""
            }
            
        # Indicators
        ind_desc = next(g.objects(s, NS.hasIndicatorDescription), None)
        ind_name = next(g.objects(s, NS.hasIndicatorName), None)
        if ind_name or ind_desc:
            frontend_dict["indicators"][s_id] = {
                "name": str(ind_name) if ind_name else s_id,
                "description": str(ind_desc) if ind_desc else ""
            }
            
        # Metrics
        met_desc = next(g.objects(s, NS.hasMetricDescription), None)
        met_name = next(g.objects(s, NS.hasMetricName), None)
        if met_name or met_desc:
            frontend_dict["metrics"][s_id] = {
                "name": str(met_name) if met_name else s_id,
                "description": str(met_desc) if met_desc else ""
            }
            
        # Micro Causes
        cause_desc = next(g.objects(s, NS.hasCauseDescription), None)
        cause_name = next(g.objects(s, NS.hasCauseName), None)
        if cause_name or cause_desc:
            frontend_dict["micro_causes"][s_id] = {
                "name": str(cause_name) if cause_name else s_id,
                "description": str(cause_desc) if cause_desc else ""
            }
            
    with open("data/frontend_ontology_dictionary.json", "w", encoding="utf-8") as f:
        json.dump(frontend_dict, f, ensure_ascii=False, indent=2)
        
    print("Diccionario generado en data/frontend_ontology_dictionary.json")

generate_dict()
