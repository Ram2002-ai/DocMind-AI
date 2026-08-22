"""Document repository"""
from sqlalchemy.orm import Session
from models.document import Document


class DocumentRepository:
    """Repository for document database operations"""
    
    @staticmethod
    def get_by_id_and_user(db: Session, document_id: int, user_id: int) -> Document:
        """Get document by ID and user"""
        return db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
    
    @staticmethod
    def get_user_documents(db: Session, user_id: int, skip: int = 0, limit: int = 20):
        """Get paginated user documents"""
        query = db.query(Document).filter(Document.user_id == user_id)
        total = query.count()
        documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
        return documents, total
