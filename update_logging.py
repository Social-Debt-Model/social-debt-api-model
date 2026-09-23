import re

with open("app/infrastructure/ontology_client.py", "r") as f:
    code = f.read()

if "import logging" not in code:
    code = "import logging\n\nlogger = logging.getLogger(__name__)\n\n" + code

code = code.replace("print(f\"Warning: Failed to load ontology: {e}\")", "logger.warning(f\"Failed to load ontology: {e}\")")

with open("app/infrastructure/ontology_client.py", "w") as f:
    f.write(code)

print("Updated ontology_client.py logging")
