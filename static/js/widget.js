
        
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
            utterance.rate = 1.1;      // Más rápida = más energética
            utterance.pitch = 1.3;     // Más aguda = más amigable
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

        async function sendMessage() {
            const mensaje = chatInput.value.trim();
            if (!mensaje) return;

            addUserMessage(mensaje);
            chatInput.value = '';
            sendButton.disabled = true;
            typingIndicator.classList.add('active');

            try {
                let endpoint, body;

                if (selectedAgentId) {
                    endpoint = `${API_BASE_URL}/chat/agent`;
                    body = { message: mensaje, agent_id: Number(selectedAgentId), k: 4 };
                } else {
                    endpoint = `${API_BASE_URL}/chat/auto`;
                    body = { message: mensaje, departamento_codigo: "", k: 4 };
                }

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });

                if (!response.ok) {
                    throw new Error('Error en el servidor');
                }

                const data = await response.json();
                typingIndicator.classList.remove('active');
                
                addBotMessage(data.response || 'No se pudo generar respuesta');

            } catch (error) {
                console.error('Error:', error);
                typingIndicator.classList.remove('active');
                addBotMessage('Lo siento, hubo un error al conectar con el servidor.');
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