[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/aiohttp-deps?style=for-the-badge)](https://pypi.org/project/aiohttp-deps/)
[![PyPI](https://img.shields.io/pypi/v/aiohttp-deps?style=for-the-badge)](https://pypi.org/project/aiohttp-deps/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/aiohttp-deps?style=for-the-badge)](https://pypistats.org/packages/aiohttp-deps)

# AioHTTP deps


This project was initially created to show the abillities of [taskiq-dependencies](https://github.com/taskiq-python/taskiq-dependencies) project, which is used by [taskiq](https://github.com/taskiq-python/taskiq) to provide you with the best experience of sending distributed tasks.

This project adds [FastAPI](https://github.com/tiangolo/fastapi)-like dependency injection to your [AioHTTP](https://github.com/aio-libs/aiohttp) application.

To start using dependency injection, just initialize the injector.

```python
from aiohttp import web
from aiohttp_deps import init as deps_init


app = web.Application()


app.on_startup.append(deps_init)

web.run_app(app)

```


If you use mypy, then we have a custom router with propper types.


```python
from aiohttp import web
from aiohttp_deps import init as deps_init
from aiohttp_deps import Router

router = Router()


@router.get("/")
async def handler():
    return web.json_response({})


app = web.Application()

app.router.add_routes(router)

app.on_startup.append(deps_init)

web.run_app(app)

```

Also, you can nest routers with prefixes,

```python
api_router = Router()

memes_router = Router()

main_router = Router()

main_router.add_routes(api_router, prefix="/api")
main_router.add_routes(memes_router, prefix="/memes")
```


## Default dependencies

By default this library provides only two injectables. `web.Request` and `web.Application`.

```python

async def handler(app: web.Application = Depends()): ...

async def handler2(request: web.Request = Depends()): ...

```

It's super useful, because you can use these dependencies in
any other dependency. Here's a more complex example of how you can use this library.


```python
from aiohttp_deps import Router, Depends
from aiohttp import web

router = Router()


async def get_db_session(app: web.Application = Depends()):
    async with app["db"] as sess:
        yield sess


class MyDAO:
    def __init__(self, session=Depends(get_db_session)):
        self.session = session

    async def get_objects(self) -> list[object]:
        return await self.session.execute("SELECT 1")


@router.get("/")
async def handler(db_session: MyDAO = Depends()):
    objs = await db_session.get_objects()
    return web.json_response({"objects": objs})

```

If you do something like this, you would never think about initializing your DAO. You can just inject it and that's it.


# Built-in dependencies

This library also provides you with some default dependencies that can help you in building the best web-service.

## Json

To parse json, create a pydantic model and add a dependency to your handler.


```python
from aiohttp import web
from pydantic import BaseModel
from aiohttp_deps import Router, Json, Depends

router = Router()


class UserInfo(BaseModel):
    name: str


@router.post("/users")
async def new_data(user: UserInfo = Depends(Json())):
    return web.json_response({"user": user.dict()})

```

This dependency automatically validates data and send
errors if the data doesn't orrelate with schema or body is not a valid json.

If you want to make this data optional, just mark it as optional.

```python
@router.post("/users")
async def new_data(user: Optional[UserInfo] = Depends(Json())):
    if user is None:
        return web.json_response({"user": None})
    return web.json_response({"user": user.dict()})

```

## Headers

You can get and validate headers using `Header` dependency.

Let's try to build simple example for authorization.

```python
from aiohttp_deps import Router, Header, Depends
from aiohttp import web

router = Router()


def decode_token(authorization: str = Depends(Header())) -> str:
    if authorization == "secret":
        # Let's pretend that here we
        # decode our token.
        return authorization
    raise web.HTTPUnauthorized()


@router.get("/secret_data")
async def new_data(token: str = Depends(decode_token)) -> web.Response:
    return web.json_response({"secret": "not a secret"})

```

As you can see, header name to parse is equal to the
name of a parameter that introduces Header dependency.

If you want to use some name that is not allowed in python, or just want to have different names, you can use alias. Like this:

```python
def decode_token(auth: str = Depends(Header(alias="Authorization"))) -> str:
```

Headers can also be parsed to types. If you want a header to be parsed as int, just add the typehint.

```python
def decode_token(meme_id: int = Depends(Header())) -> str:
```

If you want to get list of values of one header, use parameter `multiple=True`.

```python
def decode_token(meme_id: list[int] = Depends(Header(multiple=True))) -> str:

```

And, of course, you can provide this dependency with default value if the value from user cannot be parsed for some reason.

```python
def decode_token(meme_id: str = Depends(Header(default="not-a-secret"))) -> str:
```


# Queries

You can depend on `Query` to get and parse query parameters.

```python
from aiohttp_deps import Router, Query, Depends
from aiohttp import web

router = Router()


@router.get("/shop")
async def shop(item_id: str = Depends(Query())) -> web.Response:
    return web.json_response({"id": item_id})

```

the name of the parameter is the same as the name of function parameter.

The Query dependency is acually the same as the Header dependency, so everything about the `Header` dependency also applies to `Query`.

## Views

If you use views as handlers, please use View class from `aiohttp_deps`, otherwise the magic won't work.

```python
from aiohttp_deps import Router, View, Depends
from aiohttp import web

router = Router()


@router.view("/view")
class MyView(View):
    async def get(self, app: web.Application = Depends()):
        return web.json_response({"app": str(app)})

```


## Forms

Now you can easiy get and validate form data from your request.
To make the magic happen, please add `arbitrary_types_allowed` to the config of your model.


```python
from pydantic import BaseModel
from aiohttp_deps import Router, Depends, Form
from aiohttp import web

router = Router()


class MyForm(BaseModel):
    id: int
    file: web.FileField

    class Config:
        arbitrary_types_allowed = True


@router.post("/")
async def handler(my_form: MyForm = Depends(Form())):
    with open("my_file", "wb") as f:
        f.write(my_form.file.file.read())
    return web.json_response({"id": my_form.id})

```
