"""Conversation and Message database models"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base

# Association table for many-to-many relationship between Message and Document
message_document_association = Table(
    'message_document_association',
    Base.metadata,
    Column('message_id', Integer, ForeignKey('messages.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True)
)


class Conversation(Base):
    """Conversation model for chat sessions"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    
    class Config:
        from_attributes = True


class Message(Base):
    """Message model for chat messages"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    documents = relationship("Document", secondary=message_document_association)
    
    class Config:
        from_attributes = True
