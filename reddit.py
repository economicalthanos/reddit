from bs4 import BeautifulSoup
import requests
import concurrent.futures
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from random import uniform, choice
import os
from datetime import datetime, timedelta
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SUBREDDITS_FILE = 'subreddits.json'

class RedditFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.last_request_time = None
        self.min_request_interval = 3
        self.timeout = 5  # Reduced timeout from 10 to 5 seconds

    def get_post(self, subreddit):
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                logger.debug(f"Sleeping for {sleep_time:.2f} seconds to respect rate limits.")
                time.sleep(sleep_time)

        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=1"
        
        try:
            self.last_request_time = time.time()
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 429:  # Rate limit
                logger.warning(f"Rate limit hit for r/{subreddit}, waiting...")
                time.sleep(self.min_request_interval * 2)
                return None
                
            if response.status_code != 200:
                logger.error(f"Error fetching r/{subreddit}: Status code {response.status_code}")
                return None

            data = response.json()
            
            if not data.get('data', {}).get('children'):
                logger.info(f"No posts found in r/{subreddit}")
                return None

            for post in data['data']['children']:
                if not post['data'].get('stickied', False):
                    return self.extract_post_data(post['data'], subreddit)
            
            return None

        except requests.Timeout:
            logger.error(f"Timeout while fetching r/{subreddit}")
            return None
        except requests.RequestException as e:
            logger.error(f"Network error while fetching r/{subreddit}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching r/{subreddit}: {e}")
            return None

    def extract_post_data(self, post_data, subreddit):
        try:
            return {
                'title': post_data.get('title', ''),
                'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                'score': str(post_data.get('score', '0')),
                'subreddit': subreddit,
                'media_url': post_data.get('url_overridden_by_dest', ''),
                'thumbnail': post_data.get('thumbnail', ''),
                'author': post_data.get('author', '[deleted]'),
                'num_comments': post_data.get('num_comments', 0),
                'selftext': post_data.get('selftext', ''),
                'is_self': post_data.get('is_self', False),
                'created_utc': post_data.get('created_utc', 0),
                'domain': post_data.get('domain', ''),
                'external_url': post_data.get('url', ''),
                'post_hint': post_data.get('post_hint', '')
            }
        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            return None

def get_subreddits_from_url(url):
    """Extract subreddits from a Reddit URL"""
    url = url.lstrip('@')
    
    if 'reddit.com/r/' in url:
        subreddits_part = url.split('/r/')[-1].strip('/')
    else:
        subreddits_part = url.strip('/')
    
    subreddits = [
        s for s in subreddits_part.split('+')
        if s and not s.startswith('u_')
    ]
    
    logger.info(f"Extracted {len(subreddits)} subreddits from URL: {subreddits}")
    return subreddits

class RedditQueue:
    def __init__(self, buffer_size=5):
        self.fetcher = RedditFetcher()
        self.buffer_size = buffer_size
        self.current_posts = []
        self.subreddits = []
        self.current_index = 0
        self.load_subreddits()
        self.retry_delay = 3
        self.max_retries = 3
        self.last_fetched_index = -1

    def get_current_posts(self):
        """Return the current posts in the buffer"""
        return self.current_posts

    def initialize_buffer(self):
        """Initial fetch of only the first buffer_size posts"""
        logger.info("Initializing post buffer...")
        while len(self.current_posts) < self.buffer_size and self.current_index < len(self.subreddits):
            try:
                new_post = self.fetch_next_post()
                if new_post:
                    self.current_posts.append(new_post)
                    logger.info(f"Added initial post from r/{new_post['subreddit']}")
                time.sleep(2)  # Respect rate limits
            except Exception as e:
                logger.error(f"Error during initialization: {e}")
                time.sleep(2)
        
        logger.info(f"Buffer initialized with {len(self.current_posts)} posts")
        return self.current_posts

    def advance_queue(self):
        """Remove oldest post and fetch just one new post"""
        logger.debug(f"Advancing queue. Current index: {self.current_index}, Total subreddits: {len(self.subreddits)}")
        
        if not self.current_posts:
            return self.initialize_buffer()

        # Remove the oldest post
        if self.current_posts:
            removed = self.current_posts.pop(0)
            logger.info(f"Removed post from r/{removed['subreddit']}")

        # Try to fetch new posts until we get one or run out of attempts
        attempts = 0
        max_attempts = 5  # Increased from 3 to 5
        retry_delay = 2

        while len(self.current_posts) < self.buffer_size and attempts < max_attempts:
            if self.current_index >= len(self.subreddits):
                logger.info("Reached end of subreddits")
                break

            try:
                new_post = self.fetch_next_post()
                if new_post:
                    self.current_posts.append(new_post)
                    logger.info(f"Added new post from r/{new_post['subreddit']}")
                    break
                
                attempts += 1
                logger.warning(f"Failed to fetch post, attempt {attempts}/{max_attempts}")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Increase delay with each attempt
                
            except Exception as e:
                logger.error(f"Error fetching post: {e}")
                attempts += 1
                time.sleep(retry_delay)
                retry_delay *= 1.5

        # If we couldn't fetch any new posts and the buffer is empty, reset
        if not self.current_posts and self.current_index >= len(self.subreddits):
            logger.info("Resetting queue")
            self.current_index = 0
            return self.initialize_buffer()

        logger.debug(f"Current buffer state: Buffer size: {len(self.current_posts)}, Current index: {self.current_index}, Total subreddits: {len(self.subreddits)}")
        
        return self.current_posts

    def fetch_next_post(self, retries=0):
        """Fetch a post from the next subreddit"""
        if self.current_index >= len(self.subreddits):
            logger.info("No more subreddits to fetch from")
            return None

        subreddit = self.subreddits[self.current_index]
        logger.debug(f"Attempting to fetch post from r/{subreddit} (index: {self.current_index})")
        
        try:
            time.sleep(self.retry_delay)
            post = self.fetcher.get_post(subreddit)
            
            if post:
                self.last_fetched_index = self.current_index
                self.current_index += 1
                self.retry_delay = 3
                logger.info(f"Successfully fetched post from r/{subreddit}")
                return post
            
            logger.info(f"No post available from r/{subreddit}")
            self.current_index += 1
            return None

        except Exception as e:
            logger.error(f"Error fetching from r/{subreddit}: {e}")
            if "429" in str(e) and retries < self.max_retries:
                wait_time = self.retry_delay * (2 ** retries)
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                return self.fetch_next_post(retries + 1)
            
            self.current_index += 1
            return None

    def load_subreddits(self):
        """Load subreddits from file"""
        try:
            with open(SUBREDDITS_FILE, 'r') as f:
                data = json.load(f)
                self.subreddits = data['subreddits']
                logger.info(f"Loaded {len(self.subreddits)} subreddits")
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading subreddits file: {e}")
            self.subreddits = []

    def get_progress(self):
        """Get progress information"""
        return {
            'current_index': self.current_index,
            'total_subreddits': len(self.subreddits),
            'buffer_size': len(self.current_posts),
            'remaining_subreddits': len(self.subreddits) - self.current_index,
            'last_fetched': self.last_fetched_index
        }

def main():
    # This main function can be removed if this file is only used as a module
    pass

if __name__ == "__main__":
    main()
