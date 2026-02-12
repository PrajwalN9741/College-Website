// Chatbot Logic with Gemini AI Integration

const chatIcon = document.getElementById('chat-icon');
const chatBox = document.getElementById('chat-box');
const closeChat = document.getElementById('close-chat');
const sendBtn = document.getElementById('send-btn');
const userInput = document.getElementById('user-input');
const chatBody = document.getElementById('chat-body');

// 🔁 Change this when deploying
const BACKEND_URL = "/chat";

// Toggle Chat
chatIcon.addEventListener('click', () => {
    chatBox.classList.add('active');
    chatIcon.style.opacity = '0';
    setTimeout(() => chatIcon.style.display = 'none', 300);

    if (chatBody.children.length <= 1) showSuggestions();
});

closeChat.addEventListener('click', () => {
    chatBox.classList.remove('active');
    setTimeout(() => {
        chatIcon.style.display = 'flex';
        setTimeout(() => chatIcon.style.opacity = '1', 10);
    }, 300);
});

// Send Message
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
    const message = userInput.value.trim();
    if (message === '') return;

    addMessage(message, 'user-msg');
    userInput.value = '';

    const typingId = showTypingIndicator();

    try {
        const response = await fetch(BACKEND_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        removeTypingIndicator(typingId);
        addMessage(data.response, 'bot-msg');

    } catch (error) {
        console.error('Error:', error);
        removeTypingIndicator(typingId);
        addMessage(
            "⚠️ Unable to connect to the College Assistant server. Please ensure the backend is running.",
            'bot-msg'
        );
    }
}

// Add Message
function addMessage(text, className) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('msg', className);
    msgDiv.innerHTML = text.replace(/\n/g, '<br>');
    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Typing Indicator
function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('msg', 'bot-msg', 'typing');
    msgDiv.id = id;
    msgDiv.innerHTML =
        '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// 🎓 Updated Suggestions (National College Bagepalli)
function showSuggestions() {
    const div = document.createElement('div');
    div.classList.add('suggestions');
    div.innerHTML = `
        <button onclick="quickAsk('When was National College Bagepalli established?')">🏛 Founded Year</button>
        <button onclick="quickAsk('Who founded National College Bagepalli?')">👤 Founder</button>
        <button onclick="quickAsk('What courses are offered?')">📚 Courses</button>
        <button onclick="quickAsk('Where is the college located?')">📍 Location</button>
        <button onclick="quickAsk('What are the college highlights?')">📊 Highlights</button>
    `;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
}

// Quick Ask
window.quickAsk = function (text) {
    userInput.value = text;
    sendMessage();
};
