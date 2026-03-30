import re
import unicodedata
from nltk.tokenize import word_tokenize
import nltk
from nltk.corpus import stopwords

def setup_nltk():
    nltk.download('punkt')
    nltk.download('wordnet')
    nltk.download('stopwords')
    nltk.download('punkt_tab')

try:
    stop_words = set(stopwords.words('spanish'))
except LookupError:
    nltk.download('stopwords')
    stop_words = set(stopwords.words('spanish'))

# Palabras de saludo que deben permitirse aunque sean "stopwords"
greeting_words = {"hola", "buenas", "buenos", "saludos", "hey", "hi", "hello"}

# Palabras clave para restricciones
diagnosis_keywords = ["diagnóstico", "enfermedad", "qué tengo", "qué me pasa"]
medication_keywords = ["medicación", "tratamiento", "dosis", "medicamento", "recetar"]

# Patrones de expresiones regulares para validación
HARMFUL_PATTERNS = [
    r'<script>',           # Bloquear inyección de scripts
    r'javascript:',        # Prevenir ejecución de código
    r'onerror=',           # Bloquear eventos maliciosos
    r'\b(select|drop|union|insert|delete)\b',  # Prevenir inyección SQL
    r'[^\w\s\u00C0-\u00FF.?!,áéíóúüñ¿¡]'  # Permitir caracteres en español
]

def normalize_text(text):
    """Normaliza texto eliminando acentos y convirtiendo a minúsculas."""
    return ''.join(
        char for char in unicodedata.normalize('NFKD', text)
        if unicodedata.category(char) != 'Mn'
    ).lower()

def is_greeting_message(text):
    """Verifica si el mensaje es un saludo simple."""
    normalized = normalize_text(text.strip())
    tokens = word_tokenize(normalized)
    
    # Si el mensaje tiene 1-3 palabras y contiene palabras de saludo
    if len(tokens) <= 3:
        return any(token in greeting_words for token in tokens)
    return False

def validate_input(user_message):
    """Valida la entrada del usuario con múltiples capas de verificación."""
    # Verificar mensaje vacío o solo espacios
    if not user_message or user_message.isspace():
        return False, "El mensaje no puede estar vacío."
    
    # Normalizar y limpiar el texto
    normalized_message = normalize_text(user_message)
    
    # Verificar longitud máxima
    if len(user_message) > 500:
        return False, "El mensaje es demasiado largo. Límite máximo: 500 caracteres."
    
    # Verificar patrones dañinos con regex
    for pattern in HARMFUL_PATTERNS:
        if re.search(pattern, normalized_message, re.IGNORECASE):
            return False, "Entrada no válida: se detectaron caracteres o patrones potencialmente dañinos."
    
    # Análisis de tokens
    tokens = word_tokenize(normalized_message)
    
    # Verificar si es un saludo simple - permitir sin validación adicional
    if is_greeting_message(user_message):
        return True, ""
    
    # Remover stopwords para mensajes no-saludo
    filtered_tokens = [token for token in tokens if token not in stop_words]
    
    # Verificar densidad de palabras significativas (más flexible)
    if len(filtered_tokens) == 0 and len(tokens) > 3:
        return False, "El mensaje debe contener al menos una palabra significativa."
    
    # Permitir mensajes cortos (1-3 palabras) aunque no tengan palabras "significativas"
    if len(tokens) <= 3:
        return True, ""
    
    # Para mensajes más largos, requerir al menos una palabra significativa
    if len(filtered_tokens) == 0:
        return False, "El mensaje debe contener al menos una palabra significativa."
    
    # Verificar repetición excesiva de caracteres
    if re.search(r'(.)\1{4,}', user_message):  # Cambiado de 3 a 4 para ser menos restrictivo
        return False, "No se permiten repeticiones excesivas de caracteres."
    
    return True, ""

def analyze_message(user_message):
    """Analiza el mensaje después de la validación."""
    is_valid, error_message = validate_input(user_message)
    if not is_valid:
        return ("input_error", error_message)
    
    normalized_message = normalize_text(user_message)
    tokens = word_tokenize(normalized_message)
    
    # Verificar si es un saludo
    if is_greeting_message(user_message):
        return ("greeting", "")
    
    if any(keyword in normalized_message for keyword in diagnosis_keywords):
        return ("diagnosis_restriction", "")
    elif any(keyword in normalized_message for keyword in medication_keywords):
        return ("medication_restriction", "")
    else:
        return ("general_response", "")

def generate_response(user_message):
    """Genera respuesta basada en el análisis del mensaje."""
    restriction_type, error_message = analyze_message(user_message)
    
    if restriction_type == "input_error":
        return error_message
    elif restriction_type == "greeting":
        return ("¡Hola! Soy Hipo, tu asistente de triaje médico. "
                "¿Cómo te sientes hoy? Por favor, cuéntame qué síntomas o molestias tienes.")
    elif restriction_type == "diagnosis_restriction":
        return ("No puedo proporcionar un diagnóstico médico. "
                "Por favor, consulta con un profesional de la salud para obtener una evaluación adecuada.")
    elif restriction_type == "medication_restriction":
        return ("No estoy autorizado para recetar medicamentos ni indicar tratamientos. "
                "Consulta a un médico o farmacéutico para obtener orientación.")
    else:
        return ("Gracias por compartir tus síntomas. Estoy aquí para ofrecer información general, "
                "pero siempre consulta con un profesional de la salud para más detalles.")