import os
import requests
import zipfile
import io
from flask import Flask, render_template, request, send_file, redirect, url_for
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

def check_thumbnail_availability(video_id):
    # List of thumbnail qualities to try
    qualities = [
        {"quality": "maxresdefault", "label": "HD"},
        {"quality": "sddefault", "label": "SD"},
        {"quality": "hqdefault", "label": "HQ"},
        {"quality": "mqdefault", "label": "MQ"},
        {"quality": "default", "label": "Low"}
    ]
    
    available_thumbnails = []
    
    for quality in qualities:
        url = f"https://img.youtube.com/vi/{video_id}/{quality['quality']}.jpg"
        response = requests.head(url)
        if response.status_code == 200 and int(response.headers.get('content-length', 0)) > 1000:
            available_thumbnails.append({
                "url": url,
                "quality": quality["quality"],
                "label": quality["label"]
            })
    
    # Return the best available quality or None if none are available
    return available_thumbnails[0] if available_thumbnails else None

@app.route('/', methods=['GET', 'POST'])
def index():
    thumbnail_data = []
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        video_id = extract_video_id(video_url)
        if video_id:
            title = get_video_title(video_id)
            thumbnail = check_thumbnail_availability(video_id)
            
            if thumbnail:
                thumbnail_data.append({
                    'url': thumbnail["url"],
                    'title': title,
                    'id': video_id,
                    'quality': thumbnail["quality"],
                    'label': thumbnail["label"]
                })
            else:
                thumbnail_data.append({
                    'url': None,
                    'title': f"No thumbnail available for: {title}",
                    'id': video_id
                })
        else:
            thumbnail_data.append({'url': None, 'title': 'Invalid YouTube URL', 'id': None})
    return render_template('index.html', thumbnails=thumbnail_data)

@app.route('/download/<video_id>/<quality>')
def download_thumbnail(video_id, quality="maxresdefault"):
    url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    response = requests.get(url)
    if response.status_code == 200:
        return send_file(io.BytesIO(response.content), mimetype='image/jpeg', as_attachment=True, download_name=f"{video_id}_{quality}.jpg")
    else:
        return redirect(url_for('index'))

@app.route('/download_all', methods=['POST'])
def download_all_zip():
    video_ids = request.form.getlist('video_ids[]')
    qualities = request.form.getlist('qualities[]')
    
    if not video_ids or len(video_ids) != len(qualities):
        return redirect(url_for('index'))
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for i, vid in enumerate(video_ids):
            quality = qualities[i]
            url = f"https://img.youtube.com/vi/{vid}/{quality}.jpg"
            response = requests.get(url)
            if response.status_code == 200:
                zip_file.writestr(f"{vid}_{quality}.jpg", response.content)
    
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='thumbnails.zip')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
