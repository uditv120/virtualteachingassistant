import json
import logging
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

class DataProcessor:
    """Process and prepare TDS course content and Discourse posts for indexing"""
    
    def __init__(self):
        self.course_content = []
        self.discourse_posts = []
        
    def load_data(self):
        """Load data from the provided JSON files"""
        try:
            # Load merged TDS discourse posts
            merged_file = "attached_assets/merged_tds_discourse_posts_1750255020810.json"
            if os.path.exists(merged_file):
                with open(merged_file, 'r', encoding='utf-8') as f:
                    merged_data = json.load(f)
                    logger.info(f"Loaded {len(merged_data)} items from merged file")
                    self._process_merged_data(merged_data)
            
            # Load additional discourse content
            discourse_file = "attached_assets/Discourse_content_1750255037874.json"
            if os.path.exists(discourse_file):
                with open(discourse_file, 'r', encoding='utf-8') as f:
                    discourse_data = json.load(f)
                    logger.info(f"Loaded {len(discourse_data)} discourse posts")
                    self._process_discourse_data(discourse_data)
            
            # Load combined content
            combined_file = "attached_assets/Combined_content_1750255037874.json"
            if os.path.exists(combined_file):
                with open(combined_file, 'r', encoding='utf-8') as f:
                    combined_data = json.load(f)
                    logger.info(f"Loaded {len(combined_data)} combined content items")
                    self._process_combined_data(combined_data)
                    
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
            
    def _process_merged_data(self, data: List[Dict]):
        """Process merged TDS discourse posts and course content"""
        for item in data:
            if item.get('source_type') == 'tds_handbook':
                # Course content
                self.course_content.append({
                    'id': item.get('chunk_id', item.get('url', '')),
                    'title': item.get('title', ''),
                    'content': item.get('text', ''),
                    'url': item.get('url', ''),
                    'type': 'course_content',
                    'metadata': item.get('metadata', {})
                })
            else:
                # Discourse post
                self._add_discourse_post(item)
                
    def _process_discourse_data(self, data: List[Dict]):
        """Process discourse posts"""
        for item in data:
            self._add_discourse_post(item)
            
    def _process_combined_data(self, data: List[Dict]):
        """Process combined content data"""
        for item in data:
            if item.get('source') == 'course_content':
                self.course_content.append({
                    'id': item.get('id', ''),
                    'title': item.get('title', ''),
                    'content': item.get('text', ''),
                    'url': item.get('url', ''),
                    'type': 'course_content',
                    'metadata': item.get('metadata', {})
                })
            elif item.get('source') == 'discourse':
                self._add_discourse_post(item)
                
    def _add_discourse_post(self, item: Dict):
        """Add a discourse post to the collection"""
        discourse_post = {
            'id': str(item.get('id', '')),
            'title': item.get('topic_title', ''),
            'content': item.get('content', ''),
            'url': item.get('url', ''),
            'username': item.get('username', ''),
            'post_number': item.get('post_number', 0),
            'created_at': item.get('created_at', ''),
            'type': 'discourse_post',
            'context': item.get('context', [])
        }
        self.discourse_posts.append(discourse_post)
        
    def get_all_documents(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all processed documents for indexing"""
        all_docs = []
        
        # Add course content
        for doc in self.course_content:
            if doc['content'].strip():  # Only add non-empty content
                # Truncate very long content to avoid token issues
                content = doc['content'][:3000] if len(doc['content']) > 3000 else doc['content']
                all_docs.append({
                    'id': doc['id'],
                    'content': f"{doc['title']}\n\n{content}",
                    'title': doc['title'],
                    'url': doc['url'],
                    'type': doc['type'],
                    'metadata': doc.get('metadata', {})
                })
        
        # Add discourse posts (prioritize recent ones)
        sorted_posts = sorted(self.discourse_posts, key=lambda x: x['created_at'] or '', reverse=True)
        for post in sorted_posts:
            if post['content'].strip():  # Only add non-empty content
                # Truncate content to avoid token issues
                content = post['content'][:2000] if len(post['content']) > 2000 else post['content']
                if post['title']:
                    content = f"{post['title']}\n\n{content}"
                    
                all_docs.append({
                    'id': post['id'],
                    'content': content,
                    'title': post['title'],
                    'url': post['url'],
                    'type': post['type'],
                    'username': post['username'],
                    'created_at': post['created_at'],
                    'metadata': {
                        'post_number': post['post_number'],
                        'context': post['context']
                    }
                })
        
        # Apply limit if specified (for testing with smaller datasets)
        if limit and len(all_docs) > limit:
            all_docs = all_docs[:limit]
            logger.info(f"Limited to {limit} documents for testing")
        
        logger.info(f"Processed {len(all_docs)} documents total")
        return all_docs
