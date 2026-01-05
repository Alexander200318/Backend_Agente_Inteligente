# app/repositories/unidad_contenido_repo.py
from models.unidad_contenido import UnidadContenido
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional
from exceptions.base import NotFoundException, DatabaseException, ValidationException
from schemas.unidad_contenido_schemas import UnidadContenidoCreate, UnidadContenidoUpdate


class UnidadContenidoRepository:
    def __init__(self, db: Session):
        self.db = db
    
    # 🔥 NUEVO MÉTODO: Calcula estado según fechas de vigencia
    def _aplicar_vigencia_automatica(self, contenido: UnidadContenido):
        """
        Aplica lógica de vigencia automática:
        - Antes de fecha_vigencia_inicio: inactivo
        - Entre fecha_vigencia_inicio y fecha_vigencia_fin: activo
        - Después de fecha_vigencia_fin: inactivo
        """
        if not contenido.fecha_vigencia_inicio or not contenido.fecha_vigencia_fin:
            return  # No tiene fechas configuradas, no hacer nada
        
        hoy = date.today()
        
        if hoy < contenido.fecha_vigencia_inicio:
            contenido.estado = "inactivo"
        elif contenido.fecha_vigencia_inicio <= hoy <= contenido.fecha_vigencia_fin:
            contenido.estado = "activo"
        else:  # hoy > fecha_vigencia_fin
            contenido.estado = "inactivo"
    
    def create(self, data: UnidadContenidoCreate, creado_por: int):
        try:
            contenido_dict = data.dict()
            contenido = UnidadContenido(**contenido_dict, creado_por=creado_por)
            
            # 🔥 NUEVO: Aplicar vigencia automática antes de guardar
            self._aplicar_vigencia_automatica(contenido)
            
            self.db.add(contenido)
            self.db.commit()
            self.db.refresh(contenido)
            return contenido
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_by_id(self, id_contenido: int, include_deleted: bool = False):
        query = self.db.query(UnidadContenido).filter(
            UnidadContenido.id_contenido == id_contenido
        )
        
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        cont = query.first()
        if not cont:
            raise NotFoundException("Contenido", id_contenido)
        return cont
    
    def get_by_agente(self, id_agente: int, estado: Optional[str] = None, 
                      skip: int = 0, limit: int = 100, include_deleted: bool = False):
        from models.agente_virtual import AgenteVirtual
        from models.categoria import Categoria
        
        query = (
            self.db.query(
                UnidadContenido,
                AgenteVirtual.nombre_agente,
                AgenteVirtual.area_especialidad,
                Categoria.nombre.label('categoria_nombre')
            )
            .join(AgenteVirtual, UnidadContenido.id_agente == AgenteVirtual.id_agente)
            .outerjoin(Categoria, UnidadContenido.id_categoria == Categoria.id_categoria)
            .filter(UnidadContenido.id_agente == id_agente)
        )
        
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if estado:
            query = query.filter(UnidadContenido.estado == estado)
        
        resultados = query.order_by(UnidadContenido.prioridad.desc()).offset(skip).limit(limit).all()
        
        contenidos_con_nombres = []
        for contenido, nombre_agente, area_especialidad, categoria_nombre in resultados:
            contenido_dict = {
                **{k: v for k, v in contenido.__dict__.items() if not k.startswith('_')},
                'agente_nombre': nombre_agente,
                'area_especialidad': area_especialidad,
                'categoria_nombre': categoria_nombre
            }
            contenidos_con_nombres.append(contenido_dict)
        
        return contenidos_con_nombres
    
    def update(self, id_contenido: int, data: UnidadContenidoUpdate, actualizado_por: int):
        try:
            cont = self.get_by_id(id_contenido)
            for field, value in data.dict(exclude_unset=True).items():
                setattr(cont, field, value)
            cont.actualizado_por = actualizado_por
            
            # 🔥 NUEVO: Aplicar vigencia automática después de actualizar
            self._aplicar_vigencia_automatica(cont)
            
            self.db.commit()
            self.db.refresh(cont)
            return cont
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def publicar(self, id_contenido: int, publicado_por: int):
        cont = self.get_by_id(id_contenido)
        cont.estado = "activo"
        cont.publicado_por = publicado_por
        cont.fecha_publicacion = datetime.now()
        
        # 🔥 NUEVO: Aplicar vigencia automática después de publicar
        self._aplicar_vigencia_automatica(cont)
        
        self.db.commit()
        self.db.refresh(cont)
        return cont
    
    def delete(self, id_contenido: int, eliminado_por: Optional[int] = None, hard_delete: bool = False):
        try:
            cont = self.get_by_id(id_contenido, include_deleted=True)
            
            if hard_delete:
                self.db.delete(cont)
            else:
                cont.eliminado = True
                cont.fecha_eliminacion = datetime.now()
                cont.eliminado_por = eliminado_por
                cont.estado = "inactivo"
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def restore(self, id_contenido: int):
        try:
            cont = self.get_by_id(id_contenido, include_deleted=True)
            
            if not cont.eliminado:
                raise ValidationException("El contenido no está eliminado")
            
            cont.eliminado = False
            cont.fecha_eliminacion = None
            cont.eliminado_por = None
            cont.estado = "inactivo"
            
            # 🔥 NUEVO: Aplicar vigencia automática al restaurar
            self._aplicar_vigencia_automatica(cont)
            
            self.db.commit()
            self.db.refresh(cont)
            return cont
        except Exception as e:
            self.db.rollback()
            raise DatabaseException(str(e))
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        estado: Optional[str] = None,
        id_agente: Optional[int] = None,
        id_categoria: Optional[int] = None,
        id_departamento: Optional[int] = None,
        include_deleted: bool = False
    ):
        query = self.db.query(UnidadContenido)
        
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if estado:
            query = query.filter(UnidadContenido.estado == estado)
        if id_agente:
            query = query.filter(UnidadContenido.id_agente == id_agente)
        if id_categoria:
            query = query.filter(UnidadContenido.id_categoria == id_categoria)
        if id_departamento:
            query = query.filter(UnidadContenido.id_departamento == id_departamento)
        
        return query.order_by(UnidadContenido.prioridad.desc()).offset(skip).limit(limit).all()
    
    def search(self, termino: str, id_agente: Optional[int] = None, include_deleted: bool = False):
        query = self.db.query(UnidadContenido).filter(
            (UnidadContenido.titulo.contains(termino)) |
            (UnidadContenido.contenido.contains(termino)) |
            (UnidadContenido.resumen.contains(termino))
        )
        
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if id_agente:
            query = query.filter(UnidadContenido.id_agente == id_agente)
        
        return query.all()
    
    def get_statistics(self, id_agente: Optional[int] = None, include_deleted: bool = False):
        from sqlalchemy import func
        
        query = self.db.query(
            UnidadContenido.estado,
            func.count(UnidadContenido.id_contenido).label('total')
        )
        
        if not include_deleted:
            query = query.filter(UnidadContenido.eliminado == False)
        
        if id_agente:
            query = query.filter(UnidadContenido.id_agente == id_agente)
        
        return query.group_by(UnidadContenido.estado).all()
    
    # 🔥 NUEVO MÉTODO: Actualizar vigencias masivamente
    def actualizar_vigencias_masivo(self, id_agente: Optional[int] = None):
        """
        Actualiza el estado de todos los contenidos según sus fechas de vigencia
        """
        query = self.db.query(UnidadContenido).filter(
            UnidadContenido.eliminado == False,
            UnidadContenido.fecha_vigencia_inicio.isnot(None),
            UnidadContenido.fecha_vigencia_fin.isnot(None)
        )
        
        if id_agente:
            query = query.filter(UnidadContenido.id_agente == id_agente)
        
        contenidos = query.all()
        actualizados = 0
        
        for contenido in contenidos:
            estado_anterior = contenido.estado
            self._aplicar_vigencia_automatica(contenido)
            if estado_anterior != contenido.estado:
                actualizados += 1
        
        if actualizados > 0:
            self.db.commit()
        
        return {
            "total_revisados": len(contenidos),
            "actualizados": actualizados,
            "sin_cambios": len(contenidos) - actualizados
        }