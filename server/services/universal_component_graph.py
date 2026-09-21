"""Universal Component Graph - Batch A.

Pure graph/provenance model. Does not modify workflow execution,
Temporal, plugin, persistence, or runtime infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class EdgeStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ComponentIdentity:
    component_id: str
    component_type: str
    version: str | None = None
    revision: str | None = None
    artifact_hash: str | None = None
    parent_context: str | None = None


@dataclass
class ComponentNode:
    identity: ComponentIdentity
    status: str = "AVAILABLE"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentEdge:
    source: str
    target: str
    relation: str
    status: EdgeStatus = EdgeStatus.PASS
    adapter: str | None = None
    input_ref: str | None = None
    output_ref: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


class UniversalComponentGraph:
    """Canonical topology/provenance graph.

    The graph records only relationships supplied by the caller.
    It never invents topology or opaque implementation details.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, ComponentNode] = {}
        self.edges: list[ComponentEdge] = []

    def add_node(self, node: ComponentNode) -> ComponentNode:
        self.nodes[node.identity.component_id] = node
        return node

    def add_edge(self, edge: ComponentEdge) -> ComponentEdge:
        if edge.source not in self.nodes:
            raise KeyError(f"Unknown source node: {edge.source}")
        if edge.target not in self.nodes:
            raise KeyError(f"Unknown target node: {edge.target}")

        self.edges.append(edge)

        # Invalid upstream means downstream is blocked unless the
        # edge itself has already been explicitly marked BLOCKED.
        if edge.status == EdgeStatus.FAIL:
            self.nodes[edge.target].status = "BLOCKED"

        return edge

    def downstream(self, component_id: str) -> list[ComponentNode]:
        targets = [
            e.target
            for e in self.edges
            if e.source == component_id
            and e.status != EdgeStatus.FAIL
        ]
        return [self.nodes[x] for x in targets if x in self.nodes]

    def upstream(self, component_id: str) -> list[ComponentNode]:
        sources = [
            e.source
            for e in self.edges
            if e.target == component_id
        ]
        return [self.nodes[x] for x in sources if x in self.nodes]

    def walk_downstream(self, component_id: str) -> list[ComponentNode]:
        """Recursive traversal preserving supplied topology."""
        result: list[ComponentNode] = []
        seen: set[str] = set()

        def visit(node_id: str) -> None:
            for node in self.downstream(node_id):
                if node.identity.component_id in seen:
                    continue
                seen.add(node.identity.component_id)
                result.append(node)
                visit(node.identity.component_id)

        visit(component_id)
        return result

    def edges_for(self, component_id: str) -> list[ComponentEdge]:
        return [
            e for e in self.edges
            if e.source == component_id or e.target == component_id
        ]

    def snapshot(self) -> dict[str, Any]:
        """Serializable graph snapshot.

        Opaque internals are deliberately represented as UNAVAILABLE
        rather than guessed.
        """
        return {
            "nodes": [
                {
                    "id": n.identity.component_id,
                    "type": n.identity.component_type,
                    "version": n.identity.version,
                    "revision": n.identity.revision,
                    "artifact_hash": n.identity.artifact_hash,
                    "parent_context": n.identity.parent_context,
                    "status": n.status,
                    "metadata": n.metadata,
                }
                for n in self.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                    "status": e.status.value,
                    "adapter": e.adapter,
                    "input_ref": e.input_ref,
                    "output_ref": e.output_ref,
                    "provenance": e.provenance,
                }
                for e in self.edges
            ],
        }


def make_node(
    component_id: str,
    component_type: str,
    *,
    version: str | None = None,
    revision: str | None = None,
    artifact_hash: str | None = None,
    parent_context: str | None = None,
    status: str = "AVAILABLE",
    metadata: dict[str, Any] | None = None,
) -> ComponentNode:
    return ComponentNode(
        identity=ComponentIdentity(
            component_id=component_id,
            component_type=component_type,
            version=version,
            revision=revision,
            artifact_hash=artifact_hash,
            parent_context=parent_context,
        ),
        status=status,
        metadata=metadata or {},
    )


def add_nodes(
    graph: UniversalComponentGraph,
    nodes: Iterable[ComponentNode],
) -> UniversalComponentGraph:
    for node in nodes:
        graph.add_node(node)
    return graph
