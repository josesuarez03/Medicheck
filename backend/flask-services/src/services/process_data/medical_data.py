from datetime import datetime
import logging

from models.conversation import ConversationalDatasetManager
from services.chatbot.comprehend_medical import detect_entities
from services.chatbot.bedrock_claude import call_claude
from services.api.send_api import send_data_to_django

logger = logging.getLogger(__name__)


class MedicalDataProcessor:
    def __init__(self, user_id=None, conversation_id=None, config=None):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.config = config or {}
        self.dataset_manager = ConversationalDatasetManager()

    def process_medical_data(self, user_id, conversation_id):
        try:
            conversation = self.dataset_manager.get_conversation(user_id, conversation_id)
            if not conversation:
                logger.error("Conversación no encontrada: %s para usuario %s", conversation_id, user_id)
                return {"error": "Conversación no encontrada."}

            messages = conversation.get("messages", [])
            if not messages:
                logger.error("No hay mensajes en la conversación: %s para usuario %s", conversation_id, user_id)
                return {"error": "No hay mensajes en la conversación."}

            consolidated_text = self.consolidate_conversation(messages)
            medical_context = self.generate_medical_context_summary(messages, consolidated_text)
            enhanced_entities = detect_entities(consolidated_text)
            structured_data = self.extract_structured_data(conversation, messages, enhanced_entities)
            structured_data["medical_context"] = medical_context
            structured_data["processed_at"] = datetime.now().isoformat()
            structured_data["source"] = "chatbot"
            return structured_data
        except Exception as e:
            logger.error("Error procesando datos médicos de conversación %s: %s", conversation_id, str(e))
            return {"error": f"Error procesando datos médicos: {str(e)}"}

    def consolidate_conversation(self, messages):
        consolidated = []
        for message in messages:
            if message.get("role", "").lower() == "user":
                consolidated.append(message.get("content", ""))
        return " ".join(consolidated).strip()

    def generate_medical_context_summary(self, messages, consolidated_text):
        prompt = f"""
Eres un asistente médico especializado en extraer información médica relevante de conversaciones.
Genera un resumen clínico conciso, objetivo y sin diagnósticos con:
- Síntomas principales
- Duración/evolución
- Factores agravantes/alivio
- Antecedentes médicos mencionados
- Medicación o alergias mencionadas

Conversación:
{messages}

Texto consolidado:
{consolidated_text}
"""
        try:
            return call_claude(prompt, max_tokens=400, temperature=0.1).strip()
        except Exception as e:
            logger.error("Error generando resumen de contexto médico: %s", str(e))
            return "No se pudo generar el resumen del contexto médico."

    def extract_structured_data(self, conversation, messages, enhanced_entities):
        raw_pain = conversation.get("pain_scale")
        pain_scale = None
        if raw_pain is not None:
            try:
                pain_scale = int(float(raw_pain))
                pain_scale = max(0, min(10, pain_scale))
            except (TypeError, ValueError):
                pain_scale = None

        return {
            "triaje_level": conversation.get("triaje_level") or None,
            "pain_scale": pain_scale,
            "medical_context": "",
            "allergies": self.extract_allergies(messages, enhanced_entities),
            "medications": self.extract_medications(enhanced_entities),
            "medical_history": self.extract_medical_history(messages, enhanced_entities),
            "ocupacion": self.extract_occupation(messages),
        }

    def extract_allergies(self, messages, entities):
        allergies = []
        for entity in entities:
            if entity.get("Type") == "MEDICATION" and entity.get("Traits", []):
                for trait in entity.get("Traits", []):
                    if trait.get("Name") == "NEGATION":
                        continue
                    if trait.get("Name") == "ALLERGY":
                        allergies.append(entity.get("Text"))

        allergy_keywords = ["alergia", "alérgico", "alérgica", "reacción alérgica"]
        for message in messages:
            if message.get("role", "").lower() == "user":
                content = message.get("content", "").lower()
                if any(keyword in content for keyword in allergy_keywords) and not allergies:
                    allergies = ["Paciente menciona alergias, verificar detalles."]
        return "; ".join(allergies) if allergies else ""

    def extract_medications(self, entities):
        medications = []
        for entity in entities:
            if entity.get("Type") == "MEDICATION" and not any(
                trait.get("Name") == "NEGATION" for trait in entity.get("Traits", [])
            ):
                medication = entity.get("Text")
                if entity.get("Attributes"):
                    for attr in entity.get("Attributes"):
                        if attr.get("Type") == "DOSAGE":
                            medication += f" ({attr.get('Text')})"
                medications.append(medication)
        return "; ".join(medications) if medications else ""

    def extract_medical_history(self, messages, entities):
        conditions = []
        for entity in entities:
            if entity.get("Type") in ["MEDICAL_CONDITION", "DX_NAME"] and not any(
                trait.get("Name") == "NEGATION" for trait in entity.get("Traits", [])
            ):
                conditions.append(entity.get("Text"))

        history_keywords = ["antecedente", "historia médica", "diagnóstico previo", "padezco de", "sufro de"]
        for message in messages:
            if message.get("role", "").lower() == "user":
                content = message.get("content", "").lower()
                if any(keyword in content for keyword in history_keywords) and not conditions:
                    conditions = ["Paciente menciona antecedentes médicos, verificar detalles."]
        return "; ".join(conditions) if conditions else ""

    def extract_occupation(self, messages):
        occupation_keywords = ["trabajo como", "soy", "profesión", "ocupación", "me dedico a"]
        for message in messages:
            if message.get("role", "").lower() == "user":
                content = message.get("content", "").lower()
                for keyword in occupation_keywords:
                    if keyword in content:
                        idx = content.find(keyword) + len(keyword)
                        end_idx = content.find(".", idx)
                        if end_idx == -1:
                            end_idx = content.find(",", idx)
                        if end_idx == -1:
                            end_idx = len(content)
                        occupation = content[idx:end_idx].strip()
                        if occupation and len(occupation) < 100:
                            return occupation
        return ""

    def send_data_to_django(self, user_id, medical_data, jwt_token=None):
        try:
            return send_data_to_django(user_id, medical_data, jwt_token=jwt_token)
        except Exception as e:
            logger.error("Error al enviar datos a Django: %s", str(e))
            return {"error": f"Error al enviar datos a Django: {str(e)}"}
