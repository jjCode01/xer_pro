from xer_pro.data.task import Task
from xer_pro.data.wbs import WbsLinkedList

ADMIN_VERBS = (
    "submit",
    "submittal",
    "shop drawing",
    "product data",
    "review",
    "approve",
    "approval",
    "procure",
    "procurement",
    "fabricate",
    "lead time",
    "deliver",
    "obtain",
    "buyout",
    "purchase",
    "coordination",
    "coordinate",
    "allowance",
    "closeout",
)

CONSTRUCTION_VERBS = (
    "install",
    "erect",
    "swing",
    "set",
    "pour",
    "place",
    "form",
    "layout",
    "excavate",
    "dig",
    "rough in",
    "rough-in",
)


def is_construction_task(task: Task) -> bool:
    """Determine if Task is construction work.

    Args:
        task (Task): Schedule activity

    Returns:
        bool: True if is Construction; False if Administrative or Procurement
    """
    wbs_path = WbsLinkedList(task.wbs)
    for node in wbs_path.iter_path():
        if any(verb in node.name.lower() for verb in ADMIN_VERBS):
            return False

    if task.name.lower().startswith(CONSTRUCTION_VERBS):
        return True

    if any(verb in task.name.lower() for verb in ADMIN_VERBS):
        return False

    return True
