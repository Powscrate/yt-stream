from flask import Flask, request, send_file, jsonify, Response
from flask_cors import CORS
import yt_dlp
import os
import uuid
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
# IMPORTANT : Activer CORS pour autoriser les requêtes depuis votre frontend
CORS(app) 

DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Lisez la valeur du cookie depuis les variables d'environnement de Render
YOUTUBE_COOKIE_CONTENT = os.environ.get('YOUTUBE_COOKIE')

def get_ydl_opts(format_id='best'):
    """Génère les options pour yt_dlp, en incluant les cookies si disponibles."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'format': format_id,
        'merge_output_format': 'mp4',
    }
    if YOUTUBE_COOKIE_CONTENT:
        # L'option 'cookiesfrombrowser' avec un tuple ('firefox', '/path/to/cookies.sqlite') serait idéale mais complexe.
        # En attendant, passer le contenu du fichier cookie est une bonne alternative.
        # NOTE : yt_dlp ne supporte pas directement le passage du *contenu* du cookie Netscape.
        # La solution la plus robuste reste d'utiliser --cookies-from-browser ou un fichier.
        # Mais pour un environnement de serveur, nous allons utiliser une astuce en l'écrivant dans un fichier temporaire.
        cookie_path = os.path.join(DOWNLOADS_DIR, 'cookies.txt')
        with open(cookie_path, 'w') as f:
            f.write(YOUTUBE_COOKIE_CONTENT)
        opts['cookies'] = cookie_path
    else:
        logging.warning("La variable d'environnement YOUTUBE_COOKIE n'est pas définie. Le téléchargement de vidéos protégées pourrait échouer.")
        
    return opts

@app.route('/formats', methods=['GET'])
def get_formats():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL manquante"}), 400

    logging.info(f"Récupération des formats pour l'URL : {url}")
    try:
        # On utilise des options sans format spécifique pour juste lister
        ydl_opts = get_ydl_opts()
        del ydl_opts['format']
        del ydl_opts['merge_output_format']
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            
            # Nettoyage du fichier cookie temporaire si créé
            cookie_path = ydl_opts.get('cookies')
            if cookie_path and os.path.exists(cookie_path):
                os.remove(cookie_path)
                
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
        logging.error(f"Erreur lors de la récupération des formats : {e}")
        # Nettoyage en cas d'erreur aussi
        cookie_path_on_error = os.path.join(DOWNLOADS_DIR, 'cookies.txt')
        if os.path.exists(cookie_path_on_error):
            os.remove(cookie_path_on_error)
        return jsonify({"error": str(e)}), 500


@app.route('/download', methods=['GET'])
def download():
    url = request.args.get('url')
    format_id = request.args.get('format_id', 'best')
    if not url:
        return jsonify({"error": "URL manquante"}), 400

    logging.info(f"Demande de téléchargement pour l'URL : {url} avec le format {format_id}")
    try:
        # Utilise un nom de fichier temporaire unique
        filename = f"{uuid.uuid4()}.%(ext)s"
        filepath_template = os.path.join(DOWNLOADS_DIR, filename)
        
        ydl_opts = get_ydl_opts(format_id)
        ydl_opts['outtmpl'] = filepath_template

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Le nom de fichier réel après le téléchargement
            real_file = ydl.prepare_filename(info)

        if not os.path.exists(real_file):
             # Nettoyage du fichier cookie temporaire si créé
            cookie_path = ydl_opts.get('cookies')
            if cookie_path and os.path.exists(cookie_path):
                os.remove(cookie_path)
            raise FileNotFoundError("Le fichier téléchargé n'a pas été trouvé.")

        # Envoyer le fichier puis le supprimer
        def generate():
            with open(real_file, 'rb') as f:
                yield from f
            
            # Nettoyage après l'envoi
            os.remove(real_file)
            cookie_path = ydl_opts.get('cookies')
            if cookie_path and os.path.exists(cookie_path):
                os.remove(cookie_path)
            logging.info(f"Fichier {real_file} envoyé et supprimé.")

        # Création du nom de fichier pour le client
        file_title = info.get('title', 'video')
        file_ext = info.get('ext', 'mp4')
        attachment_filename = f"{file_title}.{file_ext}"

        return Response(generate(), mimetype='application/octet-stream', headers={
            "Content-Disposition": f"attachment; filename=\"{attachment_filename}\""
        })

    except Exception as e:
        logging.error(f"Erreur lors du téléchargement : {e}")
        # Nettoyage en cas d'erreur
        cookie_path_on_error = os.path.join(DOWNLOADS_DIR, 'cookies.txt')
        if os.path.exists(cookie_path_on_error):
            os.remove(cookie_path_on_error)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Le port 5000 est souvent utilisé, mais vous pouvez le changer
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))