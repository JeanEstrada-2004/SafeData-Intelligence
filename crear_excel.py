import pandas as pd
from datetime import datetime

# Datos de ejemplo para el archivo Excel
datos_ejemplo = [
    {
        'fecha_registro': '2024-01-15',
        'hora_registro': '08:30',
        'nombre_comisaria': 'Comisaría Central Arequipa',
        'efectivo_policial': 'Sub Oficial Juan Carlos Pérez',
        'nombre_denunciante': 'María Elena García López',
        'distrito': 'Arequipa',
        'hora_hecho': '20:15',
        'tipo_denuncia': 'Robo de celular',
        'observaciones': 'Robo en vía pública cerca al mercado central'
    },
    {
        'fecha_registro': '2024-01-15',
        'hora_registro': '09:45',
        'nombre_comisaria': 'Comisaría Cayma',
        'efectivo_policial': 'Cabo Ana María Rodriguez',
        'nombre_denunciante': 'Carlos Alberto Mendoza',
        'distrito': 'Cayma',
        'hora_hecho': '22:30',
        'tipo_denuncia': 'Violencia familiar',
        'observaciones': 'Agresión física por parte del conviviente'
    },
    {
        'fecha_registro': '2024-01-15',
        'hora_registro': '10:20',
        'nombre_comisaria': 'Comisaría Cerro Colorado',
        'efectivo_policial': 'Sub Oficial Luis Fernando Torres',
        'nombre_denunciante': 'Rosa María Quispe Mamani',
        'distrito': 'Cerro Colorado',
        'hora_hecho': '19:00',
        'tipo_denuncia': 'Hurto menor',
        'observaciones': 'Sustracción de dinero en efectivo del bolso'
    },
    {
        'fecha_registro': '2024-01-16',
        'hora_registro': '14:15',
        'nombre_comisaria': 'Comisaría Paucarpata',
        'efectivo_policial': 'Cabo Pedro Alejandro Silva',
        'nombre_denunciante': 'Miguel Ángel Huamán',
        'distrito': 'Paucarpata',
        'hora_hecho': '12:45',
        'tipo_denuncia': 'Daños contra el patrimonio',
        'observaciones': 'Rayado de vehículo estacionado'
    },
    {
        'fecha_registro': '2024-01-16',
        'hora_registro': '15:30',
        'nombre_comisaria': 'Comisaría Central Arequipa',
        'efectivo_policial': 'Sub Oficial Carmen Rosa Flores',
        'nombre_denunciante': 'José Luis Vargas Cáceres',
        'distrito': 'Arequipa',
        'hora_hecho': '23:15',
        'tipo_denuncia': 'Perturbación del orden público',
        'observaciones': 'Música a alto volumen en horario no permitido'
    },
    {
        'fecha_registro': '2024-01-17',
        'hora_registro': '08:00',
        'nombre_comisaria': 'Comisaría Cayma',
        'efectivo_policial': 'Cabo Roberto Carlos Mamani',
        'nombre_denunciante': 'Ana Patricia Morales',
        'distrito': 'Cayma',
        'hora_hecho': '06:30',
        'tipo_denuncia': 'Robo de vehículo',
        'observaciones': 'Sustracción de motocicleta marca Honda'
    },
    {
        'fecha_registro': '2024-01-17',
        'hora_registro': '11:20',
        'nombre_comisaria': 'Comisaría Cerro Colorado',
        'efectivo_policial': 'Sub Oficial María Teresa Condori',
        'nombre_denunciante': 'Francisco Javier Anco',
        'distrito': 'Cerro Colorado',
        'hora_hecho': '21:00',
        'tipo_denuncia': 'Estafa',
        'observaciones': 'Estafa mediante redes sociales por S/. 500'
    },
    {
        'fecha_registro': '2024-01-18',
        'hora_registro': '13:45',
        'nombre_comisaria': 'Comisaría Paucarpata',
        'efectivo_policial': 'Cabo Diana Elizabeth Ccopa',
        'nombre_denunciante': 'Lucía Beatriz Chávez',
        'distrito': 'Paucarpata',
        'hora_hecho': '16:20',
        'tipo_denuncia': 'Amenazas',
        'observaciones': 'Amenazas verbales por parte del ex pareja'
    },
    {
        'fecha_registro': '2024-01-18',
        'hora_registro': '16:10',
        'nombre_comisaria': 'Comisaría Central Arequipa',
        'efectivo_policial': 'Sub Oficial Raúl Eduardo Pinto',
        'nombre_denunciante': 'Elena Sofía Apaza',
        'distrito': 'Arequipa',
        'hora_hecho': '14:30',
        'tipo_denuncia': 'Hurto agravado',
        'observaciones': 'Hurto de cartera en transporte público'
    },
    {
        'fecha_registro': '2024-01-19',
        'hora_registro': '09:30',
        'nombre_comisaria': 'Comisaría Cayma',
        'efectivo_policial': 'Cabo Sandra Liliana Ramos',
        'nombre_denunciante': 'Fernando Gabriel Llerena',
        'distrito': 'Cayma',
        'hora_hecho': '03:45',
        'tipo_denuncia': 'Robo con violencia',
        'observaciones': 'Asalto en cajero automático con arma blanca'
    },
    {
        'fecha_registro': '2024-01-19',
        'hora_registro': '12:00',
        'nombre_comisaria': 'Comisaría Cerro Colorado',
        'efectivo_policial': 'Sub Oficial Jorge Antonio Sulla',
        'nombre_denunciante': 'Patricia Roxana Medina',
        'distrito': 'Cerro Colorado',
        'hora_hecho': '18:15',
        'tipo_denuncia': 'Violencia psicológica',
        'observaciones': 'Maltrato psicológico continuo en el hogar'
    },
    {
        'fecha_registro': '2024-01-20',
        'hora_registro': '07:45',
        'nombre_comisaria': 'Comisaría Paucarpata',
        'efectivo_policial': 'Cabo Wilson Edmundo Huanca',
        'nombre_denunciante': 'Ricardo Manuel Zuñiga',
        'distrito': 'Paucarpata',
        'hora_hecho': '22:10',
        'tipo_denuncia': 'Usurpación de terreno',
        'observaciones': 'Invasión de terreno de propiedad familiar'
    }
]

# Crear DataFrame
df = pd.DataFrame(datos_ejemplo)

# Guardar como Excel
df.to_excel('ejemplo_denuncias.xlsx', index=False)

print("✅ Archivo ejemplo_denuncias.xlsx creado exitosamente!")
print(f"📊 Total de registros: {len(datos_ejemplo)}")
print("\n📋 Columnas del archivo:")
for col in df.columns:
    print(f"   - {col}")

print("\n💡 Ahora puedes usar este archivo para probar la carga en tu sistema!")