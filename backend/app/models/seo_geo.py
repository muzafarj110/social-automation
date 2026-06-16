from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class SeoProject(Base):
    __tablename__ = "seo_projects"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    website = Column(String(255), nullable=True)
    target_keywords = Column(Text, nullable=True)
    audience = Column(Text, nullable=True)
    results = Column(Text, nullable=True)  # JSON
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
