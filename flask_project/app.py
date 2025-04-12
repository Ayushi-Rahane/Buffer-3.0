from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
import gridfs
import fitz
import io
from sklearn.feature_extraction.text import TfidfVectorizer  # for the extracting the keywords from the text
from googleapiclient.discovery import build # used for using the youtube api and fetching the videos from youtube
import requests
app = Flask(__name__)

#AIzaSyDTaXioc_E8_2jp8p3ULsAM6E7Sn8a00ms
YOUTUBE_API_KEY = "AIzaSyDTaXioc_E8_2jp8p3ULsAM6E7Sn8a00ms"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

RAPIDAPI_KEY = "4de2a67504mshbead1d7f14f4773p15b0ddjsn825b5608a30b"
# Set up MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/Buffer30"
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

#Fetches the websites
def fetch_related_websites(query, max_results=5):
    url = "https://bing-web-search1.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "bing-web-search1.p.rapidapi.com"
    }
    params = {"q": query, "count": max_results, "textFormat": "Raw", "safeSearch": "Moderate"}

    response = requests.get(url, headers=headers, params=params)
    results = []

    if response.status_code == 200:
        data = response.json()
        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "name": item["name"],
                "url": item["url"]
            })
    return results

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

        # 🔥 Fetch YouTube videos for top 3 keywords (you can tweak this)
        video_results = []
        for kw in keywords[:3]:
            video_results.extend(fetch_youtube_videos(kw))
        
        # Fetch related websites for the first keyword (you can tweak this)
        website_results = []
        if keywords:
            for keyword in keywords[:2]:
                website_results.extend(fetch_related_websites(keyword))
        
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