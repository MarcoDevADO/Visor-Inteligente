# 🍋 Visor-Inteligente - Detección y Análisis de Objetos con YOLO

**Sistema de captura de video en tiempo real con detección de objetos, integración IoT y análisis de datos mediante machine learning**

---

## 📋 Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Características Principales](#características-principales)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [API Web](#api-web)
- [Documentación Técnica](#documentación-técnica)
- [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Descripción General

**Visor-Inteligente** es una aplicación integrada que combina:

- **Interfaz Gráfica (PyQt6)**: Aplicación de escritorio para visualización en tiempo real
- **Detección de Objetos (YOLO)**: Modelo preentrenado para identificación y clasificación
- **Servidor Web (Flask)**: API REST y streaming de video en tiempo real
- **Integración IoT (Arduino)**: Captura de datos de sensores
- **Base de Datos (PostgreSQL)**: Almacenamiento de resultados y análisis históricos
- **Streaming en Vivo (SSE)**: Server-Sent Events para actualización en tiempo real

### Caso de Uso Principal
Inspección y clasificación automatizada de lotes (ej: análisis de frutas), con validación de calidad y generación de reportes.

---

## 🖼️ Capturas de Pantalla

Estas imágenes muestran la interfaz principal, el panel web y el estado de detección en tiempo real.

![Interfaz principal](imagenes/Captura%20de%20pantalla%202026-04-03%20192648.png)

![Interfaz web](imagenes/Captura%20de%20pantalla%202026-04-03%20192612.png)

![Panel de control](imagenes/Captura%20de%20pantalla%202026-04-03%20192448.png)

---

## ✨ Características Principales

### 🎬 Captura de Video
- ✅ Captura desde cámara USB en tiempo real
- ✅ Procesamiento asíncrono con threading
- ✅ Buffer de frames thread-safe
- ✅ FPS adaptativo (30+ FPS)

### 🤖 Detección de Objetos (YOLO)
- ✅ Modelo YOLOv8 preentrenado
- ✅ Inferencia en hilo separado (no bloquea UI)
- ✅ Bbox, confianza y clase de objeto
- ✅ Latencia optimizada (100-500ms)

### 🌐 Interfaz Web
- ✅ Streaming de video en tiempo real (SSE)
- ✅ Panel de control con actualización en vivo
- ✅ Tabla de resultados por lote
- ✅ Gráficas de validación y estadísticas
- ✅ QR para acceso rápido

### 💾 Persistencia de Datos
- ✅ Guardado automático de detecciones
- ✅ Base de datos PostgreSQL (Supabase)
- ✅ Consultas optimizadas por lote
- ✅ Historial y estadísticas

### 🎨 Interfaz de Usuario
- ✅ Tema claro y oscuro
- ✅ Visualización de cámara en vivo
- ✅ Gráficas interactivas (pyqtgraph)

### 📡 Conectividad
- ✅ Comunicación serial con Arduino
- ✅ Tunel ngrok para acceso remoto
- ✅ CORS habilitado para requests desde web
- ✅ Variables de entorno seguras

---

## 📦 Requisitos Previos

### Hardware
- **Cámara USB** (compatible con OpenCV)
- **Arduino** (para sensores)
- **Puerto COM disponible** (para Arduino)
- **Conexión a Internet** (para ngrok y base de datos)

### Software
- **Python 3.8 o superior**
- **PostgreSQL 12+** (o Supabase) accesible remotamente
- **Git** (opcional, para control de versiones)

### Dependencias Python
Ver [librerias.txt](librerias.txt) para la lista completa.

---

## 🚀 Instalación

### 1. Clonar o Descargar el Proyecto
```bash
git clone <repo-url>
```

### 2. Crear Entorno Virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r librerias.txt
```
---

## ⚙️ Configuración

### Variables de Entorno (.env)

Crear archivo `.env` en la raíz del proyecto:

```env
# Ngrok (para acceso remoto - obtener en https://ngrok.com)
KEY=tu_token_ngrok_aqui

# Base de Datos PostgreSQL
URL=postgresql://usuario:password@host:puerto/dbname

# Arduino (opcional)
ARDUINO_PORT=/dev/ttyUSB0  # Windows: COM3, Linux: /dev/ttyUSB0
ARDUINO_BAUDRATE=9600
```

### Configuración de la Aplicación

En `Interfaz.py`, líneas ajustables:

```python
# Modelo YOLO
MODEL_PATH = "best.pt"
CONFIDENCE_THRESHOLD = 0.5

# Arduino
PUERTO_SERIAL = "COM3"
VELOCIDAD_SERIAL = 9600

# Flask
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

# Base de Datos
DB_TIMEOUT = 10  # segundos
```

---

## ▶️ Uso

### Iniciar Aplicación Principal
```bash
python Interfaz.py
```

### Interfaz Gráfica (PyQt6)
1. **Iniciar Captura**: Click en "Configuración"
2. **Seleccionar Lote**: Dropdown con lotes disponibles
3. **Monitor de Detecciones**: Tabla en tiempo real

### Interfaz Web
1. Abrir navegador: `http://localhost:5000`
2. Ver stream de video en vivo

### Arduino/Sensores
Conectar Puerto Serial:
```bash
# Detectar puertos disponibles
python -m serial.tools.list_ports

# En Windows: COM3, COM4, etc.
# En Linux: /dev/ttyUSB0, /dev/ttyUSB1, etc.
```

---

## 📂 Estructura del Proyecto

```
Visor-Inteligente/
├── 📄 README.md                    ← Este archivo
├── 📄 librerias.txt                ← Dependencias Python
│
├── 🐍 CÓDIGO PRINCIPAL
│   ├── Interfaz.py                 ← Punto de entrada (main)
│   ├── Querys.py                   ← Gestor de BD PostgreSQL
│   └── Estilo.py                   ← Temas PyQt6 (claro/oscuro)
│
├── 🤖 MODELOS IA
│   └── best.pt                     ← YOLO v8 (~250MB, no en git)
│
├── 📦 ARDUINO
│   └── CodigoArduino/
│       └── ArduinoCodeBanda.ino    ← Firmware para Arduino
│
├── 🌐 WEB
│   └── templates/
│       └── index.html              ← Panel web (SSE streaming)
```

## 🌐 API Web

### Endpoints Disponibles

#### 1. **GET `/`**
Página principal con panel de control
```bash
curl http://localhost:5000/
```

#### 2. **GET `/stream`**
Stream de video en vivo (SSE)
```bash
curl http://localhost:5000/stream
```
Retorna frames MJPEG en tiempo real

#### 3. **GET `/stats`**
Estadísticas del lote actual
```bash
curl http://localhost:5000/stats
{
  "lote_actual": "Lote_001",
  "validos": 45,
  "invalidos": 3,
  "total": 48,
  "porcentaje_validez": 93.75
}
```

#### 4. **POST `/select_lote`**
Cambiar lote de análisis
```bash
curl -X POST http://localhost:5000/select_lote \
  -H "Content-Type: application/json" \
  -d '{"lote": "Lote_002"}'
```

---

## 📚 Documentación Técnica

### 📖 Recursos de Aprendizaje

- Consulta el código en `Interfaz.py` para entender la arquitectura principal
- Revisa `Querys.py` para ver cómo se gestiona la base de datos
- Explore `templates/index.html` para la interfaz web
- Consulta los comentarios en el código para detalles técnicos

---

## 🔧 Solución de Problemas

### ❌ Error: "No module named 'ultralytics'"
```bash
# Instalar YOLO
pip install ultralytics
```

### ❌ Error: "Camera not found"
```bash
# Listar cámaras disponibles
python -m cv2 --version
python -c "import cv2; print(cv2.getBuildInformation())"
```

### ❌ Error: "Cannot connect to database"
1. Verificar variable `URL` en `.env`
2. Comprobar que la base de datos está en línea
3. Verificar firewall permite conexión remota

### ❌ Error: "Arduino port not found"
```bash
# Listar puertos seriales
python -m serial.tools.list_ports

# Actualizar ARDUINO_PORT en .env
```

### ❌ Error: "YOLO model too large"
1. Modelo `best.pt` (~250MB) debe estar en raíz
2. Descargar desde: [modelo custom]
3. O entrenar nuevo modelo desde [datos]

### ⚠️ Performance Bajo
- Aumentar `CONFIDENCE_THRESHOLD` (menos detecciones)
- Reducir resolución de cámara en `cv2.CAP_PROP_FRAME_WIDTH`
- Ejecutar en GPU si disponible
- Ver logs en `proyecto_norn.log`

---

## 🎓 Mejoras Recientes (Dec 2025)

✅ Frame locking thread-safe  
✅ Worker de inferencia YOLO asíncrono  
✅ Guardado automático no bloqueante  
✅ Logging centralizado  
✅ Validación de setup mejorada  
✅ Documentación técnica completa  

---

## 📄 Licencia

Este proyecto está bajo la licencia **MIT**.

```
MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```