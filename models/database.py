from sqlalchemy import create_engine, Column, Integer, Float, String, Text, ARRAY, ForeignKey, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import IntegrityError
import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Fetch environment variables
def get_env_variable(key):
    """
    Fetch environment variable from Streamlit secrets or .env file.
    """
    try:
        # Try Streamlit secrets first (for cloud deployment)
        if key in st.secrets:
            return st.secrets[key]
    except FileNotFoundError:
        # Fall back to .env file (for local development)
        pass
    return os.getenv(key)

# Example usage
DATABASE_URL = get_env_variable("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL not found. Please check your configuration.")
    st.stop()

# Create database engine with proper connection pooling and SSL handling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # Increased from 5
    max_overflow=10,  # Increased from 2
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    poolclass=QueuePool,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 30
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationships
    favorites = relationship("UserFavorite", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String, unique=True, index=True)
    website = Column(String)
    description = Column(Text)
    category = Column(String, index=True)
    certifications = Column(ARRAY(String))
    sustainability_score = Column(Float)
    eco_materials_score = Column(Float)
    carbon_footprint = Column(Float)
    water_usage = Column(Float)
    worker_welfare = Column(Float)
    year = Column(Integer)
    latitude = Column(Float)
    longitude = Column(Float)
    city = Column(String, index=True)
    state = Column(String(2), index=True)
    zip_code = Column(String)

    # Relationships
    favorited_by = relationship("UserFavorite", back_populates="business")

class UserFavorite(Base):
    __tablename__ = "user_favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    business_id = Column(Integer, ForeignKey("businesses.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="favorites")
    business = relationship("Business", back_populates="favorited_by")

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(Text)
    icon = Column(String)  # SVG icon string
    criteria = Column(Text)  # JSON string of criteria
    points = Column(Integer)
    category = Column(String)  # e.g., 'exploration', 'sustainability', 'community'
    level = Column(Integer)  # Badge level (1, 2, 3, etc.)

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    earned_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")

class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    interaction_type = Column(String)  # view_business, search_location, filter_category
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)
    category = Column(String, nullable=True)
    state = Column(String(2), nullable=True)
    sustainability_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    business = relationship("Business")

def get_db():
    """Get database session with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise Exception(f"Database session error: {str(e)}")
    finally:
        db.close()

def init_db():
    """Initialize database schema."""
    Base.metadata.create_all(bind=engine)

def init_database():
    """Initialize database schema and sample data if needed."""
    db = next(get_db())
    try:
        # Check if the database is already initialized
        if not db.execute(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'businesses')")).scalar():
            # Create tables if they don't exist
            Base.metadata.create_all(bind=engine)
            st.write("Database schema initialized.")

        # Load sample data if the database is empty
        if db.execute(text("SELECT COUNT(*) FROM businesses")).scalar() == 0:
            # Load and insert sample data
            # ... (Sample data loading logic would go here) ...
            st.write("Sample data loaded.")
    except Exception as e:
        db.rollback()
        st.error(f"Error initializing database: {str(e)}")
    finally:
        db.close()