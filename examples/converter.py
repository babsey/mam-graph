import networkx as nx
from supermam.network import Network

lobes = ["cingulate", "frontal", "insula", "occipital" "parietal", "temporal"]

def mam_to_graph(network: Network, levels: str = ['lobe', 'area', 'layer']) -> dict:

    areas = network.neuron_numbers.index.levels[0].tolist()
    syn_int = network.synapses_internal.root

    nodes, links = [],[]

    nodes.append({"id": "brain"})

    for lobe in lobes:
        nodes.append({"id": lobe, "parent": "brain"})
        
    if "layer" in levels:
        for area in areas:
            nodes.append({"id": f"{area}", "parent": f"{lobes[area]}"})

        layers = network.neuron_numbers.index.levels[1].tolist()
        for area in areas:
            for layer in layers:
                nodes.append({"id": f"{area}.{layer}", "parent": f"{area}"})

        syn_int_area_layer = syn_int.groupby(['area', 'layer']).sum().T.groupby(['layer', 'area']).sum().unstack().unstack()
        syn_int_area_layer = syn_int_area_layer[syn_int_area_layer!=0]

        for src_area, src_layer, tgt_area, tgt_layer in syn_int_area_layer.index.tolist():
            links.append({"source": f"{src_area}.{src_layer}", "target": f"{tgt_area}.{tgt_layer}"})
    else:
        for area in areas:
            nodes.append({"id": f"{area}"})

        syn_int_area = syn_int.groupby('area').sum().T.groupby('area').sum().unstack()
        syn_int_area = syn_int_area[syn_int_area!=0]

        for src, tgt in syn_int_area.index.tolist():
            links.append({"source": f"{src}", "target": f"{tgt}"})

    return {"nodes": nodes, "links": links}


def mam_to_digraph(network: Network) -> nx.DiGraph:
    graph = mam_to_graph(network)

    M = nx.DiGraph()
    for node in graph['nodes']:
        area, layer = node['id'].split('.')
        M.add_node(
            f"{node['id']}",
            area=area,
            layer=layer,
            label=f"{area} {layer}",
        )

    for link in graph['links']:
        M.add_edge(link['source'], link['target'])

    return M