"""Topological sort for project module execution ordering.

Resolves module dependencies into parallel execution layers using Kahn's algorithm.
Each layer contains modules that can run concurrently (no intra-layer dependencies).
"""
from __future__ import annotations

import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


def resolve_execution_order(modules: list[dict]) -> list[list[dict]]:
    """Topological sort into layers. Each layer can run in parallel.

    Uses Kahn's algorithm (BFS-based) to determine a valid execution order
    respecting depends_on declarations.

    Args:
        modules: List of module dicts with keys 'name' and 'depends_on' (list[str]).
                 Example: [{"name": "a", "depends_on": []},
                           {"name": "b", "depends_on": ["a"]}]

    Returns:
        Ordered list of layers. Each layer is a list of module dicts that
        can be executed in parallel.
        Example: [[{"name": "a", ...}], [{"name": "b", ...}]]

    Raises:
        ValueError: If a cycle is detected or an unknown dependency is referenced.
    """
    if not modules:
        return []

    # Index by name for quick lookup
    by_name: dict[str, dict] = {m["name"]: m for m in modules}

    # Validate all dependency references exist
    for mod in modules:
        for dep in mod.get("depends_on") or []:
            if dep not in by_name:
                raise ValueError(
                    f"Module '{mod['name']}' depends on unknown module '{dep}'"
                )

    # Build adjacency: dep -> dependents (edges go dep → dependent)
    dependents: dict[str, list[str]] = defaultdict(list)
    # in-degree: number of unresolved dependencies per module
    in_degree: dict[str, int] = {m["name"]: 0 for m in modules}

    for mod in modules:
        for dep in mod.get("depends_on") or []:
            dependents[dep].append(mod["name"])
            in_degree[mod["name"]] += 1

    # Kahn's algorithm: start with nodes having in_degree == 0
    queue: deque[str] = deque(
        name for name, degree in in_degree.items() if degree == 0
    )
    layers: list[list[dict]] = []

    while queue:
        # All nodes currently in the queue form one parallel layer
        layer_names = list(queue)
        queue.clear()

        layer = [by_name[name] for name in layer_names]
        layers.append(layer)

        # Reduce in-degree for each dependent
        next_ready: list[str] = []
        for name in layer_names:
            for dependent in dependents[name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    next_ready.append(dependent)

        queue.extend(next_ready)

    # If any module still has in_degree > 0, a cycle exists
    remaining = [name for name, d in in_degree.items() if d > 0]
    if remaining:
        raise ValueError(
            f"Dependency cycle detected involving module(s): {', '.join(sorted(remaining))}"
        )

    logger.debug(
        "Resolved %d modules into %d execution layers", len(modules), len(layers)
    )
    return layers
