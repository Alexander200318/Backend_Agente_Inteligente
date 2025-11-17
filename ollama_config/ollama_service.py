import requests
import json
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from models.departamento import Departamento
from models.categoria import Categoria
from models.unidad_contenido import UnidadContenido
from exceptions.base import ValidationException, DatabaseException

class OllamaService:
    """Servicio para interactuar con Ollama API"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
    
    def _make_request(self, endpoint: str, method: str = "POST", data: dict = None) -> dict:
        """Hacer petición HTTP a Ollama"""
        url = f"{self.api_url}/{endpoint}"
        
        try:
            if method == "POST":
                response = requests.post(url, json=data, timeout=300)
            elif method == "GET":
                response = requests.get(url, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, json=data, timeout=30)
            
            response.raise_for_status()
            
            # Ollama puede retornar múltiples JSONs separados por líneas
            if endpoint == "create":
                # Leer todas las líneas del streaming
                lines = response.text.strip().split('\n')
                last_line = json.loads(lines[-1])
                return last_line
            
            return response.json() if response.text else {}
            
        except requests.exceptions.ConnectionError:
            raise ValidationException(
                "No se puede conectar con Ollama. Asegúrate de que esté corriendo en " + self.base_url
            )
        except requests.exceptions.Timeout:
            raise ValidationException("Timeout al conectar con Ollama")
        except requests.exceptions.RequestException as e:
            raise DatabaseException(f"Error al comunicarse con Ollama: {str(e)}")
    
    def verificar_conexion(self) -> bool:
        """Verificar que Ollama esté corriendo"""
        try:
            self._make_request("tags", method="GET")
            return True
        except:
            return False
    
    def listar_modelos(self) -> List[str]:
        """Listar modelos disponibles en Ollama"""
        try:
            response = self._make_request("tags", method="GET")
            return [model['name'] for model in response.get('models', [])]
        except:
            return []
    
    def verificar_modelo_base(self, modelo_base: str = "llama3") -> bool:
        """Verificar que existe el modelo base"""
        modelos = self.listar_modelos()
        return any(modelo_base in modelo for modelo in modelos)
    
    def generar_modelfile(
        self,
        departamento: Departamento,
        contenido_estructurado: str,
        modelo_base: str = "llama3"
    ) -> str:
        """
        Generar Modelfile personalizado para el departamento
        
        Args:
            departamento: Objeto Departamento
            contenido_estructurado: Contenido RAG formateado
            modelo_base: Modelo base de Ollama (default: llama3)
        """
        
        # Nombre del modelo personalizado
        nombre_modelo = f"depto_{departamento.codigo.lower()}"
        
        # Construir el system prompt con el conocimiento del departamento
        system_prompt = f"""Eres un asistente virtual especializado del departamento de {departamento.nombre}.

Tu función es ayudar a estudiantes, profesores y personal administrativo con información específica sobre este departamento.

INFORMACIÓN DEL DEPARTAMENTO:
- Nombre: {departamento.nombre}
- Código: {departamento.codigo}
- Descripción: {departamento.descripcion or 'N/A'}
- Email: {departamento.email or 'N/A'}
- Teléfono: {departamento.telefono or 'N/A'}
- Ubicación: {departamento.ubicacion or 'N/A'}
- Facultad: {departamento.facultad or 'N/A'}

BASE DE CONOCIMIENTO:
{contenido_estructurado}

INSTRUCCIONES:
1. Responde SOLO con información de la base de conocimiento proporcionada
2. Si no sabes algo, di claramente que no tienes esa información
3. Sé amable, claro y conciso
4. Si la información está desactualizada, indícalo
5. Proporciona contactos del departamento cuando sea relevante
6. Organiza tus respuestas usando las categorías de información
"""

        # Construir el Modelfile
        modelfile = f"""FROM {modelo_base}

# Configuración del modelo
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40

# System prompt con conocimiento del departamento
SYSTEM \"\"\"{system_prompt}\"\"\"

# Plantilla de respuesta
TEMPLATE \"\"\"{{{{ if .System }}}}{{{{ .System }}}}{{{{ end }}}}

Usuario: {{{{ .Prompt }}}}

Asistente: \"\"\"
"""
        
        return modelfile, nombre_modelo
    
    def crear_modelo_departamento(
        self,
        departamento: Departamento,
        contenido_estructurado: str,
        modelo_base: str = "llama3"
    ) -> dict:
        """
        Crear modelo personalizado en Ollama para el departamento
        
        Returns:
            dict con 'success', 'nombre_modelo' y 'message'
        """
        
        # Verificar que Ollama esté corriendo
        if not self.verificar_conexion():
            raise ValidationException("Ollama no está corriendo. Inícialo con: ollama serve")
        
        # Verificar que existe el modelo base
        if not self.verificar_modelo_base(modelo_base):
            raise ValidationException(
                f"El modelo base '{modelo_base}' no está disponible. "
                f"Descárgalo con: ollama pull {modelo_base}"
            )
        
        # Generar Modelfile
        modelfile, nombre_modelo = self.generar_modelfile(
            departamento, 
            contenido_estructurado,
            modelo_base
        )
        
        # Crear modelo en Ollama
        try:
            data = {
                "name": nombre_modelo,
                "modelfile": modelfile
            }
            
            response = self._make_request("create", method="POST", data=data)
            
            return {
                "success": True,
                "nombre_modelo": nombre_modelo,
                "message": f"Modelo '{nombre_modelo}' creado exitosamente",
                "status": response.get("status")
            }
            
        except Exception as e:
            raise DatabaseException(f"Error al crear modelo en Ollama: {str(e)}")
    
    def actualizar_modelo_departamento(
        self,
        departamento: Departamento,
        contenido_estructurado: str,
        modelo_base: str = "llama3"
    ) -> dict:
        """
        Actualizar modelo existente (eliminar y recrear)
        """
        nombre_modelo = f"depto_{departamento.codigo.lower()}"
        
        # Intentar eliminar modelo existente
        try:
            self.eliminar_modelo(nombre_modelo)
        except:
            pass  # Si no existe, continuar
        
        # Crear nuevo modelo
        return self.crear_modelo_departamento(departamento, contenido_estructurado, modelo_base)
    
    def eliminar_modelo(self, nombre_modelo: str) -> dict:
        """Eliminar modelo de Ollama"""
        try:
            data = {"name": nombre_modelo}
            self._make_request("delete", method="DELETE", data=data)
            return {
                "success": True,
                "message": f"Modelo '{nombre_modelo}' eliminado"
            }
        except Exception as e:
            raise DatabaseException(f"Error al eliminar modelo: {str(e)}")
    
    def consultar_modelo(
        self,
        nombre_modelo: str,
        pregunta: str,
        stream: bool = False
    ) -> str:
        """
        Hacer una consulta al modelo personalizado
        
        Args:
            nombre_modelo: Nombre del modelo (ej: depto_ti)
            pregunta: Pregunta del usuario
            stream: Si retornar respuesta en streaming
        """
        try:
            data = {
                "model": nombre_modelo,
                "prompt": pregunta,
                "stream": stream
            }
            
            response = self._make_request("generate", method="POST", data=data)
            
            if stream:
                # Manejar respuesta streaming
                return response
            else:
                return response.get("response", "")
                
        except Exception as e:
            raise DatabaseException(f"Error al consultar modelo: {str(e)}")


class ContenidoRAGService:
    """Servicio para estructurar contenido en formato RAG"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _construir_arbol_categorias(
        self, 
        id_agente: int,
        id_categoria_padre: Optional[int] = None,
        nivel: int = 0
    ) -> List[Dict]:
        """
        Construir árbol jerárquico de categorías
        Recursivo para manejar subcategorías
        """
        categorias = self.db.query(Categoria).filter(
            Categoria.id_agente == id_agente,
            Categoria.id_categoria_padre == id_categoria_padre,
            Categoria.activo == True
        ).order_by(Categoria.orden, Categoria.nombre).all()
        
        arbol = []
        for categoria in categorias:
            nodo = {
                "id": categoria.id_categoria,
                "nombre": categoria.nombre,
                "descripcion": categoria.descripcion,
                "nivel": nivel,
                "subcategorias": self._construir_arbol_categorias(
                    id_agente, 
                    categoria.id_categoria, 
                    nivel + 1
                ),
                "contenidos": []
            }
            arbol.append(nodo)
        
        return arbol
    
    def _obtener_contenidos_categoria(self, id_categoria: int) -> List[UnidadContenido]:
        """Obtener contenidos activos de una categoría"""
        return self.db.query(UnidadContenido).filter(
            UnidadContenido.id_categoria == id_categoria,
            UnidadContenido.estado == "activo"
        ).order_by(UnidadContenido.prioridad.desc()).all()
    
    def _formatear_contenido(self, contenido: UnidadContenido) -> str:
        """Formatear un contenido individual"""
        texto = f"### {contenido.titulo}\n\n"
        
        if contenido.resumen:
            texto += f"**Resumen:** {contenido.resumen}\n\n"
        
        texto += f"{contenido.contenido}\n"
        
        if contenido.palabras_clave:
            texto += f"\n**Palabras clave:** {contenido.palabras_clave}\n"
        
        if contenido.fecha_vigencia_inicio or contenido.fecha_vigencia_fin:
            texto += f"\n**Vigencia:** "
            if contenido.fecha_vigencia_inicio:
                texto += f"Desde {contenido.fecha_vigencia_inicio}"
            if contenido.fecha_vigencia_fin:
                texto += f" hasta {contenido.fecha_vigencia_fin}"
            texto += "\n"
        
        texto += "\n---\n\n"
        return texto
    
    def _formatear_arbol_categoria(self, nodo: Dict, nivel: int = 0) -> str:
        """Formatear árbol de categorías recursivamente"""
        indentacion = "  " * nivel
        marcador = "#" * (nivel + 2)
        
        texto = f"{indentacion}{marcador} {nodo['nombre']}\n\n"
        
        if nodo['descripcion']:
            texto += f"{indentacion}{nodo['descripcion']}\n\n"
        
        # Obtener y formatear contenidos de esta categoría
        contenidos = self._obtener_contenidos_categoria(nodo['id'])
        for contenido in contenidos:
            texto += self._formatear_contenido(contenido)
        
        # Procesar subcategorías recursivamente
        for subcategoria in nodo['subcategorias']:
            texto += self._formatear_arbol_categoria(subcategoria, nivel + 1)
        
        return texto
    
    def generar_contenido_estructurado_departamento(
        self, 
        id_departamento: int
    ) -> str:
        """
        Generar contenido estructurado para un departamento
        Incluye TODOS los agentes del departamento
        """
        
        # Obtener departamento
        departamento = self.db.query(Departamento).filter(
            Departamento.id_departamento == id_departamento
        ).first()
        
        if not departamento:
            raise ValidationException(f"Departamento {id_departamento} no encontrado")
        
        # Obtener todos los agentes del departamento
        from models.agente_virtual import AgenteVirtual
        agentes = self.db.query(AgenteVirtual).filter(
            AgenteVirtual.id_departamento == id_departamento,
            AgenteVirtual.activo == True
        ).all()
        
        if not agentes:
            return "# Sin información disponible\n\nEste departamento aún no tiene contenido configurado."
        
        # Construir contenido estructurado
        contenido_total = ""
        
        for agente in agentes:
            contenido_total += f"# AGENTE: {agente.nombre_agente}\n"
            contenido_total += f"**Área:** {agente.area_especialidad or 'General'}\n\n"
            
            if agente.descripcion:
                contenido_total += f"{agente.descripcion}\n\n"
            
            # Construir árbol de categorías del agente
            arbol = self._construir_arbol_categorias(agente.id_agente)
            
            if arbol:
                for categoria_raiz in arbol:
                    contenido_total += self._formatear_arbol_categoria(categoria_raiz)
            else:
                contenido_total += "*No hay contenido disponible para este agente*\n\n"
            
            contenido_total += "\n" + "="*80 + "\n\n"
        
        return contenido_total


class DepartamentoOllamaService:
    """Servicio integrado: Departamento + Ollama"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ollama = OllamaService()
        self.rag = ContenidoRAGService(db)
    
    def crear_modelo_para_departamento(
        self, 
        id_departamento: int,
        modelo_base: str = "llama3"
    ) -> dict:
        """
        Crear modelo de Ollama para un departamento
        Incluye todo el contenido estructurado
        """
        
        # Obtener departamento
        departamento = self.db.query(Departamento).filter(
            Departamento.id_departamento == id_departamento
        ).first()
        
        if not departamento:
            raise ValidationException(f"Departamento {id_departamento} no encontrado")
        
        # Generar contenido estructurado
        contenido_estructurado = self.rag.generar_contenido_estructurado_departamento(
            id_departamento
        )
        
        # Crear modelo en Ollama
        resultado = self.ollama.crear_modelo_departamento(
            departamento,
            contenido_estructurado,
            modelo_base
        )
        
        return resultado
    
    def actualizar_modelo_departamento(
        self,
        id_departamento: int,
        modelo_base: str = "llama3"
    ) -> dict:
        """Actualizar modelo existente con nuevo contenido"""
        
        departamento = self.db.query(Departamento).filter(
            Departamento.id_departamento == id_departamento
        ).first()
        
        if not departamento:
            raise ValidationException(f"Departamento {id_departamento} no encontrado")
        
        contenido_estructurado = self.rag.generar_contenido_estructurado_departamento(
            id_departamento
        )
        
        resultado = self.ollama.actualizar_modelo_departamento(
            departamento,
            contenido_estructurado,
            modelo_base
        )
        
        return resultado
    
    def consultar_departamento(
        self,
        codigo_departamento: str,
        pregunta: str
    ) -> str:
        """
        Hacer consulta al modelo del departamento
        
        Args:
            codigo_departamento: Código del departamento (ej: TI, ADM)
            pregunta: Pregunta del usuario
        """
        nombre_modelo = f"depto_{codigo_departamento.lower()}"
        return self.ollama.consultar_modelo(nombre_modelo, pregunta)