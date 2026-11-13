# Validate a workflow file against the running ComfyUI node registry:
#   - every node type exists in /object_info
#   - every COMBO widget value is inside the allowed list
#
# Usage:
#   python scripts/validate_workflow.py workflows/minimax_h3_image_t2i_q3km.json
#   python scripts/validate_workflow.py workflows/api_prompt_img2img.json --api
#
# The --api flag validates an API-format prompt instead of a UI workflow
# (API format: no node type registry check, but combo values are still checked).
import json
import os
import sys
import urllib.request

API = os.environ.get("COMFY_API", "http://127.0.0.1:8188")


def load(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def check_api_format(prompt, info):
    problems = []
    for nid, node in prompt.items():
        ctype = node["class_type"]
        if ctype not in info:
            problems.append(f"node {nid}: unknown class_type {ctype}")
            continue
        schema = info[ctype]["input"]
        allowed = {}
        for group in ("required", "optional"):
            for name, spec in schema.get(group, {}).items():
                if isinstance(spec[0], list):
                    allowed[name] = spec[0]
        for name, val in node.get("inputs", {}).items():
            if name in allowed and isinstance(val, str) and val not in allowed[name]:
                problems.append(f"node {nid} ({ctype}) input '{name}' = '{val}' not in list")
    return problems


def check_ui_format(wf, info):
    problems, checked = [], 0

    def check_node(n, where):
        nonlocal checked
        t = n.get("type")
        if t in ("MarkdownNote", "PrimitiveStringMultiline", "PreviewAny"):
            return
        if t.startswith("b350fbfc") or t in [s["id"] for s in wf["definitions"]["subgraphs"]]:
            return  # subgraph instance
        if t not in info:
            problems.append(f"[{where}] node {n.get('id')} unknown type: {t}")
            return
        schema = info[t]["input"]
        order = []
        for group in ("required", "optional"):
            for name, spec in schema.get(group, {}).items():
                if isinstance(spec[0], list):
                    order.append((name, spec[0]))
        vals = n.get("widgets_values") or []
        FRONTEND_ONLY = {"randomize", "fixed", "increment"}
        vi = 0
        for name, allowed in order:
            while vi < len(vals) and isinstance(vals[vi], str) and vals[vi] in FRONTEND_ONLY and vals[vi] not in allowed:
                vi += 1
            if vi >= len(vals):
                break
            v = vals[vi]
            vi += 1
            if not isinstance(v, str):
                continue
            checked += 1
            if v not in allowed:
                problems.append(f"[{where}] node {n.get('id')} ({t}) widget '{name}' = '{v}' not in list")

    for n in wf["nodes"]:
        check_node(n, "top")
    for sg in wf["definitions"]["subgraphs"]:
        for n in sg["nodes"]:
            check_node(n, f"subgraph:{sg.get('name')}")
    return problems, checked


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    api_mode = "--api" in sys.argv[2:]

    with urllib.request.urlopen(f"{API}/object_info", timeout=120) as r:
        info = json.load(r)

    data = load(path)
    if api_mode:
        problems = check_api_format(data, info)
        print(f"checked {len(data)} API nodes")
    else:
        problems, checked = check_ui_format(data, info)
        print(f"checked {checked} combo widget values")

    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("OK: all node types and combo values valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
