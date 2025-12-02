// static/js/widget.js
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Variables globales
let speechSynthesis = window.speechSynthesis;
let availableVoices = [];

function initVoices() {
    availableVoices = speechSynthesis.getVoices();
    console.log('Voces disponibles:', availableVoices.map(v => `${v.name} (${v.lang})`));
}

speechSynthesis.onvoiceschanged = initVoices;
initVoices();

let chatButton, chatContainer, closeChat, chatMessages, chatInput, sendButton, typingIndicator, agentSelector, agentCards, selectedAgentInfo, agentDisplayName, clearAgentBtn, toggleAgentsBtn, voiceToggleBtn;
let selectedAgentId = null;
let selectedAgentName = null;
let voiceEnabled = false;

// 🔥 NUEVA variable para controlar streaming
let currentStreamController = null;

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', () => {
    chatButton = document.getElementById('chat-button');
    chatContainer = document.getElementById('chat-container');
    closeChat = document.getElementById('close-chat');
    chatMessages = document.getElementById('chat-messages');
    chatInput = document.getElementById('chat-input');
    sendButton = document.getElementById('send-button');
    typingIndicator = document.getElementById('typing-indicator');
    agentSelector = document.getElementById('agent-selector');
    agentCards = document.getElementById('agent-cards');
    selectedAgentInfo = document.getElementById('selected-agent-info');
    agentDisplayName = document.getElementById('agent-display-name');
    clearAgentBtn = document.getElementById('clear-agent-btn');
    toggleAgentsBtn = document.getElementById('toggle-agents-btn');
    voiceToggleBtn = document.getElementById('voice-toggle-btn');

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

    cargarAgentes();

    if (clearAgentBtn) {
        clearAgentBtn.addEventListener('click', () => {
            limpiarSeleccionAgente();
        });
    }

    if (toggleAgentsBtn) {
        toggleAgentsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleAgentSelector();
        });
    }

    if (voiceToggleBtn) {
        voiceToggleBtn.addEventListener('click', () => {
            toggleVoice();
        });
    }

    chatContainer.addEventListener('click', (e) => {
        e.stopPropagation();
    });
});

// ==================== GESTIÓN DE VOZ ====================
function toggleVoice() {
    voiceEnabled = !voiceEnabled;
    voiceToggleBtn.classList.toggle('active', voiceEnabled);
    
    if (voiceEnabled) {
        addBotMessage('Voz activada. Ahora leeré en voz alta mis respuestas.');
    } else {
        speechSynthesis.cancel();
        addBotMessage('Voz desactivada.');
    }
}

function speakText(text) {
    if (!voiceEnabled || !text) return;

    const cleanText = text
        .replace(/<[^>]*>/g, '')
        .replace(/https?:\/\/[^\s]+/g, '')
        .trim();

    if (!cleanText) return;

    speakWithBrowserTTS(cleanText);
}

function speakWithBrowserTTS(text) {
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-ES';     
    utterance.rate = 1.1;
    utterance.pitch = 1.3;
    utterance.volume = 1;

    const preferredVoiceNames = [
        "Microsoft Helena",
        "Google español",   
        "Mónica",
        "Paulina",
        "Microsoft Laura",
        "Diego"
    ];
    let voice = availableVoices.find(v =>
        v.lang.startsWith('es') &&
        (
            v.name.toLowerCase().includes('diego') ||
            v.name.toLowerCase().includes('jorge') ||
            v.name.toLowerCase().includes('pablo') ||
            v.name.toLowerCase().includes('raul') ||
            v.name.toLowerCase().includes('male')
        )
    );

    if (!voice) {
        voice = availableVoices.find(v => 
            preferredVoiceNames.some(name => v.name.includes(name))
        );
    }

    if (!voice) {
        voice = availableVoices.find(v => v.lang.startsWith('es'));
    }

    if (voice) {
        utterance.voice = voice;
    }

    speechSynthesis.speak(utterance);
}

// ==================== GESTIÓN DE AGENTES ====================
function toggleAgentSelector() {
    agentSelector.classList.toggle('show');
    toggleAgentsBtn.classList.toggle('active');
}

function seleccionarAgente(card, agentId, agentName) {
    document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    
    selectedAgentId = agentId || null;
    selectedAgentName = agentName;

    if (agentId) {
        mostrarInfoAgente();
    }
}

function mostrarInfoAgente() {
    if (selectedAgentName) {
        agentDisplayName.textContent = selectedAgentName;
        selectedAgentInfo.classList.add('active');
        agentSelector.classList.remove('show');
        toggleAgentsBtn.classList.remove('active');
        addBotMessage(`Ahora estás hablando con ${selectedAgentName}. Todas tus consultas serán atendidas por este agente especializado.`);
    }
}

function limpiarSeleccionAgente() {
    selectedAgentId = null;
    selectedAgentName = null;
    selectedAgentInfo.classList.remove('active');
    agentSelector.classList.add('show');
    
    document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('selected'));
    
    addBotMessage('Has vuelto al modo automático. Seleccionaré el mejor agente para cada consulta.');
}

async function cargarAgentes() {
    try {
        const res = await fetch(`${API_BASE_URL}/agentes/`);
        
        if (!res.ok) return;

        const agentes = await res.json();
        
        agentes.forEach((agente) => {
            const card = document.createElement('div');
            card.className = 'agent-card';
            card.dataset.agentId = agente.id_agente;
            card.dataset.agentName = agente.nombre_agente;
            
            const iconMap = {
                'especializado': '🎯',
                'router': '🔀',
                'hibrido': '⚡'
            };
            const icon = iconMap[agente.tipo_agente] || '🤖';
            
            card.innerHTML = `
                <div class="agent-card-icon">${icon}</div>
                <div class="agent-card-content">
                    <div class="agent-card-name">${agente.nombre_agente}</div>
                    <div class="agent-card-type">${agente.area_especialidad || agente.tipo_agente}</div>
                </div>
                <div class="agent-card-check">
                    <svg viewBox="0 0 24 24" fill="none" stroke-width="3">
                        <path d="M20 6L9 17l-5-5"/>
                    </svg>
                </div>
            `;
            
            card.addEventListener('click', () => {
                seleccionarAgente(card, agente.id_agente, agente.nombre_agente);
            });
            
            agentCards.appendChild(card);
        });
        
    } catch (err) {
        console.error('Error al cargar agentes:', err);
    }
}

// ==================== FUNCIONES ====================
function inicializarChat() {
    addBotMessage('¡Hola! Soy el asistente virtual de TEC AZUAY. ¿En qué puedo ayudarte hoy?');
}

// ==================== ENVIAR MENSAJE CON TIMEOUT Y RETRY ====================
async function sendMessage() {
    const mensaje = chatInput.value.trim();
    if (!mensaje) return;

    // Cancelar streaming anterior si existe
    if (currentStreamController) {
        currentStreamController.abort();
        currentStreamController = null;
    }

    addUserMessage(mensaje);
    chatInput.value = '';
    sendButton.disabled = true;
    typingIndicator.classList.add('active');

    // 🔥 Configuración de reintentos
    const MAX_RETRIES = 2;
    const TIMEOUT_MS = 60000; // 60 segundos
    
    let attempt = 0;
    let success = false;

    while (attempt <= MAX_RETRIES && !success) {
        try {
            attempt++;
            
            if (attempt > 1) {
                console.log(`🔄 Reintento ${attempt}/${MAX_RETRIES + 1}...`);
                addBotMessage(`⚠️ Reintentando conexión (${attempt}/${MAX_RETRIES + 1})...`);
                await sleep(1000 * attempt); // Backoff: 1s, 2s, 3s
            }

            let endpoint, body;

            if (selectedAgentId) {
                endpoint = `${API_BASE_URL}/chat/agent/stream`;
                body = { 
                    message: mensaje, 
                    agent_id: Number(selectedAgentId)
                };
            } else {
                endpoint = `${API_BASE_URL}/chat/auto/stream`;
                body = { 
                    message: mensaje, 
                    departamento_codigo: ""
                };
            }

            // 🔥 NUEVO: Crear AbortController con timeout
            currentStreamController = new AbortController();
            const timeoutId = setTimeout(() => {
                console.warn('⏱️ Timeout alcanzado, abortando...');
                currentStreamController.abort();
            }, TIMEOUT_MS);

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                    signal: currentStreamController.signal
                });

                // Limpiar timeout si la respuesta llega
                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status}`);
                }

                // 🔥 Procesar stream
                await processStream(response);
                
                success = true; // ✅ Éxito
                console.log('✅ Stream completado exitosamente');

            } catch (fetchError) {
                clearTimeout(timeoutId);
                
                // Si es abort por timeout o usuario
                if (fetchError.name === 'AbortError') {
                    // Verificar si fue timeout o cancelación manual
                    if (currentStreamController.signal.aborted) {
                        throw new Error('Timeout: El servidor tardó demasiado en responder');
                    } else {
                        throw new Error('Cancelado por el usuario');
                    }
                }
                
                throw fetchError; // Re-lanzar otros errores
            }

        } catch (error) {
            console.error(`❌ Intento ${attempt} falló:`, error.message);

            // Si es el último intento, mostrar error final
            if (attempt > MAX_RETRIES) {
                typingIndicator.classList.remove('active');
                
                let errorMsg = 'Lo siento, no pude conectar con el servidor.';
                
                if (error.message.includes('Timeout')) {
                    errorMsg = '⏱️ El servidor está tardando demasiado. Por favor, intenta con una pregunta más corta.';
                } else if (error.message.includes('Cancelado')) {
                    console.log('Stream cancelado por el usuario');
                    break; // No mostrar error si el usuario canceló
                } else if (error.message.includes('Failed to fetch')) {
                    errorMsg = '🔌 No hay conexión con el servidor. Verifica tu conexión a internet.';
                }
                
                addBotMessage(errorMsg);
            }
            
            // Si no es el último intento, continuar el loop
            if (attempt <= MAX_RETRIES) {
                continue;
            }
        } finally {
            currentStreamController = null;
        }
    }

    // Limpiar estado final
    typingIndicator.classList.remove('active');
    sendButton.disabled = false;
    chatInput.focus();
}

// 🔥 NUEVA: Función helper para sleep
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function processStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let fullResponse = '';
    let currentBotMessageDiv = null;
    let messageContent = null;
    let buffer = '';
    
    try {
        // 🔥 NUEVO: Heartbeat detection
        let lastDataTime = Date.now();
        const HEARTBEAT_TIMEOUT = 30000; // 30 segundos sin datos
        
        // 🔥 NUEVO: Verificar heartbeat periódicamente
        const heartbeatCheck = setInterval(() => {
            const timeSinceLastData = Date.now() - lastDataTime;
            if (timeSinceLastData > HEARTBEAT_TIMEOUT) {
                console.warn('⚠️ Sin datos por más de 30s, posible conexión perdida');
                clearInterval(heartbeatCheck);
                reader.cancel();
                throw new Error('Conexión perdida: sin respuesta del servidor');
            }
        }, 5000); // Revisar cada 5 segundos
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                clearInterval(heartbeatCheck);
                console.log('✅ Stream completado');
                break;
            }
            
            // 🔥 Actualizar timestamp
            lastDataTime = Date.now();
            
            // Decodificar chunk
            buffer += decoder.decode(value, { stream: true });
            
            // Procesar líneas completas
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                
                try {
                    const jsonStr = line.substring(6).trim();
                    if (!jsonStr) continue;
                    
                    const event = JSON.parse(jsonStr);
                    
                    switch (event.type) {
                        case 'status':
                            console.log('📊', event.content);
                            break;
                            
                        case 'context':
                            console.log('📚', event.content);
                            typingIndicator.classList.remove('active');
                            break;
                            
                        case 'classification':
                            console.log('🎯 Agente clasificado:', event.agent_id);
                            break;
                            
                        case 'token':
                            if (!currentBotMessageDiv) {
                                typingIndicator.classList.remove('active');
                                
                                currentBotMessageDiv = document.createElement('div');
                                currentBotMessageDiv.className = 'message bot streaming';
                                currentBotMessageDiv.innerHTML = `
                                    <div class="message-content">
                                        <span class="bot-text"></span>
                                        <span class="typing-cursor">|</span>
                                        <div class="message-time">${getCurrentTime()}</div>
                                    </div>
                                `;
                                chatMessages.appendChild(currentBotMessageDiv);
                                messageContent = currentBotMessageDiv.querySelector('.bot-text');
                            }
                            
                            fullResponse += event.content;
                            messageContent.textContent = fullResponse;
                            scrollToBottom();
                            break;
                            
                        case 'done':
                            clearInterval(heartbeatCheck);
                            console.log('✅ Generación completada');
                            
                            if (currentBotMessageDiv) {
                                currentBotMessageDiv.classList.remove('streaming');
                                const cursor = currentBotMessageDiv.querySelector('.typing-cursor');
                                if (cursor) cursor.remove();
                                
                                messageContent.innerHTML = formatBotMessage(fullResponse);
                            }
                            
                            typingIndicator.classList.remove('active');
                            speakText(fullResponse);
                            break;
                            
                        case 'error':
                            clearInterval(heartbeatCheck);
                            console.error('❌', event.content);
                            typingIndicator.classList.remove('active');
                            throw new Error(event.content);
                    }
                    
                } catch (e) {
                    console.error('❌ Error parsing JSON:', e, 'Line:', line);
                }
            }
        }
        
        // Procesar buffer final
        if (buffer.trim() && buffer.startsWith('data: ')) {
            try {
                const jsonStr = buffer.substring(6).trim();
                const event = JSON.parse(jsonStr);
                
                if (event.type === 'done') {
                    console.log('✅ Evento final procesado');
                }
            } catch (e) {
                console.error('❌ Error en buffer final:', e);
            }
        }
        
    } catch (error) {
        console.error('❌ Error en stream:', error);
        typingIndicator.classList.remove('active');
        throw error; // Re-lanzar para que sendMessage() lo maneje
    } finally {
        typingIndicator.classList.remove('active');
    }
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
    
    speakText(text);
}

function getCurrentTime() {
    return new Date().toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' });
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
    text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #667eea; text-decoration: underline;">$1</a>');
    return text;
}