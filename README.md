# TDS Virtual TA

A Virtual Teaching Assistant API for the Tools in Data Science (TDS) course at IIT Madras. This application uses RAG (Retrieval-Augmented Generation) to answer student questions based on course content and Discourse posts.

## Features

- **Intelligent Q&A**: Uses OpenAI GPT-4o and embeddings for contextual answers
- **Multi-modal Support**: Handles both text and image-based questions
- **Vector Search**: ChromaDB-powered semantic search across course materials
- **Source Citations**: Provides relevant links and sources for answers
- **Fast Response**: Optimized for sub-30 second response times
- **Web Interface**: Built-in test interface for easy interaction
- **Discourse Scraper**: Bonus script for scraping TDS Discourse posts

## API Endpoints

### POST /api/
Answer a student question with optional image attachment.

**Request Body:**
```json
{
  "question": "Your question about TDS course",
  "image": "base64_encoded_image_data (optional)"
}
