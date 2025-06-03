class DueDateInPastError(Exception):
    """
    Custom exception raised when a task's due date is set to a past date.
    """

    def __init__(self, message="Due date cannot be in the past."):
        self.message = message
        super().__init__(self.message)


class ScheduledDateInPastError(Exception):
    """
    Custom exception raised when a task's scheduled date is set to a past date.
    """

    def __init__(self, message="scheduled date cannot be in the past."):
        self.message = message
        super().__init__(self.message)
