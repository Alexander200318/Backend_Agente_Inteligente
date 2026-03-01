// static/js/widget.js

// 🔥 VARIABLES GLOBALES - DECLARAR AL INICIO
let websocket = null;
let isEscalated = false;
let humanAgentName = null;
let escalamientoTimeout = null; // 🔥 NUEVO: Timeout para cerrar socket
const ESCALAMIENTO_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutos
let lastConsultedSources = []; // 🔥 NUEVO: Almacenar contenidos consultados
let currentAgenteData = null; // 🔥 NUEVO: Guardar datos completo del agente actual

// 🔥 SISTEMA DE REGISTRO - SOLO EMAIL
let messageCount = 0;
const MAX_MESSAGES_WITHOUT_EMAIL = 3;
let isEmailVerified = false;
let registeredVisitorId = null;
let emailModal;
let emailRequiredForm;
let emailRegistrationForm; // 🔥 NUEVO: Formulario completo de registro

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

// Detectar URL base automáticamente en lugar de hardcodear localhost
const API_BASE_URL = window.location.protocol + '//' + window.location.host + '/api/v1';

// ==================== GESTIÓN DE SESIONES ====================
const SESSION_STORAGE_KEY = 'tecai_session_id';
const SESSION_TIMESTAMP_KEY = 'tecai_session_timestamp';
const SESSION_PAGE_KEY = 'tecai_session_page';
const SESSION_TIMEOUT_MINUTES = 10;

let SESSION_ID = null;
let CURRENT_PAGE = null;

function obtenerIdentificadorPagina() {
    const path = window.location.pathname;
    const hash = window.location.hash;
    const page = path + hash;
    
    let hashCode = 0;
    for (let i = 0; i < page.length; i++) {
        const char = page.charCodeAt(i);
        hashCode = ((hashCode << 5) - hashCode) + char;
        hashCode = hashCode & hashCode;
    }
    
    return Math.abs(hashCode).toString(36);
}

function generarSessionID() {
    const timestamp = Date.now();
    const random = Math.random().toString(36).slice(2, 10);
    const pageId = obtenerIdentificadorPagina();
    
    return `web-${timestamp}-${random}-${pageId}`;
}

function crearNuevaSesion() {
    const nuevoSessionId = generarSessionID();
    const currentPage = window.location.pathname + window.location.hash;
    
    try {
        localStorage.setItem(SESSION_STORAGE_KEY, nuevoSessionId);
        localStorage.setItem(SESSION_TIMESTAMP_KEY, Date.now().toString());
        localStorage.setItem(SESSION_PAGE_KEY, currentPage);
        console.log('🆕 Nueva sesión creada:', nuevoSessionId);
        console.log('📄 Página:', currentPage);
    } catch (e) {
        console.warn('No se pudo guardar sesión en localStorage');
    }
    return nuevoSessionId;
}

function actualizarTimestampSesion() {
    try {
        localStorage.setItem(SESSION_TIMESTAMP_KEY, Date.now().toString());
    } catch (e) {
        // Ignorar si falla
    }
}

function verificarYActualizarSesion() {
    try {
        const storedTimestamp = localStorage.getItem(SESSION_TIMESTAMP_KEY);
        const storedPage = localStorage.getItem(SESSION_PAGE_KEY);
        const currentPage = window.location.pathname + window.location.hash;
        
        if (storedPage && storedPage !== currentPage) {
            console.log('📄 Cambio de página detectado → Nueva sesión requerida');
            SESSION_ID = crearNuevaSesion();
            CURRENT_PAGE = currentPage;
            return false;
        }
        
        if (storedTimestamp) {
            const tiempoTranscurrido = Date.now() - parseInt(storedTimestamp);
            const minutos = tiempoTranscurrido / 1000 / 60;
            
            if (minutos >= SESSION_TIMEOUT_MINUTES) {
                console.log(`⏱️ Sesión expirada (${minutos.toFixed(1)} min) → Creando nueva`);
                SESSION_ID = crearNuevaSesion();
                return false;
            }
        }
        
        actualizarTimestampSesion();
        return true;
        
    } catch (e) {
        console.warn('Error verificando sesión:', e);
        return true;
    }
}

function obtenerOGenerarSession() {
    try {
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY);
        const storedTimestamp = localStorage.getItem(SESSION_TIMESTAMP_KEY);
        const storedPage = localStorage.getItem(SESSION_PAGE_KEY);
        const currentPage = window.location.pathname + window.location.hash;
        
        if (storedPage && storedPage !== currentPage) {
            console.log('📄 Página diferente detectada');
            console.log('   Anterior:', storedPage);
            console.log('   Actual:', currentPage);
            console.log('   → Creando nueva sesión');
            return crearNuevaSesion();
        }
        
        if (storedSessionId && storedTimestamp) {
            const tiempoTranscurrido = Date.now() - parseInt(storedTimestamp);
            const minutos = tiempoTranscurrido / 1000 / 60;
            
            if (minutos < SESSION_TIMEOUT_MINUTES) {
                console.log(`♻️ Sesión activa (${minutos.toFixed(1)} min desde última actividad)`);
                console.log(`   Session ID: ${storedSessionId}`);
                return storedSessionId;
            } else {
                console.log(`⏱️ SESIÓN EXPIRADA (${minutos.toFixed(1)} min)`);
                console.log('   → La conversación anterior se ha cerrado');
                console.log('   → Creando nueva sesión');
                return crearNuevaSesion();
            }
        }
        
        console.log('🆕 Primera visita o sesión no encontrada');
        return crearNuevaSesion();
        
    } catch (e) {
        console.warn('localStorage no disponible, usando session_id temporal');
        return generarSessionID();
    }
}

// Inicializar sesión
SESSION_ID = obtenerOGenerarSession();
CURRENT_PAGE = window.location.pathname + window.location.hash;
console.log('🆔 SESSION_ID activo:', SESSION_ID);
console.log('📄 Página actual:', CURRENT_PAGE);

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

// ==================== DETECCIÓN DE INFORMACIÓN DEL CLIENTE ====================
function getClientInfo() {
    const ua = navigator.userAgent;
    
    let deviceType = 'desktop';
    if (/tablet|ipad|playbook|silk/i.test(ua)) {
        deviceType = 'tablet';
    } else if (/mobile|iphone|ipod|android|blackberry|opera mini|windows phone/i.test(ua)) {
        deviceType = 'mobile';
    }
    
    let browser = 'Unknown';
    if (ua.indexOf('Firefox') > -1) {
        browser = 'Firefox';
    } else if (ua.indexOf('Opera') > -1 || ua.indexOf('OPR') > -1) {
        browser = 'Opera';
    } else if (ua.indexOf('Trident') > -1) {
        browser = 'Internet Explorer';
    } else if (ua.indexOf('Edge') > -1) {
        browser = 'Edge';
    } else if (ua.indexOf('Chrome') > -1) {
        browser = 'Chrome';
    } else if (ua.indexOf('Safari') > -1) {
        browser = 'Safari';
    }
    
    let os = 'Unknown';
    if (ua.indexOf('Windows NT 10.0') > -1) os = 'Windows 10';
    else if (ua.indexOf('Windows NT 6.3') > -1) os = 'Windows 8.1';
    else if (ua.indexOf('Windows NT 6.2') > -1) os = 'Windows 8';
    else if (ua.indexOf('Windows NT 6.1') > -1) os = 'Windows 7';
    else if (ua.indexOf('Mac OS X') > -1) os = 'Mac OS X';
    else if (ua.indexOf('Android') > -1) os = 'Android';
    else if (ua.indexOf('iOS') > -1 || ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) os = 'iOS';
    else if (ua.indexOf('Linux') > -1) os = 'Linux';
    
    return {
        user_agent: ua,
        dispositivo: deviceType,
        navegador: browser,
        sistema_operativo: os,
        pantalla: {
            width: window.screen.width,
            height: window.screen.height
        },
        idioma: navigator.language || navigator.userLanguage,
        canal_acceso: 'widget'
    };
}

const CLIENT_INFO = getClientInfo();
console.log('📱 Información del cliente:', CLIENT_INFO);

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
    
    emailModal = document.getElementById('email-required-modal');
    emailRequiredForm = document.getElementById('email-required-form');
    emailRegistrationForm = document.getElementById('email-registration-form'); // 🔥 NUEVO
    
    // 🔥 Event listener para formulario de email simple
    if (emailRequiredForm) {
        emailRequiredForm.addEventListener('submit', handleEmailCheck);
    }
    
    // 🔥 Event listener para formulario de registro completo
    if (emailRegistrationForm) {
        emailRegistrationForm.addEventListener('submit', handleRegistrationSubmit);
    }

    // 🔥 NUEVO: Event listeners para modal de escalamiento
    const confirmacionModal = document.getElementById('confirmacion-escalamiento-modal');
    const btnModalNo = document.getElementById('btn-modal-no');
    const btnModalSi = document.getElementById('btn-modal-si');
    
    if (btnModalNo) {
        btnModalNo.addEventListener('click', () => {
            console.log('❌ Usuario rechazó escalamiento');
            if (confirmacionModal) confirmacionModal.classList.remove('active');
            addBotMessage('Entendido. Seguiré aquí para ayudarte. ¿En qué más puedo asistirte?');
            enviarMensajeProcesado('No quiero escalar');
        });
    }
    
    if (btnModalSi) {
        btnModalSi.addEventListener('click', async () => {
            console.log('✅ Usuario confirmó escalamiento');
            if (confirmacionModal) confirmacionModal.classList.remove('active');
            addBotMessage('Perfecto, te conectaré con un agente humano. Por favor espera...');
            
            // 🔥 ENVIAMOS MENSAJE ESPECIAL AL BACKEND INDICANDO CONFIRMACIÓN
            // En lugar de enviar "Sí, quiero hablar con un agente" que causaría re-detección
            try {
                const response = await fetch(`${API_BASE_URL}/escalamiento/confirmar`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: SESSION_ID
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('✅ Escalamiento confirmado:', data);
                    addBotMessage('Tu conversación ha sido transferida a un agente. Espera por favor...');
                } else {
                    console.error('Error confirmando escalamiento');
                    addBotMessage('Hubo un error al procesar tu solicitud. Por favor intenta de nuevo.');
                }
            } catch (error) {
                console.error('Error:', error);
                addBotMessage('Hubo un error de conexión. Por favor intenta de nuevo.');
            }
        });
    }




    // 🔥 NUEVO: Validación en tiempo real para nombre y apellido
    const nombreInput = document.getElementById('reg-nombre');
    const apellidoInput = document.getElementById('reg-apellido');

    if (nombreInput) {
        nombreInput.addEventListener('input', function(e) {
            this.value = this.value.replace(/[^A-Za-zÀ-ÿ\s]/g, '');
            if (this.value.length > 25) {
                this.value = this.value.substring(0, 25);
            }
        });
        
        nombreInput.addEventListener('blur', function(e) {
            this.value = this.value.trim();
            if (this.value.length === 0 && this.hasAttribute('required')) {
                this.setCustomValidity('El nombre es requerido');
            } else if (this.value.length > 25) {
                this.setCustomValidity('El nombre no puede superar 25 caracteres');
            } else {
                this.setCustomValidity('');
            }
        });
    }

    if (apellidoInput) {
        apellidoInput.addEventListener('input', function(e) {
            this.value = this.value.replace(/[^A-Za-zÀ-ÿ\s]/g, '');
            if (this.value.length > 25) {
                this.value = this.value.substring(0, 25);
            }
        });
        
        apellidoInput.addEventListener('blur', function(e) {
            this.value = this.value.trim();
            if (this.value.length > 25) {
                this.setCustomValidity('El apellido no puede superar 25 caracteres');
            } else {
                this.setCustomValidity('');
            }
        });
    }








    // 🔥 NUEVO: Cerrar modal con tecla ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && emailModal && emailModal.classList.contains('active')) {
            hideEmailRequiredModal();
            console.log('🚪 Modal cerrado con tecla ESC');
        }


    });

    try {
        const savedCount = sessionStorage.getItem('message_count');
        if (savedCount) {
            messageCount = parseInt(savedCount);
            console.log(`📊 Mensajes enviados en esta sesión: ${messageCount}`);
        }
    } catch (e) {
        console.warn('No se pudo recuperar contador de mensajes');
    }

    try {
        const emailVerified = sessionStorage.getItem('email_verified');
        const visitorId = sessionStorage.getItem('visitor_id');

        if (emailVerified === 'true' && visitorId) {
            isEmailVerified = true;
            registeredVisitorId = parseInt(visitorId);
            
            // 🔥 GUARDAR EMAIL EN LOCALSTORAGE
            if (visitorEmail) {
                localStorage.setItem('tecai_visitor_email', visitorEmail);
            }
            
            console.log('✅ Email ya verificado en esta sesión');
            console.log('   Visitor ID:', registeredVisitorId);
            console.log('   Visitor Email:', visitorEmail);
        }
    } catch (e) {
        console.warn('No se pudo recuperar estado de email');
    }

    chatButton.addEventListener('click', () => {
        console.log('🖱️ CLICK en chat button');
        
        // 🔥 NUEVO: Toggle - si está abierto, cerrarlo
        if (chatContainer.classList.contains('active')) {
            chatContainer.classList.remove('active');
            
            // Cerrar modal si está abierto
            if (emailModal && emailModal.classList.contains('active')) {
                hideEmailRequiredModal();
            }
            
            if (websocket) {
                websocket.close();
                websocket = null;
            }
            
            actualizarTimestampSesion();
            console.log('🚪 Chat cerrado desde botón flotante → Timestamp actualizado');
            return; // 🔥 Importante: salir de la función
        }
        
        // Si está cerrado, abrirlo normalmente
        const sessionValida = verificarYActualizarSesion();
        chatContainer.classList.add('active');
        
        if (chatMessages.children.length === 0 || !sessionValida) {
            if (!sessionValida) {
                chatMessages.innerHTML = '';
            }
            inicializarChat();
        }
        
        chatInput.focus();
    });

    closeChat.addEventListener('click', () => {
        chatContainer.classList.remove('active');
        
        // 🔥 NUEVO: Cerrar modal si está abierto
        if (emailModal && emailModal.classList.contains('active')) {
            hideEmailRequiredModal();
        }
        
        if (websocket) {
            websocket.close();
            websocket = null;
        }
        
        actualizarTimestampSesion();
        console.log('🚪 Chat cerrado → Timestamp actualizado');
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

    // Detectar navegador
    const isOpera = (!!window.opr && !!window.opr.addons) || !!window.opera || navigator.userAgent.indexOf(' OPR/') >= 0;
    const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
    const isEdge = /Edg/.test(navigator.userAgent);
    const isFirefox = /Firefox/.test(navigator.userAgent);
    
    console.log('🌐 [INIT] Navegador detectado:', { isOpera, isChrome, isEdge, isFirefox });

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
            if (isOpera) {
                alert('❌ Opera tiene soporte limitado para micrófono.\n\nUsa Chrome, Edge o Safari para esta función.');
            } else if (isFirefox) {
                alert('❌ Firefox no soporta Web Speech API.\n\nUsa Chrome, Edge o Safari.');
            } else {
                alert('❌ Tu navegador no soporta reconocimiento de voz.\n\nUsa Chrome, Edge o Safari.');
            }
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

    recognition.onstart = function() {
        console.log('🎤 [EVENT] onstart - Micrófono activado');
        console.log('⏰ [EVENT] Timestamp:', new Date().toLocaleTimeString());
        
        if (startTimeout) {
            clearTimeout(startTimeout);
            startTimeout = null;
        }
        
        isListening = true;
        isStarting = false;
        micButton.style.color = '#e74c3c';
        micButton.style.backgroundColor = '#ffe6e6';
        micButton.style.transform = 'scale(1.1)';

        const feedbackDiv = document.createElement('div');
        feedbackDiv.id = 'voice-feedback';
        feedbackDiv.style.cssText = 'text-align: center; padding: 10px; color: #667eea; font-size: 12px; font-weight: 600;';
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
        isStarting = false;
        micButton.style.color = '';
        micButton.style.backgroundColor = '';
        micButton.style.transform = '';

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
        isStarting = false;
        micButton.style.color = '';
        micButton.style.backgroundColor = '';
        micButton.style.transform = '';

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
            case 'service-not-allowed':
                errorIcon = '⚙️';
                errorMsg = 'El servicio de voz no está disponible.\n• Intenta recargar la página (F5)\n• Usa Chrome, Edge o Safari';
                break;
            case 'bad-grammar':
                errorIcon = '⚙️';
                errorMsg = 'Error en la configuración del reconocimiento.\n• Recarga la página (F5)';
                break;
            case 'aborted':
                console.log('ℹ️ [INFO] Reconocimiento abortado por el usuario');
                return;
            default:
                errorMsg = `Error: ${event.error}`;
        }
        
        addBotMessage(`${errorIcon} ${errorMsg}`);
    };

    micButton.addEventListener('click', async function(e) {
        console.log('🖱️ [CLICK] Botón de micrófono clickeado');
        e.preventDefault();
        e.stopPropagation();
        
        console.log('📊 [STATE] isListening:', isListening);
        console.log('📊 [STATE] isStarting:', isStarting);
        console.log('📊 [STATE] recognition:', recognition ? 'Existe' : 'No existe');
        
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
            isStarting = true;
            console.log('🎤 [ACTION] Intentando iniciar reconocimiento...');
            
            try {
                console.log('🎤 [PERMISSIONS] Solicitando permisos con getUserMedia...');
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log('✅ [PERMISSIONS] Permisos obtenidos!');
                
                stream.getTracks().forEach(track => track.stop());
                console.log('🔇 [PERMISSIONS] Stream cerrado');
                
                await new Promise(resolve => setTimeout(resolve, 100));
                
                startRecognition();
                
            } catch (permError) {
                isStarting = false;
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
    
    if (isListening) {
        console.log('⚠️ [START] Ya está escuchando, abortando...');
        isStarting = false;
        return;
    }
    
    try {
        recognition.start();
        console.log('✅ [START] recognition.start() ejecutado sin errores');
        
        startTimeout = setTimeout(() => {
            console.error('⏰ [TIMEOUT] No se recibió evento onstart en 5 segundos');
            console.log('🔍 [TIMEOUT] Estado - isListening:', isListening, 'isStarting:', isStarting);
            
            isStarting = false;
            isListening = false;

            try {
                recognition.abort();
            } catch (e) {
                console.log('ℹ️ [TIMEOUT] No se pudo abortar (ya estaba detenido)');
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
        if (availableVoices.length === 0) {
            availableVoices = speechSynthesis.getVoices();
        }
        
        addBotMessage(`🔊 Voz activada. ${availableVoices.length} voces disponibles.`);
        
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

function seleccionarAgente(card, agentId, agentName, agenteData = null) {
    document.querySelectorAll('.agent-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    
    selectedAgentId = agentId || null;
    selectedAgentName = agentName;
    currentAgenteData = agenteData; // 🔥 GUARDAR DATOS DEL AGENTE

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
        
        // 🔥 FILTRAR SOLO AGENTES ACTIVOS
        const agentesActivos = agentes.filter(agente => agente.activo === true);
        
        if (agentesActivos.length === 0) {
            console.warn('⚠️ No hay agentes activos disponibles');
            return;
        }
        
        // 🔥 LIMPIAR CONTENEDOR ANTES DE AGREGAR NUEVOS
        agentCards.innerHTML = '';
        
        agentesActivos.forEach((agente) => {
            const card = document.createElement('div');
            card.className = 'agent-card';
            card.dataset.agentId = agente.id_agente;
            card.dataset.agentName = agente.nombre_agente;
            
            // 🔥 NUEVO: Usar el icono de la base de datos si existe
            let icon = '🤖'; // Icono por defecto

            if (agente.icono) {
                // Si el agente tiene icono definido en la BD, usarlo
                icon = agente.icono;
            } else {
                // Fallback: mapeo por tipo de agente
                const iconMap = {
                    'especializado': '🎯',
                    'router': '🔀',
                    'hibrido': '⚡'
                };
                icon = iconMap[agente.tipo_agente] || '🤖';
            }
            
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
                seleccionarAgente(card, agente.id_agente, agente.nombre_agente, agente);
            });
            
            agentCards.appendChild(card);
        });
        
        console.log(`✅ ${agentesActivos.length} agentes activos cargados`);
        
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
    console.log("📩 CLICK ENVIAR detectado");

    const mensaje = chatInput.value.trim();
    if (!mensaje) return;

    // 🔥 Verificar límite de mensajes
    if (!checkMessageLimit()) {
        console.log('🚫 Límite de mensajes alcanzado, mostrando modal de email');
        showEmailRequiredModal();
        return;
    }

    // 🔥 Verificar sesión antes de enviar
    const sessionValida = verificarYActualizarSesion();

    if (!sessionValida) {
        // La sesión expiró, mostrar mensaje y limpiar chat
        chatMessages.innerHTML = '';
        addBotMessage('⏱️ Tu sesión anterior expiró. Iniciando nueva conversación...');
        
        // Esperar un momento y luego permitir el envío con la nueva sesión
        setTimeout(() => {
            chatInput.value = mensaje;
            sendMessage();
        }, 1000);
        return;
    }

    // WebSocket check
    if (isEscalated && websocket && websocket.readyState === WebSocket.OPEN) {
        addUserMessage(mensaje);
        chatInput.value = '';
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

    // 🔥 GUARDAR MENSAJE EN MONGODB INMEDIATAMENTE
    try {
        const saveUrl = new URL(`${API_BASE_URL}/conversations/save-message`);
        saveUrl.searchParams.append('session_id', SESSION_ID);
        saveUrl.searchParams.append('content', mensaje);
        saveUrl.searchParams.append('role', 'user');
        saveUrl.searchParams.append('id_visitante', registeredVisitorId || '');
        
        const saveResponse = await fetch(saveUrl.toString(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (saveResponse.ok) {
            const saveData = await saveResponse.json();
            console.log('✅ Mensaje guardado en MongoDB:', saveData);
        } else {
            console.warn('⚠️ No se pudo guardar el mensaje en MongoDB');
        }
    } catch (saveError) {
        console.warn('⚠️ Error guardando en MongoDB:', saveError);
    }

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

            // 🔥 CONSTRUIR BODY CON INFORMACIÓN DEL CLIENTE
            const baseBody = {
                message: mensaje,
                session_id: SESSION_ID,
                origin: "widget",
                client_info: CLIENT_INFO
            };

            if (selectedAgentId) {
                endpoint = `${API_BASE_URL}/chat/agent/stream`;
                body = { 
                    ...baseBody,
                    agent_id: Number(selectedAgentId),
                    // 🔥 NUEVO: Agregar temperatura y max_tokens del agente
                    temperatura: currentAgenteData?.temperatura ? parseFloat(currentAgenteData.temperatura) : 0.7,
                    max_tokens: currentAgenteData?.max_tokens ? parseInt(currentAgenteData.max_tokens) : 4000
                };
                console.log(`🎯 Agente seleccionado: temperatura=${body.temperatura}, max_tokens=${body.max_tokens}`);
            } else {
                endpoint = `${API_BASE_URL}/chat/auto/stream`;
                body = { 
                    ...baseBody,
                    departamento_codigo: "",
                    // 🔥 NUEVO: Valores por defecto para modo automático
                    temperatura: 0.7,
                    max_tokens: 4000
                };
            }

            console.log('📤 Enviando request con client_info:', body.client_info);

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
                incrementMessageCount();
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

function mostrarNotificacionExpiracion(minutosTranscurridos) {
    const mensaje = `⏱️ Tu conversación anterior finalizó por inactividad (${minutosTranscurridos.toFixed(0)} minutos).

🆕 Se ha iniciado una nueva conversación.

💡 Las conversaciones se cierran automáticamente después de ${SESSION_TIMEOUT_MINUTES} minutos de inactividad.`;
    
    addBotMessage(mensaje);
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
                        case 'start':
                            console.log('🚀 Iniciando respuesta del agente');
                            typingIndicator.classList.add('active');
                            fullResponse = '';
                            currentBotMessageDiv = null;
                            break;
                            
                        case 'status':
                            console.log('📊', event.content);
                            break;
                            
                        case 'context':
                            console.log('📚', event.content);
                            break;
                            
                        case 'classification':
                            console.log('🎯 Agente clasificado:', event.agent_id);
                            
                            if (event.stateless) {
                                console.log('📌 Modo stateless: agente temporal para esta pregunta');
                            }
                            break;

                        case 'confirmacion_escalamiento':
                            console.log('🔔 Solicitud de confirmación de escalamiento');
                            
                            typingIndicator.classList.remove('active');
                            addBotMessage(event.content);
                            scrollToBottom();
                            break;

                        case 'token':
                        case 'chunk':
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

                                // Forzar reflow
                                currentBotMessageDiv.offsetHeight;
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
                            
                            // 🔥 GUARDAR RESPUESTA EN MONGODB CON CONTENIDOS
                            try {
                                const saveUrl = new URL(`${API_BASE_URL}/conversations/save-message`);
                                saveUrl.searchParams.append('session_id', SESSION_ID);
                                saveUrl.searchParams.append('content', fullResponse);
                                saveUrl.searchParams.append('role', 'assistant');
                                saveUrl.searchParams.append('id_visitante', registeredVisitorId || '');
                                
                                // 🔥 NUEVO: Agregar contenidos consultados
                                if (lastConsultedSources && lastConsultedSources.length > 0) {
                                    saveUrl.searchParams.append('contenidos_json', JSON.stringify(lastConsultedSources));
                                    console.log(`📚 Enviando ${lastConsultedSources.length} contenidos consultados`);
                                }
                                
                                const saveResponse = await fetch(saveUrl.toString(), {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' }
                                });
                                
                                if (saveResponse.ok) {
                                    const saveData = await saveResponse.json();
                                    console.log('✅ Respuesta guardada en MongoDB con', saveData.total_contenidos_usados || 0, 'contenidos');
                                } else {
                                    console.warn('⚠️ No se pudo guardar la respuesta en MongoDB');
                                }
                            } catch (saveError) {
                                console.warn('⚠️ Error guardando respuesta en MongoDB:', saveError);
                            }
                            
                            // 🔥 LIMPIAR CONTENIDOS PARA EL PRÓXIMO MENSAJE
                            lastConsultedSources = [];
                            break;

                        case 'escalamiento':
                            console.log('🔔 Conversación escalada');
                            console.log('🔍 session_id original:', SESSION_ID);
                            console.log('🔍 nuevo_session_id:', event.nuevo_session_id);
                            
                            addBotMessage(event.content);
                            isEscalated = true;
                            humanAgentName = event.metadata?.usuario_nombre || "Agente humano";
                            
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
                            
                            if (event.content.includes('seleccionar un agente específico')) {
                                addBotMessage(event.content);
                                return;
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

    // Detectar WebSocket URL automáticamente
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${sessionId}`;
    console.log('🔌 Conectando WebSocket:', wsUrl);
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function(e) {
        console.log('✅ WebSocket conectado');

        websocket.send(JSON.stringify({
            type: 'join',
            role: 'user',
            visitor_id: registeredVisitorId,  // 🔥 Enviar visitante autenticado
            email: localStorage.getItem('tecai_visitor_email')  // 🔥 Enviar email
        }));

        // 🔥 NUEVO: Establecer timeout para cerrar automáticamente
        escalamientoTimeout = setTimeout(() => {
            console.log('⏱️ Tiempo de escalamiento agotado, cerrando WebSocket');
            cerrarWebSocket('Timeout de escalamiento');
        }, ESCALAMIENTO_TIMEOUT_MS);

        console.log(`⏰ Escalamiento abierto por ${ESCALAMIENTO_TIMEOUT_MS / 60000} minutos`);
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('📨 WebSocket mensaje:', data);

        switch (data.type) {
            case 'escalamiento_info':
                if (data.escalado && data.usuario_nombre) {
                    humanAgentName = data.usuario_nombre;
                    mostrarIndicadorEscalamiento(data.usuario_nombre);
                }
                break;
            
            case 'message':
                if (data.role === 'human_agent') {
                    const nombreAgente = data.user_name || humanAgentName || 'Agente Humano';
                    addHumanMessage(data.content, nombreAgente);
                    speakText(data.content);
                }
                break;
                   

            case 'system_message':
                console.log('🔔 Mensaje de sistema recibido');
                addBotMessage(data.content);
                speakText(data.content);
                break;  // ← SOLO mostrar mensaje, no cerrar WebSocket

            case 'finalizacion_escalamiento':
                console.log('🔚 Escalamiento finalizado, cerrando WebSocket');
                
                addBotMessage(data.content);
                speakText(data.content);
                
                setTimeout(() => {
                    if (websocket) {
                        websocket.close();
                        websocket = null;
                        isEscalated = false;
                        humanAgentName = null;

                        const indicator = document.getElementById('human-agent-indicator');
                        if (indicator) indicator.remove();

                        console.log('✅ WebSocket cerrado, volviendo a modo chat normal');
                    }
                }, 2000);
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
    
    console.log('📤 Enviando mensaje via WebSocket:');
    console.log('   - SESSION_ID actual:', SESSION_ID);
    console.log('   - content:', content);
    
    websocket.send(JSON.stringify({
        type: 'message',
        content: content
    }));
}

// 🔥 NUEVO: Función para cerrar WebSocket correctamente
function cerrarWebSocket(razon = 'Desconocida') {
    console.log(`🔌 Cerrando WebSocket - Razón: ${razon}`);

    // Limpiar timeout
    if (escalamientoTimeout) {
        clearTimeout(escalamientoTimeout);
        escalamientoTimeout = null;
    }

    // Cerrar conexión
    if (websocket) {
        try {
            websocket.close();
        } catch (e) {
            console.warn('Error al cerrar WebSocket:', e);
        }
        websocket = null;
    }

    // Reset estado
    isEscalated = false;
    humanAgentName = null;

    // Remover indicador
    const indicator = document.getElementById('human-agent-indicator');
    if (indicator) indicator.remove();

    console.log('✅ WebSocket cerrado correctamente, volviendo a modo chat normal');
}

function mostrarIndicadorEscalamiento(nombreHumano) {
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
    
    // Procesar markdown: **texto** -> <strong>texto</strong>
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Procesar cursiva: *texto* -> <em>texto</em>
    text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // Procesar saltos de línea
    text = text.replace(/\n/g, '<br>');
    
    // Procesar URLs
    text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #667eea; text-decoration: underline;">$1</a>');
    
    return text;
}


// ==================== SISTEMA DE REGISTRO OBLIGATORIO ====================

function showEmailRequiredModal() {
    if (!emailModal) return;
    
    // Resetear modal al estado inicial (paso 1)
    document.getElementById('email-check-step').style.display = 'block';
    document.getElementById('email-registration-step').style.display = 'none';
    document.getElementById('required-email').value = '';
    
    emailModal.classList.add('active');
    
    setTimeout(() => {
        const input = document.getElementById('required-email');
        if (input) input.focus();
    }, 300);
}

function hideEmailRequiredModal() {
    if (!emailModal) return;
    emailModal.classList.remove('active');
    
    setTimeout(() => {
        // Resetear al paso 1
        const checkStep = document.getElementById('email-check-step');
        const regStep = document.getElementById('email-registration-step');
        const loading = document.getElementById('email-loading');
        const form = document.getElementById('email-required-form');
        const regLoading = document.getElementById('registration-loading');
        
        if (checkStep) checkStep.style.display = 'block';
        if (regStep) regStep.style.display = 'none';
        if (loading) loading.style.display = 'none';
        if (form) form.style.display = 'block';
        if (regLoading) regLoading.remove(); // 🔥 Remover loading de registro si existe
        
        // Limpiar inputs
        const emailInput = document.getElementById('required-email');
        if (emailInput) emailInput.value = '';
        
        if (emailRequiredForm) emailRequiredForm.reset();
        if (emailRegistrationForm) emailRegistrationForm.reset();
        
        console.log('🔄 Modal completamente reseteado');
    }, 300);
}

// 🔥 PASO 1: Verificar si el email existe
async function handleEmailCheck(e) {
    e.preventDefault();
    
    const emailInput = document.getElementById('required-email');
    const email = emailInput?.value.trim();
    
    if (!email) {
        alert('Por favor ingresa un email válido');
        return;
    }
    
    // 🔥 NUEVO: Validar formato de email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('Por favor ingresa un email válido');
        return;
    }
    
    // Mostrar loading
    const form = document.getElementById('email-required-form');
    const loading = document.getElementById('email-loading');
    
    if (form) form.style.display = 'none';
    if (loading) loading.style.display = 'block';
    
    try {
        console.log('🔍 Verificando email:', email);
        const checkResponse = await fetch(`${API_BASE_URL}/visitantes/email/${encodeURIComponent(email)}/exists`);
        
        if (!checkResponse.ok) {
            throw new Error('Error verificando email');
        }
        
        const checkData = await checkResponse.json();
        console.log('📊 Resultado verificación:', checkData);
        
        if (checkData.exists) {
            console.log('✅ Email existe, vinculando sesión...');
            await vincularSesionExistente(email, checkData.visitante);
        } else {
            console.log('❌ Email no existe, mostrando formulario de registro');
            mostrarFormularioRegistro(email);
        }
        
    } catch (error) {
        console.error('❌ Error verificando email:', error);
        
        // 🔥 CRÍTICO: Restaurar formulario en caso de error
        if (form) form.style.display = 'block';
        if (loading) loading.style.display = 'none';
        
        alert('❌ Error al verificar email. Por favor intenta de nuevo.');
    }
}

async function vincularSesionExistente(email, visitanteData) {
    try {
        console.log('🔗 Vinculando nuevo session_id al visitante existente...');
        
        // 🔥 Actualizar identificador_sesion del visitante
        const updateResponse = await fetch(`${API_BASE_URL}/visitantes/${visitanteData.id_visitante}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                identificador_sesion: SESSION_ID  // 🔥 Nuevo session_id
            })
        });
        
        if (!updateResponse.ok) {
            throw new Error('Error actualizando sesión');
        }
        
        const updatedVisitante = await updateResponse.json();
        console.log('✅ Session_id actualizado:', updatedVisitante);
        
        // 🔥 NO crear conversación aquí
        // La conversación se creará automáticamente al enviar el primer mensaje
        // con el nuevo session_id
        
        // Guardar datos
        registeredVisitorId = updatedVisitante.id_visitante;
        isEmailVerified = true;
        
        try {
            sessionStorage.setItem('email_verified', 'true');
            sessionStorage.setItem('visitor_id', updatedVisitante.id_visitante);
            sessionStorage.setItem('visitor_email', email);  // 🔥 GUARDAR EMAIL
            
            // 🔥 TAMBIÉN EN LOCALSTORAGE PARA WEBSOCKET
            localStorage.setItem('tecai_visitor_email', email);
            localStorage.setItem('tecai_visitor_id', updatedVisitante.id_visitante);
            sessionStorage.setItem('visitor_id', registeredVisitorId);
            localStorage.setItem('visitor_email', email);
        } catch (e) {
            console.warn('No se pudo guardar en storage');
        }
        
        // Cerrar modal y mostrar mensaje
        hideEmailRequiredModal();
        addBotMessage(`✅ ¡Bienvenido de nuevo${visitanteData.nombre ? ' ' + visitanteData.nombre : ''}! Puedes continuar chateando.`);
        
        // Resetear formulario
        document.getElementById('email-required-form').reset();
        document.getElementById('email-required-form').style.display = 'block';
        document.getElementById('email-loading').style.display = 'none';
        
    } catch (error) {
        console.error('❌ Error vinculando sesión:', error);
        alert('❌ Error al vincular sesión. Por favor intenta de nuevo.');
        
        // Restaurar formulario
        document.getElementById('email-required-form').style.display = 'block';
        document.getElementById('email-loading').style.display = 'none';
    }
}

// 🔥 Mostrar formulario de registro completo
function mostrarFormularioRegistro(email) {
    // Ocultar paso 1
    document.getElementById('email-check-step').style.display = 'none';
    
    // Mostrar paso 2
    document.getElementById('email-registration-step').style.display = 'block';
    
    // Pre-llenar email (readonly)
    document.getElementById('reg-email').value = email;
    
    // Enfocar primer campo
    setTimeout(() => {
        const nombreInput = document.getElementById('reg-nombre');
        if (nombreInput) nombreInput.focus();
    }, 100);
}

// 🔥 PASO 2: Completar registro con datos completos

async function handleRegistrationSubmit(e) {
    e.preventDefault();
    
    const email = document.getElementById('reg-email').value.trim();
    const nombre = document.getElementById('reg-nombre').value.trim();
    const apellido = document.getElementById('reg-apellido').value.trim() || null;
    const edad = document.getElementById('reg-edad').value.trim() || null;
    const ocupacion = document.getElementById('reg-ocupacion').value.trim() || null;
    const pertenece_instituto = document.getElementById('reg-instituto').checked;
    
    // 🔥 VALIDACIONES (mantener todas)
    if (!nombre) {
        alert('❌ El nombre es requerido');
        return;
    }
    
    if (nombre.length > 25) {
        alert('❌ El nombre no puede superar 25 caracteres');
        return;
    }
    
    if (apellido && apellido.length > 25) {
        alert('❌ El apellido no puede superar 25 caracteres');
        return;
    }
    
    const soloLetras = /^[A-Za-zÀ-ÿ\s]+$/;
    if (!soloLetras.test(nombre)) {
        alert('❌ El nombre solo puede contener letras y espacios');
        return;
    }
    
    if (apellido && !soloLetras.test(apellido)) {
        alert('❌ El apellido solo puede contener letras y espacios');
        return;
    }
    
    if (!edad) {
        alert('❌ Selecciona un rango de edad');
        return;
    }
    
    if (!ocupacion) {
        alert('❌ Selecciona una ocupación');
        return;
    }
    
    // Mostrar loading
    const form = document.getElementById('email-registration-form');
    form.style.display = 'none';
    
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'registration-loading';
    loadingDiv.style.cssText = 'text-align: center; padding: 20px;';
    loadingDiv.innerHTML = '<div style="font-size: 14px; color: #667eea;">Creando tu cuenta...</div>';
    document.getElementById('email-registration-step').appendChild(loadingDiv);
    
    try {
        console.log('📝 Registrando nuevo visitante...');
        
        const registrationData = {
            identificador_sesion: SESSION_ID,
            email: email,
            nombre: nombre,
            apellido: apellido,
            edad: edad,
            ocupacion: ocupacion,
            pertenece_instituto: pertenece_instituto,
            ip_origen: 'unknown',
            user_agent: CLIENT_INFO.user_agent,
            dispositivo: CLIENT_INFO.dispositivo,
            navegador: CLIENT_INFO.navegador,
            sistema_operativo: CLIENT_INFO.sistema_operativo,
            canal_acceso: 'widget'
        };
        
        // ✅ MANTENER: Crear visitante en MySQL
        const response = await fetch(`${API_BASE_URL}/visitantes/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(registrationData)
        });
        
        if (!response.ok) {
            throw new Error('Error creando visitante');
        }
        
        const visitante = await response.json();
        console.log('✅ Visitante creado:', visitante);

        // ❌ ELIMINAR ESTE BLOQUE COMPLETO:
        /*
        const conversacionResponse = await fetch(`${API_BASE_URL}/conversaciones/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: SESSION_ID,
                id_visitante: visitante.id_visitante
            })
        });

        if (conversacionResponse.ok) {
            console.log('✅ Conversación creada en Mongo');
        }
        */
        
        // ✅ MANTENER: Guardar datos localmente
        registeredVisitorId = visitante.id_visitante;
        isEmailVerified = true;
        
        try {
            sessionStorage.setItem('email_verified', 'true');
            sessionStorage.setItem('visitor_id', registeredVisitorId);
            localStorage.setItem('visitor_email', email);
        } catch (e) {
            console.warn('No se pudo guardar en storage');
        }
        
        // ✅ MANTENER: Cerrar modal
        hideEmailRequiredModal();
        
        // ✅ MANTENER: Mensaje de bienvenida
        addBotMessage(`✅ ¡Bienvenido ${nombre}! Tu registro ha sido exitoso.

📝 A partir de ahora, todas tus conversaciones quedarán registradas.

¿En qué más puedo ayudarte?`);
        
        // ✅ MANTENER: Limpiar formulario
        form.reset();
        
    } catch (error) {
        console.error('❌ Error en registro:', error);
        alert('❌ Error al crear tu cuenta. Por favor intenta de nuevo.');
    } finally {
        // ✅ MANTENER: Limpiar loading
        const loading = document.getElementById('registration-loading');
        if (loading) loading.remove();
        form.style.display = 'block';
    }
}





function checkMessageLimit() {
    if (isEmailVerified) {
        return true;
    }
    
    if (messageCount < MAX_MESSAGES_WITHOUT_EMAIL) {
        return true;
    }
    
    console.log(`⚠️ Límite alcanzado: ${messageCount}/${MAX_MESSAGES_WITHOUT_EMAIL} mensajes`);
    return false;
}

function incrementMessageCount() {
    messageCount++;
    
    try {
        sessionStorage.setItem('message_count', messageCount.toString());
    } catch (e) {
        console.warn('No se pudo guardar contador');
    }
    
    console.log(`📊 Mensajes: ${messageCount}/${MAX_MESSAGES_WITHOUT_EMAIL}`);
}

// 🔥 NUEVA FUNCIÓN: Enviar mensaje de respuesta a escalamiento
function enviarMensajeProcesado(mensaje) {
    chatInput.value = mensaje;
    sendMessage();
}