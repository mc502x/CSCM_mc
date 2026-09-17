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


class SegregationOfDutiesViolation(DomainError):
    pass


class InvalidTransitionError(DomainError):
    pass


class NotFoundError(DomainError):
    pass
