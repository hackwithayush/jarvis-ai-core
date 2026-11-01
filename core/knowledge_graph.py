"""
JARVIS 5.0 — Persistent Personal Knowledge Graph
Connects people, projects, files, decisions, tasks, documents, and system events.
Enables relational reasoning across:
- Dependencies: Project A DEPENDS_ON Project B
- Decisions: Code change RELATES_TO Decision X
- Blockers: Milestone 2 is BLOCKED_BY Task 1
- Evidence: Research document SUPPORTS Implementation Y
- Root Cause: System failure is CAUSED_BY Root Cause Z
Persists as an atomic graph on disk with backup snapshot protection.
"""
import os
import time
import json
import shutil
import logging
import threading
from typing import Dict, Any, List, Optional, Set, Tuple

logger = logging.getLogger("jarvis.knowledge_graph")


class KnowledgeGraph:
    """
    In-memory directed multi-relational graph with persistent atomic disk storage.
    Thread-safe and optimized for situational awareness and contextual queries.
    """

    VALID_NODE_TYPES = {
        "project",
        "decision",
        "task",
        "milestone",
        "objective",
        "file",
        "person",
        "system_event",
        "document",
        "tool"
    }

    VALID_RELATIONS = {
        "DEPENDS_ON",     # A depends on B
        "RELATES_TO",     # A is related to B
        "BLOCKED_BY",     # A is blocked by B
        "SUPPORTS",       # A provides evidence/support for B
        "CAUSED_BY",      # A (failure/event) was caused by B
        "AUTHORED_BY",    # Decision/code authored by Person
        "MODIFIES",       # Task/milestone modifies File
        "PART_OF"         # Milestone is part of Objective
    }

    def __init__(self, storage_dir: Optional[str] = None):
        self.lock = threading.RLock()
        self.storage_dir = os.path.abspath(storage_dir or os.path.join(os.getcwd(), "data", "knowledge_graph"))
        os.makedirs(self.storage_dir, exist_ok=True)
        self.graph_file = os.path.join(self.storage_dir, "graph.json")
        self.backup_file = f"{self.graph_file}.bak"

        # Graph in-memory structures:
        # nodes: {node_id: {"id": node_id, "type": str, "label": str, "properties": dict, "created_at": float, "updated_at": float}}
        self.nodes: Dict[str, Dict[str, Any]] = {}
        # edges: list of {"source": str, "target": str, "relation": str, "properties": dict, "created_at": float}
        self.edges: List[Dict[str, Any]] = []

        self._load_from_disk()
        logger.info(f"JARVIS 5.0 Knowledge Graph initialized: {len(self.nodes)} nodes, {len(self.edges)} edges.")

    # ─── Disk Persistence & Atomic Writes ──────────────────────────────────────

    def _save_to_disk(self):
        """Atomically saves graph to disk with fsync and backup snapshot."""
        temp_file = f"{self.graph_file}.tmp"
        data = {
            "version": "5.0",
            "nodes": self.nodes,
            "edges": self.edges,
            "saved_at": time.time()
        }
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())

            if os.path.exists(self.graph_file):
                try:
                    shutil.copy2(self.graph_file, self.backup_file)
                except Exception:
                    pass
                os.replace(temp_file, self.graph_file)
            else:
                os.rename(temp_file, self.graph_file)
        except Exception as e:
            logger.error(f"[KNOWLEDGE GRAPH] Failed to save graph to disk: {e}")

    def _load_from_disk(self):
        """Loads graph from disk with automatic corrupted-file backup recovery."""
        if os.path.isfile(self.graph_file):
            try:
                with open(self.graph_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])
                return
            except Exception as e:
                logger.warning(f"[KNOWLEDGE GRAPH] Primary graph corrupted: {e}. Attempting backup recovery...")

        if os.path.isfile(self.backup_file):
            try:
                with open(self.backup_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.nodes = data.get("nodes", {})
                self.edges = data.get("edges", [])
                shutil.copy2(self.backup_file, self.graph_file)
                logger.info("[KNOWLEDGE GRAPH] Restored graph from backup.")
                return
            except Exception as e:
                logger.error(f"[KNOWLEDGE GRAPH] Backup graph recovery failed: {e}")

        # Initialize defaults if brand new
        self.nodes = {}
        self.edges = []
        self._init_default_graph()

    def _init_default_graph(self):
        """Populates the base nodes and relations for the Jarvis workstation."""
        self.add_node(
            node_id="user_ayush",
            node_type="person",
            label="Ayush (Tony Stark)",
            properties={"role": "Chief Architect & Commander", "access_level": "Tier-0"}
        )
        self.add_node(
            node_id="jarvis_core",
            node_type="project",
            label="J.A.R.V.I.S. Autonomous Workstation",
            properties={"version": "5.0", "status": "active"}
        )
        self.add_edge("user_ayush", "jarvis_core", "AUTHORED_BY", {"desc": "Primary Creator"})

    # ─── Node & Edge Management ────────────────────────────────────────────────

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Adds or updates a node in the knowledge graph."""
        with self.lock:
            node_type = node_type.lower()
            if node_type not in self.VALID_NODE_TYPES:
                logger.warning(f"Unknown node type '{node_type}', registering as generic entity.")

            now = time.time()
            if node_id in self.nodes:
                self.nodes[node_id]["label"] = label
                self.nodes[node_id]["type"] = node_type
                if properties:
                    self.nodes[node_id]["properties"].update(properties)
                self.nodes[node_id]["updated_at"] = now
            else:
                self.nodes[node_id] = {
                    "id": node_id,
                    "type": node_type,
                    "label": label,
                    "properties": properties or {},
                    "created_at": now,
                    "updated_at": now
                }

            self._save_to_disk()
            return self.nodes[node_id]

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a node by its identifier."""
        with self.lock:
            return self.nodes.get(node_id)

    def delete_node(self, node_id: str) -> bool:
        """Deletes a node and all connected edges."""
        with self.lock:
            if node_id not in self.nodes:
                return False
            del self.nodes[node_id]
            # Remove all connected edges
            self.edges = [e for e in self.edges if e["source"] != node_id and e["target"] != node_id]
            self._save_to_disk()
            return True

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Adds a directed relation between source and target nodes."""
        with self.lock:
            relation = relation.upper()
            if relation not in self.VALID_RELATIONS:
                logger.warning(f"Non-standard relation '{relation}' registered.")

            # Ensure source and target exist as nodes; create placeholders if missing
            if source not in self.nodes:
                self.add_node(source, "generic", source)
            if target not in self.nodes:
                self.add_node(target, "generic", target)

            # Avoid exact duplicate edges
            for existing in self.edges:
                if (
                    existing["source"] == source
                    and existing["target"] == target
                    and existing["relation"] == relation
                ):
                    if properties:
                        existing["properties"].update(properties)
                    self._save_to_disk()
                    return existing

            edge = {
                "source": source,
                "target": target,
                "relation": relation,
                "properties": properties or {},
                "created_at": time.time()
            }
            self.edges.append(edge)
            self._save_to_disk()
            return edge

    def delete_edge(self, source: str, target: str, relation: Optional[str] = None) -> bool:
        """Deletes matching edge(s)."""
        with self.lock:
            before_len = len(self.edges)
            self.edges = [
                e for e in self.edges
                if not (
                    e["source"] == source
                    and e["target"] == target
                    and (relation is None or e["relation"] == relation.upper())
                )
            ]
            changed = len(self.edges) < before_len
            if changed:
                self._save_to_disk()
            return changed

    # ─── Relational Queries & Graph Traversal ──────────────────────────────────

    def query_relations(
        self,
        node_id: str,
        relation: Optional[str] = None,
        direction: str = "out"
    ) -> List[Dict[str, Any]]:
        """
        Queries connected edges for a given node.
        direction: 'out' (source=node_id), 'in' (target=node_id), or 'both'.
        """
        with self.lock:
            results = []
            rel_upper = relation.upper() if relation else None

            for edge in self.edges:
                match_rel = (rel_upper is None or edge["relation"] == rel_upper)
                if not match_rel:
                    continue

                if direction in ("out", "both") and edge["source"] == node_id:
                    results.append({
                        "direction": "out",
                        "relation": edge["relation"],
                        "target_id": edge["target"],
                        "target_node": self.nodes.get(edge["target"]),
                        "properties": edge["properties"]
                    })

                if direction in ("in", "both") and edge["target"] == node_id:
                    results.append({
                        "direction": "in",
                        "relation": edge["relation"],
                        "source_id": edge["source"],
                        "source_node": self.nodes.get(edge["source"]),
                        "properties": edge["properties"]
                    })

            return results

    def find_blockers(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Recursively identifies all entities that directly or indirectly block this task or milestone.
        Traverses outgoing 'BLOCKED_BY' and 'DEPENDS_ON' edges.
        """
        with self.lock:
            blockers = []
            visited: Set[str] = set()
            queue = [node_id]

            while queue:
                curr = queue.pop(0)
                if curr in visited:
                    continue
                visited.add(curr)

                for edge in self.edges:
                    if edge["source"] == curr and edge["relation"] in ("BLOCKED_BY", "DEPENDS_ON"):
                        target_id = edge["target"]
                        target_node = self.nodes.get(target_id, {})
                        # Check if target is not completed
                        status = target_node.get("properties", {}).get("status", "unknown")
                        is_active_blocker = status not in ("completed", "resolved", "passed")

                        blocker_record = {
                            "blocked_node": curr,
                            "blocking_node_id": target_id,
                            "relation": edge["relation"],
                            "label": target_node.get("label", target_id),
                            "type": target_node.get("type", "unknown"),
                            "status": status,
                            "is_active_blocker": is_active_blocker,
                            "reason": edge["properties"].get("reason", "Direct dependency or blocker")
                        }
                        blockers.append(blocker_record)

                        if target_id not in visited:
                            queue.append(target_id)

            return blockers

    def find_root_cause(self, event_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """
        Recursively traces 'CAUSED_BY' relationships to find the ultimate root cause of a system event or failure.
        """
        with self.lock:
            event_node = self.nodes.get(event_id)
            if not event_node:
                return {"error": f"Event '{event_id}' not found in knowledge graph."}

            chain = [event_node]
            curr_id = event_id
            visited: Set[str] = {curr_id}

            for _ in range(max_depth):
                # Look for outgoing CAUSED_BY edges
                found_next = False
                for edge in self.edges:
                    if edge["source"] == curr_id and edge["relation"] == "CAUSED_BY":
                        target_id = edge["target"]
                        if target_id not in visited and target_id in self.nodes:
                            visited.add(target_id)
                            chain.append(self.nodes[target_id])
                            curr_id = target_id
                            found_next = True
                            break
                if not found_next:
                    break

            root_node = chain[-1]
            return {
                "initial_event": event_node,
                "root_cause_node": root_node,
                "chain_length": len(chain),
                "causal_chain": chain,
                "is_deep_root_identified": len(chain) > 1
            }

    def find_related_decisions(self, file_path_or_node_id: str) -> List[Dict[str, Any]]:
        """
        Finds all architectural decisions connected to a file, project, or task.
        Traverses 'RELATES_TO', 'MODIFIES', and 'PART_OF' edges.
        """
        with self.lock:
            decisions = []
            normalized_target = os.path.basename(file_path_or_node_id).lower()

            # Find matching nodes
            target_ids = []
            for nid, node in self.nodes.items():
                if nid.lower() == normalized_target or node.get("label", "").lower() == normalized_target:
                    target_ids.append(nid)
                elif node.get("type") == "file" and os.path.basename(node.get("label", "")).lower() == normalized_target:
                    target_ids.append(nid)

            if file_path_or_node_id in self.nodes and file_path_or_node_id not in target_ids:
                target_ids.append(file_path_or_node_id)

            visited = set(target_ids)
            for tid in target_ids:
                # Direct relationships where decision is source or target
                for edge in self.edges:
                    if edge["relation"] in ("RELATES_TO", "MODIFIES", "AUTHORED_BY"):
                        other_id = edge["target"] if edge["source"] == tid else (edge["source"] if edge["target"] == tid else None)
                        if other_id and other_id in self.nodes:
                            other_node = self.nodes[other_id]
                            if other_node.get("type") == "decision":
                                decisions.append({
                                    "decision_id": other_id,
                                    "title": other_node.get("label"),
                                    "properties": other_node.get("properties"),
                                    "relation": edge["relation"],
                                    "connected_to": tid
                                })

            return decisions

    # ─── Specialized Linking Helpers ──────────────────────────────────────────

    def link_objective_milestone(
        self,
        objective_id: str,
        milestone_id: str,
        milestone_title: str,
        status: str = "pending"
    ):
        """Registers a milestone as PART_OF an objective and tracks its status."""
        self.add_node(
            node_id=milestone_id,
            node_type="milestone",
            label=milestone_title,
            properties={"status": status}
        )
        self.add_edge(milestone_id, objective_id, "PART_OF")

    def link_decision_to_code(
        self,
        decision_id: str,
        decision_text: str,
        file_path: str,
        objective_id: Optional[str] = None
    ):
        """Records an architectural decision and associates it with the modified file."""
        self.add_node(
            node_id=decision_id,
            node_type="decision",
            label=decision_text[:80],
            properties={"full_text": decision_text, "timestamp": time.time()}
        )
        file_node_id = f"file_{os.path.basename(file_path)}"
        self.add_node(
            node_id=file_node_id,
            node_type="file",
            label=file_path,
            properties={"path": file_path}
        )
        self.add_edge(decision_id, file_node_id, "RELATES_TO", {"desc": "Justifies code changes"})
        if objective_id:
            self.add_edge(decision_id, objective_id, "RELATES_TO", {"desc": "Produced during objective"})

    def link_failure_to_root_cause(
        self,
        event_id: str,
        failure_description: str,
        root_cause_id: str,
        root_cause_description: str
    ):
        """Registers a system failure and links it to its identified root cause."""
        self.add_node(
            node_id=event_id,
            node_type="system_event",
            label=failure_description[:80],
            properties={"description": failure_description, "status": "failed", "timestamp": time.time()}
        )
        self.add_node(
            node_id=root_cause_id,
            node_type="system_event",
            label=root_cause_description[:80],
            properties={"description": root_cause_description, "is_root_cause": True}
        )
        self.add_edge(event_id, root_cause_id, "CAUSED_BY", {"logged_at": time.time()})

    # ─── Graph Inspection & Export ────────────────────────────────────────────

    def inspect_graph(self) -> Dict[str, Any]:
        """Provides a complete serializable representation of the graph."""
        with self.lock:
            type_counts: Dict[str, int] = {}
            for n in self.nodes.values():
                t = n.get("type", "unknown")
                type_counts[t] = type_counts.get(t, 0) + 1

            rel_counts: Dict[str, int] = {}
            for e in self.edges:
                r = e.get("relation", "unknown")
                rel_counts[r] = rel_counts.get(r, 0) + 1

            return {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": type_counts,
                "relations": rel_counts,
                "nodes": list(self.nodes.values()),
                "edges": self.edges
            }


# Global Singleton Instance
knowledge_graph = KnowledgeGraph()
