"""Import every model so its table is registered on db.metadata before
Alembic autogenerate or create_all() runs."""

from app.models.audit import AuditLogEntry  # noqa: F401
from app.models.change_request import (  # noqa: F401
    ChangeRequest,
    DomainSignoff,
    DomainSignoffRequest,
    ReviewComment,
)
from app.models.export_job import ExportJob  # noqa: F401
from app.models.import_job import ImportJob  # noqa: F401
from app.models.lookup import (  # noqa: F401
    LookupAvailableGroup,
    LookupCustomerAccess,
    LookupDevelopmentAccess,
    LookupEngineeringDomain,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupGridOperatorAccess,
    LookupSalesAccess,
    LookupServiceAccess,
    LookupServicePartnerAccess,
    LookupTccAccess,
    LookupTopAccess,
    LookupTurbinePlatform,
    Role,
)
from app.models.release import Release, ReleaseItem  # noqa: F401
from app.models.status_code import (  # noqa: F401
    StatusCode,
    StatusCodeRevision,
    StatusCodeRevisionPlatform,
)
from app.models.user import User, UserEngineeringDomain, UserPasswordHistory  # noqa: F401
