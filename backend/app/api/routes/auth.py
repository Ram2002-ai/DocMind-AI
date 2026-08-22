"""Authentication routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from api.deps import get_current_user, get_db
from models.user import User
from core.security import hash_password, verify_password, create_access_token, decode_token
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password)
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Generate token
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        logger.info(f"New user registered: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login user"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == credentials.email).first()
        
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate token
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        logger.info(f"User logged in: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)
