"""
Resaltador de sintaxis para Python en QTextEdit
Colores suaves y profesionales para mejor legibilidad
"""
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class ResaltadorPython(QSyntaxHighlighter):
    """Resaltador de sintaxis para Python"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Formato para palabras clave
        formato_palabra_clave = QTextCharFormat()
        formato_palabra_clave.setForeground(QColor("#569CD6"))  # Azul
        formato_palabra_clave.setFontWeight(QFont.Weight.Bold)

        # Formato para comentarios
        formato_comentario = QTextCharFormat()
        formato_comentario.setForeground(QColor("#6A9955"))  # Verde

        # Formato para strings
        formato_string = QTextCharFormat()
        formato_string.setForeground(QColor("#CE9178"))  # Naranja

        # Formato para números
        formato_numero = QTextCharFormat()
        formato_numero.setForeground(QColor("#B5CEA8"))  # Verde claro

        # Formato para funciones
        formato_funcion = QTextCharFormat()
        formato_funcion.setForeground(QColor("#DCDCAA"))  # Amarillo

        # Formato para clases
        formato_clase = QTextCharFormat()
        formato_clase.setForeground(QColor("#4EC9B0"))  # Turquesa

        # Formato para decoradores
        formato_decorador = QTextCharFormat()
        formato_decorador.setForeground(QColor("#C586C0"))  # Morado

        # Formato para errores
        formato_error = QTextCharFormat()
        formato_error.setForeground(QColor("#F44747"))  # Rojo
        formato_error.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)
        formato_error.setUnderlineColor(QColor("#F44747"))

        # Palabras clave de Python
        palabras_clave = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "finally", "for", "from",
            "global", "if", "import", "in", "is", "lambda", "nonlocal",
            "not", "or", "pass", "raise", "return", "try", "while",
            "with", "yield", "True", "False", "None", "self", "cls"
        ]

        # Expresiones regulares para cada patrón
        self.reglas = []

        # Palabras clave
        for palabra in palabras_clave:
            patron = QRegularExpression(rf'\b{palabra}\b')
            self.reglas.append((patron, formato_palabra_clave))

        # Clases (palabras que comienzan con mayúscula)
        patron_clase = QRegularExpression(r'\b[A-Z][a-zA-Z0-9_]*\b')
        self.reglas.append((patron_clase, formato_clase))

        # Funciones (palabras seguidas de paréntesis)
        patron_funcion = QRegularExpression(r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\()')
        self.reglas.append((patron_funcion, formato_funcion))

        # Decoradores
        patron_decorador = QRegularExpression(r'@[a-zA-Z_][a-zA-Z0-9_]*')
        self.reglas.append((patron_decorador, formato_decorador))

        # Comentarios (línea completa)
        patron_comentario = QRegularExpression(r'#.*$')
        self.reglas.append((patron_comentario, formato_comentario))

        # Strings (comillas dobles)
        patron_string_doble = QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"')
        self.reglas.append((patron_string_doble, formato_string))

        # Strings (comillas simples)
        patron_string_simple = QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'")
        self.reglas.append((patron_string_simple, formato_string))

        # Strings (triples comillas dobles)
        patron_string_triple_doble = QRegularExpression(r'"""[^"]*"""')
        self.reglas.append((patron_string_triple_doble, formato_string))

        # Strings (triples comillas simples)
        patron_string_triple_simple = QRegularExpression(r"'''[^']*'''")
        self.reglas.append((patron_string_triple_simple, formato_string))

        # Números
        patron_numero = QRegularExpression(r'\b[0-9]+\b')
        self.reglas.append((patron_numero, formato_numero))

        # F-strings (resaltado especial)
        patron_fstring = QRegularExpression(r'f"[^"\\]*(\\.[^"\\]*)*"')
        self.reglas.append((patron_fstring, formato_string))

        patron_fstring_simple = QRegularExpression(r"f'[^'\\]*(\\.[^'\\]*)*'")
        self.reglas.append((patron_fstring_simple, formato_string))

        # Errores comunes (palabras mal escritas en contexto)
        self.reglas_errores = [
            (QRegularExpression(r'\bpront\b'), formato_error),
            (QRegularExpression(r'\bprin\b'), formato_error),
            (QRegularExpression(r'\bdef\s+[0-9]'), formato_error),
            (QRegularExpression(r'\bclass\s+[0-9]'), formato_error),
        ]

    def highlightBlock(self, texto):
        """Aplica el resaltado a un bloque de texto"""
        # Aplicar reglas principales
        for patron, formato in self.reglas:
            iterator = patron.globalMatch(texto)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), formato)

        # Aplicar reglas de errores (se superponen a las principales)
        for patron, formato in self.reglas_errores:
            iterator = patron.globalMatch(texto)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), formato)