from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
import gridfs
import fitz
import io
from sklearn.feature_extraction.text import TfidfVectorizer  # for the extracting the keywords from the text
from googleapiclient.discovery import build # used for using the youtube api and fetching the videos from youtube
import requests
import json
import html
import urllib.parse

app = Flask(__name__)

#AIzaSyDTaXioc_E8_2jp8p3ULsAM6E7Sn8a00ms
YOUTUBE_API_KEY = "AIzaSyDTaXioc_E8_2jp8p3ULsAM6E7Sn8a00ms"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Set up MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/Buffer30"
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

# ✅ Function to fetch YouTube videos for a given keyword
def fetch_youtube_videos(query, max_results=2):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)
    
    search_response = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results
    ).execute()
    
    videos = []
    for item in search_response["items"]:
        # Extract video ID, title, and thumbnail URL
        # Check if the item is a video
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        thumbnail = item["snippet"]["thumbnails"]["default"]["url"]
        # Construct the video URL
        url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append({"title": title, "url": url,   "thumbnail": thumbnail})
    
    return videos

# ✅ Function to fetch relevant websites using DuckDuckGo
def fetch_websites_duckduckgo(query, max_results=3):
    try:
        # URL encode the query
        encoded_query = urllib.parse.quote(query)
        
        # DuckDuckGo API endpoint for JSON results
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&pretty=1"
        
        response = requests.get(url)
        data = response.json()
        
        websites = []
        
        # Add the main abstract result if available
        if data.get("AbstractURL") and data.get("AbstractText"):
            websites.append({
                "title": data.get("Heading", query),
                "url": data["AbstractURL"],
                "snippet": data["AbstractText"]
            })
        
        # Add related topics results
        related_topics = data.get("RelatedTopics", [])
        for topic in related_topics:
            if len(websites) >= max_results:
                break
                
            # Check if it's a standard topic with Text and FirstURL
            if "Text" in topic and "FirstURL" in topic:
                # Split the text to get a better title if possible
                text_parts = topic["Text"].split(" - ", 1)
                title = text_parts[0] if len(text_parts) > 1 else topic["Text"]
                snippet = text_parts[1] if len(text_parts) > 1 else topic["Text"]
                
                websites.append({
                    "title": html.unescape(title),
                    "url": topic["FirstURL"],
                    "snippet": html.unescape(snippet)
                })
            
            # Check if it's a category with nested Topics
            elif "Topics" in topic:
                for subtopic in topic["Topics"]:
                    if len(websites) >= max_results:
                        break
                    
                    if "Text" in subtopic and "FirstURL" in subtopic:
                        text_parts = subtopic["Text"].split(" - ", 1)
                        title = text_parts[0] if len(text_parts) > 1 else subtopic["Text"]
                        snippet = text_parts[1] if len(text_parts) > 1 else subtopic["Text"]
                        
                        websites.append({
                            "title": html.unescape(title),
                            "url": subtopic["FirstURL"],
                            "snippet": html.unescape(snippet)
                        })
        
        # If we still don't have enough results, add a fallback
        if not websites:
            # Create a DuckDuckGo search URL as fallback
            search_url = f"https://duckduckgo.com/?q={encoded_query}"
            websites.append({
                "title": f"Search results for: {query}",
                "url": search_url,
                "snippet": f"View DuckDuckGo search results for '{query}'"
            })
            
        return websites[:max_results]  # Ensure we return at most max_results
    
    except Exception as e:
        print(f"Error fetching websites from DuckDuckGo: {e}")
        # Fallback in case of errors
        fallback_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}"
        return [{
            "title": f"Search results for: {query}",
            "url": fallback_url,
            "snippet": f"View search results for '{query}'"
        }]

# 🔥 Function to extract top keywords from text
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
    extracted_text_doc = mongo.db.syllabus_text.find_one(sort=[("_id", -1)])
    extracted_text = extracted_text_doc["text"] if extracted_text_doc else "No text extracted yet."
    keywords = extract_keywords_tfidf(extracted_text) if extracted_text_doc else []
    return render_template('index.html', extracted_text=extracted_text, keywords=keywords)


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

        # 🔥 Fetch YouTube videos for top 3 keywords
        video_results = []
        for kw in keywords[:3]:
            video_results.extend(fetch_youtube_videos(kw))
        
        # 🌐 Fetch relevant websites for top 3 keywords using DuckDuckGo
        website_results = []
        for kw in keywords[:3]:
            website_results.extend(fetch_websites_duckduckgo(kw))
        
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
            "videos": video_results,
            "websites": website_results
        })
        

    return jsonify({"success": False, "error": "Text extraction failed"}), 500

if __name__ == "__main__":
    app.run(debug=True)