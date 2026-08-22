"""User repository"""
from sqlalchemy.orm import Session
from models.user import User


class UserRepository:
    """Repository for user database operations"""
    
    @staticmethod
    def get_by_email(db: Session, email: str) -> User:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()
