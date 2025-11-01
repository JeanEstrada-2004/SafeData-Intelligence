#!/usr/bin/env python3
"""
Script para crear datos de ejemplo en la base de datos
"""

import sys
import os
from datetime import datetime, date, time
import pandas as pd

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app import models, schemas, crud

def create_tables():
    """Crear todas las tablas"""
    print("📋 Creando tablas en la base de datos...")
    models.Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente")

def create_sample_denuncias():
    """Crear denuncias de ejemplo"""
    db = SessionLocal()
    
    # Verificar si ya hay datos
    count = crud.get_denuncia_count(db)
    if count > 0:
        print(f"ℹ️  Ya existen {count} denuncias en la base de datos")
        response = input("¿Deseas agregar más datos de ejemplo? (s/N): ")
        if response.lower() not in ['s', 'si', 'sí', 'yes', 'y']:
            db.close()
            return
    
    print("📝 Creando denuncias de ejemplo...")
    
    # Datos de ejemplo
    denuncias_ejemplo = [
        {
            'fecha_registro': date(2024, 1, 15),
            'hora_registro': time(8, 30),
            'nombre_comisaria': 'Comisaría Central Arequipa',
            'efectivo_policial': 'Sub Oficial Juan Carlos Pérez',
            'nombre_denunciante': 'María Elena García López',
            'distrito': 'Arequipa',
            'hora_hecho': time(20, 15),
            'tipo_denuncia': 'Robo de celular',
            'observaciones': 'Robo en vía pública cerca al mercado central'
        },
        {
            'fecha_registro': date(2024, 1, 15),
            'hora_registro': time(9, 45),
            'nombre_comisaria': 'Comisaría Cayma',
            'efectivo_policial': 'Cabo Ana María Rodriguez',
            'nombre_denunciante': 'Carlos Alberto Mendoza',
            'distrito': 'Cayma',
            'hora_hecho': time(22, 30),
            'tipo_denuncia': 'Violencia familiar',
            'observaciones': 'Agresión física por parte del conviviente'
        },
        {
            'fecha_registro': date(2024, 1, 15),
            'hora_registro': time(10, 20),
            'nombre_comisaria': 'Comisaría Cerro Colorado',
            'efectivo_policial': 'Sub Oficial Luis Fernando Torres',
            'nombre_denunciante': 'Rosa María Quispe Mamani',
            'distrito': 'Cerro Colorado',
            'hora_hecho': time(19, 0),
            'tipo_denuncia': 'Hurto menor',
            'observaciones': 'Sustracción de dinero en efectivo del bolso'
        },
        {
            'fecha_registro': date(2024, 1, 16),
            'hora_registro': time(14, 15),
            'nombre_comisaria': 'Comisaría Paucarpata',
            'efectivo_policial': 'Cabo Pedro Alejandro Silva',
            'nombre_denunciante': 'Miguel Ángel Huamán',
            'distrito': 'Paucarpata',
            'hora_hecho': time(12, 45),
            'tipo_denuncia': 'Daños contra el patrimonio',
            'observaciones': 'Rayado de vehículo estacionado'
        },
        {
            'fecha_registro': date(2024, 1, 16),
            'hora_registro': time(15, 30),
            'nombre_comisaria': 'Comisaría Central Arequipa',
            'efectivo_policial': 'Sub Oficial Carmen Rosa Flores',
            'nombre_denunciante': 'José Luis Vargas Cáceres',
            'distrito': 'Arequipa',
            'hora_hecho': time(23, 15),
            'tipo_denuncia': 'Perturbación del orden público',
            'observaciones': 'Música a alto volumen en horario no permitido'
        },
        {
            'fecha_registro': date(2024, 1, 17),
            'hora_registro': time(8, 0),
            'nombre_comisaria': 'Comisaría Cayma',
            'efectivo_policial': 'Cabo Roberto Carlos Mamani',
            'nombre_denunciante': 'Ana Patricia Morales',
            'distrito': 'Cayma',
            'hora_hecho': time(6, 30),
            'tipo_denuncia': 'Robo de vehículo',
            'observaciones': 'Sustracción de motocicleta marca Honda'
        },
        {
            'fecha_registro': date(2024, 1, 17),
            'hora_registro': time(11, 20),
            'nombre_comisaria': 'Comisaría Cerro Colorado',
            'efectivo_policial': 'Sub Oficial María Teresa Condori',
            'nombre_denunciante': 'Francisco Javier Anco',
            'distrito': 'Cerro Colorado',
            'hora_hecho': time(21, 0),
            'tipo_denuncia': 'Estafa',
            'observaciones': 'Estafa mediante redes sociales por S/. 500'
        },
        {
            'fecha_registro': date(2024, 1, 18),
            'hora_registro': time(13, 45),
            'nombre_comisaria': 'Comisaría Paucarpata',
            'efectivo_policial': 'Cabo Diana Elizabeth Ccopa',
            'nombre_denunciante': 'Lucía Beatriz Chávez',
            'distrito': 'Paucarpata',
            'hora_hecho': time(16, 20),
            'tipo_denuncia': 'Amenazas',
            'observaciones': 'Amenazas verbales por parte del ex pareja'
        },
        {
            'fecha_registro': date(2024, 1, 18),
            'hora_registro': time(16, 10),
            'nombre_comisaria': 'Comisaría Central Arequipa',
            'efectivo_policial': 'Sub Oficial Raúl Eduardo Pinto',
            'nombre_denunciante': 'Elena Sofía Apaza',
            'distrito': 'Arequipa',
            'hora_hecho': time(14, 30),
            'tipo_denuncia': 'Hurto agravado',
            'observaciones': 'Hurto de cartera en transporte público'
        },
        {
            'fecha_registro': date(2024, 1, 19),
            'hora_registro': time(9, 30),
            'nombre_comisaria': 'Comisaría Cayma',
            'efectivo_policial': 'Cabo Sandra Liliana Ramos',
            'nombre_denunciante': 'Fernando Gabriel Llerena',
            'distrito': 'Cayma',
            'hora_hecho': time(3, 45),
            'tipo_denuncia': 'Robo con violencia',
            'observaciones': 'Asalto en cajero automático con arma blanca'
        },
        {
            'fecha_registro': date(2024, 1, 19),
            'hora_registro': time(12, 0),
            'nombre_comisaria': 'Comisaría Cerro Colorado',
            'efectivo_policial': 'Sub Oficial Jorge Antonio Sulla',
            'nombre_denunciante': 'Patricia Roxana Medina',
            'distrito': 'Cerro Colorado',
            'hora_hecho': time(18, 15),
            'tipo_denuncia': 'Violencia psicológica',
            'observaciones': 'Maltrato psicológico continuo en el hogar'
        },
        {
            'fecha_registro': date(2024, 1, 20),
            'hora_registro': time(7, 45),
            'nombre_comisaria': 'Comisaría Paucarpata',
            'efectivo_policial': 'Cabo Wilson Edmundo Huanca',
            'nombre_denunciante': 'Ricardo Manuel Zuñiga',
            'distrito': 'Paucarpata',
            'hora_hecho': time(22, 10),
            'tipo_denuncia': 'Usurpación de terreno',
            'observaciones': 'Invasión de terreno de propiedad familiar'
        }
    ]
    
    # Convertir a esquemas de Pydantic
    denuncias_schemas = [schemas.DenunciaCreate(**denuncia) for denuncia in denuncias_ejemplo]
    
    try:
        # Insertar en lotes
        count = crud.create_denuncias_bulk(db, denuncias_schemas)
        print(f"✅ Se crearon {count} denuncias de ejemplo exitosamente")
        
        # Mostrar estadísticas
        total = crud.get_denuncia_count(db)
        print(f"📊 Total de denuncias en la base de datos: {total}")
        
        # Mostrar distribución por distrito
        por_distrito = crud.get_denuncias_por_distrito(db)
        print("\n📍 Distribución por distrito:")
        for distrito, cantidad in por_distrito.items():
            print(f"   {distrito}: {cantidad} denuncias")
            
    except Exception as e:
        print(f"❌ Error creando datos de ejemplo: {e}")
    finally:
        db.close()

def create_excel_sample():
    """Crear archivo Excel de ejemplo"""
    print("📄 Creando archivo Excel de ejemplo...")
    
    datos_excel = [
        {
            'fecha_registro': '2024-01-21',
            'hora_registro': '08:30',
            'nombre_comisaria': 'Comisaría Central Arequipa',
            'efectivo_policial': 'Sub Oficial Carmen López',
            'nombre_denunciante': 'Pedro Antonio Sánchez',
            'distrito': 'Arequipa',
            'hora_hecho': '20:15',
            'tipo_denuncia': 'Robo de billetera',
            'observaciones': 'Robo en transporte público línea 12'
        },
        {
            'fecha_registro': '2024-01-21',
            'hora_registro': '10:45',
            'nombre_comisaria': 'Comisaría Cayma',
            'efectivo_policial': 'Cabo María Fernández',
            'nombre_denunciante': 'Sofía Elena Torres',
            'distrito': 'Cayma',
            'hora_hecho': '19:30',
            'tipo_denuncia': 'Violencia doméstica',
            'observaciones': 'Agresión física en el domicilio'
        },
        {
            'fecha_registro': '2024-01-21',
            'hora_registro': '14:20',
            'nombre_comisaria': 'Comisaría Cerro Colorado',
            'efectivo_policial': 'Sub Oficial Diego Morales',
            'nombre_denunciante': 'Roberto Carlos Díaz',
            'distrito': 'Cerro Colorado',
            'hora_hecho': '12:00',
            'tipo_denuncia': 'Daño a propiedad privada',
            'observaciones': 'Rotura de luna de vehículo'
        }
    ]
    
    df = pd.DataFrame(datos_excel)
    filename = 'ejemplo_denuncias_nuevas.xlsx'
    df.to_excel(filename, index=False)
    print(f"✅ Archivo creado: {filename}")
    print("💡 Puedes usar este archivo para probar la función de carga")

def main():
    """Función principal"""
    print("🔧 Creando datos de ejemplo para el Sistema de Denuncias\n")
    
    try:
        # Crear tablas
        create_tables()
        
        # Crear datos de ejemplo
        create_sample_denuncias()
        
        # Crear archivo Excel de ejemplo
        create_excel_sample()
        
        print("\n🎉 ¡Datos de ejemplo creados exitosamente!")
        print("🌐 Ahora puedes ejecutar la aplicación con: python run_server.py")
        
    except Exception as e:
        print(f"❌ Error durante la creación de datos: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()