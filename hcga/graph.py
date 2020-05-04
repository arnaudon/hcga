"""Classes representing single and a collection of graphs."""
import networkx as nx
import numpy as np
import scipy as sc
from tqdm import tqdm

MIN_NUM_NODES = 2


class GraphCollection:
    """Contain a list of graphs."""

    def __init__(self):
        """Set empty list of graphs."""
        self.graphs = []

    def add_graph(self, graph):
        """Add a graph to the list."""
        if not isinstance(graph, Graph):
            raise Exception("Only add class Graph to GraphCollection")
        graph.id = len(self.graphs)
        self.graphs.append(graph)

    def __iter__(self):
        """Makes this class iterable over the graphs."""
        self.current_graph = -1
        return self

    def __next__(self):
        """Get the next enabled graph."""
        self.current_graph += 1
        if self.current_graph >= len(self.graphs):
            raise StopIteration
        while self.graphs[self.current_graph].disabled:
            self.current_graph += 1
            if self.current_graph >= len(self.graphs):
                raise StopIteration
        return self.graphs[self.current_graph]

    def __len__(self):
        """Overrites the len() function to get number of enabled graphs."""
        return sum([1 for graph in self.graphs if not graph.disabled])

    def get_n_node_features(self):
        """Get the number of features of the nodes."""
        n_node_features = self.graphs[0].n_node_features
        for graph in self.graphs:
            assert n_node_features == graph.n_node_features
        return n_node_features

    def get_num_disabled_graphs(self):
        """Get the number of disabled graphs."""
        return len(self.graphs) - self.__len__()

    def remove_node_features(self):
        for graph in self.graphs:
            for node_id, node in enumerate(graph.nodes):
                graph.nodes[node_id] = node[0]
            graph.set_n_node_features()

    def get_graph_ids(self):
        """Get the list of active graph ids."""
        return [graph.id for graph in self.graphs if not graph.disabled]

    def maximal_subgraphs(self):
        """ Overwrites each graph with its maximal subgraph """
        print("Returning the maximal subgraph for each graph")
        for graph in tqdm(self.graphs):
            graph.maximal_subgraph()


class Graph:
    """Class to encode various graph structures."""

    def __init__(self, nodes, edges, label):
        """Set main graphs quantities."""
        self.nodes = nodes
        self.edges = edges
        self.label = label
        self.disabled = False
        self.id = -1

        self._check_length()
        self.set_n_node_features()

    def set_n_node_features(self):
        """Get the number of node features."""
        if len(np.shape(self.nodes)) == 1:
            self.n_node_features = 0
        elif len(np.shape(self.nodes)) == 2:
            self.n_node_features = len(self.nodes[0][1])
        else:
            raise Exception("Too many elements for node data")

    def _check_length(self):
        """Verify if the graph is large enough to be considered."""
        if len(self.nodes) <= MIN_NUM_NODES:
            self.disabled = True
        if len(self.edges) == 0:
            self.disabled = True

    def get_graph(self, encoding=None):
        """Get usable graph structure with given encoding."""
        if encoding is None:
            return self
        if encoding == "networkx":
            if not hasattr(self, "_graph_networkx"):
                self.set_networkx()
            return self._graph_networkx
        if encoding == "igraph":
            raise Exception("Igraph is not yet implemented")
        raise Exception("Graph encoding not understood")

    def set_networkx(self):
        """Set the networkx graph encoding."""
        self._graph_networkx = nx.Graph()
        if self.n_node_features == 0:
            nodes = [(node, {"feat": [0]}) for node in self.nodes]
        else:
            nodes = [(node, {"feat": feat}) for node, feat in self.nodes]
        self._graph_networkx.add_nodes_from(nodes)

        if len(self.edges[0]) == 2:
            edges = [(edge[0], edge[1], 1.0) for edge in self.edges]
        elif len(self.edges) == 3:
            edges = self.edges
        else:
            raise Exception("Too many elements for edge data")
        self._graph_networkx.add_weighted_edges_from(edges)

    def maximal_subgraph(self):
        """Overwrite the graph with its maximal subgraph."""
        row = [edge[0] for edge in self.edges]
        col = [edge[1] for edge in self.edges]

        # renumbering to zero required to create a scipy sparse matrix
        renum_val = np.min([row, col])
        row -= renum_val
        col -= renum_val

        adj = sc.sparse.coo_matrix((np.ones(len(row)), (row, col)))
        n_components, labels = sc.sparse.csgraph.connected_components(
            csgraph=adj, return_labels=True
        )

        # returning to original numbering
        idx_max_subgraph = np.where(labels == 0)[0] + renum_val

        self.edges = [
            edge
            for edge in self.edges
            if edge[0] in idx_max_subgraph and edge[1] in idx_max_subgraph
        ]

        if self.n_node_features == 0:
            self.nodes = [node for node in self.nodes if node in idx_max_subgraph]
        else:
            self.nodes = [node for node in self.nodes if node[0] in idx_max_subgraph]
