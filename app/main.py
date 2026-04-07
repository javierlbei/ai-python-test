"""Application bootstrap and dependency wiring for the API service."""

from contextlib import asynccontextmanager

from dependency_injector.wiring import inject, Provide
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_timeout import TimeoutMiddleware

from dependencies import Container
from user_requests import router as requests_router
from utils import get_logger

_logger = get_logger()

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Manages application startup and shutdown lifecycle.

    On startup, starts background request processors and attaches shared
    services to application state. On shutdown, stops processors and
    closes external provider clients.

    Args:
        fastapi_app (FastAPI): The FastAPI application instance.

    Yields:
        None: Control is yielded to the application between startup and
            shutdown.
    """

    # Startup
    _logger.info('Starting application services')

    await requests_router.startup()

    yield

    # Shutdown
    await requests_router.shutdown()


def build_app() -> FastAPI:
    container = Container()

    app = FastAPI(
        title='Notification Service (Technical Test)',
        lifespan=lifespan,
        debug=False,
    )

    app.container = container
    app.include_router(requests_router.router)

    # Add timeout middleware to enforce a maximum processing time per request
    app.add_middleware(TimeoutMiddleware, timeout_seconds=5.0)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=False,
        allow_methods=['GET', 'POST'],
        allow_headers=['Content-Type', 'X-API-Key'],
    )

    @app.middleware('http')
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = (
            'strict-origin-when-cross-origin'
        )
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        return response

    @app.middleware('http')
    async def limit_body_size(request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length:
            try:
                if int(content_length) > 4096:
                    return JSONResponse(
                        status_code=413,
                        content={
                            'detail': 'Request body too large',
                        },
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={
                        'detail': 'Invalid Content-Length header',
                    },
                )

        body = await request.body()
        if len(body) > 4096:
            return JSONResponse(
                status_code=413,
                content={
                    'detail': 'Request body too large',
                },
            )
        return await call_next(request)

    # Exception handlers
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        _logger.error('Unhandled exception: %s', exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                'detail': 'An unexpected error occurred. '
                          'Please try again later.'
            },
        )

    return app

app = build_app()
