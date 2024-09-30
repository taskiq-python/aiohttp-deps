import base64

from aiohttp import web
from pydantic import BaseModel

from aiohttp_deps import Depends, ExtraOpenAPI, Header, Router, init, setup_swagger


class UserInfo(BaseModel):
    """Abstract user model."""

    id: int
    name: str
    password: str


router = Router()

# Here we create a simple user storage.
# In real-world applications, you would use a database.
users = {
    "john": UserInfo(id=1, name="John Doe", password="123"),  # noqa: S106
    "caren": UserInfo(id=2, name="Caren Doe", password="321"),  # noqa: S106
}


def get_current_user(
    # Current auth header.
    authorization: str = Depends(Header()),
    # We don't need a name to this variable,
    # because it will only affect the API schema,
    # but won't be used in runtime.
    _: None = Depends(
        ExtraOpenAPI(
            extra_openapi={
                "security": [{"basicAuth": []}],
            },
        ),
    ),
) -> UserInfo:
    """This function checks if the user authorized."""
    # Here we check if the authorization header is present.
    if not authorization.startswith("Basic"):
        raise web.HTTPUnauthorized(reason="Unsupported authorization type")
    # We decode credentials from the header.
    # And check if the user exists.
    creds = base64.b64decode(authorization.split(" ")[1]).decode()
    username, password = creds.split(":")
    found_user = users.get(username)
    if found_user is None:
        raise web.HTTPUnauthorized(reason="User not found")
    if found_user.password != password:
        raise web.HTTPUnauthorized(reason="Invalid password")
    return found_user


@router.get("/")
async def index(current_user: UserInfo = Depends(get_current_user)) -> web.Response:
    """Index handler returns current user."""
    return web.json_response(current_user.model_dump(mode="json"))


app = web.Application()
app.router.add_routes(router)
app.on_startup.extend(
    [
        init,
        setup_swagger(
            # Here we add security schemes used
            # to authorize users.
            extra_openapi={
                "components": {
                    "securitySchemes": {
                        # We only support basic auth.
                        "basicAuth": {
                            "type": "http",
                            "scheme": "basic",
                        },
                    },
                },
            },
        ),
    ],
)

if __name__ == "__main__":
    web.run_app(app)
