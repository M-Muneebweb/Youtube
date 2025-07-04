let currentVideoInfo = null;
        let currentDownloadId = null;
        let progressInterval = null;

        // Theme toggle functionality
        function toggleTheme() {
            const body = document.body;
            const icon = document.getElementById('theme-icon');
            
            if (body.dataset.theme === 'dark') {
                body.dataset.theme = 'light';
                icon.className = 'fas fa-moon';
                localStorage.setItem('theme', 'light');
            } else {
                body.dataset.theme = 'dark';
                icon.className = 'fas fa-sun';
                localStorage.setItem('theme', 'dark');
            }
        }

        // Initialize theme
        function initTheme() {
            const savedTheme = localStorage.getItem('theme') || 'light';
            const body = document.body;
            const icon = document.getElementById('theme-icon');
            
            body.dataset.theme = savedTheme;
            icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }

        // Show message
        function showMessage(text, type = 'info') {
            const messageEl = document.getElementById('message');
            messageEl.textContent = text;
            messageEl.className = `message ${type}`;
            messageEl.style.display = 'block';
            
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }

        // Format number with commas
        function formatNumber(num) {
            if (!num) return 'N/A';
            return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        }

        // Fetch video information
        async function fetchVideoInfo() {
            const urlInput = document.getElementById('url-input');
            const fetchBtn = document.getElementById('fetch-btn');
            const fetchSpinner = document.getElementById('fetch-spinner');
            const fetchIcon = document.getElementById('fetch-icon');
            const fetchText = document.getElementById('fetch-text');
            const videoPreview = document.getElementById('video-preview');
            
            const url = urlInput.value.trim();
            
            if (!url) {
                showMessage('Please enter a YouTube URL', 'error');
                return;
            }

            // Show loading state
            fetchBtn.disabled = true;
            fetchSpinner.style.display = 'block';
            fetchIcon.style.display = 'none';
            fetchText.textContent = 'Fetching...';

            try {
                const response = await fetch('/video-info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Failed to fetch video info');
                }

                currentVideoInfo = data;
                displayVideoInfo(data);
                videoPreview.classList.add('show');
                document.getElementById('download-section').classList.add('show');
                showMessage('Video information loaded successfully!', 'success');

            } catch (error) {
                showMessage(error.message, 'error');
            } finally {
                // Reset button state
                fetchBtn.disabled = false;
                fetchSpinner.style.display = 'none';
                fetchIcon.style.display = 'block';
                fetchText.textContent = 'Get Video Info';
            }
        }

        // Display video information
        function displayVideoInfo(info) {
            document.getElementById('video-thumbnail').src = info.thumbnail;
            document.getElementById('video-title').textContent = info.title;
            document.getElementById('video-duration').textContent = info.duration;
            document.getElementById('video-uploader').textContent = info.uploader;
            document.getElementById('video-views').textContent = formatNumber(info.view_count);
            
            updateResolutionOptions();
        }

        // Update resolution options based on format
        function updateResolutionOptions() {
            const formatSelect = document.getElementById('format-select');
            const resolutionSelect = document.getElementById('resolution-select');
            
            resolutionSelect.innerHTML = '';
            
            if (formatSelect.value === 'audio') {
                resolutionSelect.innerHTML = '<option value="192">192 kbps</option>';
                resolutionSelect.disabled = true;
            } else {
                resolutionSelect.disabled = false;
                const resolutions = ['360p', '480p', '720p', '1080p'];
                resolutions.forEach(res => {
                    const option = document.createElement('option');
                    option.value = res;
                    option.textContent = res === '720p' ? '720p (HD)' : res === '1080p' ? '1080p (Full HD)' : res;
                    resolutionSelect.appendChild(option);
                });
                resolutionSelect.value = '720p';
            }
        }

        // Start download
        async function startDownload() {
            if (!currentVideoInfo) {
                showMessage('Please fetch video info first', 'error');
                return;
            }

            const url = document.getElementById('url-input').value.trim();
            const format = document.getElementById('format-select').value;
            const resolution = document.getElementById('resolution-select').value;
            
            const downloadBtn = document.getElementById('download-btn');
            const downloadSpinner = document.getElementById('download-spinner');
            const downloadIcon = document.getElementById('download-icon');
            const downloadText = document.getElementById('download-text');
            const progressBar = document.getElementById('progress-bar');
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');

            // Show loading state
            downloadBtn.disabled = true;
            downloadSpinner.style.display = 'block';
            downloadIcon.style.display = 'none';
            downloadText.textContent = 'Starting...';

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: url,
                        format_type: format,
                        resolution: resolution
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Failed to start download');
                }

                currentDownloadId = data.download_id;
                downloadText.textContent = 'Downloading...';
                progressBar.style.display = 'block';
                progressText.style.display = 'block';
                
                // Start progress polling
                startProgressPolling();

            } catch (error) {
                showMessage(error.message, 'error');
                resetDownloadButton();
            }
        }

        // Start progress polling
        function startProgressPolling() {
            if (progressInterval) clearInterval(progressInterval);
            
            progressInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/download-status/${currentDownloadId}`);
                    const data = await response.json();

                    if (!response.ok) {
                        throw new Error(data.error || 'Failed to get download status');
                    }

                    updateProgress(data);

                    if (data.status === 'completed') {
                        clearInterval(progressInterval);
                        showDownloadComplete(data);
                    } else if (data.status === 'error') {
                        clearInterval(progressInterval);
                        showMessage(data.error || 'Download failed', 'error');
                        resetDownloadButton();
                    }

                } catch (error) {
                    clearInterval(progressInterval);
                    showMessage(error.message, 'error');
                    resetDownloadButton();
                }
            }, 1000);
        }

        // Update progress display
        function updateProgress(data) {
            const progressFill = document.getElementById('progress-fill');
            const progressText = document.getElementById('progress-text');
            
            const progress = Math.round(data.progress || 0);
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `${progress}% - ${data.status}`;
        }

        // Show download complete
        function showDownloadComplete(data) {
            const downloadBtn = document.getElementById('download-btn');
            const downloadSpinner = document.getElementById('download-spinner');
            const downloadIcon = document.getElementById('download-icon');
            const downloadText = document.getElementById('download-text');
            
            downloadBtn.disabled = false;
            downloadSpinner.style.display = 'none';
            downloadIcon.className = 'fas fa-download';
            downloadText.textContent = 'Download Complete!';
            
            showMessage('Download completed successfully!', 'success');
            
            // Create download link
            const downloadLink = document.createElement('a');
            downloadLink.href = `/download-file/${currentDownloadId}`;
            downloadLink.download = data.filename;
            downloadLink.click();
            
            // Reset after 3 seconds
            setTimeout(() => {
                resetDownloadButton();
                cleanupDownload();
            }, 3000);
        }

        // Reset download button
        function resetDownloadButton() {
            const downloadBtn = document.getElementById('download-btn');
            const downloadSpinner = document.getElementById('download-spinner');
            const downloadIcon = document.getElementById('download-icon');
            const downloadText = document.getElementById('download-text');
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            
            downloadBtn.disabled = false;
            downloadSpinner.style.display = 'none';
            downloadIcon.style.display = 'block';
            downloadIcon.className = 'fas fa-download';
            downloadText.textContent = 'Download';
            progressBar.style.display = 'none';
            progressText.style.display = 'none';
            
            document.getElementById('progress-fill').style.width = '0%';
        }

        // Cleanup download
        async function cleanupDownload() {
            if (currentDownloadId) {
                try {
                    await fetch(`/cleanup/${currentDownloadId}`, {
                        method: 'POST'
                    });
                } catch (error) {
                    console.error('Cleanup failed:', error);
                }
                currentDownloadId = null;
            }
        }

        // Handle Enter key in URL input
        document.getElementById('url-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                fetchVideoInfo();
            }
        });

        // Initialize theme on page load
        initTheme();
