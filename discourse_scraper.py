#!/usr/bin/env python3
"""
Discourse Scraper for TDS Course Posts

This script scrapes Discourse posts from the TDS course category within a specified date range.
It's designed to work with the IIT Madras online degree Discourse forum.

Usage:
    python discourse_scraper.py --start-date 2025-01-01 --end-date 2025-04-14 --output posts.json

Author: TDS Virtual TA
License: MIT
"""

import requests
import json
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiscourseScraper:
    """Scraper for TDS Discourse posts"""
    
    def __init__(self, base_url: str = "https://discourse.onlinedegree.iitm.ac.in"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TDS-Virtual-TA-Scraper/1.0'
        })
        
    def get_category_topics(self, category_id: int = 34, page: int = 0) -> Dict[str, Any]:
        """Get topics from a category (TDS category ID is 34)"""
        url = f"{self.base_url}/c/{category_id}.json"
        params = {'page': page}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching category topics: {e}")
            return {}
    
    def get_topic_posts(self, topic_id: int) -> Dict[str, Any]:
        """Get all posts from a topic"""
        url = f"{self.base_url}/t/{topic_id}.json"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching topic {topic_id}: {e}")
            return {}
    
    def scrape_posts_by_date_range(self, start_date: str, end_date: str, category_id: int = 34) -> List[Dict[str, Any]]:
        """Scrape posts within a date range"""
        start_dt = datetime.fromisoformat(start_date + "T00:00:00")
        end_dt = datetime.fromisoformat(end_date + "T23:59:59")
        
        logger.info(f"Scraping posts from {start_date} to {end_date}")
        
        all_posts = []
        page = 0
        
        while True:
            logger.info(f"Fetching category page {page}")
            
            # Get topics from category
            category_data = self.get_category_topics(category_id, page)
            if not category_data or 'topic_list' not in category_data:
                break
                
            topics = category_data['topic_list'].get('topics', [])
            if not topics:
                break
            
            # Process each topic
            for topic in topics:
                topic_id = topic.get('id')
                topic_created = topic.get('created_at')
                
                if not topic_created:
                    continue
                    
                # Parse topic creation date
                try:
                    topic_dt = datetime.fromisoformat(topic_created.replace('Z', '+00:00'))
                    topic_dt = topic_dt.replace(tzinfo=None)  # Remove timezone for comparison
                except ValueError:
                    continue
                
                # Skip topics outside date range
                if topic_dt < start_dt or topic_dt > end_dt:
                    continue
                
                logger.info(f"Processing topic {topic_id}: {topic.get('title', 'Unknown')}")
                
                # Get posts from topic
                topic_data = self.get_topic_posts(topic_id)
                if not topic_data or 'post_stream' not in topic_data:
                    continue
                
                posts = topic_data['post_stream'].get('posts', [])
                
                for post in posts:
                    post_created = post.get('created_at')
                    if not post_created:
                        continue
                    
                    try:
                        post_dt = datetime.fromisoformat(post_created.replace('Z', '+00:00'))
                        post_dt = post_dt.replace(tzinfo=None)
                    except ValueError:
                        continue
                    
                    # Check if post is in date range
                    if start_dt <= post_dt <= end_dt:
                        processed_post = {
                            'id': post.get('id'),
                            'topic_id': topic_id,
                            'topic_title': topic.get('title', ''),
                            'category_id': category_id,
                            'url': f"{self.base_url}/t/{topic.get('slug', topic_id)}/{topic_id}/{post.get('post_number', 1)}",
                            'username': post.get('username', ''),
                            'post_number': post.get('post_number', 1),
                            'content': post.get('cooked', ''),  # HTML content
                            'raw_content': post.get('raw', ''),  # Raw markdown
                            'created_at': post_created,
                            'updated_at': post.get('updated_at'),
                            'reply_count': post.get('reply_count', 0),
                            'like_count': post.get('actions_summary', [{}])[0].get('count', 0) if post.get('actions_summary') else 0
                        }
                        all_posts.append(processed_post)
                
                # Rate limiting
                time.sleep(1)
            
            page += 1
            
            # Break if we've gone past our date range
            if topics and all(datetime.fromisoformat(t.get('created_at', '').replace('Z', '+00:00')).replace(tzinfo=None) < start_dt for t in topics if t.get('created_at')):
                break
        
        logger.info(f"Scraped {len(all_posts)} posts")
        return all_posts
    
    def save_posts(self, posts: List[Dict[str, Any]], output_file: str):
        """Save posts to JSON file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(posts)} posts to {output_file}")

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Scrape TDS Discourse posts by date range')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', default='tds_posts.json', help='Output JSON file')
    parser.add_argument('--category-id', type=int, default=34, help='Discourse category ID (default: 34 for TDS)')
    parser.add_argument('--base-url', default='https://discourse.onlinedegree.iitm.ac.in', help='Discourse base URL')
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        datetime.fromisoformat(args.start_date)
        datetime.fromisoformat(args.end_date)
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD")
        return 1
    
    # Create scraper and scrape posts
    scraper = DiscourseScraper(args.base_url)
    posts = scraper.scrape_posts_by_date_range(args.start_date, args.end_date, args.category_id)
    
    # Save results
    scraper.save_posts(posts, args.output)
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
