"""Argo CD API integration – stub for Application/Project context."""

# Future: fetch Application status, sync state, project policies.
# Requires Argo CD server URL and auth.


def get_application_context(server: str, app_name: str) -> dict | None:
    """Stub: return None until Argo CD client is implemented."""
    return None
