import boto3
from config.config import Config
from services.chatbot.bedrock_claude import call_claude
import logging
import json

def detect_medical_context(messages):
    """
    Analyze conversation history to extract medical context
    """
    context_prompt = f"""
    Analiza el siguiente historial de conversación y extrae información médica relevante:
    
    Conversación: {json.dumps(messages)}
    
    Proporciona un resumen estructurado que incluya:
    - Información personal (edad, sexo)
    - Síntomas reportados
    - Nivel de dolor
    - Posibles áreas de preocupación médica
    """
    
    try:
        context_analysis = call_claude(context_prompt, max_tokens=300, temperature=0.1)
        return context_analysis
    except Exception as e:
        logging.error(f"Error analyzing medical context: {e}")
        return "No se pudo analizar el contexto médico"

def detect_entities(text, context=None):
    try:
        client = boto3.client(service_name='comprehendmedical', region_name=Config.AWS_REGION)

        result = client.detect_entities(Text=text)

        entities = []
        for entity in result.get('Entities', []):
            entity_data = {
               'Text': entity.get('Text', ''),
               'Category': entity.get('Category', ''),
               'Type': entity.get('Type', ''),
               'Score': entity.get('Score', 0.0)
            }

            # Safely handle SNOMED CT concepts
            if 'SNOMEDCTConcepts' in entity:
                entity_data["snomed"] = [
                    {"code": concept.get('Code', ''), 
                     "description": concept.get('Description', '')}
                    for concept in entity['SNOMEDCTConcepts']
                ]

            entities.append(entity_data)

        # If additional context is provided, enhance entity detection
        if context:
            enhanced_context = detect_medical_context([{"content": text}])
            return {
                "entities": entities,
                "context_analysis": enhanced_context
            }

        return entities

    except Exception as e:
        logging.error(f"Error detecting medical entities: {e}")
        return []

def analyze_text(text, context=None):
    return detect_entities(text, context)