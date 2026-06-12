"""Router para predicción de delitos con IA/ML."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel
import json
import pickle
import os
import numpy as np
from pathlib import Path

from ..database import get_db
from ..models import Denuncia, PredictionLog, User
from ..utils.seguridad import audit_event, require_roles

router = APIRouter()


# Modelo Pydantic para la solicitud
class PrediccionRequest(BaseModel):
    zona: int
    turno: str
    tipo_denuncia: Optional[str] = ""
    dia_semana: Optional[int] = None

# Cargar modelo ML si existe
MODEL_PATH = Path("models/prediccion_delitos.pkl")
ml_model = None
label_encoder = None
MODEL_VERSION = "heuristica"
if MODEL_PATH.exists():
    try:
        with open(MODEL_PATH, "rb") as f:
            model_data = pickle.load(f)
            # Extraer el modelo y el encoder del diccionario
            ml_model = model_data['model']
            label_encoder = model_data.get('label_encoder')
            MODEL_VERSION = str(model_data.get("trained_at") or MODEL_PATH.stat().st_mtime)
        print(f"✅ Modelo ML cargado desde {MODEL_PATH}")
    except Exception as e:
        print(f"⚠️ Error al cargar modelo ML: {e}")
        ml_model = None
        label_encoder = None
else:
    print(f"⚠️ Modelo ML no encontrado en {MODEL_PATH}. Usando sistema basado en reglas.")


@router.post("/prediccion")
async def predecir_riesgo(
    request_http: Request,
    request: PrediccionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Gerente", "JefeOperaciones", "Analista")),
):
    """
    Predice el nivel de riesgo de delitos basándose en:
    - Zona
    - Turno (mañana, tarde, noche)
    - Tipo de denuncia (opcional)
    - Día de la semana (opcional)
    
    Retorna:
    - nivel_riesgo: BAJO, MEDIO, ALTO
    - probabilidad: 0.0 a 1.0
    - incidentes_historicos: cantidad de denuncias similares
    - recomendacion: texto con sugerencias
    """
    
    # Extraer datos del request
    zona = request.zona
    turno = request.turno
    tipo_denuncia = request.tipo_denuncia
    dia_semana = request.dia_semana
    
    try:
        # Si no se proporciona día de semana, usar el día actual
        if dia_semana is None:
            dia_semana = datetime.now().weekday()
        
        # Normalizar tipo_denuncia (convertir string vacío a None)
        if tipo_denuncia == "":
            tipo_denuncia = None
        
        # Normalizar turno
        turno = turno.lower().strip()
        
        # Variables inicializadas
        nivel_riesgo = "MEDIO"
        probabilidad = 0.5
        usa_modelo_ml = False
        model_type = "heuristica"
        
        # **USAR MODELO ML SI ESTÁ DISPONIBLE**
        if ml_model is not None:
            try:
                # Preparar features para el modelo
                # Mapeo de turnos a números
                turno_map = {"mañana": 0, "tarde": 1, "noche": 2, "madrugada": 3}
                turno_encoded = turno_map.get(turno, 0)
                
                # Mapeo de tipos (si no hay tipo, usar 0)
                tipo_encoded = 0
                if tipo_denuncia:
                    # Obtener tipos únicos de la base de datos
                    tipos_db = db.query(Denuncia.tipo_denuncia).distinct().all()
                    tipos_list = [t[0] for t in tipos_db if t[0]]
                    if tipo_denuncia in tipos_list:
                        tipo_encoded = tipos_list.index(tipo_denuncia)
                
                # Hora actual o promedio según turno
                hora_map = {"mañana": 9, "tarde": 15, "noche": 21, "madrugada": 3}
                hora = hora_map.get(turno, 12)
                
                # Mes actual
                mes = datetime.now().month
                
                # Crear array de features: [zona, turno, tipo, hora, dia_semana, mes]
                features = np.array([[zona, turno_encoded, tipo_encoded, hora, dia_semana, mes]])
                
                # Predecir con el modelo
                prediccion = ml_model.predict(features)[0]
                probabilidades = ml_model.predict_proba(features)[0]
                
                # La predicción es 'ALTO' o 'MEDIO'
                nivel_riesgo = prediccion
                probabilidad = max(probabilidades)
                usa_modelo_ml = True
                model_type = "ml"
                
                print(f"🤖 Predicción ML: {nivel_riesgo} ({probabilidad:.2%})")
                
            except Exception as e:
                print(f"⚠️ Error en predicción ML: {e}. Usando sistema de reglas.")
                usa_modelo_ml = False
        
        # **SISTEMA BASADO EN REGLAS (Si no hay modelo ML o falló)**
        if not usa_modelo_ml:
            # 1. Consultar histórico de denuncias en esa zona y turno
            query = db.query(Denuncia).filter(
                Denuncia.zona_denuncia == zona,
                func.lower(Denuncia.turno) == turno
            )
            
            # Filtrar por tipo si se especifica
            if tipo_denuncia:
                query = query.filter(
                    func.lower(Denuncia.tipo_denuncia).like(f"%{tipo_denuncia.lower()}%")
                )
            
            total_denuncias = query.count()
            
            # 2. Calcular denuncias por día de la semana
            denuncias_por_dia = {}
            for d in range(7):
                count = query.filter(
                    extract('dow', Denuncia.fecha_hora_suceso) == (d + 1) % 7
                ).count()
                denuncias_por_dia[d] = count
            
            # Denuncias en el día específico
            denuncias_dia = denuncias_por_dia.get(dia_semana, 0)
            
            # 3. Calcular densidad (denuncias por día)
            if total_denuncias > 0:
                # Obtener fecha más antigua y más reciente
                fecha_min = query.order_by(Denuncia.fecha_hora_suceso.asc()).first()
                fecha_max = query.order_by(Denuncia.fecha_hora_suceso.desc()).first()
                
                if fecha_min and fecha_max:
                    dias_historico = max(1, (fecha_max.fecha_hora_suceso - fecha_min.fecha_hora_suceso).days)
                    densidad_diaria = total_denuncias / dias_historico
                else:
                    densidad_diaria = total_denuncias
            else:
                densidad_diaria = 0
            
            # 4. Calcular nivel de riesgo
            # Umbrales (puedes ajustarlos según tus datos)
            if densidad_diaria >= 5:
                nivel_riesgo = "ALTO"
                probabilidad = min(0.95, 0.5 + (densidad_diaria / 10))
            elif densidad_diaria >= 2:
                nivel_riesgo = "MEDIO"
                probabilidad = 0.3 + (densidad_diaria / 10)
            else:
                nivel_riesgo = "BAJO"
                probabilidad = max(0.05, densidad_diaria / 10)
            
            # Ajustar por día de la semana (fin de semana suele tener más incidentes)
            if dia_semana in [5, 6]:  # Sábado y Domingo
                probabilidad = min(1.0, probabilidad * 1.2)
        
        # **OBTENER ESTADÍSTICAS ADICIONALES (Común a ambos métodos)**
        # Consultar histórico para estadísticas
        query_stats = db.query(Denuncia).filter(
            Denuncia.zona_denuncia == zona,
            func.lower(Denuncia.turno) == turno
        )
        
        if tipo_denuncia:
            query_stats = query_stats.filter(
                func.lower(Denuncia.tipo_denuncia).like(f"%{tipo_denuncia.lower()}%")
            )
        
        total_denuncias = query_stats.count()
        
        # Calcular denuncias en este día de semana
        denuncias_dia = query_stats.filter(
            extract('dow', Denuncia.fecha_hora_suceso) == (dia_semana + 1) % 7
        ).count()
        
        # Calcular densidad
        if total_denuncias > 0:
            fecha_min = query_stats.order_by(Denuncia.fecha_hora_suceso.asc()).first()
            fecha_max = query_stats.order_by(Denuncia.fecha_hora_suceso.desc()).first()
            if fecha_min and fecha_max:
                dias_historico = max(1, (fecha_max.fecha_hora_suceso - fecha_min.fecha_hora_suceso).days)
                densidad_diaria = total_denuncias / dias_historico
            else:
                densidad_diaria = total_denuncias
        else:
            densidad_diaria = 0
        
        # **VALIDAR SI HAY SUFICIENTES DATOS**
        if total_denuncias == 0:
            output = {
                "zona": zona,
                "turno": turno,
                "dia_semana": dia_semana,
                "nivel_riesgo": "SIN_DATOS",
                "probabilidad": 0,
                "incidentes_historicos": 0,
                "densidad_diaria": 0,
                "denuncias_este_dia": 0,
                "tipos_comunes": [],
                "recomendaciones": [{
                    "tipo": "info",
                    "texto": "📊 No hay datos históricos suficientes para esta combinación de zona y turno. Se recomienda patrullaje preventivo estándar."
                }],
                "mensaje": "No se encontraron datos históricos para realizar una predicción confiable.",
                "model_type": "sin_datos",
                "model_version": MODEL_VERSION,
                "explicacion": "No se encontraron registros históricos para la combinación seleccionada.",
            }
            _log_prediction(db, user, request, output, "sin_datos", "SIN_DATOS")
            audit_event(db, request_http, "prediction_query", user=user, detail={"risk_level": "SIN_DATOS", "model_type": "sin_datos"})
            return output
        
        # 5. Obtener tipos de delitos más comunes en esa zona/turno
        tipos_comunes = db.query(
            Denuncia.tipo_denuncia,
            func.count(Denuncia.id).label('cantidad')
        ).filter(
            Denuncia.zona_denuncia == zona,
            func.lower(Denuncia.turno) == turno,
            Denuncia.tipo_denuncia.isnot(None)
        ).group_by(
            Denuncia.tipo_denuncia
        ).order_by(
            func.count(Denuncia.id).desc()
        ).limit(5).all()
        
        tipos_lista = [{"tipo": t[0], "cantidad": t[1]} for t in tipos_comunes]
        
        # 6. Generar recomendaciones
        recomendaciones = generar_recomendaciones(
            nivel_riesgo, 
            turno, 
            tipos_lista,
            densidad_diaria
        )
        
        output = {
            "zona": zona,
            "turno": turno,
            "dia_semana": dia_semana,
            "nivel_riesgo": nivel_riesgo,
            "probabilidad": round(probabilidad, 3),
            "incidentes_historicos": total_denuncias,
            "densidad_diaria": round(densidad_diaria, 2),
            "denuncias_este_dia": denuncias_dia,
            "tipos_comunes": tipos_lista,
            "recomendaciones": recomendaciones,
            "model_type": model_type,
            "model_version": MODEL_VERSION,
            "explicacion": _build_explanation(model_type, total_denuncias, densidad_diaria),
        }
        _log_prediction(db, user, request, output, model_type, nivel_riesgo)
        audit_event(db, request_http, "prediction_query", user=user, detail={"risk_level": nivel_riesgo, "model_type": model_type})
        return output
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al predecir: {str(e)}")


def generar_recomendaciones(nivel_riesgo: str, turno: str, tipos: list, densidad: float) -> list:
    """Genera recomendaciones basadas en el nivel de riesgo."""
    recomendaciones = []
    
    if nivel_riesgo == "ALTO":
        recomendaciones.append({
            "tipo": "urgente",
            "texto": f"⚠️ Riesgo ALTO detectado. Se recomienda patrullaje inmediato en turno {turno}."
        })
        recomendaciones.append({
            "tipo": "accion",
            "texto": "Incrementar presencia policial en un 50% durante este horario."
        })
        if tipos:
            tipo_principal = tipos[0]["tipo"]
            recomendaciones.append({
                "tipo": "info",
                "texto": f"Delito más frecuente: {tipo_principal}. Enfocar prevención específica."
            })
    
    elif nivel_riesgo == "MEDIO":
        recomendaciones.append({
            "tipo": "preventivo",
            "texto": f"Riesgo MEDIO. Patrullaje preventivo recomendado en turno {turno}."
        })
        recomendaciones.append({
            "tipo": "accion",
            "texto": "Mantener vigilancia constante y respuesta rápida ante alertas."
        })
    
    else:  # BAJO
        recomendaciones.append({
            "tipo": "normal",
            "texto": f"Riesgo BAJO. Monitoreo estándar suficiente en turno {turno}."
        })
        recomendaciones.append({
            "tipo": "info",
            "texto": "Continuar con patrullaje rutinario según cronograma establecido."
        })
    
    return recomendaciones


def _build_explanation(model_type: str, total: int, densidad: float) -> str:
    if model_type == "ml":
        return "Resultado calculado con el modelo ML disponible y contrastado con estadísticas históricas."
    return f"Resultado calculado con heurística de densidad histórica: {total} incidencias y densidad diaria {densidad:.2f}."


def _log_prediction(db: Session, user: User, request: PrediccionRequest, output: Dict[str, Any], model_type: str, risk_level: str) -> None:
    """Guarda el registro de predicción en base de datos para auditoría."""
    try:
        db.add(
            PredictionLog(
                user_id=user.id,
                input_json=request.model_dump(),
                output_json=output,
                model_type=model_type,
                model_version=MODEL_VERSION,
                risk_level=risk_level,
            )
        )
        db.commit()
        print(f"✅ Predicción guardada en base de datos (nivel: {risk_level})")
    except Exception as e:
        db.rollback()
        print(f"⚠️ No se pudo guardar la predicción en auditoría: {e}")


@router.get("/estadisticas/zona/{zona}")
async def estadisticas_zona(
    zona: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Gerente", "JefeOperaciones", "Analista")),
):
    """Obtiene estadísticas completas de una zona."""
    
    # Total de denuncias
    total = db.query(func.count(Denuncia.id)).filter(
        Denuncia.zona_denuncia == zona
    ).scalar()
    
    # Por turno
    por_turno = db.query(
        Denuncia.turno,
        func.count(Denuncia.id).label('cantidad')
    ).filter(
        Denuncia.zona_denuncia == zona,
        Denuncia.turno.isnot(None)
    ).group_by(Denuncia.turno).all()
    
    # Por tipo de denuncia
    por_tipo = db.query(
        Denuncia.tipo_denuncia,
        func.count(Denuncia.id).label('cantidad')
    ).filter(
        Denuncia.zona_denuncia == zona,
        Denuncia.tipo_denuncia.isnot(None)
    ).group_by(Denuncia.tipo_denuncia).order_by(
        func.count(Denuncia.id).desc()
    ).limit(10).all()
    
    return {
        "zona": zona,
        "total_denuncias": total,
        "por_turno": [{"turno": t[0], "cantidad": t[1]} for t in por_turno],
        "por_tipo": [{"tipo": t[0], "cantidad": t[1]} for t in por_tipo]
    }


@router.get("/zonas-riesgo")
async def obtener_zonas_riesgo(
    turno: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("Gerente", "JefeOperaciones", "Analista")),
):
    """Obtiene un ranking de zonas por nivel de riesgo."""
    
    query = db.query(
        Denuncia.zona_denuncia,
        func.count(Denuncia.id).label('cantidad')
    )
    
    if turno:
        query = query.filter(func.lower(Denuncia.turno) == turno.lower())
    
    zonas = query.group_by(
        Denuncia.zona_denuncia
    ).order_by(
        func.count(Denuncia.id).desc()
    ).limit(10).all()
    
    resultado = []
    for zona, cantidad in zonas:
        # Calcular nivel de riesgo simple
        if cantidad >= 100:
            nivel = "ALTO"
        elif cantidad >= 50:
            nivel = "MEDIO"
        else:
            nivel = "BAJO"
        
        resultado.append({
            "zona": zona,
            "incidentes": cantidad,
            "nivel_riesgo": nivel
        })
    
    return resultado
