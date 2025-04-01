from flask import Flask, render_template, request, jsonify
from flask_pymongo import PyMongo
import gridfs

app = Flask(__name__)

# Set up MongoDB connection
app.config["MONGO_URI"] = "mongodb://localhost:27017/Buffer30"
mongo = PyMongo(app)

# Set up GridFS
fs = gridfs.GridFS(mongo.db)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_syllabus():
    if 'syllabus_pdf' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400  # Return an error response

    file = request.files['syllabus_pdf']
    
    if file and file.filename.endswith('.pdf'):
        fs.put(file, filename=file.filename)
        return jsonify({"success": True, "message": "File uploaded successfully!"})  # ✅ Proper response
    
    return jsonify({"success": False, "error": "Invalid file format"}), 400  # Handle incorrect file format

if __name__ == "__main__":
    app.run(debug=True)
