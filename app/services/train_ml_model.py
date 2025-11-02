"""
Script para entrenar un modelo de Machine Learning avanzado
para predicción de delitos.

Este script es opcional y mejora las predicciones usando:
- Random Forest Classifier
- Features: zona, turno, día de semana, mes, hora
- Almacena el modelo entrenado en disco

Uso:
    python -m app.services.train_ml_model
"""

import pickle
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

from app.database import DATABASE_URL


def entrenar_modelo():
    """Entrena un modelo de ML para predicción de riesgo."""
    
    print("🤖 Iniciando entrenamiento del modelo de predicción...")
    
    # 1. Conectar a la base de datos
    engine = create_engine(DATABASE_URL)
    
    # 2. Cargar datos de denuncias
    query = """
    SELECT 
        zona_denuncia,
        turno,
        tipo_denuncia,
        fecha_hora_suceso,
        EXTRACT(HOUR FROM fecha_hora_suceso) as hora,
        EXTRACT(DOW FROM fecha_hora_suceso) as dia_semana,
        EXTRACT(MONTH FROM fecha_hora_suceso) as mes,
        EXTRACT(YEAR FROM fecha_hora_suceso) as anio
    FROM denuncias
    WHERE fecha_hora_suceso IS NOT NULL
        AND zona_denuncia IS NOT NULL
        AND turno IS NOT NULL
    """
    
    print("📊 Cargando datos desde la base de datos...")
    df = pd.read_sql(query, engine)
    
    if len(df) < 100:
        print("⚠️  Advertencia: Pocos datos disponibles. Se requieren al menos 100 registros.")
        print(f"   Registros encontrados: {len(df)}")
        return
    
    print(f"✅ Datos cargados: {len(df)} registros")
    
    # 3. Crear variable objetivo (nivel de riesgo)
    # Calculamos la densidad de delitos por zona-turno-día
    df['combinacion'] = df['zona_denuncia'].astype(str) + '_' + \
                        df['turno'].str.lower() + '_' + \
                        df['dia_semana'].astype(str)
    
    densidad = df.groupby('combinacion').size()
    percentil_75 = densidad.quantile(0.75)
    percentil_50 = densidad.quantile(0.50)
    
    def calcular_riesgo(grupo):
        count = len(grupo)
        if count >= percentil_75:
            return 'ALTO'
        elif count >= percentil_50:
            return 'MEDIO'
        else:
            return 'BAJO'
    
    df['nivel_riesgo'] = df.groupby('combinacion')['combinacion'].transform(
        lambda x: calcular_riesgo(df[df['combinacion'] == x.iloc[0]])
    )
    
    print("\n📈 Distribución de nivel de riesgo:")
    print(df['nivel_riesgo'].value_counts())
    
    # 4. Preparar features
    le_turno = LabelEncoder()
    le_tipo = LabelEncoder()
    
    df['turno_encoded'] = le_turno.fit_transform(df['turno'].str.lower())
    
    # Manejar valores nulos en tipo_denuncia
    df['tipo_denuncia'] = df['tipo_denuncia'].fillna('DESCONOCIDO')
    df['tipo_encoded'] = le_tipo.fit_transform(df['tipo_denuncia'])
    
    # Features finales
    features = [
        'zona_denuncia',
        'turno_encoded',
        'tipo_encoded',
        'hora',
        'dia_semana',
        'mes'
    ]
    
    X = df[features]
    y = df['nivel_riesgo']
    
    # 5. Dividir en train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\n🔀 Datos divididos:")
    print(f"   Entrenamiento: {len(X_train)} registros")
    print(f"   Prueba: {len(X_test)} registros")
    
    # 6. Entrenar modelo
    print("\n🏋️  Entrenando Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # 7. Evaluar modelo
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\n✅ Modelo entrenado con éxito!")
    print(f"   Precisión en datos de prueba: {accuracy * 100:.2f}%")
    print("\n📊 Reporte de clasificación:")
    print(classification_report(y_test, y_pred))
    
    # 8. Importancia de features
    print("\n🔍 Importancia de características:")
    importances = pd.DataFrame({
        'feature': features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print(importances)
    
    # 9. Guardar modelo y encoders
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    model_data = {
        'model': model,
        'le_turno': le_turno,
        'le_tipo': le_tipo,
        'features': features,
        'accuracy': accuracy,
        'trained_at': datetime.now().isoformat()
    }
    
    model_path = models_dir / "prediccion_delitos.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n💾 Modelo guardado en: {model_path}")
    print("✨ ¡Entrenamiento completado!")


if __name__ == "__main__":
    try:
        entrenar_modelo()
    except Exception as e:
        print(f"\n❌ Error durante el entrenamiento: {e}")
        import traceback
        traceback.print_exc()
