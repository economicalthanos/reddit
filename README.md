# Reddit Posts Viewer

Reddit Posts Viewer is a web application that allows users to view and navigate through posts from various subreddits. The application is built using Flask for the backend and HTML/CSS/JavaScript for the frontend.

## Features

- Fetch and display posts from specified subreddits.
- Navigate through posts using keyboard arrows or navigation buttons.
- View post details including title, author, score, comments, and media.
- Update the list of subreddits to fetch posts from.
- Responsive design for better user experience.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/reddit-posts-viewer.git
   cd reddit-posts-viewer
   ```

2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:

   ```bash
   python app.py
   ```

4. Open your web browser and go to `http://localhost:5000` to view the application.

## Usage

- Enter a Reddit URL containing subreddits in the input field and click "Update" to load posts from those subreddits.
- Use the "Next" and "Previous" buttons or arrow keys to navigate through the posts.
- Click on post titles to view them on Reddit.

## Configuration

- The application uses a JSON file (`subreddits.json`) to store the list of subreddits. This file is updated whenever a new URL is submitted.
- Logging is configured to output debug information to the console.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - The web framework used.
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - For parsing HTML and XML documents.
- [Requests](https://docs.python-requests.org/en/latest/) - For making HTTP requests.
