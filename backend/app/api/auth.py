import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import Token, TokenData, UserCreate, UserLogin, UserResponse

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Password hashing using bcrypt directly (passlib has bcrypt compat issues with Python 3.13)
import hashlib as _hashlib
import bcrypt as _bcrypt


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = _bcrypt.gensalt()
    hashed = _bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash. Also supports sha256$ fallback."""
    if hashed_password.startswith("sha256$"):
        salt = "kon_salt_secure"
        expected = "sha256$" + _hashlib.sha256((salt + plain_password).encode()).hexdigest()
        return hashed_password == expected
    try:
        return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    session_id: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": username,
        "user_id": user_id,
        "username": username,
        "role": role,
        "session_id": session_id,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates bearer token and returns authenticated customer user.
    Enforces fail-secure authentication:
    - Missing token -> 401 Unauthorized
    - Invalid or expired token -> 401 Unauthorized
    - Deactivated or missing account -> 401 Unauthorized
    Demo bypass is disabled by default and requires explicit ALLOW_DEMO_AUTH_BYPASS setting.
    """
    if not credentials:
        if settings.ALLOW_DEMO_AUTH_BYPASS:
            stmt = select(User).where(User.username == "demo_customer")
            result = await db.execute(stmt)
            demo_user = result.scalar_one_or_none()
            if demo_user:
                setattr(demo_user, "current_session_id", "demo-session-default")
                return demo_user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: Optional[str] = payload.get("username")
        user_id: Optional[str] = payload.get("user_id")
        if not username or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: Missing subject identifiers",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach token session_id to user object dynamically for downstream handlers
    setattr(user, "current_session_id", payload.get("session_id"))
    return user


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates bearer token and verifies caller holds active admin role.
    Supports Authorization header as well as query parameter 'token' for SSE streams.
    Enforces fail-secure role-based access control:
    - Missing token -> 401 Unauthorized
    - Invalid or expired token -> 401 Unauthorized
    - Authenticated non-admin -> 403 Forbidden
    Demo bypass allows seamless local presentation when enabled.
    """
    token = credentials.credentials if credentials else request.query_params.get("token")
    if not token:
        if settings.ALLOW_DEMO_AUTH_BYPASS:
            stmt = select(User).where(User.username == "admin")
            result = await db.execute(stmt)
            admin_user = result.scalar_one_or_none()
            if admin_user:
                setattr(admin_user, "current_session_id", "admin-session-default")
                return admin_user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing admin access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: Missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        uid = uuid.UUID(user_id)
    except (JWTError, ValueError, TypeError):
        if settings.ALLOW_DEMO_AUTH_BYPASS:
            stmt = select(User).where(User.username == "admin")
            result = await db.execute(stmt)
            admin_user = result.scalar_one_or_none()
            if admin_user:
                setattr(admin_user, "current_session_id", "admin-session-default")
                return admin_user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.role != "admin":
        if settings.ALLOW_DEMO_AUTH_BYPASS:
            stmt = select(User).where(User.username == "admin")
            result = await db.execute(stmt)
            admin_user = result.scalar_one_or_none()
            if admin_user:
                setattr(admin_user, "current_session_id", "admin-session-default")
                return admin_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action",
        )

    setattr(user, "current_session_id", payload.get("session_id"))
    return user


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check for existing user
    stmt = select(User).where(
        or_(User.username == user_data.username, User.email == user_data.email)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered",
        )

    session_id = str(uuid.uuid4())
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role="customer",
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token(
        user_id=str(new_user.id),
        username=new_user.username,
        role=new_user.role,
        session_id=session_id,
    )

    return Token(
        access_token=token,
        token_type="bearer",
        role=new_user.role,
        username=new_user.username,
        user_id=str(new_user.id),
        session_id=session_id,
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == credentials.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_id = str(uuid.uuid4())
    token = create_access_token(
        user_id=str(user.id),
        username=user.username,
        role=user.role,
        session_id=session_id,
    )

    return Token(
        access_token=token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        user_id=str(user.id),
        session_id=session_id,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
