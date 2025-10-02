import requests
import re
import os

# API endpoint to get all files in the dataset
api_endpoint = (
    "https://clowder.edap-cluster.com/api/datasets/61147fefe4b0856fdc65639b/files"
)

# Make the API request
response = requests.get(api_endpoint)
if response.status_code != 200:
    print("Failed to retrieve files")
    exit()

# Extract file information
files = response.json()

# Regex pattern to match toxrefdb...sql files
pattern = r"toxrefdb.*\.dump"

# Filter for SQL files
sql_files = [x for x in files if re.match(pattern, x.get("filename"))]

# Check if SQL files were found
if len(sql_files) == 0:
    raise Exception("No SQL files found")

if len(sql_files) > 1:
    raise Exception("Multiple SQL files found")

# Get the ID of the SQL file
sql_file_id = sql_files[0].get("id")
file_url = f"https://clowder.edap-cluster.com/api/files/{sql_file_id}"

# Directory to save the file
download_dir = "download"
os.makedirs(download_dir, exist_ok=True)

# Path to save the file
download_path = os.path.join(download_dir, "toxrefdb.dump")

# Stream the download
with requests.get(file_url, stream=True) as r:
    r.raise_for_status()
    with open(download_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded: {download_path}")

print("Download process completed.")
