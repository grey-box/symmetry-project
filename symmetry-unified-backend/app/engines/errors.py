# Base class for every failure an engine adapter can raise.
class AdapterError(Exception):
    retryable = False

    def __init__(self, message, *, provider="", model=""):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model

    def __str__(self):
        return f"[{self.provider}/{self.model}] {self.message}"

    # Returns a per-engine error entry the pipeline can embed in its result.
    def to_dict(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "error": type(self).__name__,
            "message": self.message,
            "retryable": self.retryable,
        }


# Raised for a missing API key, unknown model or bad settings.
class AdapterConfigError(AdapterError):
    pass


# Raised when the provider rejects the request.
class AdapterRequestError(AdapterError):
    pass


# Raised when the provider does not answer in time.
class AdapterTimeoutError(AdapterError):
    retryable = True


# Raised when the provider replies with something unusable or empty.
class AdapterResponseError(AdapterError):
    retryable = True


# Raised when no adapter is registered under the requested provider name.
class UnknownAdapterError(AdapterConfigError):
    pass
