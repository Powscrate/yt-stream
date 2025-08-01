from flask import Flask, request, send_file, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)

@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL manquante"}), 400

    try:
        # Crée un fichier temporaire
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join("downloads", filename)
        os.makedirs("downloads", exist_ok=True)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': filepath,
            'merge_output_format': 'mp4',
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        return jsonify({ "error": str(e) }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
