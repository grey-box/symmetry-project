# Base class for failures that stop a whole comparison before it starts.
class PipelineError(Exception):
    code = "invalid_request"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code

    # Returns an entry the API layer can map to its published error model.
    def to_dict(self) -> dict[str, object]:
        return {
            "error": type(self).__name__,
            "message": self.message,
            "code": self.code,
            "scope": "request",
            "retryable": False,
        }


# Raised when the requested strategies are missing, duplicated or invalid.
class PipelineConfigError(PipelineError):
    pass
