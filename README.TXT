# 🎥 YouTube Video Downloader

A simple, modern and fast YouTube Video & Audio Downloader built with **Flask** and **yt-dlp**.  
Download videos in various resolutions or extract high-quality audio in MP3 format.  
No ads. No tracking. 100% free and open-source.

## 🌐 Live Demo (Optional)

<!-- Uncomment if hosted -->
<!-- 👉 [Visit the live site](https://your-live-url.com) -->

---

## 🚀 Features

- ✅ Download **YouTube videos** in resolutions like 360p, 480p, 720p, 1080p
- 🎧 Extract and download **audio as MP3**
- ⏱️ Live download **progress tracking**
- 📊 Show **video title, duration, thumbnail, uploader**
- 🧼 Auto-cleanup of temporary files
- 💡 Built using Flask + yt-dlp + vanilla JS

---

## 📦 Tech Stack

- 🔹 **Backend:** Python (Flask), yt-dlp
- 🔹 **Frontend:** HTML, CSS, JavaScript
- 🔹 **Other:** threading, progress hooks, REST APIs

---

## 🖥️ Installation

```bash
# Clone the repo
git clone https://github.com/M-Muneebweb/Youtube.git
cd youtube-downloader

# (Optional) Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Visit `http://localhost:5000` in your browser.

---

## 📂 Project Structure

```
youtube-downloader/
├── app.py
├── templates/
│   └── index.html
├── static/
│   └── styles.css (optional)
├── downloads/
└── README.md
```

---

## 📃 License

MIT License — free to use, modify and distribute.

---

## 💬 Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for video/audio downloading
- [Flask](https://flask.palletsprojects.com/) for backend framework
- Inspired by free, open, ad-free tools for the internet

---

## 🌟 Star this repo

If you find this useful, don't forget to ⭐ star the repo and share it!
