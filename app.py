from flask import Flask, render_template, flash
from reddit import get_all_posts

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

@app.route('/')
def index():
    try:
        posts = get_all_posts()
        if not posts:
            flash('No posts were fetched. Please try again later.', 'error')
            return render_template('index.html', posts=[])
        return render_template('index.html', posts=posts)
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return render_template('index.html', posts=[])

if __name__ == '__main__':
    app.run(debug=True) 