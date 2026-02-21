"""Gestión de temas para la interfaz gráfica usando PyQt6 
Proporciona estilos para temas claro y oscuro, en formato de cadena de texto CSS.
"""
 
class ThemeManager:
    LIGHT = "light"
    DARK = "dark"

    @staticmethod
    def get_stylesheet(theme):
        if theme == ThemeManager.DARK:
            return """
            QWidget {
                background-color: #121212;
                color: #E0E0E0;
                font-size: 14px;
            }

            QPushButton {
                background-color: #1f1f1f;
                border: 1px solid #333;
                border-radius: 6px;
                padding: 6px;
            }

            QPushButton:hover {
                background-color: #333;
            }

            QLineEdit, QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #444;
                padding: 4px;
            }

            /* ===== SWITCH ===== */

            QCheckBox#themeSwitch {
                background-color: #333;
                border-radius: 15px;
            }

            QCheckBox#themeSwitch:checked {
                background-color: #28a745;
            }

            QCheckBox#themeSwitch::indicator {
                image: none;
            }

            QWidget#switchThumb {
                background-color: white;
                border-radius: 13px;
            }
            """
        else:
            return """
            QWidget {
                background-color: #f5f5f5;
                color: #222;
                font-size: 14px;
            }

            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 6px;
            }

            QPushButton:hover {
                background-color: #eaeaea;
            }

            QLineEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #bbb;
                padding: 4px;
            }

            /* ===== SWITCH ===== */

            QCheckBox#themeSwitch {
                background-color: #ccc;
                border-radius: 15px;
            }

            QCheckBox#themeSwitch:checked {
                background-color: #28a745;
            }

            QCheckBox#themeSwitch::indicator {
                image: none;
            }

            QWidget#switchThumb {
                background-color: white;
                border-radius: 13px;
            }
            """
