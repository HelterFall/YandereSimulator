#!/usr/bin/env python3
"""Decode only the active DiscordRPC MonoBehaviour's serialized fields.

UnityPy's generated MonoBehaviour TypeTree header has a known alignment issue.
This script reads m_Script via the built-in MonoBehaviour header first, then
replaces the generated header nodes with UnityPy's built-in header nodes before
reading custom fields. It is read-only and redacts secret-like field names.
"""
import json
import sys
import zipfile
from pathlib import Path

import UnityPy
from UnityPy.enums import ClassIDType
from UnityPy.helpers.Tpk import get_typetree_node
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

if len(sys.argv) != 4:
    raise SystemExit("usage: decode_discord_component.py <data-dir> <managed.zip> <output.json>")

data_dir = Path(sys.argv[1])
managed_zip = Path(sys.argv[2])
out_path = Path(sys.argv[3])
out_path.parent.mkdir(parents=True, exist_ok=True)

result = {
    "unitypy_version": UnityPy.__version__,
    "target": "level0 GameObject Discord / DiscordRPC",
    "status": "not found",
    "decoded_fields": None,
    "error": None,
    "notes": [
        "Only the active DiscordRPC component's serialized fields are inspected.",
        "Secret-like fields are redacted.",
        "No game files are modified."
    ]
}

try:
    # Load the exact managed assemblies supplied in Managed.zip.
    generator = TypeTreeGenerator("6000.2.8f1")
    dll_count = 0
    with zipfile.ZipFile(managed_zip) as z:
        for name in z.namelist():
            if name.lower().endswith(".dll"):
                generator.load_dll(z.read(name))
                dll_count += 1
    result["managed_dlls_loaded_into_typetree_generator"] = dll_count

    # Load only the supplied SerializedFiles; companion resource streams are not needed here.
    skip_suffixes = {".resource", ".ress", ".json", ".info", ".config"}
    input_files = [
        p for p in sorted(data_dir.iterdir())
        if p.is_file() and p.suffix.lower() not in skip_suffixes
    ]
    env = UnityPy.Environment(*[str(p) for p in input_files])
    env.typetree_generator = generator

    for obj in env.objects:
        sf_name = Path(getattr(obj.assets_file, "name", "")).name
        if sf_name != "level0" or getattr(obj.type, "name", "") != "MonoBehaviour":
            continue

        # Read built-in header first so script identity and GameObject are reliable.
        head = obj.parse_monobehaviour_head()
        go = head.m_GameObject.deref_parse_as_object() if head.m_GameObject else None
        go_name = getattr(go, "m_Name", "") if go else ""
        if go_name != "Discord":
            continue

        script_ref = head.m_Script
        if not script_ref:
            continue
        script = script_ref.deref_parse_as_object()
        class_name = getattr(script, "m_ClassName", "") or ""
        namespace = getattr(script, "m_Namespace", "") or ""
        assembly = getattr(script, "m_AssemblyName", "") or ""
        fullname = f"{namespace}.{class_name}" if namespace else class_name
        if class_name != "DiscordRPC":
            continue

        node = generator.get_nodes_up(assembly, fullname)
        builtin = get_typetree_node(ClassIDType.MonoBehaviour, obj.version)
        builtin_header = builtin.m_Children
        generated_header = node.m_Children
        if len(generated_header) < len(builtin_header):
            raise RuntimeError("Generated TypeTree is shorter than the built-in MonoBehaviour header")
        expected_names = [n.m_Name for n in builtin_header]
        actual_names = [n.m_Name for n in generated_header[:len(builtin_header)]]
        if actual_names != expected_names:
            raise RuntimeError(f"Unexpected MonoBehaviour header order: {actual_names}")
        # Replace only the four built-in header nodes to preserve the known correct alignment.
        node.m_Children[:len(builtin_header)] = builtin_header

        fields = obj.read_typetree(node, wrap=False, check_read=False)

        def redact(value, key=""):
            lower = key.lower()
            if any(term in lower for term in ("token", "password", "secret", "credential")):
                return "<redacted>"
            if isinstance(value, dict):
                return {str(k): redact(v, str(k)) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [redact(v, key) for v in value]
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return str(value)

        result.update({
            "status": "decoded",
            "serialized_file": sf_name,
            "component_object_id": obj.path_id,
            "game_object": go_name,
            "game_object_active": getattr(go, "m_IsActive", None) if go else None,
            "component_enabled": getattr(head, "m_Enabled", None),
            "script_class": fullname,
            "script_assembly": assembly,
            "decoded_fields": redact(fields),
        })
        break

    if result["status"] != "decoded":
        result["error"] = "Active DiscordRPC component was not found or its MonoScript could not be resolved."
except Exception as e:
    result["status"] = "decode_failed"
    result["error"] = f"{type(e).__name__}: {e}"

out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))
