from flask import Flask, render_template, flash, request, redirect, url_for, jsonify
from reddit import RedditQueue, get_subreddits_from_url
import json
import os
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

SUBREDDITS_FILE = 'subreddits.json'

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a global queue instance
reddit_queue = RedditQueue(buffer_size=3)

def save_subreddits(subreddits_url):
    """Save subreddits to a JSON file"""
    subreddits = get_subreddits_from_url(subreddits_url)
    data = {
        'url': subreddits_url,
        'subreddits': subreddits
    }
    with open(SUBREDDITS_FILE, 'w') as f:
        json.dump(data, f)
    return subreddits

def load_saved_data():
    """Load saved subreddits data"""
    if os.path.exists(SUBREDDITS_FILE):
        with open(SUBREDDITS_FILE, 'r') as f:
            return json.load(f)
    return None

@app.route('/')
def index():
    saved_data = load_saved_data()
    
    # Initialize the buffer if it's empty
    if not reddit_queue.get_current_posts():
        reddit_queue.initialize_buffer()
    
    progress = reddit_queue.get_progress()
    subreddits = reddit_queue.subreddits  # Ensure subreddits are passed to the template
    subreddit_counts = {sub: 1 for sub in subreddits}  # Placeholder counts
    return render_template('index.html',
                           posts=reddit_queue.get_current_posts(),
                           progress=progress,
                           currentPost=0,
                           subreddits=subreddits,
                           subreddit_counts=subreddit_counts,
                           saved_url=saved_data.get('url', '') if saved_data else '')

@app.route('/update_subreddits', methods=['POST'])
def update_subreddits():
    subreddits_url = request.form.get('subreddits_url', '').strip()
    if subreddits_url:
        try:
            save_subreddits(subreddits_url)
            reddit_queue.__init__(buffer_size=3)  # Reset the queue
            reddit_queue.initialize_buffer()
            flash('Subreddits updated successfully!', 'success')
            logger.info("Subreddits updated successfully.")
        except Exception as e:
            flash(f'Error saving subreddits: {str(e)}', 'error')
            logger.error(f'Error saving subreddits: {str(e)}')
    else:
        flash('No URL provided.', 'error')
        logger.warning('No subreddits URL provided in update_subreddits.')
    return redirect(url_for('index'))

@app.route('/next_post', methods=['POST'])
def next_post():
    try:
        logger.debug("Received request to fetch next post.")
        posts = reddit_queue.advance_queue()
        progress = reddit_queue.get_progress()
        
        # Convert posts to JSON-safe format
        posts_data = []
        for post in posts:
            posts_data.append({
                'title': post.get('title', ''),
                'url': post.get('url', ''),
                'score': str(post.get('score', '0')),
                'subreddit': post.get('subreddit', ''),
                'media_url': post.get('media_url', ''),
                'thumbnail': post.get('thumbnail', ''),
                'author': post.get('author', ''),
                'num_comments': post.get('num_comments', 0),
                'selftext': post.get('selftext', ''),
                'is_self': post.get('is_self', False),
                'created_utc': post.get('created_utc', 0),
                'domain': post.get('domain', ''),
                'external_url': post.get('external_url', ''),
                'post_hint': post.get('post_hint', '')
            })
        
        logger.debug(f"Sending posts: {[p['subreddit'] for p in posts_data]}")
        return jsonify({
            'success': True,
            'posts': posts_data,
            'progress': progress
        })
    except Exception as e:
        logger.error(f"Error in /next_post route: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'posts': [],
            'progress': reddit_queue.get_progress()
        }), 500

if __name__ == '__main__':
    app.run(debug=True) 