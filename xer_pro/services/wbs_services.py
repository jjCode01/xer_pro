from data.wbs import WbsNode


def get_all_wbs_levels(wbs_id: str, wbs_nodes: dict[str, WbsNode]) -> list[WbsNode]:
    """Return hierarchy of wbs nodes in a list

    Args:
        wbs_id (str): wbs id
        wbs_nodes (dict[str, Wbs]): schedule wbs nodes

    Returns:
        list[Wbs]: hierarch of wbs nodes
    """
    if wbs_id is None:
        raise ValueError('Value Error: wbs_id cannot be None type')
    elif wbs_id == '':
        raise ValueError('Value Error: wbs_id cannot be empty string')

    if wbs_nodes.get(wbs_id) is None:
        raise ValueError(f'Value Error: {wbs_id} not found')

    nodes = []
    node = wbs_nodes.get(wbs_id)
    if node is None or node.is_project_node:
        return nodes

    while not node.is_project_node:
        nodes.append(node)
        node = wbs_nodes.get(node._attr['parent_wbs_id'])
        if node is None:
            break

    return reversed(nodes)
