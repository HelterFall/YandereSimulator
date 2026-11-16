#!/usr/bin/env python3
"""Extract a compact MonoBehaviour inventory from a UnityDataTool SQLite database."""
import csv
import json
import sqlite3
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: extract_scene_scripts.py <analysis.db> <output-dir>")

db_path = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
con.row_factory = sqlite3.Row

tables = {r["name"] for r in con.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
(out_dir / "database_objects.json").write_text(
    json.dumps({"tables_and_views": sorted(tables)}, indent=2),
    encoding="utf-8"
)

if "object_view" not in tables:
    raise SystemExit("UnityDataTool database is missing object_view")

def write_csv(filename, query, params=()):
    cur = con.execute(query, params)
    rows = cur.fetchall()
    with (out_dir / filename).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([c[0] for c in cur.description])
        writer.writerows([tuple(row) for row in rows])
    return len(rows)

summary_count = write_csv(
    "scene_type_counts.csv",
    """
    SELECT serialized_file, type, COUNT(*) AS object_count
    FROM object_view
    WHERE serialized_file IN ('level0', 'level1')
    GROUP BY serialized_file, type
    ORDER BY serialized_file, object_count DESC, type
    """
)

script_count = 0
script_error = None
if "script_object_view" in tables:
    try:
        script_count = write_csv(
            "scene_scripts.csv",
            """
            SELECT mb.serialized_file,
                   mb.object_id AS component_object_id,
                   mb.name AS component_name,
                   go.name AS game_object_name,
                   so.class_name,
                   so.namespace,
                   so.assembly_name
            FROM script_object_view so
            JOIN object_view mb ON mb.id = so.id
            LEFT JOIN object_view go ON go.id = mb.game_object
            WHERE mb.serialized_file IN ('level0', 'level1')
            ORDER BY mb.serialized_file, go.name, so.assembly_name, so.namespace, so.class_name
            """
        )
    except sqlite3.Error as e:
        script_error = str(e)
else:
    script_error = "script_object_view is absent; reference extraction may have failed or been skipped"

mono_count = write_csv(
    "scene_monobehaviour_objects.csv",
    """
    SELECT serialized_file, object_id, name, game_object, pretty_size
    FROM object_view
    WHERE serialized_file IN ('level0', 'level1') AND type = 'MonoBehaviour'
    ORDER BY serialized_file, object_id
    """
)

summary = {
    "database": db_path.name,
    "tables_and_views": len(tables),
    "scene_type_count_rows": summary_count,
    "scene_script_rows": script_count,
    "scene_monobehaviour_rows": mono_count,
    "script_inventory_error": script_error,
    "scope": ["level0", "level1"],
    "note": "Partial Data archive only. A missing MonoScript target may prevent some script class names from resolving."
}
(out_dir / "SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
con.close()
