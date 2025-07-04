from flask import Flask, request, jsonify, render_template, send_file
import yt_dlp
import os
import tempfile
import re
import threading
import time
from datetime import datetime
import shutil

app = Flask(__name__)

# Global variables to store download progress
downloads = {}

class DownloadProgress:
    def __init__(self):
        self.status = "pending"
        self.progress = 0
        self.filename = ""
        self.error = None

def progress_hook(d):
    """Hook function to track download progress"""
    # Use a global variable to track current download ID
    global current_download_id
    download_id = getattr(progress_hook, 'current_id', 'unknown')
    
    if download_id in downloads:
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                downloads[download_id].progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            elif '_percent_str' in d:
                # Extract percentage from string
                percent_str = d['_percent_str'].strip('%')
                try:
                    downloads[download_id].progress = float(percent_str)
                except:
                    pass
            downloads[download_id].status = "downloading"
        elif d['status'] == 'finished':
            downloads[download_id].status = "completed"
            downloads[download_id].progress = 100
            downloads[download_id].filename = os.path.basename(d['filename'])

def sanitize_filename(filename):
    """Sanitize filename to remove invalid characters"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    return filename

def format_duration(seconds):
    """Convert seconds to HH:MM:SS format"""
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/video-info', methods=['POST'])
def get_video_info():
    """Extract video information without downloading"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Validate YouTube URL
        youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        if not re.match(youtube_regex, url):
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        # Configure yt-dlp options for info extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info
            info = ydl.extract_info(url, download=False)
            
            # Get available formats
            formats = info.get('formats', [])
            video_formats = []
            audio_formats = []
            
            # Process video formats
            seen_resolutions = set()
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('acodec') != 'none':
                    # Video with audio
                    height = fmt.get('height')
                    if height and height in [360, 480, 720, 1080]:
                        resolution = f"{height}p"
                        if resolution not in seen_resolutions:
                            video_formats.append({
                                'format_id': fmt['format_id'],
                                'resolution': resolution,
                                'ext': fmt.get('ext', 'mp4'),
                                'filesize': fmt.get('filesize')
                            })
                            seen_resolutions.add(resolution)
                elif fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                    # Audio only
                    if len(audio_formats) < 3:  # Limit to 3 audio formats
                        audio_formats.append({
                            'format_id': fmt['format_id'],
                            'ext': fmt.get('ext', 'mp3'),
                            'filesize': fmt.get('filesize')
                        })
            
            # Sort video formats by resolution
            video_formats.sort(key=lambda x: int(x['resolution'][:-1]))
            
            # Get thumbnail
            thumbnail = info.get('thumbnail', '')
            if not thumbnail and 'thumbnails' in info:
                thumbnails = info['thumbnails']
                if thumbnails:
                    thumbnail = thumbnails[-1]['url']  # Get highest quality thumbnail
            
            video_info = {
                'title': info.get('title', 'Unknown Title'),
                'duration': format_duration(info.get('duration')),
                'thumbnail': thumbnail,
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'video_id': info.get('id', ''),
                'video_formats': video_formats,
                'audio_formats': audio_formats
            }
            
            return jsonify(video_info)
            
    except Exception as e:
        return jsonify({'error': f'Failed to extract video info: {str(e)}'}), 500

@app.route('/download', methods=['POST'])
def download_video():
    """Download video/audio in specified format"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        format_type = data.get('format_type', 'video')  # 'video' or 'audio'
        resolution = data.get('resolution', '720p')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Create downloads directory if it doesn't exist
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Generate unique download ID
        download_id = f"{int(time.time())}_{hash(url) % 10000}"
        
        # Initialize download progress
        downloads[download_id] = DownloadProgress()
        
        def download_thread():
            try:
                # Set the current download ID for progress hook
                progress_hook.current_id = download_id
                
                # Configure yt-dlp options
                if format_type == 'audio':
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
                        'progress_hooks': [progress_hook],
                        'quiet': True,
                        'no_warnings': True,
                    }
                else:
                    # Video format
                    resolution_map = {
                        '360p': 'best[height<=360]',
                        '480p': 'best[height<=480]',
                        '720p': 'best[height<=720]',
                        '1080p': 'best[height<=1080]'
                    }
                    
                    format_selector = resolution_map.get(resolution, 'best[height<=720]')
                    
                    ydl_opts = {
                        'format': f'{format_selector}/best',
                        'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
                        'progress_hooks': [progress_hook],
                        'quiet': True,
                        'no_warnings': True,
                    }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Start download
                    downloads[download_id].status = "downloading"
                    ydl.download([url])
                    
                    # Find the downloaded file
                    downloaded_file = None
                    title_prefix = None
                    
                    # Get video info for title matching
                    try:
                        info = ydl.extract_info(url, download=False)
                        title = info.get('title', '')
                        title_prefix = sanitize_filename(title[:50])
                    except:
                        pass
                    
                    # Look for downloaded files
                    for file in os.listdir(downloads_dir):
                        if title_prefix and file.startswith(title_prefix):
                            downloaded_file = file
                            break
                        elif file.endswith(('.mp4', '.mp3', '.webm', '.mkv')):
                            # Fallback: get the most recent file
                            file_path = os.path.join(downloads_dir, file)
                            if os.path.getmtime(file_path) > time.time() - 60:  # Within last minute
                                downloaded_file = file
                                break
                    
                    if downloaded_file:
                        downloads[download_id].filename = downloaded_file
                        downloads[download_id].status = "completed"
                        downloads[download_id].progress = 100
                    else:
                        downloads[download_id].status = "error"
                        downloads[download_id].error = "Downloaded file not found"
                        
            except Exception as e:
                downloads[download_id].status = "error"
                downloads[download_id].error = str(e)
        
        # Start download in background thread
        thread = threading.Thread(target=download_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'download_id': download_id,
            'status': 'started',
            'message': 'Download started successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to start download: {str(e)}'}), 500

@app.route('/download-status/<download_id>')
def download_status(download_id):
    """Check download status"""
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    download = downloads[download_id]
    response = {
        'status': download.status,
        'progress': download.progress,
        'filename': download.filename,
        'error': download.error
    }
    
    return jsonify(response)

@app.route('/download-file/<download_id>')
def download_file(download_id):
    """Serve the downloaded file"""
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    
    download = downloads[download_id]
    if download.status != 'completed' or not download.filename:
        return jsonify({'error': 'File not ready for download'}), 400
    
    downloads_dir = os.path.join(os.getcwd(), 'downloads')
    file_path = os.path.join(downloads_dir, download.filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download.filename
        )
    except Exception as e:
        return jsonify({'error': f'Failed to serve file: {str(e)}'}), 500

@app.route('/cleanup/<download_id>', methods=['POST'])
def cleanup_download(download_id):
    """Clean up downloaded file and remove from memory"""
    if download_id in downloads:
        download = downloads[download_id]
        if download.filename:
            downloads_dir = os.path.join(os.getcwd(), 'downloads')
            file_path = os.path.join(downloads_dir, download.filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
        
        del downloads[download_id]
    
    return jsonify({'message': 'Cleanup completed'})

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)