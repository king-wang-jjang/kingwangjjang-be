import strawberry


@strawberry.type
class TaskStatusType:
    """ """

    status: str
    result: str = None


@strawberry.type
class AddTaskTypes:
    """ """

    task_id: str
    status: str
