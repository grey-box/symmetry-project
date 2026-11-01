# Base class for every failure a comparison strategy can raise.
class StrategyError(Exception):
    retryable = False

    def __init__(self, message: str, *, strategy: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.strategy = strategy

    def __str__(self) -> str:
        return f"[{self.strategy}] {self.message}"

    # Returns a per-strategy error entry the pipeline can embed in its result.
    def to_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "error": type(self).__name__,
            "message": self.message,
            "retryable": self.retryable,
        }


# Raised for missing or invalid strategy settings, such as a required engine.
class StrategyConfigError(StrategyError):
    pass


# Raised when the two texts handed to a strategy are unusable.
class StrategyInputError(StrategyError):
    pass


# Raised when a strategy fails while comparing.
class StrategyExecutionError(StrategyError):
    pass


# Raised when no strategy is registered under the requested name.
class UnknownStrategyError(StrategyConfigError):
    pass
