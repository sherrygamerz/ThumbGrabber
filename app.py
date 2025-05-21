import os
import requests
import zipfile
import io
import re
from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)
YOUTUBE_API_KEY = 'AIzaSyCQ5xO5gcQ5BT9OuRaZQnD96jso6LZ7rrw'  # ← Replace with your actual API key

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    if not url:
        return None
        
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
    """Get the title of a YouTube video using the YouTube API."""
    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(api_url).json()
    items = response.get("items")
    if items:
        return items[0]["snippet"]["title"]
    return "No Title Found"

def get_video_duration(video_id):
    """Get the duration of a YouTube video in seconds."""
    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(api_url).json()
    items = response.get("items")
    if items:
        duration = items[0]["contentDetails"]["duration"]
        # Convert ISO 8601 duration to seconds
        duration_regex = re.compile(r'PT((\d+)H)?((\d+)M)?((\d+)S)?')
        matches = duration_regex.match(duration)
        if matches:
            hours = int(matches.group(2) or 0)
            minutes = int(matches.group(4) or 0)
            seconds = int(matches.group(6) or 0)
            return hours * 3600 + minutes * 60 + seconds
    return 0

def get_all_thumbnails(video_id):
    """Get all available thumbnails for a YouTube video."""
    thumbnails = []
    
    # Standard thumbnail qualities
    standard_qualities = [
        {"quality": "maxresdefault", "label": "HD (1280x720)"},
        {"quality": "sddefault", "label": "SD (640x480)"},
        {"quality": "hqdefault", "label": "HQ (480x360)"},
        {"quality": "mqdefault", "label": "MQ (320x180)"},
        {"quality": "default", "label": "Default (120x90)"}
    ]
    
    # Check which standard thumbnails are available
    for quality in standard_qualities:
        url = f"https://img.youtube.com/vi/{video_id}/{quality['quality']}.jpg"
        response = requests.head(url)
        if response.status_code == 200 and int(response.headers.get('content-length', 0)) > 1000:
            thumbnails.append({
                "url": url,
                "quality": quality["quality"],
                "label": quality["label"],
                "type": "standard"
            })
    
    # Frame thumbnails (0.jpg, 1.jpg, 2.jpg, 3.jpg)
    for i in range(4):
        url = f"https://img.youtube.com/vi/{video_id}/{i}.jpg"
        response = requests.head(url)
        if response.status_code == 200 and int(response.headers.get('content-length', 0)) > 1000:
            position = "Default" if i == 0 else f"{i * 25}% through video"
            thumbnails.append({
                "url": url,
                "position": position,
                "index": i,
                "type": "frame"
            })
    
    return thumbnails

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main route for the thumbnail downloader."""
    thumbnail_data = []
    if request.method == 'POST':
        video_urls = request.form.get('video_url', '').strip().split('\n')
        
        for video_url in video_urls:
            video_url = video_url.strip()
            if not video_url:
                continue
                
            video_id = extract_video_id(video_url)
            if video_id:
                title = get_video_title(video_id)
                thumbnails = get_all_thumbnails(video_id)
                duration = get_video_duration(video_id)
                
                if thumbnails:
                    # Group thumbnails by type
                    standard_thumbnails = [t for t in thumbnails if t.get("type") == "standard"]
                    frame_thumbnails = [t for t in thumbnails if t.get("type") == "frame"]
                    
                    # Find best quality for main display
                    main_thumbnail = next((t for t in standard_thumbnails if t["quality"] == "maxresdefault"), 
                                         next((t for t in standard_thumbnails), None))
                    
                    if main_thumbnail:
                        thumbnail_data.append({
                            'url': main_thumbnail["url"],
                            'title': title,
                            'id': video_id,
                            'quality': main_thumbnail["quality"],
                            'label': main_thumbnail["label"],
                            'duration': duration,
                            'standard_thumbnails': standard_thumbnails,
                            'frame_thumbnails': frame_thumbnails
                        })
                    else:
                        thumbnail_data.append({
                            'url': None,
                            'title': f"No thumbnail available for: {title}",
                            'id': video_id,
                            'duration': duration
                        })
                else:
                    thumbnail_data.append({
                        'url': None,
                        'title': f"No thumbnail available for: {title}",
                        'id': video_id,
                        'duration': duration
                    })
            else:
                if video_url:  # Only add error for non-empty URLs
                    thumbnail_data.append({'url': None, 'title': f'Invalid YouTube URL: {video_url}', 'id': None})
    
    return render_template('index.html', thumbnails=thumbnail_data)

@app.route('/download/<video_id>/<quality>')
def download_thumbnail(video_id, quality="maxresdefault"):
    """Download a specific thumbnail quality."""
    url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    response = requests.get(url)
    if response.status_code == 200:
        return send_file(io.BytesIO(response.content), mimetype='image/jpeg', as_attachment=True, download_name=f"{video_id}_{quality}.jpg")
    else:
        return redirect(url_for('index'))

@app.route('/download_all', methods=['POST'])
def download_all_zip():
    """Download multiple thumbnails as a zip file."""
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

@app.route('/extract-frame/<video_id>', methods=['GET'])
def extract_frame_page(video_id):
    """Page for extracting frames from a video."""
    title = get_video_title(video_id)
    duration = get_video_duration(video_id)
    return render_template('extract_frame_simple.html', video_id=video_id, title=title, duration=duration)

@app.route('/api/video-frames/<video_id>', methods=['GET'])
def get_video_frames(video_id):
    """API endpoint to get all available frames for a video."""
    try:
        frames = []
        
        # Standard thumbnails (0.jpg, 1.jpg, 2.jpg, 3.jpg)
        for i in range(4):
            frame_url = f"https://img.youtube.com/vi/{video_id}/{i}.jpg"
            response = requests.head(frame_url)
            if response.status_code == 200 and int(response.headers.get('content-length', 0)) > 1000:
                position = "Default" if i == 0 else f"{i * 25}% through video"
                frames.append({
                    "url": frame_url,
                    "position": position,
                    "index": i
                })
        
        # Add different quality versions of the default thumbnail
        qualities = [
            {"quality": "maxresdefault", "label": "Maximum Resolution"},
            {"quality": "sddefault", "label": "Standard Definition"},
            {"quality": "hqdefault", "label": "High Quality"},
            {"quality": "mqdefault", "label": "Medium Quality"},
            {"quality": "default", "label": "Default Quality"}
        ]
        
        for quality in qualities:
            frame_url = f"https://img.youtube.com/vi/{video_id}/{quality['quality']}.jpg"
            response = requests.head(frame_url)
            if response.status_code == 200 and int(response.headers.get('content-length', 0)) > 1000:
                frames.append({
                    "url": frame_url,
                    "position": f"Default ({quality['label']})",
                    "quality": quality['quality'],
                    "index": 100  # Group these together
                })
        
        return jsonify({"frames": frames})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
