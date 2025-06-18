import time
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from database import db
from models import Question, SystemStats, DocumentIndex, UserFeedback
from data_processor import DataProcessor
from vector_store import VectorStore
from openai_client import OpenAIClient
import base64

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize components
data_processor = None
vector_store = None
openai_client = None

def initialize_system():
    """Initialize the RAG system"""
    global data_processor, vector_store, openai_client
    
    if data_processor is None:
        logger.info("Initializing TDS Virtual TA system...")
        
        # Initialize components
        data_processor = DataProcessor()
        vector_store = VectorStore()
        openai_client = OpenAIClient()
        
        # Load data
        logger.info("Loading data...")
        data_processor.load_data()
        
        # Check if vector store already has documents
        existing_count = vector_store.collection.count()
        if existing_count == 0:
            logger.info("Indexing documents in background...")
            # Start with a smaller dataset to handle AI Pipe token limits
            documents = data_processor.get_all_documents(limit=50)
            
            # Initialize with basic documents first for immediate functionality
            import threading
            def background_indexing():
                try:
                    vector_store.index_documents(documents)
                    logger.info("Background indexing completed!")
                except Exception as e:
                    logger.error(f"Background indexing failed: {e}")
            
            # Start background indexing
            thread = threading.Thread(target=background_indexing, daemon=True)
            thread.start()
        else:
            logger.info(f"Found {existing_count} existing documents, skipping indexing")
        
        logger.info("System initialization complete!")

@api_bp.route('/api/', methods=['POST'])
def answer_question():
    """Main API endpoint for answering questions"""
    start_time = time.time()
    
    try:
        # Initialize system if needed
        initialize_system()
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
            
        question = data.get('question', '').strip()
        if not question:
            return jsonify({'error': 'Question is required'}), 400
            
        image_base64 = data.get('image')
        
        # Validate base64 image if provided
        if image_base64:
            try:
                # Validate base64 format
                base64.b64decode(image_base64)
            except Exception:
                return jsonify({'error': 'Invalid base64 image data'}), 400
        
        logger.info(f"Processing question: {question[:100]}...")
        
        # Search for relevant documents
        relevant_docs = vector_store.search(question, n_results=5)
        
        # Prepare response data
        answer_text = None
        links = []
        relevant_docs_count = len(relevant_docs) if relevant_docs else 0
        
        if not relevant_docs:
            answer_text = 'I couldn\'t find relevant information in the TDS course materials to answer your question. Please try rephrasing your question or contact the teaching assistants directly.'
        else:
            # Generate answer using OpenAI
            result = openai_client.generate_answer(question, relevant_docs, image_base64)
            answer_text = result['answer']
            links = result['links']
        
        # Calculate response time
        elapsed_time = time.time() - start_time
        if elapsed_time > 30:
            logger.warning(f"Response took {elapsed_time:.2f} seconds")
        
        # Store question and response in database
        try:
            user_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            user_agent = request.headers.get('User-Agent', '')
            
            question_record = Question(
                question_text=question,
                has_image=bool(image_base64),
                answer_text=answer_text,
                response_time=elapsed_time,
                relevant_docs_count=relevant_docs_count,
                links_provided=links,
                user_ip=user_ip,
                user_agent=user_agent
            )
            
            db.session.add(question_record)
            db.session.commit()
            logger.info(f"Stored question record with ID: {question_record.id}")
            
        except Exception as db_error:
            logger.error(f"Error storing question in database: {db_error}")
            db.session.rollback()
        
        logger.info(f"Question answered in {elapsed_time:.2f} seconds")
        
        return jsonify({
            'answer': answer_text,
            'links': links,
            'response_time': round(elapsed_time, 2)
        })
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        
        # Try to store failed request in database
        try:
            elapsed_time = time.time() - start_time
            user_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            user_agent = request.headers.get('User-Agent', '')
            
            question_record = Question(
                question_text=data.get('question', 'ERROR') if 'data' in locals() else 'PARSE_ERROR',
                has_image=bool(data.get('image')) if 'data' in locals() else False,
                answer_text=f"ERROR: {str(e)}",
                response_time=elapsed_time,
                relevant_docs_count=0,
                links_provided=[],
                user_ip=user_ip,
                user_agent=user_agent
            )
            
            db.session.add(question_record)
            db.session.commit()
            
        except Exception as db_error:
            logger.error(f"Error storing failed request: {db_error}")
            db.session.rollback()
        
        return jsonify({
            'error': 'An internal error occurred while processing your question.',
            'details': str(e)
        }), 500

@api_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        initialize_system()
        return jsonify({
            'status': 'healthy',
            'system': 'TDS Virtual TA',
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@api_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics including database analytics"""
    try:
        initialize_system()
        
        # Get document counts
        course_content_count = len(data_processor.course_content)
        discourse_posts_count = len(data_processor.discourse_posts)
        total_indexed = vector_store.collection.count()
        
        # Get database statistics
        total_questions = db.session.query(Question).count()
        successful_responses = db.session.query(Question).filter(
            ~Question.answer_text.like('ERROR:%')
        ).count()
        failed_responses = total_questions - successful_responses
        
        # Calculate average response time
        avg_response_time = db.session.query(db.func.avg(Question.response_time)).scalar() or 0.0
        
        # Get questions with images count
        questions_with_images = db.session.query(Question).filter(
            Question.has_image == True
        ).count()
        
        # Get recent activity (last 24 hours)
        from datetime import timedelta
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_questions = db.session.query(Question).filter(
            Question.created_at >= recent_cutoff
        ).count()
        
        return jsonify({
            'system_status': 'ready',
            'course_content_documents': course_content_count,
            'discourse_posts': discourse_posts_count,
            'indexed_documents': total_indexed,
            'database_stats': {
                'total_questions': total_questions,
                'successful_responses': successful_responses,
                'failed_responses': failed_responses,
                'avg_response_time': round(avg_response_time, 2),
                'questions_with_images': questions_with_images,
                'recent_questions_24h': recent_questions
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/questions', methods=['GET'])
def get_questions():
    """Get recent questions and responses"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Limit to reasonable values
        limit = min(limit, 100)
        
        # Query recent questions
        questions = db.session.query(Question).order_by(
            Question.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Format response
        results = []
        for q in questions:
            results.append({
                'id': q.id,
                'question': q.question_text[:200] + '...' if len(q.question_text) > 200 else q.question_text,
                'has_image': q.has_image,
                'response_time': q.response_time,
                'relevant_docs_count': q.relevant_docs_count,
                'links_count': len(q.links_provided) if q.links_provided else 0,
                'created_at': q.created_at.isoformat(),
                'success': not q.answer_text.startswith('ERROR:') if q.answer_text else False
            })
        
        return jsonify({
            'questions': results,
            'total_returned': len(results),
            'offset': offset,
            'limit': limit
        })
        
    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for a question response"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        question_id = data.get('question_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback_text', '')
        is_helpful = data.get('is_helpful')
        
        if not question_id:
            return jsonify({'error': 'question_id is required'}), 400
        
        if rating is not None and (rating < 1 or rating > 5):
            return jsonify({'error': 'rating must be between 1 and 5'}), 400
        
        # Check if question exists
        question = db.session.query(Question).filter_by(id=question_id).first()
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        # Store feedback
        user_ip = request.environ.get('REMOTE_ADDR', 'unknown')
        
        feedback = UserFeedback(
            question_id=question_id,
            rating=rating,
            feedback_text=feedback_text,
            is_helpful=is_helpful,
            user_ip=user_ip
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        logger.info(f"Feedback stored for question {question_id}")
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
