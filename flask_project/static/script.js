function UploadFile(event){
    event.preventDefault(); // Prevent the default form submission behavior

    const fileInput = document.getElementById('syllabus_pdf'); // Get the file input element
    const file = fileInput.files[0]; // Get the selected file

    if (!file) {
        alert("Please select a file to upload.");
        return;
    }

    const formData = new FormData();
    formData.append('syllabus_pdf', file); // Append the file to the FormData object

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert("File uploaded successfully!");
        } else {
            alert("File upload failed: " + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("An error occurred while uploading the file.");
    });
}

const uploadForm = document.getElementById('uploadForm');
const videoList = document.getElementById('videoResults');
const websiteList = document.getElementById('websiteResults');
const loadingIndicator = document.getElementById('loading');
const outputContainer = document.getElementById('output-container');

uploadForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const formData = new FormData(uploadForm);
    
    // Show loading indicator
    loadingIndicator.style.display = 'block';
    
    // Hide output container while loading
    outputContainer.style.display = 'none';
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        // Hide loading indicator
        loadingIndicator.style.display = 'none';
        
        if (data.success) {
            // Show output container now that we have data
            outputContainer.style.display = 'block';
            
            // Show videos
            videoList.innerHTML = '';
            data.videos.forEach(video => {
                const li = document.createElement('li');
                li.style.display = "flex";
                li.style.alignItems = "center";

                const img = document.createElement('img');
                img.src = video.thumbnail;
                img.alt = video.title;
                img.style.width = "120px";
                img.style.marginRight = "10px";
                img.style.borderRadius = "8px";

                const contentDiv = document.createElement('div');
                contentDiv.style.flex = "1";

                const titleLink = document.createElement('a');
                titleLink.href = video.url;
                titleLink.textContent = video.title;
                titleLink.target = "_blank";
                titleLink.style.fontWeight = "bold";
                titleLink.style.color = "#000";
                titleLink.style.textDecoration = "none";
                titleLink.style.display = "block";
                titleLink.style.marginBottom = "5px";

                // Add relevance score badge
                const scoreSpan = document.createElement('span');
                scoreSpan.textContent = `Relevance: ${video.relevance_score.toFixed(2)}`;
                scoreSpan.style.fontSize = "12px";
                scoreSpan.style.background = "#e9f5ff";
                scoreSpan.style.padding = "2px 6px";
                scoreSpan.style.borderRadius = "10px";
                scoreSpan.style.color = "#0066cc";

                contentDiv.appendChild(titleLink);
                contentDiv.appendChild(scoreSpan);

                li.appendChild(img);
                li.appendChild(contentDiv);
                videoList.appendChild(li);
            });
            
            // Show websites
            websiteList.innerHTML = '';
            if (data.websites && data.websites.length > 0) {
                data.websites.forEach(website => {
                    const websiteDiv = document.createElement('div');
                    websiteDiv.className = 'website-item';
                    
                    const titleElement = document.createElement('h3');
                    titleElement.className = 'website-title';
                    
                    const linkElement = document.createElement('a');
                    linkElement.href = website.url;
                    linkElement.textContent = website.title;
                    linkElement.target = "_blank";
                    
                    titleElement.appendChild(linkElement);
                    
                    const snippetElement = document.createElement('p');
                    snippetElement.className = 'website-snippet';
                    snippetElement.textContent = website.snippet;
                    
                    // Add relevance score badge
                    const scoreSpan = document.createElement('span');
                    scoreSpan.textContent = `Relevance: ${website.relevance_score.toFixed(2)}`;
                    scoreSpan.style.fontSize = "12px";
                    scoreSpan.style.background = "#e9f5ff";
                    scoreSpan.style.padding = "2px 6px";
                    scoreSpan.style.borderRadius = "10px";
                    scoreSpan.style.color = "#0066cc";
                    scoreSpan.style.marginLeft = "10px";
                    
                    const urlElement = document.createElement('p');
                    urlElement.className = 'website-url';
                    urlElement.textContent = website.url;
                    
                    websiteDiv.appendChild(titleElement);
                    websiteDiv.appendChild(snippetElement);
                    websiteDiv.appendChild(scoreSpan);
                    websiteDiv.appendChild(urlElement);
                    
                    websiteList.appendChild(websiteDiv);
                });
            } else {
                websiteList.innerHTML = '<p>No relevant websites found.</p>';
            }
        } else if (data.error) {
            alert("Error: " + data.error);
        }
    } catch (err) {
        // Hide loading indicator on error
        loadingIndicator.style.display = 'none';
        
        console.error("Upload error:", err);
        alert("Something went wrong.");
    }
});


document.getElementById("syllabus_pdf").addEventListener("change", function () {
  const fileName = this.files[0]?.name || "No file selected";
  document.getElementById("file-name").textContent = fileName;
});

// Optional: make the entire area clickable
document.getElementById("uploadArea").addEventListener("click", () => {
  document.getElementById("syllabus_pdf").click();
});

const uploadArea = document.getElementById("uploadArea");
const fileInput = document.getElementById("syllabus_pdf");

["dragenter", "dragover"].forEach(eventName => {
  uploadArea.addEventListener(eventName, e => {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.add("dragover");
  });
});

["dragleave", "drop"].forEach(eventName => {
  uploadArea.addEventListener(eventName, e => {
    e.preventDefault();
    e.stopPropagation();
    uploadArea.classList.remove("dragover");
  });
});

uploadArea.addEventListener("drop", e => {
  const files = e.dataTransfer.files;
  if (files.length > 0 && files[0].type === "application/pdf") {
    fileInput.files = files; // Assign to hidden input
    document.getElementById("file-name").textContent = files[0].name;
  } else {
    alert("Please upload a valid PDF file.");
  }
});