from bs4 import BeautifulSoup
import requests
import concurrent.futures
import time
import json
from concurrent.futures import ThreadPoolExecutor

# Belirtilen subredditten "hot" gönderileri çekme
def get_hot_posts(subreddit, limit=10):
    url = f"https://old.reddit.com/r/{subreddit}/hot/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Error fetching r/{subreddit}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        posts = soup.find_all("div", {"class": "thing"}, limit=limit)
        result = []

        for post in posts:
            try:
                title = post.find("a", {"class": "title"}).text
                score = post.find("div", {"class": "score unvoted"}).text
                link = post.get("data-url")
                permalink = post.get("data-permalink")
                
                full_link = f"https://reddit.com{permalink}" if permalink else link
                
                result.append({
                    "title": title,
                    "score": score,
                    "link": full_link,
                    "subreddit": subreddit
                })
            except (AttributeError, TypeError) as e:
                print(f"Error parsing post in r/{subreddit}: {e}")
                continue

        return result
    except requests.exceptions.RequestException as e:
        print(f"Error fetching r/{subreddit}: {e}")
        return []

def get_subreddits_from_url(url):
    # Extract subreddits from the URL
    # Remove 'https://old.reddit.com/r/' from the start
    subreddits_part = url.split('/r/')[-1].strip('/')
    # Split by '+' to get individual subreddits
    subreddits = subreddits_part.split('+')
    # Remove any empty strings and user mentions
    subreddits = [s for s in subreddits if s and not s.startswith('u_')]
    return subreddits

def process_subreddit(subreddit):
    time.sleep(0.5)  # Add small delay between requests
    print(f"Processing r/{subreddit}...")
    return get_hot_posts(subreddit, limit=1)

def get_first_non_sticky_post(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        for post in data['data']['children']:
            if not post['data']['stickied']:
                return {
                    'title': post['data']['title'],
                    'url': f"https://www.reddit.com{post['data']['permalink']}",
                    'score': str(post['data']['score']),
                    'subreddit': subreddit
                }
                
    except Exception as e:
        print(f"Error fetching {subreddit}: {e}")
        return None

def get_all_posts():
    # Subreddit listesi
    subreddits = [
        "AskCulinary", "ArtificialInteligence", "ChatGPTCoding", "ClaudeAI",
        "ChatGPTPromptGenius", "ChatGPT", "AJelqForYou", "CodingTR", "Documentaries",
        "Cooking", "Dryeyes", "EnglishLearning", "FREEMEDIAHECKYEAH", "GetMotivated",
        "HENRYfinance", "Hyperhidrosis", "ITCareerQuestions", "MovieSuggestions",
        "MuslumanTurkiye", "OpenAI", "OutOfTheLoop", "Piracy", "ProgrammerHumor",
        "Psikoloji", "SebDerm", "SideProject", "SkincareAddiction", "StresOdasi",
        "TopSecretRecipes", "Turkce", "Turkey", "WorldPanorama", "Yatirim",
        "androidapps", "announcements", "applesucks", "biology", "bloodydisgusting",
        "booksuggestions", "changemyview", "codingbootcamp", "compsci",
        "computerscience", "computersciencehub", "coolguides", "csMajors",
        "cscareerquestions", "cscareerquestionsEU", "cursor", "dessert",
        "etymology", "felsefe", "financialindependence", "fitbod", "food",
        "gamingsuggestions", "grammar", "horror", "intiharetme", "investing",
        "learnprogramming", "malefashionadvice", "musicsuggestions", "origami",
        "passive_income", "poorlydrawnlines", "printSF", "puzzles",
        "puzzlevideogames", "science", "secilmiskitap", "soccer",
        "suggestmeabook", "televisionsuggestions", "tipofmyjoystick", "trackers"
    ]

    all_posts = []
    
    # ThreadPoolExecutor kullanarak paralel istek at
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_first_non_sticky_post, subreddits)
        
        for post in results:
            if post:
                all_posts.append(post)
    
    # Score'a göre sırala
    all_posts.sort(key=lambda x: parse_score(x.get('score', '0')), reverse=True)
    return all_posts

def parse_score(score_str):
    try:
        if not score_str or score_str == '•':
            return 0
        if 'k' in score_str.lower():
            num = float(score_str.lower().replace('k', ''))
            return int(num * 1000)
        return int(score_str)
    except (ValueError, TypeError):
        return 0

# Ana işlem
def main():
    url = "https://old.reddit.com/r/AJelqForYou+ArtificialInteligence+AskCulinary+ChatGPT+ChatGPTCoding+ChatGPTPromptGenius+ClaudeAI+CodingTR+Cooking+Documentaries+Dryeyes+EnglishLearning+FREEMEDIAHECKYEAH+GetMotivated+HENRYfinance+Hyperhidrosis+ITCareerQuestions+MovieSuggestions+MuslumanTurkiye+OpenAI+OutOfTheLoop+Piracy+ProgrammerHumor+Psikoloji+SebDerm+SideProject+SkincareAddiction+StresOdasi+TopSecretRecipes+Turkce+Turkey+WorldPanorama+Yatirim+androidapps+announcements+applesucks+biology+bloodydisgusting+booksuggestions+changemyview+codingbootcamp+compsci+computerscience+computersciencehub+coolguides+csMajors+cscareerquestions+cscareerquestionsEU+cursor+dessert+etymology+felsefe+financialindependence+fitbod+food+gamingsuggestions+grammar+horror+intiharetme+investing+learnprogramming+malefashionadvice+musicsuggestions+origami+passive_income+poorlydrawnlines+printSF+puzzles+puzzlevideogames+science+secilmiskitap+soccer+suggestmeabook+televisionsuggestions+tipofmyjoystick+trackers+u_PCEngTr+u_Royal_Toad/"
    
    print("Extracting subreddits from URL...")
    subreddits = get_subreddits_from_url(url)
    
    print(f"Found {len(subreddits)} subreddits")
    print("Fetching hot posts...")
    
    start_time = time.time()
    all_posts = []
    
    # Use ThreadPoolExecutor for concurrent processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks and get futures
        future_to_subreddit = {executor.submit(process_subreddit, subreddit): subreddit 
                             for subreddit in subreddits}
        
        # Process completed futures as they come in
        for future in concurrent.futures.as_completed(future_to_subreddit):
            posts = future.result()
            all_posts.extend(posts)

    end_time = time.time()
    
    # Print results
    print(f"\nFetched {len(all_posts)} posts in {end_time - start_time:.2f} seconds")
    if not all_posts:
        print("No posts were fetched. This might be due to rate limiting or parsing errors.")
        return
        
    print("\nTop posts from each subreddit:")
    # Sort posts by score for better presentation
    all_posts.sort(key=lambda x: parse_score(x.get('score', '0')), reverse=True)
    
    for post in all_posts:
        print(f"\nSubreddit: r/{post['subreddit']}")
        print(f"Title: {post['title']}")
        print(f"Score: {post['score']}")
        print(f"URL: {post['link']}")
        print("-" * 80)

if __name__ == "__main__":
    main()
