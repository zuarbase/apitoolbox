import jwt
from fastapi import Depends
from starlette.requests import Request

from apitoolbox import middleware, utils


def test_middleware_upstream(session, app, client):
    @app.get("/payload")
    async def _get(request: Request):
        return request.state.payload

    app.add_middleware(middleware.UpstreamPayloadMiddleware)

    headers = {"X-Payload-username": "testuser"}

    res = client.get("/payload", headers=headers)
    assert res.status_code == 200
    assert res.json() == {"username": "testuser"}


def test_middleware_jwt(session, app, client):
    @app.get("/payload")
    async def _get(request: Request):
        return request.state.payload

    secret = "s0secret"
    app.add_middleware(middleware.JwtMiddleware, secret=secret)

    payload = {"username": "testuser"}
    token = jwt.encode(payload, secret)

    res = client.get("/payload", cookies={"jwt": token})
    assert res.status_code == 200
    assert res.json() == payload


def test_middleware_jwt_bad_or_no_token(session, app, client):
    @app.get("/jwt")
    async def _get(request: Request):
        return {"empty_payload": request.state.payload}

    secret = "s0secret"
    app.add_middleware(middleware.JwtMiddleware, secret=secret)

    # Test bad token
    res = client.get("/jwt", cookies={"jwt": "bad-jwt-token"})
    assert res.status_code == 200
    assert res.json() == {"empty_payload": {}}

    # Test without token
    res = client.get("/jwt")
    assert res.status_code == 200
    assert res.json() == {"empty_payload": {}}


def test_middleware_session(engine, app, client):
    app.add_middleware(middleware.SessionMiddleware, bind=engine)

    @app.get("/session")
    def _get(request: Request, session=Depends(utils.get_session)):
        assert request.state.session is session

        result = session.execute("SELECT 1").scalar()
        return str(result)

    response = client.get("/session")
    assert response.status_code == 200
    assert response.json() == "1"
