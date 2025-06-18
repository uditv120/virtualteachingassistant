from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Question(Base):
    """Store user questions and responses"""
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    question_text = Column(Text, nullable=False)
    has_image = Column(Boolean, default=False)
    answer_text = Column(Text)
    response_time = Column(Float)  # seconds
    relevant_docs_count = Column(Integer, default=0)
    links_provided = Column(JSON)  # Store array of link objects
    created_at = Column(DateTime, default=datetime.utcnow)
    user_ip = Column(String(45))  # IPv6 support
    user_agent = Column(String(500))

class SystemStats(Base):
    """Track system performance and usage"""
    __tablename__ = 'system_stats'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    total_questions = Column(Integer, default=0)
    avg_response_time = Column(Float, default=0.0)
    successful_responses = Column(Integer, default=0)
    failed_responses = Column(Integer, default=0)
    indexed_documents = Column(Integer, default=0)
    
class DocumentIndex(Base):
    """Track indexed documents and their metadata"""
    __tablename__ = 'document_index'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(500))
    content_type = Column(String(50))  # 'course_content', 'discourse_post'
    url = Column(String(500))
    username = Column(String(100))  # For discourse posts
    created_at = Column(DateTime, default=datetime.utcnow)
    indexed_at = Column(DateTime, default=datetime.utcnow)
    content_length = Column(Integer)

class UserFeedback(Base):
    """Store user feedback on responses"""
    __tablename__ = 'user_feedback'
    
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer)  # Foreign key to questions table
    rating = Column(Integer)  # 1-5 scale
    feedback_text = Column(Text)
    is_helpful = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_ip = Column(String(45))