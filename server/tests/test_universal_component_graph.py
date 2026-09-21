from server.services.universal_component_graph import (
    ComponentEdge,
    EdgeStatus,
    UniversalComponentGraph,
    make_node,
)


def test_recursive_graph_preserves_supplied_topology():
    graph = UniversalComponentGraph()

    for node in (
        make_node("tool-1", "TOOL", version="1"),
        make_node("lego-1", "LEGO", version="1"),
        make_node("tool-2", "TOOL", version="2"),
        make_node("output-1", "FINAL_OUTPUT", version="1"),
    ):
        graph.add_node(node)

    graph.add_edge(ComponentEdge("tool-1", "lego-1", "TOOL_TO_LEGO"))
    graph.add_edge(ComponentEdge("lego-1", "tool-2", "LEGO_TO_TOOL"))
    graph.add_edge(ComponentEdge("tool-2", "output-1", "TOOL_TO_FINAL"))

    assert [n.identity.component_id for n in graph.walk_downstream("tool-1")] == [
        "lego-1",
        "tool-2",
        "output-1",
    ]


def test_identity_keeps_version_revision_hash_and_parent_context():
    graph = UniversalComponentGraph()

    node = make_node(
        "tool-1",
        "TOOL",
        version="3",
        revision="r17",
        artifact_hash="sha256:abc",
        parent_context="workflow-7",
    )
    graph.add_node(node)

    snapshot = graph.snapshot()
    item = snapshot["nodes"][0]

    assert item["id"] == "tool-1"
    assert item["version"] == "3"
    assert item["revision"] == "r17"
    assert item["artifact_hash"] == "sha256:abc"
    assert item["parent_context"] == "workflow-7"


def test_failed_upstream_blocks_downstream():
    graph = UniversalComponentGraph()
    graph.add_node(make_node("a", "TOOL"))
    graph.add_node(make_node("b", "LEGO"))

    graph.add_edge(
        ComponentEdge(
            "a",
            "b",
            "TOOL_TO_LEGO",
            status=EdgeStatus.FAIL,
        )
    )

    assert graph.nodes["b"].status == "BLOCKED"


def test_adapter_and_io_provenance_are_preserved():
    graph = UniversalComponentGraph()
    graph.add_node(make_node("a", "TOOL"))
    graph.add_node(make_node("b", "LEGO"))

    graph.add_edge(
        ComponentEdge(
            "a",
            "b",
            "TOOL_TO_LEGO",
            adapter="adapter-json-text",
            input_ref="input:a",
            output_ref="output:b",
            provenance={"source": "caller", "boundary": "adapter"},
        )
    )

    edge = graph.edges[0]

    assert edge.adapter == "adapter-json-text"
    assert edge.input_ref == "input:a"
    assert edge.output_ref == "output:b"
    assert edge.provenance["boundary"] == "adapter"
