// Configuración de la API
const API_BASE_URL = window.location.origin + '/api/v1';

// Variables globales
let agenteId = 1; // ID del agente por defecto

// Elementos DOM
const chatButton = document.getElementById('chat-button');
const chatContainer = document.getElementById('chat-container');
const closeChat = document.getElementById('close-chat');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const typingIndicator = document.getElementById('typing-indicator');
const quickActions = document.querySelectorAll('.quick-action');

// ==================== EVENT LISTENERS ====================

chatButton.addEventListener('click', () => {
    chatContainer.classList.add('active');
    if (chatMessages.children.length === 0) {
        inicializarChat();
    }
    chatInput.focus();
});

closeChat.addEventListener('click', () => {
    chatContainer.classList.remove('active');
});

sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

quickActions.forEach(btn => {
    btn.addEventListener('click', () => {
        chatInput.value = btn.dataset.msg;
        sendMessage();
    });
});

// ==================== FUNCIONES ====================

function inicializarChat() {
    addBotMessage('¡Hola! Soy el asistente virtual de TEC AZUAY. ¿En qué puedo ayudarte hoy?');
}

async function sendMessage() {
    const mensaje = chatInput.value.trim();
    if (!mensaje) return;

    addUserMessage(mensaje);
    chatInput.value = '';
    sendButton.disabled = true;
    typingIndicator.classList.add('active');

    try {
        // Llamar al endpoint /api/v1/chat/agent
        const response = await fetch(`${API_BASE_URL}/chat/agent`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                agent_id: agenteId,
                message: mensaje,
                k: 4,
                use_reranking: true
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error en el servidor');
        }

        const data = await response.json();
        typingIndicator.classList.remove('active');
        
        // El endpoint retorna { ok, response, sources, ... }
        if (data.ok) {
            addBotMessage(data.response || 'No se pudo generar respuesta');
        } else {
            addBotMessage('Lo siento, hubo un problema al procesar tu mensaje.');
        }

    } catch (error) {
        console.error('Error:', error);
        typingIndicator.classList.remove('active');
        addBotMessage('Lo siento, hubo un error al conectar con el servidor. Por favor intenta de nuevo.');
    }

    sendButton.disabled = false;
    chatInput.focus();
}

function addUserMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';
    messageDiv.innerHTML = `
        <div class="message-content">
            ${escapeHtml(text)}
            <div class="message-time">${getCurrentTime()}</div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addBotMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';
    messageDiv.innerHTML = `
        <div class="message-content">
            ${formatBotMessage(text)}
            <div class="message-time">${getCurrentTime()}</div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' });
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatBotMessage(text) {
    text = escapeHtml(text);
    text = text.replace(/\n/g, '<br>');
    text = text.replace(
        /(https?:\/\/[^\s]+)/g,
        '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    return text;
}

chatContainer.addEventListener('click', (e) => {
    e.stopPropagation();
});