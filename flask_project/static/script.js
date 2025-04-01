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