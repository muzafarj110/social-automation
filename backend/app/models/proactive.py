from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class ProactiveItem(Base):
    __tablename__ = "proactive_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent = Column(String(50), nullable=False)  # content | competitor | listening | seo | leadgen
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    action_tab = Column(String(50), nullable=True)   # which tab to navigate to
    status = Column(String(20), default="new")       # new | dismissed
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
