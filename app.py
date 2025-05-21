import os
import requests
import zipfile
import io
from flask import Flask, render_template, request, send_file
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
YOUTUBE_API_KEY = 'AIzaSyCQ5xO5gcQ5BT9OuRaZQnD96jso6LZ7rrw'  # ← Replace with your actual API key

def extract_video_id(url):
    parsed_url = urlparse(url)
    if 'youtube' in parsed_url.netloc:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.path.startswith('/shorts/'):
            return parsed_url.path.split('/')[2]
    elif 'youtu.be' in parsed_url.netloc:
        return parsed_url.path[1:]
    return None

def get_video_title(video_id):
    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(api_url).json()
    items = response.get("items")
    if items:
        return items[0]["snippet"]["title"]
    return "No Title Found"

@app.route('/', methods=['GET', 'POST'])
def index():
    thumbnail_data = []
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        video_id = extract_video_id(video_url)
        if video_id:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            title = get_video_title(video_id)
            thumbnail_data.append({
                'url': thumbnail_url,
                'title': title,
                'id': video_id
            })
        else:
            thumbnail_data.append({'url': None, 'title': 'Invalid YouTube URL', 'id': None})
    return render_template('index.html', thumbnails=thumbnail_data)

@app.route('/download/<video_id>')
def download_thumbnail(video_id):
    url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    response = requests.get(url)
    return send_file(io.BytesIO(response.content), mimetype='image/jpeg', as_attachment=True, download_name=f"{video_id}.jpg")

@app.route('/download_all', methods=['POST'])
def download_all_zip():
    video_ids = request.form.getlist('video_ids[]')
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for vid in video_ids:
            url = f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"
            img_data = requests.get(url).content
            zip_file.writestr(f"{vid}.jpg", img_data)
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='thumbnails.zip')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
