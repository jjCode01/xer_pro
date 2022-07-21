
class WbsNode:
    """A class to represent a schedule WBS node.

    ...

    Attributes
    ----------
    name: str
        Long name for WBS node
    short_name: str
        Short name for WBS node
    is_project_node: bool
        Flags if node is Project Node

    ...

    Methods
    ----------
    path: list
        Returns list of WBS node and all parent nodes
    """
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs
        self.parent = None

    def __getitem__(self, name: str):
        return self._attr[name]

    def __eq__(self, __o: object) -> bool:
        self_path = ".".join([node.short_name for node in self.path(False)])
        other_path = ".".join([node.short_name for node in __o.path(False)])
        return (
            self.name == __o.name and
            self.short_name == __o.short_name and
            self_path == other_path)

    def __hash__(self) -> int:
        self_path = ".".join([node.short_name for node in self.path(False)])
        return (self.name, self.short_name, self_path)

    @property
    def name(self) -> str:
        return self._attr['wbs_name']

    @property
    def short_name(self) -> str:
        return self._attr['wbs_short_name']

    @property
    def is_project_node(self) -> bool:
        return self._attr['proj_node_flag']

    def path(self, include_proj_node: bool = True) -> list:
        if self.is_project_node:
            return self._attr['short_name']

        if not self.parent:
            return []

        wbs_node = self
        path = []
        while wbs_node:
            if wbs_node.is_project_node == include_proj_node:
                path.append(wbs_node)
            wbs_node = wbs_node.parent

        return reversed(path)
