// Configuración de la API
const API_BASE_URL = window.location.origin + '/api/v1';

// Sistema de tabs
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remover clase active de todos los tabs
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Activar tab seleccionado
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
        
        // Cargar datos según la pestaña
        if (tab.dataset.tab === 'contenido') {
            cargarContenido();
        } else if (tab.dataset.tab === 'conversaciones') {
            cargarConversaciones();
        }
    });
});

// ==================== ESTADÍSTICAS ====================

async function cargarEstadisticas() {
    try {
        // Cargar conversaciones
        const convRes = await fetch(`${API_BASE_URL}/conversaciones`);
        if (convRes.ok) {
            const conversaciones = await convRes.json();
            document.getElementById('total-conversaciones').textContent = conversaciones.length || 0;
            
            // Calcular total de mensajes
            const totalMensajes = conversaciones.reduce((sum, c) => sum + (c.total_mensajes || 0), 0);
            document.getElementById('total-mensajes').textContent = totalMensajes;
        }
        
        // Cargar contenido
        const contRes = await fetch(`${API_BASE_URL}/unidades-contenido`);
        if (contRes.ok) {
            const contenido = await contRes.json();
            document.getElementById('total-contenido').textContent = contenido.length || 0;
        }
    } catch (error) {
        console.error('Error al cargar estadísticas:', error);
        // Mostrar 0 en caso de error
        document.getElementById('total-conversaciones').textContent = '0';
        document.getElementById('total-mensajes').textContent = '0';
        document.getElementById('total-contenido').textContent = '0';
    }
}

// ==================== CONTENIDO ====================

// Form de contenido
document.getElementById('form-contenido').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    // Construir el objeto de datos
    const data = {
        titulo: formData.get('titulo'),
        contenido: formData.get('contenido'),
        categoria_id: 1, // ID por defecto, ajusta según tu DB
        palabras_clave: formData.get('palabras_clave') || '',
        activo: true
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/unidades-contenido`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            mostrarMensaje('contenido', 'Contenido guardado exitosamente', 'success');
            e.target.reset();
            cargarContenido();
        } else {
            const error = await response.json();
            mostrarMensaje('contenido', error.message || 'Error al guardar contenido', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarMensaje('contenido', 'Error de conexión al guardar contenido', 'error');
    }
});

// Cargar contenido
async function cargarContenido() {
    try {
        const response = await fetch(`${API_BASE_URL}/unidades-contenido`);
        
        if (!response.ok) {
            throw new Error('Error al cargar contenido');
        }
        
        const contenido = await response.json();
        const tbody = document.querySelector('#tabla-contenido tbody');
        
        if (contenido.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: #666;">
                        No hay contenido registrado. Crea la primera unidad de contenido.
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = contenido.map(item => `
            <tr>
                <td>${item.titulo || '-'}</td>
                <td>${item.categoria?.nombre || '-'}</td>
                <td>${item.palabras_clave || '-'}</td>
                <td>
                    <span class="badge ${item.activo ? 'badge-success' : 'badge-danger'}">
                        ${item.activo ? 'Activo' : 'Inactivo'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-danger" onclick="eliminarContenido(${item.id})">
                        Eliminar
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error al cargar contenido:', error);
        const tbody = document.querySelector('#tabla-contenido tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; color: #dc3545;">
                    Error al cargar el contenido. Verifica la conexión con el servidor.
                </td>
            </tr>
        `;
    }
}

// Eliminar contenido
async function eliminarContenido(id) {
    if (!confirm('¿Estás seguro de eliminar este contenido?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/unidades-contenido/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            mostrarMensaje('contenido', 'Contenido eliminado exitosamente', 'success');
            cargarContenido();
        } else {
            mostrarMensaje('contenido', 'Error al eliminar contenido', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarMensaje('contenido', 'Error de conexión al eliminar', 'error');
    }
}

// ==================== CONVERSACIONES ====================

async function cargarConversaciones() {
    try {
        const response = await fetch(`${API_BASE_URL}/conversaciones`);
        
        if (!response.ok) {
            throw new Error('Error al cargar conversaciones');
        }
        
        const conversaciones = await response.json();
        const tbody = document.querySelector('#tabla-conversaciones tbody');
        
        if (conversaciones.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; color: #666;">
                        No hay conversaciones registradas aún.
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = conversaciones.map(conv => `
            <tr>
                <td>${conv.session_id ? conv.session_id.substring(0, 8) + '...' : '-'}</td>
                <td>${conv.fecha_inicio ? new Date(conv.fecha_inicio).toLocaleString('es-EC') : '-'}</td>
                <td>${conv.total_mensajes || 0}</td>
                <td>
                    <button class="btn btn-primary" onclick="verDetalleConversacion('${conv.session_id}')">
                        Ver detalles
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error al cargar conversaciones:', error);
        const tbody = document.querySelector('#tabla-conversaciones tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: #dc3545;">
                    Error al cargar conversaciones. Verifica la conexión con el servidor.
                </td>
            </tr>
        `;
    }
}

// Ver detalle de conversación
function verDetalleConversacion(sessionId) {
    alert(`Ver detalles de conversación: ${sessionId}\n\nEsta funcionalidad estará disponible próximamente.`);
}

// ==================== UTILIDADES ====================

// Mostrar mensajes
function mostrarMensaje(contenedor, texto, tipo) {
    const div = document.getElementById(`mensaje-${contenedor}`);
    if (!div) return;
    
    div.innerHTML = `<div class="alert alert-${tipo}">${texto}</div>`;
    
    // Ocultar después de 5 segundos
    setTimeout(() => {
        div.innerHTML = '';
    }, 5000);
}

// ==================== INICIALIZACIÓN ====================

// Cargar datos al iniciar
document.addEventListener('DOMContentLoaded', () => {
    cargarEstadisticas();
    
    // Auto-refresh cada 30 segundos
    setInterval(cargarEstadisticas, 30000);
});

// Exponer funciones globales
window.eliminarContenido = eliminarContenido;
window.verDetalleConversacion = verDetalleConversacion;