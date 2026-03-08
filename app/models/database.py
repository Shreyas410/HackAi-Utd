"""
SQLAlchemy database models for persistent storage.
Uses async SQLite for simplicity, can be swapped for PostgreSQL.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid

from ..config import settings

Base = declarative_base()


class Session(Base):
    """Learning session for a user."""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skill = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Learner profile data
    job_title = Column(String(255), nullable=True)
    experience_years = Column(Integer, nullable=True)
    prior_exposure = Column(String(50), nullable=True)
    learning_goals = Column(Text, nullable=True)
    preferred_modalities = Column(JSON, nullable=True)
    time_availability_hours = Column(Float, nullable=True)
    
    # Assessment results
    assigned_level = Column(String(20), nullable=True)
    level_confidence = Column(Float, nullable=True)
    classification_factors = Column(JSON, nullable=True)
    
    # Questionnaire data (stored as JSON)
    questionnaire_responses = Column(JSON, nullable=True)
    self_ratings = Column(JSON, nullable=True)
    
    # Relationships
    quizzes = relationship("Quiz", back_populates="session", cascade="all, delete-orphan")
    scenarios = relationship("ScenarioAttempt", back_populates="session", cascade="all, delete-orphan")
    
    # Data privacy
    data_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class Quiz(Base):
    """A diagnostic quiz attempt."""
    __tablename__ = "quizzes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    target_level = Column(String(20), nullable=False)
    questions = Column(JSON, nullable=False)
    answers = Column(JSON, nullable=True)
    
    score = Column(Float, nullable=True)
    points_earned = Column(Integer, nullable=True)
    total_points = Column(Integer, nullable=False)
    
    level_adjusted = Column(Boolean, default=False)
    new_level = Column(String(20), nullable=True)
    
    session = relationship("Session", back_populates="quizzes")


class ScenarioAttempt(Base):
    """A scenario-based practice attempt."""
    __tablename__ = "scenario_attempts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    scenario_id = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    current_node_id = Column(String(100), nullable=True)
    actions_taken = Column(JSON, default=list)
    score = Column(Integer, default=0)
    
    session = relationship("Session", back_populates="scenarios")


class Resource(Base):
    """Cached learning resource from external platforms."""
    __tablename__ = "resources"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    platform = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=True)
    
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    
    topic_coverage = Column(JSON, nullable=False)
    skills = Column(JSON, nullable=False)
    difficulty = Column(String(20), nullable=False)
    
    duration_hours = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    
    is_free = Column(Boolean, default=False)
    price = Column(String(50), nullable=True)
    affiliate_link = Column(String(1000), nullable=True)
    
    # YouTube specific
    snippet_start = Column(Integer, nullable=True)
    snippet_end = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database engine and session factory
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
