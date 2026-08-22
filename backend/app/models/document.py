"""Document database model"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base


class Document(Base):
    """Document model for file uploads and metadata"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)  # Display name
    original_filename = Column(String, nullable=False)  # Original uploaded name
    file_type = Column(String, nullable=False)  # pdf, png, jpg, jpeg
    file_size = Column(Integer, nullable=False)  # Bytes
    file_path = Column(String, nullable=False)  # Local storage path
    
    # Processing
    status = Column(String, default="UPLOADED", nullable=False)  # UPLOADED, PROCESSING, COMPLETED, FAILED
    extracted_text = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    summary = relationship("Summary", back_populates="document", uselist=False, cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True
