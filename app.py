import os
import requests
import zipfile
import io
import json
from flask import Flask, render_template, request, send_file, jsonify
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
YOUTUBE_API_KEY = 'YOUR_API_KEY_HERE'  # ← Replace with your actual API key

# Available thumbnail qualities
THUMBNAIL_QUALITIES = {
    'maxres': 'Maximum Resolution (1280x720)',
    'hqdefault': 'High Quality (480x360)',
    'mqdefault': 'Medium Quality (320x180)',
    'sddefault': 'Standard Definition (640x480)',
    'default': 'Default (120x90)'
}

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
    try:
        response = requests.get(api_url).json()
        items = response.get("items")
        if items:
            return items[0]["snippet"]["title"]
    except Exception as e:
        print(f"Error fetching video title: {e}")
    return "No Title Found"

def check_thumbnail_availability(video_id, quality):
    """Check if a specific thumbnail quality is available"""
    url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    response = requests.head(url)
    # YouTube returns a 404 status for non-existent thumbnails
    return response.status_code == 200

@app.route('/', methods=['GET', 'POST'])
def index():
    thumbnail_data = []
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        video_id = extract_video_id(video_url)
        if video_id:
            title = get_video_title(video_id)
            
            # Check which qualities are available for this video
            available_qualities = {}
            for quality in THUMBNAIL_QUALITIES.keys():
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
                if check_thumbnail_availability(video_id, quality):
                    available_qualities[quality] = thumbnail_url
            
            thumbnail_data.append({
                'title': title,
                'id': video_id,
                'qualities': available_qualities
            })
        else:
            thumbnail_data.append({'title': 'Invalid YouTube URL', 'id': None, 'qualities': {}})
    
    # Store recent searches in session
    recent_searches = request.cookies.get('recent_searches', '[]')
    recent_searches = json.loads(recent_searches)
    
    return render_template('index.html', 
                          thumbnails=thumbnail_data, 
                          qualities=THUMBNAIL_QUALITIES,
                          recent_searches=recent_searches[:5])

@app.route('/download/<video_id>/<quality>')
def download_thumbnail(video_id, quality):
    url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return send_file(
                io.BytesIO(response.content), 
                mimetype='image/jpeg', 
                as_attachment=True, 
                download_name=f"{video_id}_{quality}.jpg"
            )
        else:
            return "Thumbnail not available", 404
    except Exception as e:
        return f"Error downloading thumbnail: {str(e)}", 500

@app.route('/download_all', methods=['POST'])
def download_all_zip():
    video_ids = request.form.getlist('video_ids[]')
    quality = request.form.get('quality', 'maxres')
    
    if not video_ids:
        return "No thumbnails selected", 400
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for vid in video_ids:
            url = f"https://img.youtube.com/vi/{vid}/{quality}.jpg"
            try:
                img_data = requests.get(url).content
                zip_file.writestr(f"{vid}_{quality}.jpg", img_data)
            except Exception as e:
                print(f"Error adding {vid} to zip: {e}")
                continue
    
    zip_buffer.seek(0)
    return send_file(
        zip_buffer, 
        mimetype='application/zip', 
        as_attachment=True, 
        download_name=f'thumbnails_{quality}.zip'
    )

@app.route('/preview/<video_id>/<quality>')
def preview_thumbnail(video_id, quality):
    """Return JSON with thumbnail URL and title for preview modal"""
    title = get_video_title(video_id)
    url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    return jsonify({
        'url': url,
        'title': title,
        'id': video_id,
        'quality': quality,
        'quality_name': THUMBNAIL_QUALITIES.get(quality, 'Unknown Quality')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
