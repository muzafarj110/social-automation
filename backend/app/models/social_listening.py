from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class ListeningTopic(Base):
    __tablename__ = "listening_topics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    keyword = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    platform = Column(String(50), default="linkedin")
    results = Column(Text, nullable=True)  # JSON
    scanned_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
