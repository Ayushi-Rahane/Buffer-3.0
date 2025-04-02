from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
import gridfs
import fitz
import io

app = Flask(__name__)

# Set up MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/Buffer30"
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

@app.route('/')
def index():
    extracted_text_doc = mongo.db.syllabus_text.find_one(sort=[("_id", -1)])  # Get latest text
    extracted_text = extracted_text_doc["text"] if extracted_text_doc else "No text extracted yet."
    return render_template('index.html', extracted_text=extracted_text)

@app.route('/upload', methods=['POST'])
def upload_and_extract():
    """Uploads a PDF and extracts text immediately."""
    
    # ✅ 1️⃣ Check if a file was uploaded
    if 'syllabus_pdf' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files['syllabus_pdf']

    # ✅ 2️⃣ Check if the file is a valid PDF
    if not file.filename.endswith('.pdf'):
        return jsonify({"success": False, "error": "Invalid file format"}), 400

    # ✅ 3️⃣ Save the PDF to GridFS
    file_id = fs.put(file, filename="syllabus.pdf")

    # ✅ 4️⃣ Retrieve the file for extraction
    syllabus_binary = fs.get(file_id).read()
    pdf_stream = io.BytesIO(syllabus_binary)  # Convert bytes to file-like object

    # ✅ 5️⃣ Extract text using PyMuPDF
    with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
        text = "\n".join(page.get_text("text") for page in doc)
   
    # ✅ 6️⃣ Store extracted text in MongoDB
    if text.strip():  # Only save if text is not empty
        mongo.db.syllabus_text.insert_one({"text": text})
        return jsonify({"success": True, "message": "File uploaded and text extracted successfully!", "extracted_text": text})
    
    return jsonify({"success": False, "error": "Text extraction failed"}), 500

if __name__ == "__main__":
    app.run(debug=True)
