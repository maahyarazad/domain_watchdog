from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SPEC = yaml.safe_load(
    (Path(__file__).resolve().parents[3] / "specs/001-domain-uptime-watchdog/contracts/openapi.yaml").read_text()
)


def validator(schema_name: str) -> Draft202012Validator:
    """Validator for components.schemas[schema_name], resolving local $refs."""
    schema = {"$ref": f"#/components/schemas/{schema_name}", "components": SPEC["components"]}
    return Draft202012Validator(schema)


def inline_validator(path: str, status: str = "200") -> Draft202012Validator:
    node = SPEC["paths"][path]["get"]["responses"][status]["content"]["application/json"]["schema"]
    return Draft202012Validator({**node, "components": SPEC["components"]})
