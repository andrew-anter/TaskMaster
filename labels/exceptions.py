class DuplicateLabelError(Exception):
    """
    Raised when a user already owns a label with the requested name.
    """

    def __init__(self, message="You already have a label with this name."):
        self.message = message
        super().__init__(self.message)
