"""v1 router aggregator."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

from . import auth
from .deps.principal import get_principal
from .resources import RESOURCE_MODULES


class FloorRoute(APIRoute):
    """Verify the bearer token before the request body is read.

    FastAPI parses the body before it solves dependencies, so a router-level
    dependency would answer 400 to an anonymous caller sending bad JSON. Wrapping
    the handler is what makes the 401 come first.
    """

    def get_route_handler(
        self,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        inner = super().get_route_handler()

        async def handler(request: Request) -> Response:
            get_principal(request)
            return await inner(request)

        return handler


def build_v1_router() -> APIRouter:
    v1 = APIRouter(prefix="/v1")
    for mod in RESOURCE_MODULES:
        router = mod.build_router()
        for route in router.routes:
            # include_router rebuilds each route from type(route), which is how
            # the class reaches the app; a parent route_class is ignored.
            route.__class__ = FloorRoute
        v1.include_router(router)
    # ``auth`` is a feature module (custom-method endpoints), not an entity
    # resource — it stays out of RESOURCE_MODULES and isn't @inject-wired.
    # It also stays outside the floor: callers sign in here.
    v1.include_router(auth.build_router())
    return v1
