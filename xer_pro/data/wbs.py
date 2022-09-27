from typing import Iterator


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
    """

    def __init__(self, **kwargs) -> None:
        self._attr = kwargs
        self.parent = None
        self.assignments = 0

    def __getitem__(self, name: str):
        return self._attr[name]

    def __eq__(self, __o: object) -> bool:
        self_path = WbsLinkedList(self)
        other_path = WbsLinkedList(__o)
        return self_path.short_name_path(False) == other_path.short_name_path(False)

    def __hash__(self) -> int:
        self_path = WbsLinkedList(self)
        return self_path.short_name_path(False)

    @property
    def name(self) -> str:
        return self._attr["wbs_name"]

    @property
    def short_name(self) -> str:
        return self._attr["wbs_short_name"]

    @property
    def is_project_node(self) -> bool:
        return self._attr["proj_node_flag"]


class WbsLinkedList:
    def __init__(self, tail: WbsNode = None) -> None:
        self.tail = tail

    def __eq__(self, __o: object) -> bool:
        return self.short_name_path() == __o.short_name_path()

    def __hash__(self) -> int:
        return hash(self.short_name_path())

    def iter_path(self, include_proj_node=False) -> Iterator[WbsNode]:
        node = self.tail
        if not include_proj_node and node.is_project_node:
            node = None

        while node is not None and not node.is_project_node:
            yield node
            node = node.parent

    def short_name_path(self, include_proj_node=False) -> str:
        short_path = ".".join(
            reversed([node.short_name for node in self.iter_path(include_proj_node)])
        )
        return short_path

    def long_name_path(self, include_proj_node=False) -> str:
        long_path = ".".join(
            reversed([node.name for node in self.iter_path(include_proj_node)])
        )
        return long_path
