class Wbs:
    def __init__(self, **kwargs) -> None:
        self._data = kwargs

    def __getitem__(self, name: str):
        return self._data[name]

    @property
    def is_project_node(self) -> bool:
        return self._data['proj_node_flag']