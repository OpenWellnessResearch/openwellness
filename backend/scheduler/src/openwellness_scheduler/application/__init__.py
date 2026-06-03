"""Application ring — use cases (interactors) for the scheduler service.

Modules here hold enterprise/application business rules only. They depend
*inward* on domain entities and repository ports (defined in
``openwellness_core``) and know nothing about Celery, the DI container, or
any database backend.
"""
