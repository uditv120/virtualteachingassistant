import time
import logging
from flask import Blueprint, request, jsonify
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
        
        # Load and index data
        logger.info("Loading data...")
        data_processor.load_data()
        
        logger.info("Indexing documents...")
        documents = data_processor.get_all_documents()
        vector_store.index_documents(documents)
        
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
        
        if not relevant_docs:
            return jsonify({
                'answer': 'I couldn\'t find relevant information in the TDS course materials to answer your question. Please try rephrasing your question or contact the teaching assistants directly.',
                'links': []
            })
        
        # Generate answer using OpenAI
        result = openai_client.generate_answer(question, relevant_docs, image_base64)
        
        # Check response time
        elapsed_time = time.time() - start_time
        if elapsed_time > 30:
            logger.warning(f"Response took {elapsed_time:.2f} seconds")
        
        logger.info(f"Question answered in {elapsed_time:.2f} seconds")
        
        return jsonify({
            'answer': result['answer'],
            'links': result['links'],
            'response_time': round(elapsed_time, 2)
        })
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
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
    """Get system statistics"""
    try:
        initialize_system()
        
        # Get document counts
        course_content_count = len(data_processor.course_content)
        discourse_posts_count = len(data_processor.discourse_posts)
        total_indexed = vector_store.collection.count()
        
        return jsonify({
            'course_content_documents': course_content_count,
            'discourse_posts': discourse_posts_count,
            'total_indexed_documents': total_indexed,
            'system_status': 'ready'
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500
