""" authentication and authorization """
import logging
from typing import Dict, List

from fastapi import HTTPException, Request, status
from fastapi.security import SecurityScopes
from starlette.authentication import SimpleUser
from starlette.concurrency import run_in_threadpool

ADMIN_SCOPE = "*"

logger = logging.getLogger(__name__)


class PayloadAuth:
    """ Get auth information from the request payload """

    def __init__(
            self,
            user_cls: type = None,
            admin_scope: str = ADMIN_SCOPE,
            auto_error: bool = True
    ):
        super().__init__()
        self.user_cls = user_cls
        self.admin_scope = admin_scope
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        user = await self.get_user(request)
        if user is None and self.auto_error:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED)
        return user

    async def get_user(self, request: Request):
        try:
            payload = request.state.payload
        except AttributeError:
            raise RuntimeError(
                "Missing 'request.state.payload': "
                "try adding 'middleware.UpstreamPayloadMiddleware'"
            )

        username = payload.get("username")
        if not username:
            return

        if self.user_cls:
            try:
                session = request.state.session
            except AttributeError:
                raise RuntimeError(
                    "Missing 'request.state.session': "
                    "try adding 'middleware.SessionMiddleware'"
                )

            user = await run_in_threadpool(
                self.user_cls.get_by_username, session, username
            )
            if not user:
                logger.warning("User not found: %s", username)
                return
        else:
            user = SimpleUser(username=username)
        return user

    def get_scopes(self, payload: Dict[str, str]) -> List[str]:
        """ Return the list of scopes """
        if "scopes" in payload:
            scopes = payload["scopes"]
        elif "permissions" in payload:
            scopes = payload["permissions"]
        else:
            return []

        if isinstance(scopes, str):
            scopes = [token.strip() for token in scopes.split(",")]

        if self.admin_scope in scopes:
            scopes = [self.admin_scope]

        return scopes

    def is_admin(self, req_scopes: List[str]) -> bool:
        """Check if given scopes contain admin scope."""
        return self.admin_scope and self.admin_scope in req_scopes

    async def all_scopes(self, request: Request, scopes: SecurityScopes):
        user = await self(request)

        req_scopes = self.get_scopes(request.state.payload)
        if self.is_admin(req_scopes) or all(
                scope in req_scopes
                for scope in scopes.scopes
        ):
            return user

        raise HTTPException(status.HTTP_403_FORBIDDEN)

    async def any_scope(self, request: Request, scopes: SecurityScopes):
        user = await self(request)

        req_scopes = self.get_scopes(request.state.payload)
        if self.is_admin(req_scopes) or any(
                scope in req_scopes
                for scope in scopes.scopes
        ):
            return user

        raise HTTPException(status.HTTP_403_FORBIDDEN)

    async def admin(self, request: Request):
        user = await self(request)

        req_scopes = self.get_scopes(request.state.payload)
        if self.is_admin(req_scopes):
            return user

        raise HTTPException(status.HTTP_403_FORBIDDEN)
