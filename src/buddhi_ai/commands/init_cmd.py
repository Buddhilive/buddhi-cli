import argparse
import os
import time
from pathlib import Path

from buddhi_ai.db.connection import init_db
from buddhi_ai.parser.tree_sitter import parse_file, LANGUAGE_MAP, load_languages
from buddhi_ai.parser.entropy import filter_boilerplate
from buddhi_ai.graph.builder import load_graph
from buddhi_ai.graph.clustering import run_leiden
from buddhi_ai.graph.sync import update_communities


def handle_init(args: argparse.Namespace) -> None:
    workspace_root = os.getcwd()
    print(f"Initializing buddhi-ai in workspace: {workspace_root}")
    print(f"Entropy threshold: {args.entropy_threshold}")

    # Initialize DB
    conn = init_db(workspace_root)
    load_languages()

    supported_exts = set(LANGUAGE_MAP.keys())

    scanned_count = 0
    skipped_count = 0
    filtered_nodes_count = 0
    inserted_nodes_count = 0

    # Simple sequential walk
    for root, dirs, files in os.walk(workspace_root):
        # Exclude common directories
        if ".git" in dirs:
            dirs.remove(".git")
        if ".buddhi" in dirs:
            dirs.remove(".buddhi")
        if ".venv" in dirs:
            dirs.remove(".venv")
        if "node_modules" in dirs:
            dirs.remove("node_modules")

        for file in files:
            filepath = Path(root) / file
            if filepath.suffix.lower() not in supported_exts:
                continue

            try:
                mtime = os.path.getmtime(filepath)
            except OSError:
                continue

            rel_path = str(filepath.relative_to(workspace_root))

            # Check incremental update
            cur = conn.cursor()
            cur.execute("SELECT id, mtime FROM files WHERE path = ?", (rel_path,))
            row = cur.fetchone()

            file_id = None
            if row:
                file_id, db_mtime = row
                if db_mtime == mtime:
                    # Unchanged
                    skipped_count += 1
                    continue

            # File is new or modified
            scanned_count += 1
            print(f"Scanning: {rel_path}")

            # Upsert file record
            current_time = time.time()
            if file_id:
                cur.execute(
                    "UPDATE files SET mtime = ?, last_scanned = ? WHERE id = ?",
                    (mtime, current_time, file_id),
                )
                # Delete old nodes to replace them (cascade should delete edges)
                cur.execute("DELETE FROM nodes WHERE file_id = ?", (file_id,))
            else:
                cur.execute(
                    "INSERT INTO files (path, mtime, last_scanned) VALUES (?, ?, ?)",
                    (rel_path, mtime, current_time),
                )
                file_id = cur.lastrowid

            # Parse file
            nodes = parse_file(filepath)
            language_name = LANGUAGE_MAP[filepath.suffix.lower()].name

            for node in nodes:
                content = node["content"]

                # Check entropy
                if filter_boilerplate(content, args.entropy_threshold):
                    filtered_nodes_count += 1
                    continue

                # Insert node
                # Note: tree-sitter node type mapping
                cur.execute(
                    """
                    INSERT INTO nodes (file_id, language, node_type, name, content, start_line, end_line, entropy_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        file_id,
                        language_name,
                        node["type"],
                        node["name"],
                        content,
                        node["start_line"],
                        node["end_line"],
                        0.0,  # Optional: store the actual score if needed
                    ),
                )
                inserted_nodes_count += 1

            conn.commit()

    conn.close()

    print("\nScan Summary (Phase 1):")
    print(f"  Files scanned: {scanned_count}")
    print(f"  Files skipped (unchanged): {skipped_count}")
    print(f"  Nodes inserted: {inserted_nodes_count}")
    print(f"  Boilerplate nodes filtered: {filtered_nodes_count}")
    
    print("\n--- Phase 2: Topological Graph Clustering ---")
    db_path = os.path.join(workspace_root, ".buddhi", "graph.db")
    print("Loading graph into memory...")
    g, ig_id_to_db_id = load_graph(db_path)
    print(f"Graph loaded with {g.vcount()} nodes and {g.ecount()} edges.")
    
    if g.vcount() > 0:
        print("Running Leiden clustering algorithm...")
        community_mapping = run_leiden(g, ig_id_to_db_id)
        print(f"Identified {len(set(community_mapping.values()))} communities.")
        
        print("Synchronizing communities to database...")
        update_communities(db_path, community_mapping)
        print("Database synchronization complete.")
        
        print("\n--- Phase 3: Client Visualization ---")
        from buddhi_ai.graph.visualizer import generate_graph_html
        html_path = os.path.join(workspace_root, ".buddhi", "graph.html")
        print("Generating interactive graph visualization...")
        generate_graph_html(db_path, html_path)
    else:
        print("Graph is empty. Skipping clustering and visualization.")
        
    print("\nDone.")
