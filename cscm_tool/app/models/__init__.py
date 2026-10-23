"""Import every model so its table is registered on db.metadata before
Alembic autogenerate or create_all() runs."""

from app.models.audit import AuditLogEntry  # noqa: F401
from app.models.change_request import (  # noqa: F401
    ChangeRequest,
    ChangeSet,
    CrAttachment,
    CrChecklistConfirmation,
    DomainSignoff,
    DomainSignoffRequest,
    FieldComment,
    ReviewChecklistItem,
    ReviewComment,
)
from app.models.export_job import ExportJob, ExportProfile  # noqa: F401
from app.models.import_job import ImportJob, ImportSourceItem  # noqa: F401
from app.models.lookup import (  # noqa: F401
    LookupAvailableGroup,
    LookupControllerSoftwareVersion,
    LookupCustomerAccess,
    LookupDevelopmentAccess,
    LookupEngineeringDomain,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupGridOperatorAccess,
    LookupLanguage,
    LookupSalesAccess,
    LookupServiceAccess,
    LookupServicePartnerAccess,
    LookupTccAccess,
    LookupTopAccess,
    LookupTurbinePlatform,
    Role,
)
from app.models.operations import (  # noqa: F401
    ApiToken,
    AppSetting,
    CodeOccurrence,
    Delegation,
    HubMcMapping,
    LoginAttempt,
    Notification,
    OccurrenceImport,
    RevisionTranslation,
    SavedSearch,
    Webhook,
    WebhookDelivery,
)
from app.models.release import Release, ReleaseItem, ReleaseTargetVersion  # noqa: F401
from app.models.status_code import (  # noqa: F401
    StatusCode,
    StatusCodeRevision,
    StatusCodeRevisionPlatform,
)
from app.models.terminology import TerminologyTerm, TerminologyTranslation  # noqa: F401
from app.models.translation import (  # noqa: F401
    LanguageReviewer,
    TranslationOverride,
    TranslationReview,
    TranslationReviewItem,
)
from app.models.user import User, UserEngineeringDomain, UserPasswordHistory  # noqa: F401
