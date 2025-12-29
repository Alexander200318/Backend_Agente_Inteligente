// static/js/widget.js

// 🔥 VARIABLES GLOBALES - DECLARAR AL INICIO
let websocket = null;
let isEscalated = false;
let humanAgentName = null;

(function() {
    'use strict';
    
    // Bloquear errores de extensiones
    const originalError = console.error;

    console.error = function(...args) {
        const msg = args.join(' ');
        if (msg.includes('Cannot determine language') || 
            msg.includes('content-all.js') ||
            msg.includes('extension://')) {
            return;
        }
        originalError.apply(console, args);
    };
    
    window.addEventListener('error', function(e) {
        if (e.filename && (
            e.filename.includes('extension://') || 
            e.filename.includes('content-all.js') ||
            e.filename.includes('monica') ||
            e.filename.includes('sider')
        )) {
            e.preventDefault();
            e.stopPropagation();
            return true;
        }
    }, true);
    
    window.addEventListener('unhandledrejection', function(e) {
        if (e.reason && e.reason.stack && (
            e.reason.stack.includes('content-all.js') ||
            e.reason.stack.includes('extension://') ||
            e.reason.stack.includes('monica') ||
            e.reason.stack.includes('sider')
        )) {
            e.preventDefault();
            e.stopPropagation();
            return true;
        }
    }, true);
    
    console.log('✅ Protección contra extensiones activada');
})();

const API_BASE_URL = 'http://localhost:8000/api/v1';
const SESSION_STORAGE_KEY = 'tecai_session_id';

let SESSION_ID = null;
try {
    SESSION_ID = localStorage.getItem(SESSION_STORAGE_KEY);
} catch (e) {
    console.warn('localStorage no disponible, usando session_id en memoria');
}

if (!SESSION_ID) {
    SESSION_ID = 'web-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10);
    try {
        localStorage.setItem(SESSION_STORAGE_KEY, SESSION_ID);
    } catch (e) {
        console.warn('No se pudo guardar session_id en localStorage');
    }
}

console.log('🆔 SESSION_ID usado por este widget:', SESSION_ID);

// Variables globales
let speechSynthesis = window.speechSynthesis;
let availableVoices = [];
let recognition = null;
let isListening = false;
let startTimeout = null;

function initVoices() {
    availableVoices = speechSynthesis.getVoices();
    console.log('Voces disponibles:', availableVoices.length);
}

speechSynthesis.onvoiceschanged = initVoices;
initVoices();
setTimeout(initVoices, 100);
setTimeout(initVoices, 500);

let chatButton, chatContainer, closeChat, chatMessages, chatInput, sendButton, typingIndicator, agentSelector, agentCards, selectedAgentInfo, agentDisplayName, clearAgentBtn, toggleAgentsBtn, voiceToggleBtn, micButton;
let selectedAgentId = null;
let selectedAgentName = null;
let voiceEnabled = false;
let currentStreamController = null;
let isStarting = false;

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
    micButton = document.getElementById('mic-button');

    chatButton.addEventListener('click', () => {
        chatContainer.classList.add('active');
        if (chatMessages.children.length === 0) {
            inicializarChat();
        }
        chatInput.focus();
    });

    closeChat.addEventListener('click', () => {
        chatContainer.classList.remove('active');
        if (websocket) {
            websocket.close();
            websocket = null;
        }
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

    initSpeechRecognition();
});


// ==================== 🔥 SPEECH RECOGNITION ====================
function initSpeechRecognition() {
    console.log('🔧 [INIT] Iniciando configuración de Speech Recognition...');
    
    if (!micButton) {
        console.error('❌ [INIT] Botón de micrófono NO encontrado');
        return;
    }
    if (!chatInput) {
        console.error('❌ [INIT] Input de chat NO encontrado');
        return;
    }
    
    console.log('✅ [INIT] Elementos DOM encontrados correctamente');

    // Verificar soporte del navegador
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    console.log('🔍 [INIT] window.SpeechRecognition:', typeof window.SpeechRecognition);
    console.log('🔍 [INIT] window.webkitSpeechRecognition:', typeof window.webkitSpeechRecognition);
    
    if (!SpeechRecognition) {
        console.error('❌ [INIT] Speech Recognition NO soportado');
        console.log('🌐 [INIT] Navegador:', navigator.userAgent);
        micButton.style.opacity = '0.5';
        micButton.title = 'Speech Recognition no disponible en este navegador';
        micButton.addEventListener('click', (e) => {
            e.preventDefault();
            alert('❌ Tu navegador no soporta reconocimiento de voz. Usa Chrome, Edge o Safari.');
        });
        return;
    }

    console.log('✅ [INIT] SpeechRecognition disponible');
    
    try {
        recognition = new SpeechRecognition();
        console.log('✅ [INIT] Instancia de SpeechRecognition creada');
    } catch (error) {
        console.error('❌ [INIT] Error al crear instancia:', error);
        return;
    }
    
    // Configuración
    recognition.lang = 'es-ES';
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    console.log('⚙️ [CONFIG] Configuración aplicada:', {
        lang: recognition.lang,
        continuous: recognition.continuous,
        interimResults: recognition.interimResults,
        maxAlternatives: recognition.maxAlternatives
    });

    console.log('✅ [INIT] Speech Recognition inicializado correctamente');

    // Eventos
    recognition.onstart = function() {
        console.log('🎤 [EVENT] onstart - Micrófono activado');
        console.log('⏰ [EVENT] Timestamp:', new Date().toLocaleTimeString());
        
        // 🔥 Limpiar timeout
        if (startTimeout) {
            clearTimeout(startTimeout);
            startTimeout = null;
        }
        
        isListening = true;
        isStarting = false;
        micButton.style.color = '#e74c3c';
        micButton.style.backgroundColor = '#ffe6e6';
        micButton.style.transform = 'scale(1.1)';
        
        // Añadir feedback visual en el chat
        const feedbackDiv = document.createElement('div');
        feedbackDiv.id = 'voice-feedback';
        feedbackDiv.style.cssText = 'text-align: center; padding: 10px; color: #e74c3c; font-size: 12px; animation: pulse 1s infinite;';
        feedbackDiv.innerHTML = '🎤 Escuchando... Habla ahora';
        chatMessages.appendChild(feedbackDiv);
        scrollToBottom();
    };

    recognition.onspeechstart = function() {
        console.log('🗣️ [EVENT] onspeechstart - Voz detectada!');
    };

    recognition.onspeechend = function() {
        console.log('🔇 [EVENT] onspeechend - Voz terminada');
    };

    recognition.onsoundstart = function() {
        console.log('🔊 [EVENT] onsoundstart - Sonido detectado');
    };

    recognition.onsoundend = function() {
        console.log('🔈 [EVENT] onsoundend - Sonido terminado');
    };

    recognition.onaudiostart = function() {
        console.log('🎵 [EVENT] onaudiostart - Audio iniciado');
    };

    recognition.onaudioend = function() {
        console.log('🎵 [EVENT] onaudioend - Audio terminado');
    };

    recognition.onresult = function(event) {
        console.log('📝 [EVENT] onresult - Resultado recibido!');
        console.log('📊 [EVENT] Número de resultados:', event.results.length);
        console.log('📊 [EVENT] Evento completo:', event);
        
        try {
            const transcript = event.results[0][0].transcript;
            const confidence = event.results[0][0].confidence;
            console.log('✅ [RESULT] Transcripción:', transcript);
            console.log('🎯 [RESULT] Confianza:', (confidence * 100).toFixed(1) + '%');
            
            // Remover feedback
            const feedback = document.getElementById('voice-feedback');
            if (feedback) {
                feedback.remove();
                console.log('🗑️ [UI] Feedback removido');
            }
            
            chatInput.value = transcript;
            chatInput.focus();
            console.log('✅ [UI] Texto insertado en input');
        } catch (error) {
            console.error('❌ [RESULT] Error procesando resultado:', error);
        }
    };

    recognition.onnomatch = function() {
        console.warn('⚠️ [EVENT] onnomatch - No se reconoció lo que dijiste');
    };

    recognition.onend = function() {
        console.log('🎤 [EVENT] onend - Reconocimiento terminado');
        console.log('⏰ [EVENT] Timestamp:', new Date().toLocaleTimeString());
        isListening = false;
        isStarting = false; // 🔥 Reset flag
        micButton.style.color = '';
        micButton.style.backgroundColor = '';
        micButton.style.transform = '';
        
        // Remover feedback si existe
        const feedback = document.getElementById('voice-feedback');
        if (feedback) {
            feedback.remove();
            console.log('🗑️ [UI] Feedback removido en onend');
        }
    };

    recognition.onerror = function(event) {
        console.error('❌ [EVENT] onerror - Error detectado');
        console.error('❌ [ERROR] Tipo:', event.error);
        console.error('❌ [ERROR] Mensaje:', event.message);
        console.error('❌ [ERROR] Evento completo:', event);
        console.log('⏰ [ERROR] Timestamp:', new Date().toLocaleTimeString());
        
        isListening = false;
        isStarting = false; // 🔥 Reset flag
        micButton.style.color = '';
        micButton.style.backgroundColor = '';
        micButton.style.transform = '';
        
        // Remover feedback
        const feedback = document.getElementById('voice-feedback');
        if (feedback) feedback.remove();

        let errorMsg = '';
        let errorIcon = '❌';
        
        switch(event.error) {
            case 'not-allowed':
            case 'permission-denied':
                errorIcon = '🔒';
                errorMsg = 'Permiso denegado.\n\n' +
                          '📋 PASOS PARA HABILITAR:\n' +
                          '1. Haz clic en el icono 🔒 o ⓘ en la barra de direcciones\n' +
                          '2. Busca "Micrófono" en permisos\n' +
                          '3. Cambia a "Permitir"\n' +
                          '4. Recarga la página (F5)';
                break;
            case 'no-speech':
                errorIcon = '🤫';
                errorMsg = 'No detecté ninguna voz. Intenta:\n• Hablar más cerca del micrófono\n• Verificar que el micrófono esté activo\n• Hablar más alto';
                break;
            case 'audio-capture':
                errorIcon = '🎤';
                errorMsg = 'No se detectó micrófono.\n• Conecta un micrófono\n• Verifica que esté seleccionado en configuración del sistema';
                break;
            case 'network':
                errorIcon = '🌐';
                errorMsg = 'Error de red. Verifica tu conexión a internet.';
                break;
            case 'aborted':
                console.log('ℹ️ [INFO] Reconocimiento abortado por el usuario');
                return;
            default:
                errorMsg = `Error desconocido: ${event.error}`;
        }
        
        addBotMessage(`${errorIcon} ${errorMsg}`);
    };

    // Event listener para el botón
    micButton.addEventListener('click', async function(e) {
        console.log('🖱️ [CLICK] Botón de micrófono clickeado');
        e.preventDefault();
        e.stopPropagation();
        
        console.log('📊 [STATE] isListening:', isListening);
        console.log('📊 [STATE] isStarting:', isStarting);
        console.log('📊 [STATE] recognition:', recognition ? 'Existe' : 'No existe');
        
        // 🔥 Evitar clics múltiples
        if (isStarting) {
            console.log('⚠️ [CLICK] Ya se está iniciando, ignorando clic...');
            return;
        }
        
        if (isListening) {
            console.log('🛑 [ACTION] Deteniendo reconocimiento...');
            try {
                recognition.stop();
                console.log('✅ [ACTION] stop() ejecutado');
            } catch (error) {
                console.error('❌ [ACTION] Error al detener:', error);
            }
        } else {
            isStarting = true; // 🔥 Marcar que está iniciando
            console.log('🎤 [ACTION] Intentando iniciar reconocimiento...');
            
            // 🔥 Solicitar permisos explícitamente con getUserMedia
            try {
                console.log('🎤 [PERMISSIONS] Solicitando permisos con getUserMedia...');
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log('✅ [PERMISSIONS] Permisos obtenidos!');
                
                // Detener el stream inmediatamente (solo lo usamos para obtener permisos)
                stream.getTracks().forEach(track => track.stop());
                console.log('🔇 [PERMISSIONS] Stream cerrado');
                
                // 🔥 Pequeña pausa para evitar race condition
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Ahora sí iniciar el reconocimiento
                startRecognition();
                
            } catch (permError) {
                isStarting = false; // 🔥 Reset flag
                console.error('❌ [PERMISSIONS] Error obteniendo permisos:', permError);
                
                if (permError.name === 'NotAllowedError' || permError.name === 'PermissionDeniedError') {
                    addBotMessage('🔒 Permisos de micrófono bloqueados.\n\n' +
                          '📋 Para habilitarlos:\n' +
                          '1. Haz clic en el 🔒 en la barra de direcciones\n' +
                          '2. Busca "Micrófono"\n' +
                          '3. Selecciona "Permitir"\n' +
                          '4. Recarga la página (F5)');
                } else if (permError.name === 'NotFoundError') {
                    addBotMessage('🎤 No se encontró ningún micrófono.\n\nVerifica que:\n• Tu micrófono esté conectado\n• Esté habilitado en la configuración del sistema');
                } else {
                    addBotMessage('❌ Error al acceder al micrófono: ' + permError.message);
                }
            }
        }
    });
    
    console.log('✅ [INIT] Event listeners configurados');
}

function startRecognition() {
    console.log('🚀 [START] Intentando iniciar reconocimiento...');
    console.log('📊 [START] Estado actual - isListening:', isListening);
    console.log('📊 [START] Estado actual - isStarting:', isStarting);
    console.log('📊 [START] recognition existe:', !!recognition);
    
    // 🔥 No iniciar si ya está escuchando
    if (isListening) {
        console.log('⚠️ [START] Ya está escuchando, abortando...');
        isStarting = false;
        return;
    }
    
    try {
        recognition.start();
        console.log('✅ [START] recognition.start() ejecutado sin errores');
        
        // 🔥 NUEVO: Timeout de seguridad - si no hay evento onstart en 3 segundos
        startTimeout = setTimeout(() => {
            console.error('⏰ [TIMEOUT] No se recibió evento onstart en 3 segundos');
            console.log('🔍 [TIMEOUT] Estado - isListening:', isListening, 'isStarting:', isStarting);
            
            isStarting = false;
            isListening = false;
            
            // Intentar detener por si acaso
            try {
                recognition.stop();
            } catch (e) {
                console.log('ℹ️ [TIMEOUT] No se pudo detener (ya estaba detenido)');
            }
            
            addBotMessage('⏰ El micrófono no respondió.\n\n' +
                         'Posibles causas:\n' +
                         '• Otro programa está usando el micrófono\n' +
                         '• El micrófono está deshabilitado en Windows\n' +
                         '• Intenta cerrar otras aplicaciones (Zoom, Teams, etc.)\n\n' +
                         'Prueba recargar la página (F5)');
        }, 3000);
        
    } catch (error) {
        console.error('❌ [START] Error al iniciar:', error);
        console.error('❌ [START] Error.name:', error.name);
        console.error('❌ [START] Error.message:', error.message);
        
        // 🔥 Limpiar timeout
        if (startTimeout) {
            clearTimeout(startTimeout);
            startTimeout = null;
        }
        
        isStarting = false;
        
        if (error.message && error.message.includes('already started')) {
            console.log('⚠️ [START] Ya estaba iniciado, esperando a que termine...');
        } else {
            addBotMessage('❌ No se pudo iniciar el reconocimiento de voz.\n\nIntenta recargar la página (F5)');
        }
    }
}

// ==================== GESTIÓN DE VOZ ====================
function toggleVoice() {
    voiceEnabled = !voiceEnabled;
    voiceToggleBtn.classList.toggle('active', voiceEnabled);
    
    if (voiceEnabled) {
        // Cargar voces si no están disponibles
        if (availableVoices.length === 0) {
            availableVoices = speechSynthesis.getVoices();
        }
        
        addBotMessage(`🔊 Voz activada. ${availableVoices.length} voces disponibles.`);
        
        // Prueba de voz
        setTimeout(() => {
            speakText('Hola, voz de prueba activada');
        }, 500);
    } else {
        speechSynthesis.cancel();
        addBotMessage('🔇 Voz desactivada.');
    }
}

function speakText(text) {
    if (!voiceEnabled || !text) return;

    const cleanText = text
        .replace(/<[^>]*>/g, '')
        .replace(/https?:\/\/[^\s]+/g, '')
        .replace(/🔊|🔇|🎤|📝|✅|❌|⚠️|🔒|🤫|🌐/g, '')
        .trim();

    if (!cleanText) return;

    speakWithBrowserTTS(cleanText);
}

function speakWithBrowserTTS(text) {
    speechSynthesis.cancel();

    // Cargar voces si están vacías
    if (availableVoices.length === 0) {
        availableVoices = speechSynthesis.getVoices();
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-ES';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    // Buscar voz en español
    let voice = availableVoices.find(v => v.lang.startsWith('es'));

    if (voice) {
        utterance.voice = voice;
        console.log('🔊 Usando voz:', voice.name);
    } else {
        console.warn('⚠️ No se encontró voz en español, usando voz predeterminada');
    }

    utterance.onerror = function(event) {
        console.error('❌ Error TTS:', event.error);
    };

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




async function cargarMensajeBienvenida(agentId) {
    try {
        const res = await fetch(`${API_BASE_URL}/agentes/${agentId}/welcome`);
        if (res.ok) {
            const data = await res.json();
            addBotMessage(data.mensaje_bienvenida);
        } else {
            // Fallback si falla el endpoint
            addBotMessage(`Ahora estás hablando con ${selectedAgentName}. Todas tus consultas serán atendidas por este agente especializado.`);
        }
    } catch (error) {
        console.error('Error cargando bienvenida:', error);
        addBotMessage(`Ahora estás hablando con ${selectedAgentName}. ¿En qué puedo ayudarte?`);
    }
}

function mostrarInfoAgente() {
    if (selectedAgentName) {
        agentDisplayName.textContent = selectedAgentName;
        selectedAgentInfo.classList.add('active');
        agentSelector.classList.remove('show');
        toggleAgentsBtn.classList.remove('active');
        
        cargarMensajeBienvenida(selectedAgentId);
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
async function inicializarChat() {
    // 🔥 Si hay agente seleccionado, usar su bienvenida
    if (selectedAgentId) {
        await cargarMensajeBienvenida(selectedAgentId);
    } else {
        // Mensaje genérico cuando no hay agente
        addBotMessage('¡Hola! Soy el asistente virtual de TEC AZUAY. ¿En qué puedo ayudarte hoy?');
    }
}

// ==================== ENVIAR MENSAJE CON TIMEOUT Y RETRY ====================
async function sendMessage() {
    console.log("📩 CLICK ENVIAR detectado", { 
    sendButtonExists: !!sendButton,
    chatInputExists: !!chatInput,
    value: chatInput?.value
  });

    const mensaje = chatInput.value.trim();
    if (!mensaje) return;

    // 🔥 AGREGAR ESTA VERIFICACIÓN:
    if (isEscalated && websocket && websocket.readyState === WebSocket.OPEN) {
        // Enviar por WebSocket
        addUserMessage(mensaje);  // ← AGREGAR ESTA LÍNEA
        chatInput.value = '';     // ← AGREGAR ESTA LÍNEA
        sendMessageViaWebSocket(mensaje);
        return;
    }

    // Cancelar streaming anterior si existe
    if (currentStreamController) {
        currentStreamController.abort();
        currentStreamController = null;
    }

    addUserMessage(mensaje);
    chatInput.value = '';




    sendButton.disabled = true;
    typingIndicator.classList.add('active');

    const MAX_RETRIES = 2;
    const TIMEOUT_MS = 60000;
    
    let attempt = 0;
    let success = false;

    while (attempt <= MAX_RETRIES && !success) {
        try {
            attempt++;
            
            if (attempt > 1) {
                console.log(`🔄 Reintento ${attempt}/${MAX_RETRIES + 1}...`);
                addBotMessage(`⚠️ Reintentando conexión (${attempt}/${MAX_RETRIES + 1})...`);
                await sleep(1000 * attempt);
            }

            let endpoint, body;

            if (selectedAgentId) {
                endpoint = `${API_BASE_URL}/chat/agent/stream`;
                body = { 
                    message: mensaje, 
                    agent_id: Number(selectedAgentId),
                    session_id: SESSION_ID,
                    origin: "widget"  // ← AGREGAR
                };
            } else {
                endpoint = `${API_BASE_URL}/chat/auto/stream`;
                body = { 
                    message: mensaje, 
                    departamento_codigo: "",
                    session_id: SESSION_ID,
                    origin: "widget"  // ← AGREGAR
                    
                };
            }


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

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status}`);
                }

                await processStream(response);
                
                success = true;
                console.log('✅ Stream completado exitosamente');

            } catch (fetchError) {
                clearTimeout(timeoutId);
                
                if (fetchError.name === 'AbortError') {
                    if (currentStreamController.signal.aborted) {
                        throw new Error('Timeout: El servidor tardó demasiado en responder');
                    } else {
                        throw new Error('Cancelado por el usuario');
                    }
                }
                
                throw fetchError;
            }

        } catch (error) {
            console.error(`❌ Intento ${attempt} falló:`, error.message);

            if (attempt > MAX_RETRIES) {
                typingIndicator.classList.remove('active');
                
                let errorMsg = 'Lo siento, no pude conectar con el servidor.';
                
                if (error.message.includes('Timeout')) {
                    errorMsg = '⏱️ El servidor está tardando demasiado. Por favor, intenta con una pregunta más corta.';
                } else if (error.message.includes('Cancelado')) {
                    console.log('Stream cancelado por el usuario');
                    break;
                } else if (error.message.includes('Failed to fetch')) {
                    errorMsg = '🔌 No hay conexión con el servidor. Verifica tu conexión a internet.';
                }
                
                addBotMessage(errorMsg);
            }
            
            if (attempt <= MAX_RETRIES) {
                continue;
            }
        } finally {
            currentStreamController = null;
        }
    }

    typingIndicator.classList.remove('active');
    sendButton.disabled = false;
    chatInput.focus();
}

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
        let lastDataTime = Date.now();
        const HEARTBEAT_TIMEOUT = 30000;
        
        const heartbeatCheck = setInterval(() => {
            const timeSinceLastData = Date.now() - lastDataTime;
            if (timeSinceLastData > HEARTBEAT_TIMEOUT) {
                console.warn('⚠️ Sin datos por más de 30s, posible conexión perdida');
                clearInterval(heartbeatCheck);
                reader.cancel();
                throw new Error('Conexión perdida: sin respuesta del servidor');
            }
        }, 5000);
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                clearInterval(heartbeatCheck);
                console.log('✅ Stream completado');
                break;
            }
            
            lastDataTime = Date.now();
            buffer += decoder.decode(value, { stream: true });
            
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                
                try {
                    const jsonStr = line.substring(6).trim();
                    if (!jsonStr || jsonStr === '[DONE]') continue;
                    
                    const event = JSON.parse(jsonStr);

                    if (event.session_id && event.session_id !== SESSION_ID) {
                    continue;
                    }

                    switch (event.type) {
                        case 'status':
                            console.log('📊', event.content);
                            break;
                            
                        case 'context':
                            console.log('📚', event.content);
                            
                            break;
                            
                        case 'classification':
                            console.log('🎯 Agente clasificado:', event.agent_id);
                            
                            // 🔥 En modo auto NO se mantiene agente seleccionado
                            if (event.stateless) {
                                console.log('📌 Modo stateless: agente temporal para esta pregunta');
                            }
                            break;
                            
                        case 'token':
                            if (!currentBotMessageDiv) {
                                
                                
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

                                 // 🔥 2. Forzar reflow (para que el navegador pinte el div)
                                currentBotMessageDiv.offsetHeight;
                                
                                // 🔥 3. AHORA sí ocultar loader
                                typingIndicator.classList.remove('active');
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


                        case 'escalamiento':
                            console.log('🔔 Conversación escalada');
                            console.log('🔍 session_id original:', SESSION_ID);
                            console.log('🔍 nuevo_session_id:', event.nuevo_session_id);
                            
                            addBotMessage(event.content);
                            isEscalated = true;
                            humanAgentName = event.metadata?.usuario_nombre || "Agente humano";
                            
                            // 🔥 ACTUALIZAR SESSION_ID al nuevo
                            if (event.nuevo_session_id) {
                                SESSION_ID = event.nuevo_session_id;
                                
                                try {
                                    localStorage.setItem(SESSION_STORAGE_KEY, SESSION_ID);
                                    console.log('✅ SESSION_ID actualizado a:', SESSION_ID);
                                } catch (e) {
                                    console.warn('No se pudo guardar nuevo session_id en localStorage');
                                }
                            }
                            
                            connectWebSocket(SESSION_ID);
                            mostrarIndicadorEscalamiento(humanAgentName);
                            break;
                                                
                            
                        case 'error':
                            console.error('❌', event.content);
                            typingIndicator.classList.remove('active');
                            
                            // 🔥 Si es error de escalamiento, mostrar en chat
                            if (event.content.includes('seleccionar un agente específico')) {
                                addBotMessage(event.content);
                                return; // No lanzar error
                            }
                            
                            throw new Error(event.content);
                    }
                    
                } catch (e) {
                    console.error('❌ Error parsing JSON:', e, 'Line:', line);
                }
            }
        }
        
        if (buffer.trim() && buffer.startsWith('data: ')) {
            try {
                const jsonStr = buffer.substring(6).trim();
                if (jsonStr && jsonStr !== '[DONE]') {
                    const event = JSON.parse(jsonStr);
                    
                    if (event.type === 'done') {
                        console.log('✅ Evento final procesado');
                    }
                }
            } catch (e) {
                console.error('❌ Error en buffer final:', e);
            }
        }
        
    } catch (error) {
        console.error('❌ Error en stream:', error);
        typingIndicator.classList.remove('active');
        throw error;
    } finally {
        typingIndicator.classList.remove('active');
    }
}


function connectWebSocket(sessionId) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        console.log('⚠️ WebSocket ya conectado');
        return;
    }
    
    const wsUrl = `ws://localhost:8000/ws/chat/${sessionId}`;
    console.log('🔌 Conectando WebSocket:', wsUrl);
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function(e) {
        console.log('✅ WebSocket conectado');
        
        // Enviar join
        websocket.send(JSON.stringify({
            type: 'join',
            role: 'user'
        }));
    };
    



websocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('📨 WebSocket mensaje:', data);
    
    switch(data.type) {
        case 'escalamiento_info':
            if (data.escalado && data.usuario_nombre) {
                humanAgentName = data.usuario_nombre;
                mostrarIndicadorEscalamiento(data.usuario_nombre);
            }
            break;
        
        case 'message':
            if (data.role === 'human_agent') {
                // 🔥 Mensaje del humano - siempre mostrar con nombre
                const nombreAgente = data.user_name || humanAgentName || 'Agente Humano';
                addHumanMessage(data.content, nombreAgente);
                speakText(data.content);
            }
            break;
        
        case 'typing':
            if (data.is_typing) {
                mostrarIndicadorEscribiendo(data.user_name || humanAgentName || 'Agente');
            } else {
                ocultarIndicadorEscribiendo();
            }
            break;
        
        case 'user_joined':
            if (data.role === 'human') {
                humanAgentName = data.user_name;
                addSystemMessage(`👨‍💼 ${data.user_name} se ha unido a la conversación`);
                mostrarIndicadorEscalamiento(data.user_name);
            }
            break;
    }
};


    
    websocket.onerror = function(error) {
        console.error('❌ WebSocket error:', error);
    };
    
    websocket.onclose = function(event) {
        console.log('🔌 WebSocket desconectado');
        websocket = null;
    };
}

function sendMessageViaWebSocket(content) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        console.error('❌ WebSocket no conectado');
        return;
    }
    
    websocket.send(JSON.stringify({
        type: 'message',
        content: content
    }));
}

function mostrarIndicadorEscalamiento(nombreHumano) {
    // Crear o actualizar indicador en la UI
    let indicator = document.getElementById('human-agent-indicator');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'human-agent-indicator';
        indicator.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            margin: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
            animation: slideIn 0.3s ease;
        `;
        
        chatMessages.insertBefore(indicator, chatMessages.firstChild);
    }
    
    indicator.innerHTML = `
        <span style="font-size: 24px;">👨‍💼</span>
        <div>
            <div style="font-weight: 600;">${nombreHumano}</div>
            <div style="font-size: 12px; opacity: 0.9;">te está atendiendo</div>
        </div>
        <div style="margin-left: auto;">
            <div class="pulse-dot"></div>
        </div>
    `;
    
    // Agregar estilos de animación si no existen
    if (!document.getElementById('human-indicator-styles')) {
        const style = document.createElement('style');
        style.id = 'human-indicator-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateY(-20px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            .pulse-dot {
                width: 8px;
                height: 8px;
                background: #4ade80;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        `;
        document.head.appendChild(style);
    }
}

function addHumanMessage(text, userName) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot human-agent';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <span style="font-size: 18px;">👨‍💼</span>
                <strong style="color: #667eea;">${userName || humanAgentName || 'Agente Humano'}</strong>
            </div>
            ${formatBotMessage(text)}
            <div class="message-time">${getCurrentTime()}</div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addSystemMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system';
    messageDiv.innerHTML = `
        <div class="message-content" style="text-align: center; font-style: italic; color: #666;">
            ${text}
            <div class="message-time">${getCurrentTime()}</div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function mostrarIndicadorEscribiendo(userName) {
    let indicator = document.getElementById('typing-indicator-human');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'typing-indicator-human';
        indicator.className = 'message bot';
        indicator.innerHTML = `
            <div class="message-content">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 18px;">👨‍💼</span>
                    <strong style="color: #667eea;">${userName}</strong>
                </div>
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }
}

function ocultarIndicadorEscribiendo() {
    const indicator = document.getElementById('typing-indicator-human');
    if (indicator) {
        indicator.remove();
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