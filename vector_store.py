import chromadb
import logging
from typing import List, Dict, Any
from openai_client import OpenAIClient
import os

logger = logging.getLogger(__name__)

class VectorStore:
    """ChromaDB-based vector store for semantic search"""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = None
        self.openai_client = OpenAIClient()
        self._initialize_collection()
        
    def _initialize_collection(self):
        """Initialize or get the ChromaDB collection"""
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(name="tds_knowledge_base")
            logger.info("Found existing ChromaDB collection")
        except:
            # Create new collection
            self.collection = self.client.create_collection(
                name="tds_knowledge_base",
                metadata={"description": "TDS course content and discourse posts"}
            )
            logger.info("Created new ChromaDB collection")
            
    def index_documents(self, documents: List[Dict[str, Any]]):
        """Index documents in the vector store"""
        if not documents:
            logger.warning("No documents to index")
            return
            
        # Check if collection already has documents
        existing_count = self.collection.count()
        if existing_count > 0:
            logger.info(f"Collection already has {existing_count} documents, skipping indexing")
            return
            
        logger.info(f"Indexing {len(documents)} documents...")
        
        # Prepare data for ChromaDB
        ids = []
        contents = []
        metadatas = []
        
        for doc in documents:
            # Use document ID or generate one
            doc_id = doc.get('id') or f"doc_{len(ids)}"
            ids.append(str(doc_id))
            contents.append(doc['content'])
            
            # Prepare metadata (ChromaDB doesn't support nested dicts)
            metadata = {
                'title': doc.get('title', ''),
                'url': doc.get('url', ''),
                'type': doc.get('type', ''),
                'username': doc.get('username', ''),
                'created_at': doc.get('created_at', '')
            }
            metadatas.append(metadata)
        
        # Generate embeddings using OpenAI
        try:
            embeddings = self.openai_client.get_embeddings(contents)
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            
            logger.info(f"Successfully indexed {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            raise
            
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        try:
            # Generate embedding for the query
            query_embedding = self.openai_client.get_embeddings([query])[0]
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                result = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                }
                formatted_results.append(result)
                
            logger.info(f"Found {len(formatted_results)} relevant documents")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
