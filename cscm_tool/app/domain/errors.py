"""Domain-level exceptions raised by the service layer. Route handlers
translate these into HTTP responses; repositories never raise them."""


class DomainError(Exception):
    """Base class for all service-layer domain errors."""


class InvalidCredentialsError(DomainError):
    pass


class AccountLockedError(DomainError):
    pass


class RateLimitedError(DomainError):
    pass


class PasswordPolicyError(DomainError):
    def __init__(self, violations: list[str]):
        super().__init__("; ".join(violations))
        self.violations = violations


class LastAdministratorError(DomainError):
    pass


class ForbiddenError(DomainError):
    """The actor's role does not permit the operation (SEC-010)."""


class SegregationOfDutiesViolation(DomainError):
    pass


class InvalidTransitionError(DomainError):
    pass


class NotFoundError(DomainError):
    pass


class ConcurrentModificationError(DomainError):
    """I-01: the Draft was changed by someone else since the form was loaded."""

    def __init__(self, message: str, current_row_version: int, current_updated_at: str | None):
        super().__init__(message)
        self.current_row_version = current_row_version
        self.current_updated_at = current_updated_at


class StepUpRequiredError(DomainError):
    """I-17: a sensitive action needs the actor's password again (missing or wrong)."""

    def __init__(self, message: str, *, wrong_password: bool = False):
        super().__init__(message)
        self.wrong_password = wrong_password
