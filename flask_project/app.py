from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
import gridfs
import fitz
import io
from sklearn.feature_extraction.text import TfidfVectorizer  # 🔥 NEW import

app = Flask(__name__)

# Set up MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/Buffer30"
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

# 🔥 Function to extract top keywords from text
def extract_keywords_tfidf(text, num_keywords=10):
    vectorizer = TfidfVectorizer(stop_words="english", max_features=100)
    X = vectorizer.fit_transform([text])
    keywords = vectorizer.get_feature_names_out()
    return keywords[:num_keywords]


@app.route('/')
def index():
    extracted_text_doc = mongo.db.syllabus_text.find_one(sort=[("_id", -1)])
    extracted_text = extracted_text_doc["text"] if extracted_text_doc else "No text extracted yet."

    keywords = extract_keywords_tfidf(extracted_text) if extracted_text_doc else []

    return render_template('index.html', extracted_text=extracted_text, keywords=keywords)


@app.route('/upload', methods=['POST'])
def upload_and_extract():
    """Uploads a PDF and extracts text and keywords."""
    
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
        # ✅ Extract keywords
        keywords = extract_keywords_tfidf(text)

        # ✅ Save both text and keywords to MongoDB
        mongo.db.syllabus_text.insert_one({
            "text": text,
            "keywords": list(keywords)
        })

        return jsonify({
            "success": True,
            "message": "File uploaded and text extracted successfully!",
            "extracted_text": text,
            "keywords": list(keywords)
        })
    
    return jsonify({"success": False, "error": "Text extraction failed"}), 500


if __name__ == "__main__":
    app.run(debug=True)
