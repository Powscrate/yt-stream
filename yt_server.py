from flask import Flask, request, send_file, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)
DOWNLOADS_DIR = "downloads"
COOKIES_FILE = "cookies.txt"

os.makedirs(DOWNLOADS_DIR, exist_ok=True)

@app.route('/formats', methods=['GET'])
def get_formats():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL manquante"}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'cookies': COOKIES_FILE
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            return jsonify({
                "title": info.get('title'),
                "id": info.get('id'),
                "formats": [
                    {
                        "format_id": f['format_id'],
                        "ext": f['ext'],
                        "resolution": f.get('resolution'),
                        "filesize": f.get('filesize'),
                        "format_note": f.get('format_note'),
                        "vcodec": f.get('vcodec'),
                        "acodec": f.get('acodec'),
                        "fps": f.get('fps'),
                        "audio_channels": f.get('audio_channels'),
                    }
                    for f in formats if f.get('format_id')
                ]
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    format_id = request.args.get('format_id', 'best')
    if not url:
        return jsonify({"error": "URL manquante"}), 400

    try:
        filename = f"{uuid.uuid4()}.%(ext)s"
        filepath = os.path.join(DOWNLOADS_DIR, filename)

        ydl_opts = {
            'format': format_id,
            'outtmpl': filepath,
            'merge_output_format': 'mp4',
            'cookies': COOKIES_FILE,
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            real_file = ydl.prepare_filename(info)

        return send_file(real_file, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
