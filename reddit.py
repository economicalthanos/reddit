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
            media_url = ''
            if post_data.get('is_video'):
                # v.redd.it videoları için
                if 'v.redd.it' in post_data.get('url', ''):
                    media_url = post_data.get('url')
                # Diğer video kaynakları için
                elif post_data.get('media', {}).get('reddit_video', {}):
                    media_url = post_data['media']['reddit_video'].get('fallback_url', '')
                else:
                    media_url = post_data.get('url_overridden_by_dest', '')
            else:
                media_url = post_data.get('url_overridden_by_dest', '')

            return {
                'title': post_data.get('title', ''),
                'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                'score': str(post_data.get('score', '0')),
                'subreddit': subreddit,
                'media_url': media_url,
                'thumbnail': post_data.get('thumbnail', ''),
                'author': post_data.get('author', '[deleted]'),
                'num_comments': post_data.get('num_comments', 0),
                'selftext': post_data.get('selftext', ''),
                'is_self': post_data.get('is_self', False),
                'created_utc': post_data.get('created_utc', 0),
                'domain': post_data.get('domain', ''),
                'external_url': post_data.get('url', ''),
                'post_hint': post_data.get('post_hint', ''),
                'is_video': post_data.get('is_video', False)
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
    def __init__(self, buffer_size=3):
        self.fetcher = RedditFetcher()
        self.buffer_size = buffer_size
        self.current_posts = []
        self.subreddits = []
        self.current_index = 0
        self.load_subreddits()
        self.retry_delay = 3
        self.max_retries = 3
        self.last_fetched_index = -1
        self.min_buffer_size = 2  # Current post + 2 next posts
        logger.debug(f"Initialized RedditQueue with buffer_size={buffer_size}, min_buffer_size={self.min_buffer_size}")

    def get_current_posts(self):
        """Return the current posts in the buffer"""
        return self.current_posts

    def initialize_buffer(self):
        """Initial fetch of posts to fill the buffer"""
        logger.debug(f"=== INITIALIZE BUFFER START ===")
        logger.debug(f"Target buffer size: {self.buffer_size}")
        self.current_posts = []
        
        while len(self.current_posts) < self.buffer_size and self.current_index < len(self.subreddits):
            try:
                logger.debug(f"Fetching initial post... (current size: {len(self.current_posts)})")
                new_post = self.fetch_next_post()
                if new_post:
                    self.current_posts.append(new_post)
                    logger.debug(f"Added initial post from r/{new_post['subreddit']}")
                else:
                    logger.debug("Failed to fetch initial post")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error during initialization: {e}")
        
        logger.debug(f"=== INITIALIZE BUFFER END ===")
        logger.debug(f"Buffer initialized with {len(self.current_posts)} posts: {[p['subreddit'] for p in self.current_posts]}")
        return self.current_posts

    def advance_queue(self):
        """Remove oldest post and fetch new posts to maintain buffer"""
        logger.debug(f"\n=== ADVANCE QUEUE START ===")
        logger.debug(f"BEFORE - Current index: {self.current_index}")
        logger.debug(f"BEFORE - Buffer size: {len(self.current_posts)}")
        logger.debug(f"BEFORE - Posts in buffer: {[p['subreddit'] for p in self.current_posts]}")
        logger.debug(f"BEFORE - Total subreddits: {len(self.subreddits)}")
        
        if not self.current_posts:
            logger.debug("Buffer empty, initializing...")
            return self.initialize_buffer()

        # Her zaman bir sonraki postu fetch et
        try:
            logger.debug(f"Attempting to fetch next post at index {self.current_index}")
            new_post = self.fetch_next_post()
            if new_post:
                self.current_posts.append(new_post)
                logger.debug(f"SUCCESS: Added new post from r/{new_post['subreddit']}")
                logger.debug(f"New buffer size: {len(self.current_posts)}")
            else:
                logger.debug(f"FAILED: Could not fetch post at index {self.current_index}")
        except Exception as e:
            logger.error(f"ERROR during fetch: {str(e)}")

        # En eski postu kaldır
        if len(self.current_posts) > self.buffer_size:
            removed = self.current_posts.pop(0)
            logger.debug(f"Removed oldest post from r/{removed['subreddit']}")
            logger.debug(f"After removal - Buffer size: {len(self.current_posts)}")

        # Buffer boşsa ve subredditler bittiyse reset at
        if not self.current_posts and self.current_index >= len(self.subreddits):
            logger.debug("Resetting queue - reached end of subreddits")
            self.current_index = 0
            return self.initialize_buffer()

        logger.debug(f"\n=== ADVANCE QUEUE END ===")
        logger.debug(f"AFTER - Current index: {self.current_index}")
        logger.debug(f"AFTER - Buffer size: {len(self.current_posts)}")
        logger.debug(f"AFTER - Posts in buffer: {[p['subreddit'] for p in self.current_posts]}")
        return self.current_posts

    def fetch_next_post(self, retries=0):
        """Fetch a post from the next subreddit"""
        if self.current_index >= len(self.subreddits):
            logger.debug(f"FETCH: Index {self.current_index} exceeds subreddit count {len(self.subreddits)}")
            return None

        subreddit = self.subreddits[self.current_index]
        logger.debug(f"\nFETCH: Attempting r/{subreddit} at index {self.current_index}")
        
        try:
            time.sleep(self.retry_delay)
            post = self.fetcher.get_post(subreddit)
            
            if post:
                if any(existing['url'] == post['url'] for existing in self.current_posts):
                    logger.debug(f"FETCH: Post from r/{subreddit} already in buffer, skipping")
                    self.current_index += 1
                    return self.fetch_next_post(retries)
                
                logger.debug(f"FETCH: Successfully got post from r/{subreddit}")
                self.last_fetched_index = self.current_index
                self.current_index += 1
                self.retry_delay = 3
                return post
            
            logger.debug(f"FETCH: No post available from r/{subreddit}")
            self.current_index += 1
            return self.fetch_next_post(retries)

        except Exception as e:
            logger.error(f"FETCH ERROR for r/{subreddit}: {e}")
            if "429" in str(e) and retries < self.max_retries:
                wait_time = self.retry_delay * (2 ** retries)
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                return self.fetch_next_post(retries + 1)
            
            self.current_index += 1
            return self.fetch_next_post(retries)

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
