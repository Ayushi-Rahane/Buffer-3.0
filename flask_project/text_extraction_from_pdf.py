import fitz

file = fitz.open("syllabus.pdf")

# Extract text from each page
text="";
for page_num in range(len(file)):
    page = file[page_num]
    text += page.get_text("text") + "\n"  # Extract text from the page

print(text);
# Close the document
file.close()