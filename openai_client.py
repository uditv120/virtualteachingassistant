import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIClient:
    """OpenAI client for embeddings and chat completion"""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.client = OpenAI(api_key=self.api_key)
        
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            response = self.client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return [embedding.embedding for embedding in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
            
    def generate_answer(self, question: str, context_docs: List[Dict], image_base64: Optional[str] = None) -> Dict[str, Any]:
        """Generate an answer using GPT-4o with context"""
        try:
            # Prepare context from retrieved documents
            context_text = ""
            source_links = []
            
            for doc in context_docs:
                metadata = doc['metadata']
                context_text += f"\n--- Source: {metadata.get('title', 'Unknown')} ---\n"
                context_text += doc['content'][:2000]  # Limit context length
                context_text += "\n\n"
                
                # Collect source links
                if metadata.get('url'):
                    source_links.append({
                        'url': metadata['url'],
                        'text': metadata.get('title', 'Source'),
                        'type': metadata.get('type', 'unknown')
                    })
            
            # Prepare system prompt
            system_prompt = """You are a virtual Teaching Assistant for the Tools in Data Science (TDS) course at IIT Madras. 
            Your role is to help students by answering their questions based on the provided course content and Discourse posts.
            
            Guidelines:
            1. Answer questions accurately based on the provided context
            2. If the context doesn't contain enough information, say so clearly
            3. Be helpful, concise, and educational
            4. Reference specific sources when possible
            5. For coding questions, provide clear examples when available in the context
            6. Maintain a friendly but professional tone
            
            Always format your response as JSON with this structure:
            {
                "answer": "Your detailed answer here",
                "confidence": 0.8,
                "sources_used": ["url1", "url2"]
            }"""
            
            # Prepare user message
            user_content = []
            
            if image_base64:
                user_content.append({
                    "type": "text",
                    "text": f"Question: {question}\n\nContext from TDS course materials:\n{context_text}\n\nPlease analyze the attached image if relevant to the question and provide a comprehensive answer."
                })
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                })
            else:
                user_content.append({
                    "type": "text", 
                    "text": f"Question: {question}\n\nContext from TDS course materials:\n{context_text}"
                })
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                max_tokens=1500,
                temperature=0.1
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            try:
                response_json = json.loads(response_text)
                answer = response_json.get('answer', response_text)
                confidence = response_json.get('confidence', 0.5)
                sources_used = response_json.get('sources_used', [])
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                answer = response_text
                confidence = 0.5
                sources_used = []
            
            # Filter and format source links
            relevant_links = []
            for link in source_links[:5]:  # Limit to top 5 sources
                if link['url'] and link['url'] not in [l['url'] for l in relevant_links]:
                    relevant_links.append(link)
            
            return {
                'answer': answer,
                'confidence': confidence,
                'links': relevant_links
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                'answer': 'I apologize, but I encountered an error while processing your question. Please try again.',
                'confidence': 0.0,
                'links': []
            }
