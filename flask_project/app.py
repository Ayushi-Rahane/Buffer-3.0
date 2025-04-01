from flask import Flask, render_template,request, redirect
from flask_pymongo import PyMongo
import gridfs
import io

app = Flask(__name__)
# Set up MongoDB connection

app.config["MONGO_URI"] = "mongodb://localhost:27017/myDatabase"
mongo = PyMongo(app)

# Set up GridFS
fs = gridfs.GridFS(mongo)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_syllabus():
    if 'syllabus_pdf' in request.files:
        file = request.files['syllabus_pdf']
        if file and file.filename.endswith('.pdf'):
            # Save the file to GridFS
            fs.put(file, filename=file.filename)
            return "File uploaded successfully"



if __name__ == "__main__":
    app.run(debug=True)
