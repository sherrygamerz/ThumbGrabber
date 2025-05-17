from flask import Flask, render_template, request
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

def extract_video_id(url):
    """
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    """
    parsed_url = urlparse(url)

    if 'youtube' in parsed_url.netloc:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.path.startswith('/shorts/'):
            return parsed_url.path.split('/')[2]
    elif 'youtu.be' in parsed_url.netloc:
        return parsed_url.path[1:]

    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    thumbnail_url = None
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        video_id = extract_video_id(video_url)
        if video_id:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        else:
            thumbnail_url = "invalid"

    return render_template('index.html', thumbnail_url=thumbnail_url)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
