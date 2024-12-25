# Reddit Posts Viewer

This project is a web application that allows users to view posts from various subreddits. It fetches posts using the Reddit API and displays them in a user-friendly interface.

## Features

- View posts from multiple subreddits.
- Navigate through posts using keyboard arrows or navigation buttons.
- Filter posts by subreddit.
- Display images, videos, and galleries.
- Update subreddit list via a URL.
- Automatic backup script with AI-powered commit messages
- Smart file change detection

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/economicalthanos/reddit.git
   cd reddit
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**

   ```bash
   python app.py
   ```

4. **Access the application:**

   Open your web browser and go to `http://localhost:5000`.

## Backup

The repository includes an automatic backup script (`backup.py`) that:
- Generates intelligent commit messages based on file changes
- Analyzes code modifications for meaningful descriptions
- Detects the type of changes (functions, classes, documentation, etc.)
- Pushes to GitHub automatically

To use it, simply run:
```bash
python backup.py
```

## Configuration

- **Secret Key:** Update `app.secret_key` in `app.py` with a secure key.
- **Subreddits File:** The list of subreddits is stored in `subreddits.json`.

## Usage

- **Update Subreddits:** Enter a Reddit URL containing subreddits in the input field and click "Update".
- **Navigate Posts:** Use the "Previous" and "Next" buttons or arrow keys to navigate through posts.
- **Filter Subreddits:** Use the search box to filter subreddits in the sidebar.

## Logging

- Logs are configured to display debug information. Adjust the logging level in `app.py` and `reddit.py` as needed.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.
