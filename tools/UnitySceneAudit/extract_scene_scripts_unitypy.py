#!/usr/bin/env python3
"""List MonoBehaviour script classes from stripped Unity Player scenes.

Only the built-in MonoBehaviour header is decoded (GameObject, enabled flag,
MonoScript pointer and component name). Custom serialized fields are not read.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import UnityPy

if len(sys.argv) != 3:
    raise SystemExit("usage: extract_scene_scripts_unitypy.py <data-dir> <output-dir>")

data_dir = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

# Load only the SerializedFiles supplied in the partial Data archive.
skip_suffixes = {".resource", ".ress", ".json", ".info", ".config"}
input_files = [
    p for p in sorted(data_dir.iterdir())
    if p.is_file() and p.suffix.lower() not in skip_suffixes
]
env = UnityPy.Environment(*[str(p) for p in input_files])

# UnityPy's environment keys are paths; map parsed SerializedFile instances to their filenames.
file_names = {}
for key, value in env.files.items():
    file_names[id(value)] = Path(key).name

rows = []
errors = []
type_counts = Counter()
mono_count = 0
resolved_count = 0

for obj in env.objects:
    sf_name = file_names.get(id(obj.assets_file), Path(getattr(obj.assets_file, "name", "")).name)
    if sf_name not in {"level0", "level1"}:
        continue

    type_name = getattr(obj.type, "name", str(obj.type))
    type_counts[(sf_name, type_name)] += 1
    if type_name != "MonoBehaviour":
        continue

    mono_count += 1
    record = {
        "serialized_file": sf_name,
        "component_object_id": obj.path_id,
        "component_name": "",
        "game_object_name": "",
        "game_object_active": "",
        "component_enabled": "",
        "class_name": "",
        "namespace": "",
        "assembly_name": "",
        "script_path_id": "",
        "status": "unresolved",
    }

    try:
        # Decode only Unity's built-in MonoBehaviour header; no game-specific TypeTree is required.
        head = obj.parse_monobehaviour_head()
        record["component_name"] = getattr(head, "m_Name", "") or ""
        record["component_enabled"] = getattr(head, "m_Enabled", "")

        go_ref = getattr(head, "m_GameObject", None)
        if go_ref:
            try:
                go = go_ref.deref_parse_as_object()
                record["game_object_name"] = getattr(go, "m_Name", "") or ""
                record["game_object_active"] = getattr(go, "m_IsActive", "")
            except Exception as e:
                errors.append(f"{sf_name}:{obj.path_id}: GameObject reference: {type(e).__name__}: {e}")

        script_ref = getattr(head, "m_Script", None)
        if not script_ref:
            record["status"] = "no MonoScript reference"
        else:
            record["script_path_id"] = getattr(script_ref, "path_id", "")
            try:
                script = script_ref.deref_parse_as_object()
                record["class_name"] = getattr(script, "m_ClassName", "") or ""
                record["namespace"] = getattr(script, "m_Namespace", "") or ""
                record["assembly_name"] = getattr(script, "m_AssemblyName", "") or ""
                record["status"] = "resolved"
                resolved_count += 1
            except Exception as e:
                record["status"] = "MonoScript target unavailable"
                errors.append(f"{sf_name}:{obj.path_id}: MonoScript reference: {type(e).__name__}: {e}")
    except Exception as e:
        record["status"] = "header parse failed"
        errors.append(f"{sf_name}:{obj.path_id}: MonoBehaviour header: {type(e).__name__}: {e}")

    rows.append(record)

fields = [
    "serialized_file", "component_object_id", "component_name", "game_object_name",
    "game_object_active", "component_enabled", "class_name", "namespace",
    "assembly_name", "script_path_id", "status"
]
with (out_dir / "scene_scripts.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

with (out_dir / "scene_type_counts.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["serialized_file", "type", "object_count"])
    for (sf, typ), count in sorted(type_counts.items()):
        writer.writerow([sf, typ, count])

summary = {
    "unitypy_version": UnityPy.__version__,
    "input_serialized_files": [p.name for p in input_files],
    "scene_files": ["level0", "level1"],
    "scene_object_type_rows": len(type_counts),
    "monobehaviour_objects": mono_count,
    "resolved_script_references": resolved_count,
    "unresolved_or_failed": mono_count - resolved_count,
    "parse_error_count": len(errors),
    "note": "Only the built-in MonoBehaviour header and MonoScript references were decoded. Custom script fields were not decoded. The supplied Player Data archive is partial, so external MonoScript targets may be missing."
}
(out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
(out_dir / "errors.txt").write_text("\n".join(errors), encoding="utf-8")
print(json.dumps(summary, indent=2))
if errors:
    print(f"Detailed parse/reference errors: {len(errors)} (see errors.txt)")
