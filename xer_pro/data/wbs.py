class Wbs:
    def __init__(self, **kwargs) -> None:
        self._attr = kwargs

    def __getitem__(self, name: str):
        return self._attr[name]

    @property
    def is_project_node(self) -> bool:
        return self._attr['proj_node_flag']
