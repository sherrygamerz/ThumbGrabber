from flask import Flask, render_template, request, send_file
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        # Placeholder: You'll add YouTube thumbnail extraction here later
        return render_template('index.html', thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg")

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
