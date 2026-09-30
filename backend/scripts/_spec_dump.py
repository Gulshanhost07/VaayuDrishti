import json

with open("../docs/openapi.json", encoding="utf-8") as fh:
    spec = json.load(fh)
print("title:", spec["info"].get("title"))
print("version:", spec["info"].get("version"))
print("schemas:", len(spec.get("components", {}).get("schemas", {})))
print("securitySchemes:", list(spec.get("components", {}).get("securitySchemes", {})))
print()
for path, ops in sorted(spec["paths"].items()):
    for method, op in ops.items():
        if method not in ("get", "post", "put", "patch", "delete"):
            continue
        sec = "auth" if op.get("security") else "public"
        summary = op.get("summary", "")
        print(f"{method.upper():6} {sec:6} {path}  {summary}")
