# Importaciones de clases desde archivos del proyecto
from lambda_b import DBManager
from lambda_c import ThemeManager

# Importaciones de librerías estándar de Python
import sys
import os
import time
import threading
import queue
import json
from datetime import datetime
 
# Importaciones de librerías de terceros
import numpy as np
import cv2
import serial
import serial.tools.list_ports
import pyqtgraph as pg
from ultralytics import YOLO
from pyngrok import ngrok
from dotenv import load_dotenv

# Importaciones de PyQt6
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QDialogButtonBox, QHBoxLayout, QMainWindow,
    QDialog, QWidget, QLabel, QPushButton, QMessageBox, QCheckBox,
    QVBoxLayout, QComboBox, QFileDialog, QGridLayout
)
from PyQt6.QtCore import (
    QTimer, QThread, pyqtSignal, Qt,
    QPropertyAnimation, QRect, QSettings
)
from PyQt6.QtGui import QGuiApplication, QImage, QPixmap

# Importaciones de Flask
from flask import Flask, Response, jsonify, request, render_template, stream_with_context
from flask_cors import CORS

# Cargar variables del .env
load_dotenv()
KEY = os.getenv("KEY")

# Configuración Flask y SSE
app_flask = Flask(__name__)
CORS(app_flask)
clients = []
clients_lock = threading.Lock()

# Cargar modelo YOLO
model = YOLO("best.pt") 

# Clase del Switch del Tema
class SwitchButton(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Componentes visuales del Switch
        self.setObjectName("themeSwitch")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(60, 30)
        self.setChecked(False)

        # Configuración del Thumb del Switch
        self.thumb = QWidget(self)
        self.thumb.setObjectName("switchThumb")
        self.thumb.setGeometry(2, 2, 26, 26)
        self.thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Animación del Switch
        self.anim = QPropertyAnimation(self.thumb, b"geometry")
        self.anim.setDuration(180)
        self.stateChanged.connect(self.start_animation)

    # Metodo para cambiar el estado del Switch al hacer click
    def mousePressEvent(self, event):
        self.setChecked(not self.isChecked())
        super().mousePressEvent(event)

    # Metodo para iniciar la animación del Switch
    def start_animation(self, state):
        if state:
            start_rect = QRect(2, 2, 26, 26)
            end_rect = QRect(32, 2, 26, 26)
        else:
            start_rect = QRect(32, 2, 26, 26)
            end_rect = QRect(2, 2, 26, 26)

        self.anim.stop()
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(end_rect)
        self.anim.start()

# Clase la ventana de configuración
class ConfigDialog(QDialog):
    tema_cambiado = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Configuración de la ventana
        self.setWindowTitle("Configuración")
        self.setFixedSize(300, 220)
        layout = QVBoxLayout(self)

        # Selección de Puerto COM
        labelCOM = QLabel("Seleccionar Puerto COM:")
        self.comboCOM = QComboBox()
        self.comboCOM.addItems(
            [port.device for port in serial.tools.list_ports.comports()]
        )

        # Añadir widgets al layout
        layout.addWidget(labelCOM)
        layout.addWidget(self.comboCOM)

        # Selección de Cámara
        labelCams = QLabel("Seleccionar Cámara:")
        self.comboCams = QComboBox()
        self.buscar_camaras()

        # Añadir widgets al layout
        layout.addWidget(labelCams)
        layout.addWidget(self.comboCams)

        # Tema oscuro
        labelTema = QLabel("Modo oscuro")
        self.switchTema = SwitchButton()

        # Establecer estado inicial del switch según el tema actual
        if parent is not None:
            self.switchTema.setChecked(
                parent.tema_actual == ThemeManager.DARK
            )
        self.switchTema.stateChanged.connect(
            lambda state: self.tema_cambiado.emit(bool(state))
        )

        # Añadir widgets al layout
        temaLayout = QHBoxLayout()
        temaLayout.addWidget(labelTema)
        temaLayout.addStretch()
        temaLayout.addWidget(self.switchTema)
        layout.addLayout(temaLayout)

        # Botones Aceptar y Cancelar
        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )

        # Botones de Aceptar y Cerrar conectados a sus funciones
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
    
    # Metodo para buscar cámaras conectadas al sistema
    def buscar_camaras(self):
        self.comboCams.clear()
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.comboCams.addItem(f"Cámara {i}", i)
                cap.release()

# Clase de la Ventana Principal
class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()

        """
        Configuración de QSettings, se guarda en el registro de Windows: 
        'HKEY_CURRENT_USER/Software/ProyectoNorn/VisorInteligente'
        """
        self.settings = QSettings("ProyectoNorn", "VisorInteligente")
        self.tema_actual = ThemeManager.LIGHT

        # Variables de configuración
        self.puertoCOM = None
        self.camaraIndex = None
        self.arduino = None
        self.cap = None
        self.delay = 0
        self.hilo_espera_sensor = None
        self.detectando = False
        self.camAnterior = None
        self.puertoAnterior = None

        # Configuración para no modificar el tamaño de la ventana
        self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.CustomizeWindowHint |
                Qt.WindowType.WindowMinimizeButtonHint |
                Qt.WindowType.WindowCloseButtonHint
        )

        # Obtener el área disponible de la pantalla (sin la barra de tareas)
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(pantalla)

        # Fijar tamaño al área disponible
        self.setFixedSize( pantalla.width(), pantalla.height()-30)
        
        # QLabel para mostrar la cámara
        self.cameraLabel = QLabel()
        self.cameraLabel.setFixedSize(640, 360)

        # ComboBox para seleccionar lotes
        self.comboLotes = QComboBox()

        # Conectar cambio de lote para notificar a clientes SSE
        self.comboLotes.currentIndexChanged.connect(self.on_lote_changed)

        # Configuración de la gráfica
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setTitle("Registro de piezas por lote")
        self.graphWidget.setLabel('left', 'Cantidad')
        self.graphWidget.setLabel('bottom', 'Tipo')
        self.graphWidget.setFixedSize(640, 360)

        # Desactivar interacción del usuario con la gráfica
        self.graphWidget.setMouseEnabled(x=False, y=False)
        self.graphWidget.hideButtons()
        self.graphWidget.getPlotItem().setMenuEnabled(False)

        # Botón para agregar lote
        self.agregarlote = QPushButton("Agregar lote")
        self.agregarlote.clicked.connect(self.abrir_agregar_lote)

        # Etiqueta para mostrar el total
        self.total_label = QLabel()
        self.total_label.setText("Total: 0")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Botón de configuración
        self.btnConfig = QPushButton("Configuración")
        self.btnConfig.clicked.connect(self.abrir_config)

        # Botón para exportar PDF
        self.btnExportPDF = QPushButton("Exportar PDF")
        self.btnExportPDF.clicked.connect(self.generar_pdf_lote)

        # Botón para compartir URL de Ngrok
        self.btnShareURL = QPushButton("Compartir URL")
        self.btnShareURL.clicked.connect(self.mostrar_url_dialog)

        # Botón para modificar nombre de lote
        self.btnUpdateLotes = QPushButton("Modificar Nombre de Lote")
        self.btnUpdateLotes.clicked.connect(self.abrir_modificar_lote)  

        # Layout horizontal para los botones de configuración, exportar PDF y compartir URL
        btnBar = QHBoxLayout()
        btnBar.addWidget(self.btnConfig)
        btnBar.addWidget(self.btnExportPDF)
        btnBar.addWidget(self.btnShareURL)

        # Layout horizontal para los botones de agregar lote y modificar lote
        btnlote = QHBoxLayout()
        btnlote.addWidget(self.agregarlote)
        btnlote.addWidget(self.btnUpdateLotes)

        # Layout principal
        layout = QGridLayout()
        layout.addWidget(self.cameraLabel, 1, 0)
        layout.addWidget(self.comboLotes, 2, 0)
        layout.addLayout(btnlote, 3, 0)
        layout.addWidget(self.total_label, 2, 1)
        layout.addWidget(self.graphWidget, 1, 1)
        layout.addLayout(btnBar, 3, 1)

        # Establecer el layout en un widget central
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Timer para actualizar la imagen de la cámara
        self.timer = QTimer()
        self.timer.timeout.connect(self.PrincipalImagen)
        self.timer.start(30)
        self.graphWidget.addLegend()

        # Inicializar la base de datos
        self.db = DBManager()
        self.llenar_lista_desde_db()

        # Inicializar configuración guardada
        self.cargar_configuracion()

        # Actualizar gráfica inicial
        self.actualizar_grafica()

        # Aplicar tema guardado        
        self.aplicar_tema()

    # Metodo para guardar la configuración actual
    def guardar_configuracion(self):
        # Guardar configuración en QSettings
        self.settings.setValue("puertoCOM", self.puertoCOM)
        self.settings.setValue("camaraIndex", self.camaraIndex)
        self.settings.setValue("tema", self.tema_actual)

    # Metodo para cargar la configuración guardada
    def cargar_configuracion(self):

        # Cargar configuración desde QSettings
        self.puertoCOM = self.settings.value("puertoCOM", None)
        self.camaraIndex = self.settings.value("camaraIndex", None, int)
        self.tema_actual = self.settings.value("tema", ThemeManager.LIGHT)

        # Aplicar tema guardado
        self.aplicar_tema()
        print(f"Tema cargado: {self.tema_actual}")

        # Carga la cámara guardada, si existe o si ha cambiado
        if self.camaraIndex is not None and self.camaraIndex != self.camAnterior:
            self.camAnterior = self.camaraIndex
            self.cap = cv2.VideoCapture(self.camaraIndex)
            self.cap.set(3, 1280)
            self.cap.set(4, 720)

        # Carfga el puerto COM guardado, si existe o si ha cambiado
        if self.puertoCOM is not None and self.puertoCOM != self.puertoAnterior:
            try:
                self.puertoAnterior = self.puertoCOM

                # Se conecta al Arduino
                self.arduino = serial.Serial(self.puertoCOM, 9600, timeout=1)
            
            # Mensaje si llega a fallar la conexión
            except serial.SerialException:
                self.mostrar_mensaje(
                    "warn",
                    "Puerto no disponible",
                    f"No se pudo abrir {self.puertoCOM}"
                )

    # Metodo para cambiar el tema de la aplicación
    def toggle_tema(self, state):
        self.tema_actual = (
            ThemeManager.DARK if state else ThemeManager.LIGHT
        )
        self.aplicar_tema()

    # Metodo para aplicar el tema seleccionado
    def aplicar_tema(self):
        self.setStyleSheet(
            ThemeManager.get_stylesheet(self.tema_actual)
        )

        # Aplicar tema a la gráfica
        if self.tema_actual == ThemeManager.DARK:
            self.graphWidget.setBackground('#121212')
            self.graphWidget.getPlotItem().getAxis('left').setPen('w')
            self.graphWidget.getPlotItem().getAxis('bottom').setPen('w')
        else:
            self.graphWidget.setBackground('w')
            self.graphWidget.getPlotItem().getAxis('left').setPen('k')
            self.graphWidget.getPlotItem().getAxis('bottom').setPen('k')

    # Metodo para abrir el dialogo de agregar lote
    def abrir_agregar_lote(self):
        nombre, ok = QInputDialog.getText(
            self,
            "Agregar lote",
            "Nombre del nuevo lote:"
        )

        # Si el usuario cancela o no ingresa nada, salir
        if not ok or not nombre.strip():
            return

        # Agregar el lote
        self.agregar_lote(nombre.strip())
    
    # Metodo para mostrar mensajes al usuario
    def mostrar_mensaje(self, tipo, titulo, texto):
        msg = QMessageBox(self)
        
        if tipo == "info":
            msg.setIcon(QMessageBox.Icon.Information)
        elif tipo == "warn":
            msg.setIcon(QMessageBox.Icon.Warning)
        elif tipo == "error":
            msg.setIcon(QMessageBox.Icon.Critical)
        else:
            msg.setIcon(QMessageBox.Icon.NoIcon)

        # Configuración del mensaje
        msg.setWindowTitle(titulo)
        msg.setText(texto)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    # Metodo para abrir el dialogo de configuración
    def abrir_config(self):
        dialogo = ConfigDialog(self)
        dialogo.tema_cambiado.connect(self.toggle_tema)
        
        # Mostrar el diálogo y aplicar cambios si se acepta
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.puertoCOM = dialogo.comboCOM.currentText()
            self.camaraIndex = dialogo.comboCams.currentData()

            # Conectar cámara si ha cambiado o es la primera vez
            if self.camaraIndex is not None and self.camaraIndex != self.camAnterior:
                if self.cap and self.cap.isOpened():
                    self.cap.release()
                self.camAnterior = self.camaraIndex
                self.cap = cv2.VideoCapture(self.camaraIndex)
                self.cap.set(3, 1280)
                self.cap.set(4, 720)

            # Conectar Arduino si ha cambiado o es la primera vez
            if self.puertoCOM and self.puertoCOM != self.puertoAnterior:
                try:
                    self.puertoAnterior = self.puertoCOM
                    self.arduino = serial.Serial(self.puertoCOM, 9600, timeout=1)
                except serial.SerialException as e:
                    self.mostrar_mensaje("error", "Error COM", str(e))
                    return

            # Guardar configuración actual en QSettings
            self.guardar_configuracion()

            # Mensaje de confirmación
            self.mostrar_mensaje(
                "info",
                "Configuración aplicada",
                f"Puerto: {self.puertoCOM}\nCámara: {self.camaraIndex}"
            )

    # Metodo para generar un PDF del lote seleccionado
    def generar_pdf_lote(self):
        """Genera un PDF con una tabla que contiene todas las filas de la tabla
        'lemon' para el lote seleccionado. No incluye el campo id.
        """

        # Obtener lote actual
        lote_actual = self.comboLotes.currentText()
        if not lote_actual:
            self.mostrar_mensaje("warn", "Lote no seleccionado", "Selecciona un lote antes de exportar PDF.")
            return

        # Obtener filas desde la BD
        try:
            filas = self.db.obtener_filas_por_lote(lote_actual)
        except Exception as e:
            self.mostrar_mensaje("error", "Error BD", f"No se pudo obtener datos del lote:\n{e}")
            return

        # Verificar si hay datos
        if not filas:
            self.mostrar_mensaje("info", "Sin datos", f"No hay registros para el lote '{lote_actual}'.")
            return

        # Importar reportlab dinámicamente para evitar fallo si no está instalado
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet

        #Si falla la importación, mostrar mensaje
        except Exception as e:
            self.mostrar_mensaje(
                "error",
                "Dependencia faltante",
                "La librería 'reportlab' no está instalada. Instálala con:\n\npip install reportlab"
            )
            return

        # Preparar datos para la tabla (sin ID). filas expected: (ancho,largo,valido,fecha,lote)
        data = [["Ancho","Largo","Válido","Fecha","Lote"]]

        # Rellenar con los datos obtenidos de la BD
        for row in filas:
            ancho, largo, valido, fecha, lote = row
            valido_str = "Sí" if bool(valido) else "No"
            fecha_str = str(fecha)
            data.append([str(round(float(ancho), 3)), str(round(float(largo), 3)), valido_str, fecha_str, str(lote)])

        # Nombre de archivo por defecto con timestamp que incluye fecha y hora
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = f"reporte_{lote_actual}_{timestamp}.pdf"

        """Pedir al usuario dónde guardar el archivo
        En PyQt6 `QFileDialog.Options()` puede no existir; llamamos a getSaveFileName sin opciones. """
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", os.path.join(os.getcwd(), default_filename), "PDF Files (*.pdf)")
        
        # Si el usuario cancela, salir
        if not ruta:
            return
        
        # Asegurarse de que la ruta termina en .pdf
        if not ruta.lower().endswith('.pdf'):
            ruta += '.pdf'

        # Crear el PDF
        try:
            """
            Genera el PDF con la tabla de datos para el lote seleccionado
            y lo guarda en la ruta especificada. Se utilizan estilos básicos y se centra
            la tabla en la página.
            """
            doc = SimpleDocTemplate(ruta, pagesize=letter)
            styles = getSampleStyleSheet()
            elems = []
            title = Paragraph(f"Reporte - Lote: {lote_actual}", styles['Title'])
            elems.append(title)
            elems.append(Spacer(1, 12))

            # Crear tabla
            table = Table(data, hAlign='CENTER')
            tbl_style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#28a745')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER')
            ])
            table.setStyle(tbl_style)
            elems.append(table)
            doc.build(elems)

        # Mensaje de error si falla la creación del PDF
        except Exception as e:
            self.mostrar_mensaje("error", "Error generando PDF", f"No se pudo crear el PDF:\n{e}")
            return

        # Mensaje de éxito al guardar el PDF
        self.mostrar_mensaje("info", "PDF creado", f"PDF guardado en:\n{ruta}")
    
    # Metodo para mostrar el diálogo con la URL de Ngrok y su QR
    def mostrar_url_dialog(self):
        """Muestra un diálogo con la URL pública (clickable) y su QR.
        Usa import dinámico de `qrcode` para no romper si la librería no está instalada.
        """
        # Obtener la URL pública desde la variable global
        try:
            url = globals().get('public_url', None)

        # Si falla, asignar None
        except Exception:
            url = None

        # Verificar si la URL está disponible
        if not url:
            self.mostrar_mensaje("warn", "URL no disponible", "El servidor público no está disponible.")
            return

        # Intentar importar qrcode y BytesIO dinámicamente
        try:
            import qrcode
            from io import BytesIO
        except Exception:
            self.mostrar_mensaje("error", "Dependencia faltante", "La librería 'qrcode' no está instalada. Instálala con:\n\npip install qrcode[pil]")
            return

        # Generar QR de la URL 
        try:
            img = qrcode.make(url)
            buf = BytesIO()
            img.save(buf, format='PNG')
            data = buf.getvalue()
            pix = QPixmap()
            pix.loadFromData(data)
        except Exception as e:
            self.mostrar_mensaje("error", "Error generando QR", f"No se pudo generar el QR:\n{e}")
            return
    
        # Construir diálogo
        dlg = QDialog(self)
        dlg.setWindowTitle("URL pública")
        dlg.setFixedSize(480, 380)
        vbox = QVBoxLayout()

        # Enlace clickable
        link = QLabel(f'<a href="{url}">{url}</a>')
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(link)

        # QR
        qr_label = QLabel()
        qr_label.setPixmap(pix.scaled(260, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(qr_label)

        # Botón cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dlg.accept)
        vbox.addWidget(btn_close)

        # Establecer layout y mostrar diálogo
        dlg.setLayout(vbox)
        dlg.exec()

    # Metodo para modificar el nombre del lote actual
    def modificar_lote_actual(self, nuevo_nombre):
        lote_actual = self.comboLotes.currentText()

        # Verifica que haya un lote seleccionado
        if not lote_actual:
            self.mostrar_mensaje(
                "warn",
                "Sin lote",
                "No hay un lote seleccionado."
            )
            return

        # Verificar que el nombre no esté vacío
        if not nuevo_nombre.strip():
            self.mostrar_mensaje(
                "warn",
                "Nombre inválido",
                "El nombre del lote no puede estar vacío."
            )
            return

        # Evitar que el nuevo nombre ya exista
        if nuevo_nombre in [self.comboLotes.itemText(i) for i in range(self.comboLotes.count())]:
            self.mostrar_mensaje(
                "warn",
                "Lote existente",
                f"El lote '{nuevo_nombre}' ya existe."
            )
            return

        # Actualizar en la base de datos
        try:
            self.db.actualizar_nombre_lote(lote_actual, nuevo_nombre)
        except Exception as e:
            self.mostrar_mensaje(
                "error",
                "Error BD",
                f"No se pudo actualizar el lote:\n{e}"
            )
            return

        # Actualizar ComboBox
        index = self.comboLotes.currentIndex()
        self.comboLotes.setItemText(index, nuevo_nombre)
        self.comboLotes.setCurrentIndex(index)

        # Actualizar gráfica
        self.actualizar_grafica()

        # Se notifica a los clientes SSE sobre el cambio de nombre
        try:
            payload = {
                "evento": "lote_modificado",
                "lote_viejo": lote_actual,
                "lote_nuevo": nuevo_nombre
            }
            self.notify_clients(payload)
        except Exception as e:
            self.mostrar_mensaje("warn", "Error SSE", f"No se pudo notificar a los clientes:\n{e}")

        self.mostrar_mensaje(
            "info",
            "Lote modificado",
            f"El lote '{lote_actual}' fue renombrado a '{nuevo_nombre}'."
        )

    # Metodo para abrir el diálogo de modificar lote
    def abrir_modificar_lote(self):
        lote_actual = self.comboLotes.currentText()

        # Verifica que haya un lote seleccionado
        if not lote_actual:
            self.mostrar_mensaje("warn", "Sin lote", "Selecciona un lote primero.")
            return

        # Pedir nuevo nombre del lote
        nuevo_nombre, ok = QInputDialog.getText(
            self,
            "Modificar lote",
            f"Nuevo nombre para el lote '{lote_actual}':"
        )

        # Verificar si el usuario canceló o no ingresó nada
        if ok:
            self.modificar_lote_actual(nuevo_nombre.strip())

    # Metodo para llenar el comboBox de lotes desde la base de datos
    def llenar_lista_desde_db(self):
        
        # Bloquear señales para evitar llamadas innecesarias
        try:
            self.comboLotes.blockSignals(True)
        except Exception:
            pass

        # Limpiar y llenar el comboBox con lotes desde la BD
        self.comboLotes.clear()
        lotes = self.db.obtener_lotes()

        for lote in lotes:
            self.comboLotes.addItem(lote)

        try:
            self.comboLotes.blockSignals(False)
        except Exception:
            pass

        # Notificar a clientes SSE el lote inicial (si existe)
        if self.comboLotes.count() > 0:
            try:
                self.on_lote_changed(self.comboLotes.currentIndex())
            except Exception:
                pass

    # Metodo para enviar comandos al Arduino
    def enviar_comando(self, comando):

        # Enviar comando al Arduino si está conectado
        if self.arduino and self.arduino.is_open:
            try:
                self.arduino.write(comando.encode('utf-8') + b"\n")
            except Exception as e:
                self.mostrar_mensaje("error","Error Arduino",f"No se pudo enviar el comando:\n{e}"
                )
        else:
            self.mostrar_mensaje("warn","Arduino no conectado","No se pudo enviar el comando: Arduino no está conectado.")  
    
    # Metodo llamado cuando cambia el lote seleccionado
    def on_lote_changed(self, index):
        """Se llama cuando cambia el lote seleccionado en la UI.
        Consulta la BD y notifica a los clientes SSE con los conteos actuales.
        """
        try:

            # Obtiene el lote seleccionado
            lote = self.comboLotes.itemText(index) if index is not None and index >= 0 else self.comboLotes.currentText()
            
            # Verifica que haya un lote seleccionado
            if not lote:
                return
            
            # Consulta la BD para obtener conteos
            resultado = self.db.obtener_validos_y_no_validos_por_lote(lote)

            # Si la BD no devuelve nada, forzamos ceros
            if resultado:
                validos, no_validos = map(int, resultado)
            else:
                validos, no_validos = 0, 0

            # Notifica a los clientes SSE
            payload = {
                "lote": lote,
                "validos": validos,
                "no_validos": no_validos
            }
            self.notify_clients(payload)
            self.actualizar_grafica()
        except Exception as e:
            self.actualizar_grafica()

    # Metodo para agregar un nuevo lote
    def agregar_lote(self, nuevo_lote: str):

        # Verificar que no esté vacío
        if not nuevo_lote:
            self.mostrar_mensaje(
                "warn",
                "Lote vacío",
                "Por favor ingresa un nombre para el nuevo lote."
            )
            return

        # Verificar si ya existe
        if nuevo_lote in [self.comboLotes.itemText(i) for i in range(self.comboLotes.count())]:
            self.mostrar_mensaje(
                "info",
                "Lote existente",
                f"El lote '{nuevo_lote}' ya está en la lista."
            )
            self.comboLotes.setCurrentText(nuevo_lote)
            return

        # Agregar al combo
        self.comboLotes.addItem(nuevo_lote)
        self.comboLotes.setCurrentText(nuevo_lote)

        # Actualizar gráfica
        self.actualizar_grafica()

        # Notificar a los clientes SSE sobre el nuevo lote
        try:
            payload = {
                "lote": nuevo_lote,
                "validos": 0,
                "no_validos": 0
            }
            self.notify_clients(payload)
        except Exception as e:
            self.mostrar_mensaje("warn", "Error SSE", f"No se pudo notificar a los clientes:\n{e}")

        # Mensaje de confirmación
        self.mostrar_mensaje(
            "info",
            "Lote agregado",
            f"Lote '{nuevo_lote}' agregado exitosamente."
        )
    
    # Metodo para actualizar la gráfica de barras
    def actualizar_grafica(self):
        lote_actual = self.comboLotes.currentText()

        # Verificar que haya un lote seleccionado
        if not lote_actual:
            return

        # Consulta con la BD
        resultado = self.db.obtener_validos_y_no_validos_por_lote(lote_actual)

        # Si la BD no devuelve nada, forzamos ceros
        if not resultado:
            validos = 0
            no_validos = 0
        else:
            try:
                validos, no_validos = map(int, resultado)
            except:
                validos = 0
                no_validos = 0

        # Actualizar total
        self.total_label.setText(f"Total: {validos + no_validos}")

        # Actualizar título del gráfico
        self.graphWidget.setTitle(f"Lote: {lote_actual}<br><i>Registro de piezas</i>")

        # Limpiar la gráfica
        self.graphWidget.clear()

        # Barras
        bar_validos = pg.BarGraphItem(x=[1], height=[validos], width=0.4, brush='g')
        bar_no_validos = pg.BarGraphItem(x=[2], height=[no_validos], width=0.4, brush='r')

        # Agregar al gráfico
        self.graphWidget.setYRange(0, max(validos, no_validos, 10) + 5)
        self.graphWidget.addItem(bar_validos)
        self.graphWidget.addItem(bar_no_validos)

        # Etiquetas
        ax = self.graphWidget.getAxis('bottom')
        ax.setTicks([[(1, 'Válidos'), (2, 'No válidos')]])

    # Metodo para iniciar el hilo de espera del sensor IR
    def iniciar_espera_sensor_ir(self):

        # Inicia un hilo que espera la señal del sensor IR del Arduino
        if self.arduino and self.arduino.is_open:

            # Detiene hilo anterior si aún está corriendo
            if self.hilo_espera_sensor and self.hilo_espera_sensor.isRunning():
                self.hilo_espera_sensor.detener()
                self.hilo_espera_sensor.wait()

            # Limpia el buffer serial para evitar lecturas antiguas
            self.arduino.reset_input_buffer()

            # Crea y lanza un nuevo hilo
            self.hilo_espera_sensor = EsperaSensorThread(self.arduino)
            self.hilo_espera_sensor.deteccion.connect(self.accion_tras_deteccion_sensor)
            self.hilo_espera_sensor.start()
        else:
            self.mostrar_mensaje("warn","Arduino no conectado","No se pudo iniciar la espera del sensor: Arduino no está conectado.")

    # Metodo para guardar el objeto detectado
    def guardar_objeto(self):

        # Verifica que la cámara esté abierta
        ret, frame = self.cap.read()

        # Si no se pudo leer el frame, salir
        if not ret:
            self.detectando = False
            return

        # Guarda los resultados de la detección
        results = model.predict(frame, imgsz=640, conf=0.6)

        # Si no hay cajas detectadas, salir
        if not results[0].boxes:
            self.detectando = False
            return

        #Procesar cada caja detectada
        boxes = results[0].boxes.xyxy.tolist()
        clases_detectadas = [int(c) for c in results[0].boxes.cls.tolist()]
        nombres_detectados = results[0].names
        nombres = [nombres_detectados[c] for c in clases_detectadas]

        # Obtiene el lote actual
        lote_actual = self.comboLotes.currentText()

        # Inserta cada objeto en la base de datos
        for i, box in enumerate(boxes):
            nombre = nombres[i]
            x1, y1, x2, y2 = box
            ancho = float(x2 - x1)
            largo = float(y2 - y1)

            # Usamos la circularidad de ObjectDetection
            circularidad = getattr(self, "ultima_circularidad", 0)

            # Convertir dimensiones a cm
            ancho_cm = self.pixeles_a_cm(ancho)
            largo_cm = self.pixeles_a_cm(largo)

            # Determinar si es válido
            valido = True if nombre == "good" and circularidad >= 0.35 else False

            # Insertar en la base de datos
            self.db.insertar_objeto(
                ancho=ancho_cm,
                largo=largo_cm,
                valido=valido,
                fecha=datetime.now(),
                lote=lote_actual
            )

            # Señalizar al Arduino al LED correspondiente
            if not valido:
                self.enviar_comando("LED_F")
                self.iniciar_espera_sensor_ir()
                QTimer.singleShot(2000, lambda: self.enviar_comando("LED_OFF"))
            else:
                self.enviar_comando("LED_T")
                QTimer.singleShot(1000, lambda: self.enviar_comando("LED_OFF"))
    
        # Notificar a los clientes SSE sobre la actualización
            try:
                lote_actual = self.comboLotes.currentText()
                resultado = self.db.obtener_validos_y_no_validos_por_lote(lote_actual)
                if resultado:
                    validos, no_validos = map(int, resultado)
                else:
                    validos, no_validos = 0, 0

                payload = {
                    "lote": lote_actual,
                    "validos": validos,
                    "no_validos": no_validos
                }

                # Envía el evento a todos los clientes conectados
                self.notify_clients(payload)
            except Exception as e:
                self.mostrar_mensaje("warn", "Error SSE", f"No se pudo notificar a los clientes:\n{e}")
        
        #Se cambiela el estado de detectando a False y se actualiza la gráfica
        self.detectando = False
        self.actualizar_grafica()

    # Metodo para convertir pixeles a cm
    def pixeles_a_cm(self,pixeles):
        tamaño_en_pixeles = 43.56
        return pixeles / tamaño_en_pixeles
    
    # Metodo para la detección de objetos por color
    def ObjectDetection(self, frame):

        # Convertir a espacio HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        """Rangos de color para detectar limones (amarillo verdoso)
        0-180 para H, 0-255 para S y V en OpenCV
        """
        h_min = 3
        h_max = 90
        s_min = 50
        s_max = 255
        v_min = 50
        v_max = 255

        # Crear máscara binaria y aplicar morfología
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, lower, upper)
        
        # Aplicar operaciones morfológicas para limpiar la máscara
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

        # Encontrar contornos en la máscara 
        contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Procesar cada contorno encontrado 
        for cnt in contornos:

            # Filtrar por área mínima, si es menor que 350 pixeles, ignorar
            area = cv2.contourArea(cnt)
            if area < 350:
                continue


            # Calcular diámetro equivalente y filtrar por tamaño
            diametro = 2 * np.sqrt(area / np.pi)
            if diametro < 75:
                continue
            
            # Calcular circularidad 
            perimetro = cv2.arcLength(cnt, True)
            circularidad = (4 * np.pi * area) / (perimetro ** 2) if perimetro > 0 else 0

            # Calcular centroide para colocar texto
            M = cv2.moments(cnt)
            cx, cy = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])) if M["m00"] != 0 else (0, 0)

            # Dibujar contorno y texto en el frame
            color = (0, 255, 0) if circularidad >= 0.20 else (0, 0, 255)
            cv2.drawContours(frame, [cnt], -1, color, 2)
            texto = f"Diam: {int(diametro)}px Circ: {circularidad:.2f}"
            cv2.putText(frame, texto, (cx - 100, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Si no está detectando y ha pasado el tiempo de delay, guardar objeto
            if not self.detectando and (time.time() - self.delay > 6):
                self.detectando = True
                self.ultima_circularidad = circularidad
                QTimer.singleShot(1000, self.guardar_objeto)
                self.delay = time.time()

        # Retornar el frame con los contornos dibujados
        return frame

    # Metodo principal para capturar y mostrar la imagen de la cámara
    def PrincipalImagen(self):

        # Uso de variables globales para compartir el frame actual
        global current_frame, last_ret, last_frame

        # Verificar si la cámara está abierta
        if self.cap is None or not self.cap.isOpened():
            last_ret = False
            last_frame = None
            return

        # Leer frame de la cámara
        ret, frame = self.cap.read()
        if not ret:
            last_ret = False
            last_frame = None
            return

        # Realizar predicciones con el modelo YOLO
        results = model.predict(frame, imgsz=640, conf=0.6)
        annotated_frame = results[0].plot()

        # Añadir contornos de limones detectados por color
        annotated_frame = self.ObjectDetection(annotated_frame)
        
        # Convertir a QImage
        rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Mostrar en QLabel manteniendo proporción
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self.cameraLabel.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.cameraLabel.setPixmap(pixmap)

        """Actualizamos los globals para que otros hilos/funciones
        (p. ej. `gen_frames`) puedan acceder a la última lectura.
        """
        last_ret = ret
        try:
            last_frame = frame.copy()
        except Exception:
            last_frame = frame

        # Actualizamos el frame actual para streaming
        current_frame = annotated_frame.copy()

    # Metodo llamado tras la detección del sensor IR
    def accion_tras_deteccion_sensor(self):
        #Acciona el servo con un delay de 1.5s y apaga el LED tras la detección del sensor IR
        QTimer.singleShot(1500,lambda:self.enviar_comando("SERVO_ON"))
        self.enviar_comando("LED_OFF")

    # Metodo para manejar el cierre de la aplicación
    def closeEvent(self, event):

        """
        Cierra la cámara y el puerto serial del Arduino si están abiertos, esto previene
        posibles fugas de recursos al cerrar la aplicación.
        """
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
        super().closeEvent(event)
    
    # Metodo para notificar a los clientes SSE conectados
    def notify_clients(self, payload: dict):

        """Envía payload (dict) como JSON a todos los clientes SSE conectados."""

        data = json.dumps(payload)

        with clients_lock:

            # iteramos copia para evitar modificación concurrente
            for q in list(clients):
                try:
                    q.put_nowait(data)

                except Exception:

                    # si falla la cola, la quitamos
                    try:
                        clients.remove(q)

                    except ValueError:
                        pass

# Hilo para esperar la señal del sensor IR del Arduino
class EsperaSensorThread(QThread):
    deteccion = pyqtSignal()
    def __init__(self, arduino):
        super().__init__()
        self.arduino = arduino
        self.running = True

    # Metodo principal del hilo
    def run(self):

        # Espera hasta que el Arduino envíe "DETECCION_IR"
        while self.running:
            if self.arduino.in_waiting > 0:
                linea = self.arduino.readline().decode(errors="ignore").strip()
                if not self.running:
                    break
                if linea == "DETECCION_IR":
                    self.deteccion.emit()
                    break
    # Metodo para detener el hilo
    def detener(self):  
        self.running = False

# Variable global para frame actual
current_frame = None

# Últimas lecturas (ret, frame) provenientes de `PrincipalImagen`
last_ret = False
last_frame = None

# referencia a tu ventana principal
ventana = None  

# Metodo generador de frames JPEG para streaming
def gen_frames():
    global last_ret, last_frame, current_frame

    # Bucle infinito para generar frames
    while True:
        # Usamos la última lectura publicada por PrincipalImagen
        if not last_ret or last_frame is None:
            time.sleep(0.01)
            continue

        try:
            # Asegurarnos de tener un frame disponible
            if current_frame is None:
                time.sleep(0.01)
                continue

            # Codificar a JPEG
            ret, buffer = cv2.imencode('.jpg', current_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                time.sleep(0.01)
                continue
            
            img_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img_bytes + b'\r\n')
        except GeneratorExit:
            break
        except Exception:
            # Si hay cualquier error en la codificación, esperar y continuar
            time.sleep(0.01)
            continue

# Variables globales para SSE 
stats = {"validos": 0, "no_validos": 0}
current_camera_index = 0
camera = None
public_url = None

# Carga del HTLM de Flask para la interfaz web
@app_flask.route("/")
def index():
    return render_template("index.html")

# Ruta para el stream SSE de actualizaciones
@app_flask.route("/stream_actualizaciones")

# Metodo para el stream SSE de actualizaciones
def stream_actualizaciones():

    # Generador de eventos SSE
    def event_stream(q: queue.Queue):

        # Bucle infinito para enviar datos al cliente
        try:
            while True:
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            # Cliente desconectado
            with clients_lock:
                try:
                    clients.remove(q)
                except ValueError:
                    pass

    # Crear una cola para este cliente
    q = queue.Queue()

    # Agregar la cola a la lista de clientes
    with clients_lock:
        clients.append(q)

    # Enviar estado inicial
    try:
        if ventana is not None:
            lote = ventana.comboLotes.currentText()

            if lote:
                resultado = ventana.db.obtener_validos_y_no_validos_por_lote(lote)

                if resultado:
                    validos, no_validos = map(int, resultado)
                else:
                    validos, no_validos = 0, 0

                payload = {
                    "lote": lote,
                    "validos": validos,
                    "no_validos": no_validos
                }

                # Enviamos el primer evento SSE al cliente recién conectado
                q.put(json.dumps(payload))

    except Exception as e:
        print("Error enviando estado inicial SSE:", e)

    # Stream de eventos SSE
    return Response(stream_with_context(event_stream(q)),
                    mimetype="text/event-stream")

# Ruta para actualizar datos vía POST
@app_flask.route("/actualizar_datos", methods=["POST"])
def actualizar_datos():
    global stats
    data = request.json

    # Actualizar estadísticas globales
    stats["validos"] += data.get("validos", 0)
    stats["no_validos"] += data.get("no_validos", 0)

    # Notificar a la web por SSE
    mensaje = json.dumps({
        "validos": stats["validos"],
        "no_validos": stats["no_validos"]
    })

    # Enviar a todos los clientes conectados
    with clients_lock:
        for c in clients:
            c.put(mensaje)

    return jsonify({"status": "ok"})

# Ruta para el feed de la cámara
@app_flask.route("/camera")
def camera_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Metodo para ejecutar Flask en un hilo separado
def run_flask():
    app_flask.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# Punto de entrada principal
if __name__ == "__main__":
    import socket
    
    # Función para verificar si un puerto está ocupado
    def puerto_ocupado(puerto):

        """
        Intentar enlazar al puerto especificado. Si falla, el puerto está ocupado.
        Retorna True si el puerto está ocupado, False si está libre.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", puerto))
            s.close()
            return False
        except OSError:
            return True    

    # Si Flask ya estaba corriendo, lo evitamos
    if not puerto_ocupado(5000):
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
    else:
        print("Flask YA está ejecutándose. No se iniciará otra instancia.")

    # Iniciar ngrok solo si el túnel no existe ya
    try:
        ngrok.set_auth_token(KEY)
        tunnels = ngrok.get_tunnels()

        if any("5000" in t.public_url for t in tunnels):
            print("Ya existe un túnel ngrok activo.")
            public_url = [t.public_url for t in tunnels][0]
        else:
            public_url = ngrok.connect(5000).public_url

    except Exception as e:
        print("Error iniciando ngrok:", e)

    # Inicia la app PyQt
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())
