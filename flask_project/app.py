from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
import gridfs
import fitz
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from googleapiclient.discovery import build
import requests
import json
import html
import urllib.parse
import re
from collections import defaultdict
import heapq

# Import our priority queue class
from collections import defaultdict
import heapq

class ContentPriorityQueue:
    """
    A priority queue implementation to rank content based on relevance scores.
    Uses a min-heap internally but presents results in descending order of relevance.
    """
    def __init__(self):
        self.queue = []  # min heap
        self.entry_finder = {}  # mapping of items to entries
        self.counter = 0  # unique sequence count for same-priority items
        
    def add_item(self, item, priority):
        """Add a new item or update the priority of an existing item"""
        # Convert item to a hashable representation if it's a dict
        item_key = str(item) if isinstance(item, dict) else item
        
        # Lower value = higher priority in heapq, so we negate score
        # to get highest scores at the top
        if item_key in self.entry_finder:
            self.remove_item(item_key)
        count = self.counter
        entry = [-priority, count, item]  # negate priority for max-heap behavior
        self.entry_finder[item_key] = entry
        heapq.heappush(self.queue, entry)
        self.counter += 1
        
    def remove_item(self, item_key):
        """Mark an existing item as removed"""
        entry = self.entry_finder.pop(item_key)
        entry[-1] = None  # Mark as removed
        
    def pop_item(self):
        """Remove and return the highest priority item"""
        while self.queue:
            priority, count, item = heapq.heappop(self.queue)
            if item is not None:
                item_key = str(item) if isinstance(item, dict) else item
                if item_key in self.entry_finder:
                    del self.entry_finder[item_key]
                return item, -priority  # Return original (positive) priority
        raise KeyError('pop from an empty priority queue')
        
    def get_all_sorted(self):
        """Get all items sorted by priority (highest first)"""
        result = []
        temp_queue = self.queue.copy()  # Create a copy to preserve the original queue
        while temp_queue:
            try:
                priority, count, item = heapq.heappop(temp_queue)
                if item is not None:
                    result.append((item, -priority))  # Return original (positive) priority
            except KeyError:
                break
        return result

app = Flask(__name__)

YOUTUBE_API_KEY = "AIzaSyB8eAtxjQItHOp2y_UPfjFkRahhNU8TIkQ"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Set up MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/Buffer30"
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

# Function to calculate content relevance score
def calculate_relevance_score(content_text, keywords, keyword_weights=None):
    """
    Calculate a relevance score for content based on keywords.
    
    Args:
        content_text (str): The text to analyze (title + description)
        keywords (list): List of important keywords
        keyword_weights (dict, optional): Weight for each keyword
        
    Returns:
        float: Relevance score
    """
    if keyword_weights is None:
        # If no weights provided, create weights that favor more important keywords
        # Earlier keywords in the list have higher weights
        keyword_weights = {kw: 1.0/(i+1) for i, kw in enumerate(keywords)}
    
    score = 0.0
    for keyword in keywords:
        # Count occurrences of keyword in content
        # Using case-insensitive regex to match whole words
        pattern = r'\b' + re.escape(keyword) + r'\b'
        matches = re.findall(pattern, content_text, re.IGNORECASE)
        count = len(matches)
        
        # Add weighted score for this keyword
        weight = keyword_weights.get(keyword, 1.0)
        score += count * weight
    
    return score

# Enhanced function to fetch YouTube videos with relevance ranking
def fetch_youtube_videos(query, keywords, max_results=2):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)
    
    search_response = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results*2  # Fetch more than we need to allow for ranking
    ).execute()
    
    videos_pq = ContentPriorityQueue()
    
    for item in search_response["items"]:
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        description = item["snippet"].get("description", "")
        thumbnail = item["snippet"]["thumbnails"]["default"]["url"]
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Calculate relevance score based on title and description
        content_text = f"{title} {description}"
        relevance_score = calculate_relevance_score(content_text, keywords)
        
        video_data = {
            "title": title, 
            "url": url,
            "thumbnail": thumbnail,
            "relevance_score": relevance_score
        }
        
        # Add to priority queue with relevance score
        videos_pq.add_item(video_data, relevance_score)
    
    # Get the top videos based on relevance score
    top_videos = []
    for _ in range(min(max_results, len(videos_pq.queue))):
        try:
            video, score = videos_pq.pop_item()
            top_videos.append(video)
        except KeyError:
            break
    
    return top_videos

# Enhanced function to fetch websites with relevance ranking
def fetch_websites_duckduckgo(query, keywords, max_results=3):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&pretty=1"
        
        response = requests.get(url)
        data = response.json()
        
        websites_pq = ContentPriorityQueue()
        
        # Process the main abstract result
        if data.get("AbstractURL") and data.get("AbstractText"):
            title = data.get("Heading", query)
            abstract_url = data["AbstractURL"]
            abstract_text = data["AbstractText"]
            
            content_text = f"{title} {abstract_text}"
            relevance_score = calculate_relevance_score(content_text, keywords)
            
            website_data = {
                "title": title,
                "url": abstract_url,
                "snippet": abstract_text,
                "relevance_score": relevance_score
            }
            
            # Add to priority queue with relevance score
            websites_pq.add_item(website_data, relevance_score)
        
        # Process related topics
        related_topics = data.get("RelatedTopics", [])
        for topic in related_topics:
            # Process standard topics
            if "Text" in topic and "FirstURL" in topic:
                text_parts = topic["Text"].split(" - ", 1)
                title = text_parts[0] if len(text_parts) > 1 else topic["Text"]
                snippet = text_parts[1] if len(text_parts) > 1 else topic["Text"]
                
                content_text = f"{title} {snippet}"
                relevance_score = calculate_relevance_score(content_text, keywords)
                
                website_data = {
                    "title": html.unescape(title),
                    "url": topic["FirstURL"],
                    "snippet": html.unescape(snippet),
                    "relevance_score": relevance_score
                }
                
                # Add to priority queue with relevance score
                websites_pq.add_item(website_data, relevance_score)
            
            # Process topics with subtopics
            elif "Topics" in topic:
                for subtopic in topic["Topics"]:
                    if "Text" in subtopic and "FirstURL" in subtopic:
                        text_parts = subtopic["Text"].split(" - ", 1)
                        title = text_parts[0] if len(text_parts) > 1 else subtopic["Text"]
                        snippet = text_parts[1] if len(text_parts) > 1 else subtopic["Text"]
                        
                        content_text = f"{title} {snippet}"
                        relevance_score = calculate_relevance_score(content_text, keywords)
                        
                        website_data = {
                            "title": html.unescape(title),
                            "url": subtopic["FirstURL"],
                            "snippet": html.unescape(snippet),
                            "relevance_score": relevance_score
                        }
                        
                        # Add to priority queue with relevance score
                        websites_pq.add_item(website_data, relevance_score)
        
        # Fallback if no results found
        if len(websites_pq.queue) == 0:
            search_url = f"https://duckduckgo.com/?q={encoded_query}"
            website_data = {
                "title": f"Search results for: {query}",
                "url": search_url,
                "snippet": f"View DuckDuckGo search results for '{query}'",
                "relevance_score": 0.1  # Low relevance score for fallback
            }
            websites_pq.add_item(website_data, 0.1)
        
        # Get the top websites based on relevance score
        top_websites = []
        for _ in range(min(max_results, len(websites_pq.queue))):
            try:
                website, score = websites_pq.pop_item()
                top_websites.append(website)
            except KeyError:
                break
        
        return top_websites
        
    except Exception as e:
        print(f"Error fetching websites from DuckDuckGo: {e}")
        fallback_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
        return [{
            "title": f"Search results for: {query}",
            "url": fallback_url,
            "snippet": f"View search results for '{query}'",
            "relevance_score": 0.1
        }]

# Function to extract top keywords from text (unchanged)
def extract_keywords_tfidf(text, num_keywords=10):
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=100,
        token_pattern=r"\b[a-zA-Z]{2,}\b",
        ngram_range=(2, 2)  # bigrams
    )
    X = vectorizer.fit_transform([text])
    keywords = vectorizer.get_feature_names_out()
    tfidf_scores = X.toarray().flatten()
    sorted_indices = tfidf_scores.argsort()[::-1]
    top_keywords = [keywords[i] for i in sorted_indices[:num_keywords]]
    return top_keywords

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_and_extract():
    if 'syllabus_pdf' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files['syllabus_pdf']
    if not file.filename.endswith('.pdf'):
        return jsonify({"success": False, "error": "Invalid file format"}), 400

    file_id = fs.put(file, filename="syllabus.pdf")
    syllabus_binary = fs.get(file_id).read()
    pdf_stream = io.BytesIO(syllabus_binary)

    with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
        text = "\n".join(page.get_text("text") for page in doc)

    if text.strip():
        keywords = extract_keywords_tfidf(text)

        # Create keyword weights - more important keywords get higher weights
        keyword_weights = {kw: 1.0/(i+1) for i, kw in enumerate(keywords)}

        # Fetch YouTube videos for top keywords using priority queue
        video_results = []
        for kw in keywords[:5]:
            video_results.extend(fetch_youtube_videos(kw, keywords, max_results=2))
        
        # Rank all videos together using a single priority queue
        all_videos_pq = ContentPriorityQueue()
        for video in video_results:
            all_videos_pq.add_item(video, video.get("relevance_score", 0))
        
        # Get top 6 videos overall
        top_videos = []
        for _ in range(min(10, len(all_videos_pq.queue))):
            try:
                video, score = all_videos_pq.pop_item()
                top_videos.append(video)
            except KeyError:
                break
        
        # Fetch websites for top keywords using priority queue
        website_results = []
        for kw in keywords[:5]:
            website_results.extend(fetch_websites_duckduckgo(kw, keywords, max_results=3))
        
        # Rank all websites together using a single priority queue
        all_websites_pq = ContentPriorityQueue()
        for website in website_results:
            all_websites_pq.add_item(website, website.get("relevance_score", 0))
        
        # Get top 6 websites overall
        top_websites = []
        for _ in range(min(10, len(all_websites_pq.queue))):
            try:
                website, score = all_websites_pq.pop_item()
                top_websites.append(website)
            except KeyError:
                break
        
        # Save data to DB
        mongo.db.syllabus_text.insert_one({
            "text": text,
            "keywords": list(keywords)
        })
          
        return jsonify({
            "success": True,
            "message": "File uploaded and text extracted successfully!",
            "extracted_text": text,
            "keywords": list(keywords),
            "videos": top_videos,
            "websites": top_websites
        })
        
    return jsonify({"success": False, "error": "Text extraction failed"}), 500

if __name__ == "__main__":
    app.run(debug=True)