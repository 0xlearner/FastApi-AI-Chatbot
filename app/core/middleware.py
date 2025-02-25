from fastapi import Request
from fastapi.responses import RedirectResponse

from app.core.security import get_current_user


async def auth_middleware(request: Request, call_next):
    # List of paths that require authentication
    protected_paths = ['/pdfs']

    # List of paths that should redirect to /pdfs if user is authenticated
    redirect_if_authenticated = ['/login', '/signup']

    try:
        # Try to get current user
        user = await get_current_user(request)

        # If user is authenticated and tries to access login/signup, redirect to /pdfs
        if request.url.path in redirect_if_authenticated and user:
            return RedirectResponse(url="/pdfs", status_code=302)

    except:
        # If user is not authenticated and tries to access protected paths, redirect to login
        if request.url.path in protected_paths:
            return RedirectResponse(
                url=f"/login?next={request.url.path}",
                status_code=302
            )

    response = await call_next(request)
    return response


async def websocket_cors(request: Request, call_next):
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)
    response = await call_next(request)
    return response


async def add_auth_header(request: Request, call_next):
    # Check for token in cookie
    token = request.cookies.get("access_token")

    # If token exists in cookie, add it to headers
    if token and "authorization" not in request.headers:
        request.headers.__dict__["_list"].append(
            (b"authorization", f"Bearer {token}".encode())
        )

    response = await call_next(request)
    return response
