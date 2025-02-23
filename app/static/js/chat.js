// Scroll chat to bottom
function scrollToBottom(elementId) {
    const element = document.getElementById(elementId);
    element.scrollTop = element.scrollHeight;
}

// Clear input after sending message
function clearInput(form) {
    form.reset();
    form.querySelector('input[name="message"]').focus();
}

// Show loading state
function showLoading(target) {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'flex justify-start message-in';
    loadingDiv.innerHTML = `
        <div class="max-w-[70%] bg-white rounded-lg px-4 py-2 shadow">
            <div class="flex items-center space-x-2">
                <div class="animate-pulse">
                    <div class="h-2 w-2 bg-gray-400 rounded-full"></div>
                </div>
                <div class="animate-pulse">
                    <div class="h-2 w-2 bg-gray-400 rounded-full"></div>
                </div>
                <div class="animate-pulse">
                    <div class="h-2 w-2 bg-gray-400 rounded-full"></div>
                </div>
            </div>
        </div>
    `;
    target.appendChild(loadingDiv);
    scrollToBottom('chat-messages');
}

// Handle file upload progress
function handleFileUpload(event) {
    const progress = event.detail.progress;
    const progressBar = document.getElementById('upload-progress');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
}