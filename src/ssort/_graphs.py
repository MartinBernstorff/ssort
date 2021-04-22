from ssort._bubble_sort import bubble_sort
from ssort._utils import sort_key_from_iter


class Graph:
    def __init__(self):
        self.nodes = []
        self.dependencies = {}
        self.dependants = {}

    def add_node(self, identifier):
        if identifier not in self.nodes:
            self.nodes.append(identifier)
            self.dependencies[identifier] = []
            self.dependants[identifier] = []

    def add_dependency(self, node, dependency):
        assert dependency in self.nodes

        if dependency not in self.dependencies[node]:
            self.dependencies[node].append(dependency)
            self.dependants[dependency].append(node)

    def remove_node(self, node):
        self.nodes.remove(node)
        del self.dependencies[node]
        del self.dependants[node]

        for other in self.nodes:
            try:
                self.dependencies[other].remove(node)
            except ValueError:
                pass

            try:
                self.dependants[other].remove(node)
            except ValueError:
                pass

    def remove_dependency(self, node, dependency):
        assert dependency in self.nodes

        try:
            self.dependencies[node].remove(dependency)
        except ValueError:
            pass

        try:
            self.dependants[dependency].remove(node)
        except ValueError:
            pass

    def copy(self):
        dup = Graph()
        for node in self.nodes:
            dup.add_node(node)

        for node in self.nodes:
            for dependency in self.dependencies[node]:
                dup.add_dependency(node, dependency)

        return dup


def _remove_self_references(graph):
    for node in graph.nodes:
        graph.remove_dependency(node, node)


def _find_cycle(graph):
    processed = set()
    for node in graph.nodes:
        if node in processed:
            continue

        in_stack = {node}
        stack = [(node, set(graph.dependencies[node]))]

        while stack:
            top_node, top_dependencies = stack[-1]

            if not top_dependencies:
                processed.add(top_node)
                in_stack.remove(top_node)
                stack.pop()
                continue

            dependency = top_dependencies.pop()
            if dependency in in_stack:
                cycle = [dependency]
                while stack[-1][0] != dependency:
                    cycle.append(stack[-1][0])
                    stack.pop()
                return cycle
            if dependency not in processed:
                stack.append((dependency, set(graph.dependencies[dependency])))
                in_stack.add(dependency)


def replace_cycles(graph, *, key):
    """
    Finds all cycles and replaces them with forward links that keep them from
    being re-ordered.
    """
    _remove_self_references(graph)
    while True:
        cycle = _find_cycle(graph)
        if not cycle:
            break

        for node in cycle:
            for dependency in cycle:
                graph.remove_dependency(node, dependency)

        # TODO this is a bit of an abstraction leak.  Need a better way to tell
        # this function what the safe order is.
        nodes = iter(sorted(cycle, key=key))
        prev = next(nodes)
        for node in nodes:
            graph.add_dependency(node, prev)
            prev = node


def is_topologically_sorted(nodes, graph):
    visited = set()
    for node in nodes:
        visited.add(node)
        for dependency in graph.dependencies[node]:
            if dependency not in visited:
                return False
    return True


def topological_sort(graph):
    # Create a mutable copy of the graph so that we can pop edges from it as we
    # traverse.
    remaining = graph.copy()

    key = sort_key_from_iter(graph.nodes)

    pending = [node for node in graph.nodes if not graph.dependants[node]]

    result = []
    while pending:
        pending = list(sorted(pending, key=key))
        node = pending.pop()
        dependencies = remaining.dependencies[node]
        remaining.remove_node(node)

        for dependency in dependencies:
            if not remaining.dependants[dependency]:
                if dependency not in pending:
                    pending.append(dependency)

        result.append(node)

    result.reverse()

    assert not remaining.nodes
    assert is_topologically_sorted(result, graph)

    return result


def _optimize(statements, graph, *, key=lambda value: value):
    statements = statements.copy()

    def _swap(a, b):
        if a in graph.dependencies[b]:
            return False

        if key(a) < key(b):
            return False
        return True

    # Bubble sort will only move items one step at a time, meaning that we can
    # make sure nothing ever moves past something that depends on it.  The
    # builtin `sorted` function, while much faster, might result in us breaking
    # the topological sort.
    bubble_sort(statements, _swap)

    return statements


def stable_topological_sort(nodes, graph):
    # TODO this function came about in an extremely path dependent way.  It can
    # definitely be done without the bubble sort.
    sorted_nodes = [node for node in topological_sort(graph) if node in nodes]

    sorted_nodes = _optimize(
        sorted_nodes, graph, key=sort_key_from_iter(nodes)
    )

    return sorted_nodes
