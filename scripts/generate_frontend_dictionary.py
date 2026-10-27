"""
Generador de Diccionario Ontológico Frontend.

Parsea la ontología OWL/RDF de deuda social (app/infrastructure/ontologyv4.rdf)
y genera la estructura estructurada en JSON en data/frontend_ontology_dictionary.json,
utilizada por los clientes frontend y los scripts de prueba.

Uso:
    python scripts/generate_frontend_dictionary.py
"""

import json
import os
import sys
from rdflib import Graph, Namespace

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RDF_PATH = os.path.join(BASE_DIR, "app", "infrastructure", "ontologyv4.rdf")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "frontend_ontology_dictionary.json")

def generate_dict():
    if not os.path.exists(RDF_PATH):
        print(f"[ERROR] Archivo RDF no encontrado en: {RDF_PATH}")
        sys.exit(1)

    g = Graph()
    g.parse(RDF_PATH)
    ns = Namespace("http://www.example.org/ontosocialdebt#")

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
        return str(node).split("#")[-1]

    for s in g.subjects():
        s_id = local_name(s)

        strat_desc = next(g.objects(s, ns.hasStrategyDescription), None)
        strat_name = next(g.objects(s, ns.hasStrategyName), None)
        if strat_name or strat_desc:
            frontend_dict["strategies"][s_id] = {
                "name": str(strat_name) if strat_name else s_id,
                "description": str(strat_desc) if strat_desc else ""
            }

        eff_desc = next(g.objects(s, ns.hasEffectDescription), None)
        eff_name = next(g.objects(s, ns.hasEffectName), None)
        if eff_name or eff_desc:
            frontend_dict["effects"][s_id] = {
                "name": str(eff_name) if eff_name else s_id,
                "description": str(eff_desc) if eff_desc else ""
            }

        risk_desc = next(g.objects(s, ns.hasRiskDescription), None)
        risk_name = next(g.objects(s, ns.hasRiskName), None)
        if risk_name or risk_desc:
            frontend_dict["risks"][s_id] = {
                "name": str(risk_name) if risk_name else s_id,
                "description": str(risk_desc) if risk_desc else ""
            }

        ind_desc = next(g.objects(s, ns.hasIndicatorDescription), None)
        ind_name = next(g.objects(s, ns.hasIndicatorName), None)
        if ind_name or ind_desc:
            frontend_dict["indicators"][s_id] = {
                "name": str(ind_name) if ind_name else s_id,
                "description": str(ind_desc) if ind_desc else ""
            }

        met_desc = next(g.objects(s, ns.hasMetricDescription), None)
        met_name = next(g.objects(s, ns.hasMetricName), None)
        if met_name or met_desc:
            frontend_dict["metrics"][s_id] = {
                "name": str(met_name) if met_name else s_id,
                "description": str(met_desc) if met_desc else ""
            }

        cause_desc = next(g.objects(s, ns.hasCauseDescription), None)
        cause_name = next(g.objects(s, ns.hasCauseName), None)
        if cause_name or cause_desc:
            frontend_dict["micro_causes"][s_id] = {
                "name": str(cause_name) if cause_name else s_id,
                "description": str(cause_desc) if cause_desc else ""
            }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(frontend_dict, f, ensure_ascii=False, indent=2)

    print(f"[OK] Diccionario ontológico generado exitosamente en: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_dict()
