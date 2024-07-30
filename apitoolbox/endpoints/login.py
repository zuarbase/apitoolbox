""" Login functionality """
import copy
import inspect
import logging
import os
from datetime import datetime
from typing import Optional, Union

from starlette.concurrency import run_in_threadpool
from starlette.responses import Response, HTMLResponse, JSONResponse

from apitoolbox import models, tz, utils

logger = logging.getLogger(__name__)


class LoginEndpoint:
    """Class-based endpoint for login"""
    # pylint: disable=too-many-instance-attributes

    DEFAULT_TEMPLATE = os.path.join(
        os.path.dirname(__file__), "templates", "login.html"
    )

    def __init__(
        self,
        user_cls,
        secret,
        *,
        template: str = DEFAULT_TEMPLATE,
        error_status_code: int = 401,
        location: str = "/",
        token_expiry: int = 86400,  # 24 hours
        secure: bool = True,
        cookie_name: str = "jwt",
        jwt_algorithm: str = "HS256",
        form_action: str = "/login",
        require_confirmation: bool = False,
        register_url: str = None,
    ):
        # pylint: disable=too-many-arguments
        assert inspect.isclass(user_cls)
        self.secret = secret
        self.user_cls = user_cls
        self.template = template.strip()
        self.error_status_code = error_status_code
        self.location = location
        self.token_expiry = token_expiry
        self.secure = secure
        self.cookie_name = cookie_name
        self.jwt_algorithm = jwt_algorithm
        self.form_action = form_action
        self.require_confirmation = require_confirmation
        self.register_url = register_url

    def render(self, **kwargs) -> str:
        """Render the template using the passed parameters"""
        kwargs.setdefault("username", "")
        kwargs.setdefault("error", "")
        kwargs.setdefault("form_action", self.form_action)
        kwargs.setdefault("modal_title", "Login")
        kwargs.setdefault("title", "APIToolbox")

        kwargs.setdefault("register_url", self.register_url)
        if self.register_url:
            register_link = f'<a href="{self.register_url}">Register</a>'
            kwargs.setdefault("register_link", register_link)
        else:
            kwargs.setdefault("register_link", "")

        return utils.render(self.template, **kwargs)

    async def jwt_encode(self, payload):
        """Build the JWT"""
        assert "exp" in payload
        return utils.jwt_encode(
            payload,
            self.secret,
            algorithm=self.jwt_algorithm,
        )

    @staticmethod
    async def payload(user_data):
        """Determine the JWT contents (keep for sub-classes"""
        user_data.pop("password", None)
        return user_data

    async def authenticate(
        self,
        session: models.Session,
        username: str,
        password: str,
        **kwargs,  # pylint: disable=unused-argument
    ) -> Optional[dict]:
        """Perform authentication against database"""

        def _get_by_username():
            return self.user_cls.get_by_username(session, username)

        user = await run_in_threadpool(_get_by_username)
        if not user:
            logger.info("Invalid user '%s'", username)
            return None

        if not user.verify(password):
            logger.info("Invalid password for user '%s'", user.username)
            return None

        logger.info("Authenticated user '%s'", user.username)
        return user.as_dict()

    async def on_get(self) -> HTMLResponse:
        """Handle GET requests"""
        html = await run_in_threadpool(self.render)
        return HTMLResponse(content=html, status_code=200)

    async def on_post(
        self,
        session: models.Session,
        username: str,
        password: str,
        location: str = None,
        **kwargs,
    ) -> Union[HTMLResponse, JSONResponse]:
        """Handle POST requests"""
        user_data = await self.authenticate(
            session, username=username, password=password, **kwargs
        )
        if not user_data:
            # ref: OWASP
            error = "Login failed; Invalid userID or password"
            html = await run_in_threadpool(
                self.render, username=username, error=error
            )
            return HTMLResponse(
                content=html, status_code=self.error_status_code
            )

        result = await self.payload(user_data)
        result = await self.add_exp_to_payload(result)
        result = await self.add_jwt_token_to_payload(result)
        response = JSONResponse(
            content=result, status_code=303,
            headers={"location": location or self.location}
        )
        await self.set_jwt_cookie(payload=result, response=response)

        return response

    async def add_exp_to_payload(self, payload):
        """Add expiry to the payload"""
        result = copy.deepcopy(payload)
        expiry = tz.utcnow() + tz.timedelta(seconds=self.token_expiry)
        result["exp"] = expiry.isoformat()
        return result

    async def add_jwt_token_to_payload(self, payload):
        """Add token to the payload"""
        result = copy.deepcopy(payload)
        expiry = self._get_expiry_dt_from_payload(result)
        assert expiry
        token = await self.jwt_encode({
            **result,
            # jwt_encode will convert this to an epoch inside the token
            "exp": expiry,
        })
        result["token"] = token
        return result

    async def set_jwt_cookie(self, payload: dict, response: Response) -> dict:
        result = copy.deepcopy(payload)
        assert not result.get("password")
        assert result["exp"]
        assert result["token"]

        expiry = self._get_expiry_dt_from_payload(result)
        response.set_cookie(
            self.cookie_name,
            result["token"],
            path="/",
            expires=int(expiry.timestamp()),
            secure=self.secure,
        )
        return result

    def _get_expiry_dt_from_payload(self, payload) -> datetime | None:
        try:
            return datetime.fromisoformat(payload["exp"])
        except KeyError:
            return None
