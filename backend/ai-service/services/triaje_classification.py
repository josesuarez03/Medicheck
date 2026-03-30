import logging
from typing import List, Dict
from services.chatbot.input_validate import analyze_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TriageClassification:
    COMMON_SYMPTOMS = {
        'MUSCULOSKELETAL': ['dolor de espalda', 'dolor de cuello', 'dolor en muñecas', 'tensión muscular', 'dolor articular'],
        'VISION_RELATED': ['fatiga visual', 'visión borrosa', 'ojos secos', 'dolor de cabeza', 'sensibilidad a la luz'],
        'STRESS_RELATED': ['ansiedad', 'insomnio', 'fatiga', 'irritabilidad', 'dificultad para concentrarse'],
        'RESPIRATORY': ['tos', 'congestión nasal', 'dolor de garganta', 'dificultad para respirar', 'estornudos frecuentes'],
        'DIGESTIVE': ['dolor estomacal', 'náuseas', 'acidez', 'pérdida de apetito', 'malestar digestivo']
    }

    EMERGENCY_MESSAGES = {
        'general': "Por favor, acuda inmediatamente al centro médico más cercano. Sus síntomas requieren atención médica urgente.",
        'workplace': "Notifique a su supervisor y diríjase al servicio médico de la empresa o al centro médico más cercano.",
        'educational': "Diríjase inmediatamente al servicio médico de la institución o al centro médico más cercano."
    }

    TRIAGE_CRITERIA = {
        'Severo': {
            'pain_threshold': 8,
            'urgent_symptoms': ['dificultad para respirar severa', 'dolor en el pecho', 'pérdida de consciencia', 'traumatismo grave', 'sangrado abundante', 'quemadura grave', 'dolor intenso persistente']
        },
        'Moderado': {
            'pain_threshold': 5,
            'concerning_symptoms': ['fiebre alta', 'vómitos persistentes', 'deshidratación', 'mareos intensos', 'dolor moderado a severo']
        },
        'Leve': {
            'pain_threshold': 3,
            'minor_symptoms': ['fatiga leve', 'dolor de cabeza leve', 'malestar general', 'síntomas de resfriado', 'molestias musculares leves']
        }
    }

    def __init__(self, symptoms: List[str], pain_level: int, environment: str = 'general'):
        self.symptoms = symptoms
        self.pain_level = pain_level
        self.environment = environment
        self.triage_level = self.classify_triage()
        logging.info(f'Triage classification initialized with symptoms: {self.symptoms}, pain level: {self.pain_level}, environment: {self.environment}')

    def classify_triage(self) -> str:
        """Clasifica el nivel de triaje según los síntomas y el nivel de dolor."""
        for level, criteria in self.TRIAGE_CRITERIA.items():
            if self.pain_level >= criteria['pain_threshold']:
                logging.info(f'Triage level classified as {level} based on pain threshold.')
                return level
            if any(symptom in criteria.get('urgent_symptoms', []) for symptom in self.symptoms):
                logging.warning('Urgent symptoms detected, classifying as Severo.')
                return 'Severo'
            if any(symptom in criteria.get('concerning_symptoms', []) for symptom in self.symptoms):
                logging.info('Concerning symptoms detected, classifying as Moderado.')
                return 'Moderado'
            if any(symptom in criteria.get('minor_symptoms', []) for symptom in self.symptoms):
                logging.info('Minor symptoms detected, classifying as Leve.')
                return 'Leve'
        logging.info('Defaulting to Leve classification.')
        return 'Leve'

    def handle_severe_case(self, message: str) -> str:
        """Maneja casos severos proporcionando instrucciones de emergencia."""
        logging.warning(f'Handling severe case for message: {message}')
        if analyze_message(message) == "diagnosis_restriction":
            logging.warning('Diagnosis restriction detected.')
            return (f"{self.EMERGENCY_MESSAGES[self.environment]}\n"
                    "No puedo proporcionar un diagnóstico. Es importante que un profesional médico evalúe su condición inmediatamente.")
        return self.EMERGENCY_MESSAGES[self.environment]

    @staticmethod
    def get_workplace_symptoms(category: str = None) -> List[str]:
        """Obtiene lista de síntomas comunes en entornos laborales/educativos."""
        logging.info(f'Retrieving workplace symptoms for category: {category}')
        if category and category in TriageClassification.COMMON_SYMPTOMS:
            return TriageClassification.COMMON_SYMPTOMS[category]
        return [symptom for symptoms in TriageClassification.COMMON_SYMPTOMS.values() for symptom in symptoms]

    @staticmethod
    def analyze_symptom_pattern(symptoms: List[str]) -> Dict[str, int]:
        """Analiza el patrón de síntomas para identificar categorías predominantes."""
        logging.info(f'Analyzing symptom pattern for symptoms: {symptoms}')
        pattern = {category: 0 for category in TriageClassification.COMMON_SYMPTOMS.keys()}
        for symptom in symptoms:
            for category, category_symptoms in TriageClassification.COMMON_SYMPTOMS.items():
                if symptom in category_symptoms:
                    pattern[category] += 1
        logging.info(f'Symptom pattern analysis result: {pattern}')
        return pattern
