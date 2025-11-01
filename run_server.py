#!/usr/bin/env python3
"""
Script para ejecutar el servidor de desarrollo del Sistema de Denuncias
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Verificar si están instaladas las dependencias"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import psycopg2
        import pandas
        import openpyxl
        print("✅ Todas las dependencias están instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("💡 Ejecuta: pip install -r requirements.txt")
        return False

def check_database():
    """Verificar conexión a la base de datos"""
    try:
        from app.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ Conexión a base de datos exitosa")
        return True
    except Exception as e:
        print(f"❌ Error de conexión a base de datos: {e}")
        print("💡 Verifica que PostgreSQL esté ejecutándose y las credenciales sean correctas")
        return False

def create_directories():
    """Crear directorios necesarios"""
    directories = [
        "static/uploads",
        "static/css",
        "static/js"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directorios creados/verificados")

def run_server():
    """Ejecutar el servidor de desarrollo"""
    print("\n🚀 Iniciando servidor de desarrollo...")
    print("📍 URL: http://localhost:8000")
    print("📚 Documentación API: http://localhost:8000/docs")
    print("⏹️  Para detener el servidor: Ctrl+C\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")

def main():
    """Función principal"""
    print("🔧 Sistema de Denuncias Ciudadanas - Iniciando...")
    
    # Verificar dependencias
    if not check_requirements():
        sys.exit(1)
    
    # Crear directorios
    create_directories()
    
    # Verificar base de datos
    if not check_database():
        print("⚠️  Continuando sin verificación de base de datos...")
    
    # Ejecutar servidor
    run_server()

if __name__ == "__main__":
    main()