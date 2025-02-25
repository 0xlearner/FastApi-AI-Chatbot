let isInitialLoad = true;

async function handleSubmit(event) {
  event.preventDefault();

  const form = event.target;
  const input = form.querySelector('input[name="message"]');
  const button = form.querySelector('button[type="submit"]');
  const message = input.value.trim();

  if (!message) return;

  // Disable form
  input.disabled = true;
  button.disabled = true;

  try {
    // Add user message immediately
    addUserMessage(message);

    // Clear input
    input.value = "";

    // Add typing indicator
    addTypingIndicator();

    // Send message to server
    const formData = new FormData();
    formData.append("message", message);

    const response = await fetch(`/api/v1/chat/{{ pdf.file_id }}/send`, {
      method: "POST",
      body: formData,
      headers: {
        Accept: "text/html",
      },
    });

    if (!response.ok) {
      throw new Error("Network response was not ok");
    }

    // Remove typing indicator
    const typingIndicator = document.getElementById("typing-indicator");
    if (typingIndicator) {
      typingIndicator.remove();
    }

    // Add bot response
    const html = await response.text();
    const messagesContainer = document.getElementById("chat-messages");
    messagesContainer.insertAdjacentHTML("beforeend", html);
    scrollToBottom();
  } catch (error) {
    console.error("Error:", error);
    const typingIndicator = document.getElementById("typing-indicator");
    if (typingIndicator) {
      typingIndicator.innerHTML = `
                <div class="max-w-[70%] bg-red-50 text-red-500 rounded-lg px-4 py-2 shadow">
                    <p class="text-sm">Sorry, there was an error processing your request.</p>
                </div>
            `;
    }
  } finally {
    // Re-enable form
    input.disabled = false;
    button.disabled = false;
    input.focus();
  }
}

// function to handle initial load animation
function handleInitialLoad() {
  if (isInitialLoad) {
    const messages = document.querySelectorAll(".message-in");
    messages.forEach((message, index) => {
      message.style.animationDelay = `${index * 100}ms`;
    });
    isInitialLoad = false;
  }
}

// load event listener
window.addEventListener("load", () => {
  scrollToBottom();
  handleInitialLoad();
});

// handle HTMX loads
document.body.addEventListener("htmx:afterOnLoad", (event) => {
  if (event.detail.target.id === "chat-messages") {
    handleInitialLoad();
    scrollToBottom();
  }
});

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
  const loadingDiv = document.createElement("div");
  loadingDiv.className = "flex justify-start message-in";
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
  scrollToBottom("chat-messages");
}

// Handle file upload progress
function handleFileUpload(event) {
  const progress = event.detail.progress;
  const progressBar = document.getElementById("upload-progress");
  if (progressBar) {
    progressBar.style.width = `${progress}%`;
  }
}
