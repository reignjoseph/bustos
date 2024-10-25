import requests
import json
import os

# Relative path of the resume PDF file to parse
resume_path = "static/images/jobseeker-uploads/CV.pdf"

# API endpoint for resume parsing
url = "https://api.apilayer.com/resume_parser/url?url="

# Prepare the request headers
headers = {
    "apikey": "sRD97QBwFuA6Z8oXkfGd8fbOZbeOkHu0"
}

# Use the base URL to construct the full URL dynamically
base_url = "https://672f0qdk-0fbmnoqs-zqnmrxojxoy8.ac2-preview.marscode.dev/"  # Replace with your actual domain
resume_url = f"{base_url}{resume_path}"

# Send the GET request
response = requests.get(url + resume_url, headers=headers)

# Check the response status and process the result
status_code = response.status_code
if status_code == 200:
    # Parse the JSON response
    parsed_data = response.json()
    print("Response:", parsed_data)

    # Extract the name of the uploaded resume (without extension)
    resume_name = os.path.splitext(os.path.basename(resume_path))[0]

    # Ensure the directory exists
    dump_dir = "static/dumps"
    os.makedirs(dump_dir, exist_ok=True)

    # Save the extracted data to a JSON file named after the uploaded resume
    dump_file_path = os.path.join(dump_dir, f'{resume_name}.json')
    with open(dump_file_path, 'w') as json_file:
        json.dump(parsed_data, json_file, indent=4)
    
    print(f"Data saved to {dump_file_path}")

else:
    print(f"Failed to parse resume: {status_code} - {response.text}")
