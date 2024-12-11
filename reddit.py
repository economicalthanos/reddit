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

            posts = data['data']['children']
            for post in posts:
                post_data = post.get('data')
                if post_data and not post_data.get('stickied', False):
                    extracted_data = self.extract_post_data(post_data, subreddit)
                    if extracted_data:
                        return extracted_data
            
            return None

        except Exception as e:
            logger.error(f"Error in get_post for r/{subreddit}: {e}")
            return None

    def unescape_url(self, url):
        """Convert HTML entities back to original characters in URLs"""
        if not url:
            return url
        return url.replace('&amp;', '&')

    def extract_post_data(self, post_data, subreddit):
        try:
            media_url = ''
            gallery_images = []
            logger.debug(f"\n=== VIDEO DEBUG ===")
            
            # Basic validation
            if not isinstance(post_data, dict):
                logger.error("Invalid post data format")
                return None
            
            # Check if this is a crosspost and get the original post data
            if 'crosspost_parent_list' in post_data and post_data['crosspost_parent_list']:
                original_post = post_data['crosspost_parent_list'][0]
                is_video = original_post.get('is_video', False)
                media = original_post.get('media', {})
                url = original_post.get('url', '')
            else:
                is_video = post_data.get('is_video', False)
                media = post_data.get('media', {})
                url = post_data.get('url', '')

            logger.debug(f"Post URL: {url}")
            logger.debug(f"Is Video: {is_video}")
            logger.debug(f"Media Data: {media}")
            
            # Handle v.redd.it videos
            dash_url = None
            if is_video and isinstance(media, dict):
                reddit_video = media.get('reddit_video', {})
                if reddit_video:
                    # Get the DASH playlist URL
                    dash_url = reddit_video.get('dash_url')
                    if not dash_url and 'fallback_url' in reddit_video:
                        # Construct DASH URL from fallback URL if not provided
                        base_url = reddit_video['fallback_url'].split('DASH_')[0]
                        dash_url = f"{base_url}DASHPlaylist.mpd"
                    
                    # Keep the fallback URL as backup
                    media_url = reddit_video.get('fallback_url', '')

            # Check if the post is a gallery
            if post_data.get('is_gallery', False):
                media_metadata = post_data.get('media_metadata', {})
                for media_id, media_info in media_metadata.items():
                    if media_info.get('e') == 'Image':
                        image_url = media_info['s']['u']
                        gallery_images.append(self.unescape_url(image_url))

            # If no video URL found, use the post URL only if it's not a self post
            if not media_url and not post_data.get('is_self', False):
                media_url = self.unescape_url(url) if url else ''
            
            logger.debug(f"Final media URL: {media_url}")
            logger.debug("=== VIDEO DEBUG END ===\n")

            # Convert selftext markdown to HTML
            selftext = post_data.get('selftext', '')
            if selftext:
                import re
                
                logger.debug("\n=== NUMBERED LIST PROCESSING START ===")
                logger.debug(f"Original text:\n{selftext}")
                
                # Process numbered lists first
                lines = selftext.split('\n')
                in_list = False
                list_buffer = []
                processed_lines = []
                current_list_number = 0
                
                for line in lines:
                    line = line.strip()
                    # Check for numbered list item
                    list_match = re.match(r'^\s*(\d+)\.\s+(.+)$', line)
                    
                    if list_match:
                        number = int(list_match.group(1))
                        content = list_match.group(2)
                        logger.debug(f"Found list item: number={number}, content={content}")
                        
                        # Start new list only if we're not in one or if number is less than current
                        if not in_list or number <= current_list_number:
                            if in_list:
                                processed_lines.append('</ol>')
                            processed_lines.append('<ol>')
                            in_list = True
                            
                        current_list_number = number
                        list_buffer.append(content)
                        processed_lines.append(f'<li>{content}</li>')
                        logger.debug(f"Added list item {number}")
                    elif line == '' and not in_list:
                        # Only add empty lines when we're not in a list
                        processed_lines.append(line)
                    elif line != '' and in_list:
                        # Non-empty, non-list line ends the list
                        logger.debug("Ending list due to non-list content")
                        in_list = False
                        processed_lines.append('</ol>')
                        processed_lines.append(line)
                    else:
                        processed_lines.append(line)
                
                if in_list:
                    logger.debug("Closing final list")
                    processed_lines.append('</ol>')
                
                selftext = '\n'.join(processed_lines)
                logger.debug(f"\nProcessed HTML:\n{selftext}")
                logger.debug("=== NUMBERED LIST PROCESSING END ===\n")
                
                # Continue with other markdown conversions
                # Headers
                selftext = re.sub(r'(?m)^# (.*?)$', r'<h1>\1</h1>', selftext)
                selftext = re.sub(r'(?m)^## (.*?)$', r'<h2>\1</h2>', selftext)
                selftext = re.sub(r'(?m)^### (.*?)$', r'<h3>\1</h3>', selftext)
                
                # Bold and Italic
                selftext = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', selftext)
                selftext = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', selftext)
                selftext = re.sub(r'\*(.*?)\*', r'<em>\1</em>', selftext)
                
                # Strikethrough
                selftext = re.sub(r'~~(.*?)~~', r'<del>\1</del>', selftext)
                
                # Spoilers
                selftext = re.sub(r'>!(.*?)!<', r'<span class="spoiler">\1</span>', selftext)
                
                # Unordered lists (unchanged)
                selftext = re.sub(r'(?m)^[*-] (.*?)$', r'<ul><li>\1</li></ul>', selftext)
                
                # Blockquotes
                selftext = re.sub(r'(?m)^> (.*?)$', r'<blockquote>\1</blockquote>', selftext)
                
                # Code blocks
                selftext = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', selftext, flags=re.DOTALL)
                selftext = re.sub(r'`(.*?)`', r'<code>\1</code>', selftext)
                
                # Links - handle both [text](url) and plain URLs
                selftext = re.sub(
                    r'\[([^\]]+)\]\(([^\)]+)\)', 
                    r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', 
                    selftext
                )
                selftext = re.sub(
                    r'(?<!href=")(?<![\(\[])(https?://[^\s\)<>]+)', 
                    r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', 
                    selftext
                )
                
                # Line breaks
                selftext = selftext.replace('\n\n', '<br><br>')
                
                # Superscript
                selftext = re.sub(r'\^(.*?)(?=\s|$)', r'<sup>\1</sup>', selftext)

            # Create post data dictionary with safe defaults and unescape URLs
            post_data_dict = {
                'title': post_data.get('title', ''),
                'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                'score': str(post_data.get('score', '0')),
                'subreddit': subreddit,
                'media_url': self.unescape_url(media_url),
                'gallery_images': gallery_images,
                'thumbnail': self.unescape_url(post_data.get('thumbnail', '')),
                'author': post_data.get('author', '[deleted]'),
                'num_comments': post_data.get('num_comments', 0),
                'selftext': selftext,
                'is_self': post_data.get('is_self', False),
                'created_utc': post_data.get('created_utc', 0),
                'domain': post_data.get('domain', ''),
                'external_url': self.unescape_url(url) if not post_data.get('is_self', False) else '',
                'post_hint': post_data.get('post_hint', ''),
                'is_video': is_video,
                'dash_url': self.unescape_url(dash_url) if dash_url else None,
            }
            
            return post_data_dict

        except Exception as e:
            logger.error(f"Error extracting post data: {e}")
            logger.error(f"Post data that caused error: {post_data}")
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
