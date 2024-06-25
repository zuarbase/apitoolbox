""" authentication and authorization """
import logging
from typing import Container, Dict, List, Optional, Sequence, Tuple

from fastapi import Request, status
from starlette.authentication import (
    AuthCredentials, AuthenticationBackend, SimpleUser,
)
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection

ADMIN_SCOPE = "*"

logger = logging.getLogger(__name__)


class PayloadAuthBackend(AuthenticationBackend):
    """Get auth information from the request payload"""

    def __init__(
        self,
        user_cls: type = None,
        admin_scope: str = ADMIN_SCOPE,
    ):
        super().__init__()
        self.user_cls = user_cls
        self.admin_scope = admin_scope

    async def scopes(self, payload: Dict[str, str]) -> List[str]:
        """Return the list of scopes"""
        if "scopes" in payload:
            scopes = payload["scopes"]
        elif "permissions" in payload:
            scopes = payload["permissions"]
        else:
            return []

        if isinstance(scopes, str):
            scopes = [token.strip() for token in scopes.split(",")]

        if self.admin_scope and self.admin_scope in scopes:
            return [self.admin_scope]

        return scopes

    async def authenticate(
        self, conn: HTTPConnection
    ) -> Optional[Tuple["AuthCredentials", "BaseUser"]]:
        try:
            payload = conn.state.payload
            zuar_service_name = conn.state.zuar_service_name
        except AttributeError as exc:
            raise RuntimeError(
                "Missing 'request.state.payload': "
                "try adding 'middleware.UpstreamPayloadMiddleware'"
            ) from exc

        if zuar_service_name:
            user = SimpleUser(username=f"zuar_service_{zuar_service_name}")
            return AuthCredentials([ADMIN_SCOPE]), user

        username = payload.get("username")
        if not username:
            return

        if self.user_cls:
            try:
                session = conn.state.session
            except AttributeError as exc:
                raise RuntimeError(
                    "Missing 'request.state.session': "
                    "try adding 'middleware.SessionMiddleware'"
                ) from exc

            user = await run_in_threadpool(
                self.user_cls.get_by_username, session, username
            )
            if not user:
                logger.warning("User not found: %s", username)
                return
        else:
            user = SimpleUser(username=username)

        scopes = await self.scopes(payload)
        return AuthCredentials(scopes), user


def validate_authenticated(request: Request):
    """Validate that 'request.user' is authenticated.

    Usage:
        >>> from fastapi import Depends
        >>> @app.get("/my_name", dependencies=[
        ...    Depends(validate_authenticated)
        ... ])
    """
    user: SimpleUser = getattr(request, "user", None)
    if user is not None and not user.is_authenticated:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)


class ScopeValidator:
    """Base class for scope validators."""

    def __init__(self, scopes: Sequence[str], admin_scope: str = ADMIN_SCOPE):
        self.scopes = scopes
        self.admin_scope = admin_scope

    def __call__(self, request: Request):
        validate_authenticated(request)

    def is_admin(self, req_scopes: Container[str]) -> bool:
        """Check if given scopes contains admin scope."""
        return self.admin_scope and self.admin_scope in req_scopes


class AllScopesValidator(ScopeValidator):
    """Validate that all defined scopes exist in 'request.auth.scopes'.

    Usage:
        >>> from fastapi import Depends
        >>> @app.get("/my_name", dependencies=[
        ...    Depends(AllScopesValidator(
        ...        scopes=["read", "write"],
        ...        admin_scope="admin"
        ...    ))
        ... ])
    """

    def __call__(self, request: Request):
        super().__call__(request)

        req_scopes = request.auth.scopes

        if self.is_admin(req_scopes):
            return

        if not all(scope in req_scopes for scope in self.scopes):
            raise HTTPException(status.HTTP_403_FORBIDDEN)


class AnyScopeValidator(ScopeValidator):
    """
    Validate that at least one defined scope exists in 'request.auth.scopes'.

    Usage:
        >>> from fastapi import Depends
        >>> @app.get("/my_name", dependencies=[
        ...    Depends(AnyScopeValidator(
        ...        scopes=["read", "write"],
        ...        admin_scope="admin"
        ...    ))
        ... ])
    """

    def __call__(self, request: Request):
        super().__call__(request)

        req_scopes = request.auth.scopes

        if self.is_admin(req_scopes):
            return

        if not any(scope in req_scopes for scope in self.scopes):
            raise HTTPException(status.HTTP_403_FORBIDDEN)


class AdminValidator(ScopeValidator):
    """Validate that admin scope exists in 'request.auth.scopes'.

    Usage:
        >>> from fastapi import Depends
        >>> @app.get("/my_name", dependencies=[
        ...    Depends(AdminValidator(
        ...        admin_scope="admin"
        ...    ))
        ... ])
    """

    def __init__(self, admin_scope: str = ADMIN_SCOPE):
        super().__init__(scopes=[], admin_scope=admin_scope)

    def __call__(self, request: Request):
        super().__call__(request)

        if request.state.zuar_service_name:
            return

        req_scopes = request.auth.scopes

        if not self.is_admin(req_scopes):
            raise HTTPException(status.HTTP_403_FORBIDDEN)
