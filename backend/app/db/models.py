from sqlalchemy import Column, String, Date, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.session import Base

class SentimentEnum(str, enum.Enum):
 POSITIVE = "positive"
 NEUTRAL = "neutral"
 NEGATIVE = "negative"

class Interaction(Base):
 __tablename__ = "interactions"

 id = Column(String, primary_key=True, index=True)
 hcp_name = Column(String, nullable=False, index=True)
 interaction_date = Column(Date, nullable=False)
 sentiment = Column(SQLEnum(SentimentEnum), default=SentimentEnum.NEUTRAL)
 interaction_time = Column(String, nullable=True)
 interaction_type = Column(String, nullable=True)
 attendees = Column(Text, nullable=True) # JSON array
 topics_discussed = Column(Text, nullable=True) # JSON array
 products_discussed = Column(Text)
 materials_shared = Column(Text)
 samples_distributed = Column(Text, nullable=True) # JSON array
 observed_sentiment = Column(String, nullable=True)
 notes = Column(Text)
 follow_up_date = Column(Date, nullable=True)
 follow_up_action = Column(Text, nullable=True)
 compliance_flag = Column(String, nullable=True)
 created_at = Column(DateTime, default=datetime.utcnow)
 updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

 follow_ups = relationship("FollowUp", back_populates="interaction")

class FollowUp(Base):
 __tablename__ = "followups"

 id = Column(String, primary_key=True, index=True)
 interaction_id = Column(String, ForeignKey("interactions.id"), nullable=False)
 due_date = Column(Date, nullable=False)
 action = Column(Text, nullable=False)
 status = Column(String, default="pending")
 created_at = Column(DateTime, default=datetime.utcnow)

 interaction = relationship("Interaction", back_populates="follow_ups")
