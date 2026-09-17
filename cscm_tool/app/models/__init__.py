"""Import every model so its table is registered on db.metadata before
Alembic autogenerate or create_all() runs."""

from app.models.audit import AuditLogEntry  # noqa: F401
from app.models.change_request import ChangeRequest, DomainSignoff, ReviewComment  # noqa: F401
from app.models.export_job import ExportJob  # noqa: F401
from app.models.lookup import (  # noqa: F401
    LookupAccessRights,
    LookupAlarmBehaviour,
    LookupAvailabilityGroup,
    LookupBrakeProgram,
    LookupEngineeringDomain,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupOperationalState,
    LookupResetProgram,
    LookupStatusCategory,
    LookupTurbinePlatform,
    Role,
)
from app.models.release import Release, ReleaseItem  # noqa: F401
from app.models.status_code import (  # noqa: F401
    StatusCode,
    StatusCodeRevision,
    StatusCodeRevisionPlatform,
)
from app.models.user import User, UserEngineeringDomain  # noqa: F401
