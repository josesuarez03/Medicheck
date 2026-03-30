import logging
from services.chatbot.context_manager import init_context
from services.chatbot.comprehend_medical import detect_entities
from services.chatbot.input_validate import analyze_message, generate_response
from services.chatbot.triaje_classification import TriageClassification
from services.chatbot.bedrock_claude import call_claude
from services.chatbot.conversation_context_service import ConversationContextService
from services.chatbot.pain_utils import extract_pain_scale

logging.basicConfig(level=logging.INFO)

class Chatbot:
    def __init__(
        self,
        user_input,
        user_data,
        initial_prompt=None,
        user_id=None,
        conversation_id=None,
        existing_context=None,
        postgres_context=None,
    ):
        self.user_input = user_input
        self.user_data = user_data
        self.initial_prompt = initial_prompt
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.existing_context = existing_context or {}
        self.postgres_context = postgres_context or {}
        self.context = {}
        self.triage = None
        self.entities = None
        self.response = None
        self.context_service = ConversationContextService()
        self.max_questions_per_turn = 2

    def initialize_conversation(self):
        try:
            # Validar el mensaje del usuario
            analysis_result = analyze_message(self.user_input)
            
            # Fix: analyze_message returns a tuple, handle it correctly
            if isinstance(analysis_result, tuple):
                analysis_type, error_message = analysis_result
            else:
                # Handle the case where it might return a dict
                analysis_type = analysis_result.get('type', 'general_response')
                error_message = analysis_result.get('error', '')
            
            # Check if the analysis indicates an invalid message
            if analysis_type == "input_error":
                return {"error": error_message or "Mensaje inválido o irreconocible."}
            
            # Handle greeting messages with a direct response
            if analysis_type == "greeting":
                greeting_response = generate_response(self.user_input)
                return {
                    "context": self.user_data or {},
                    "triaje_level": "info",
                    "entities": [],
                    "response": greeting_response,
                    "symptoms": [],
                    "symptoms_pattern": "",
                    "pain_scale": 0,
                    "missing_questions": [],
                    "analysis_type": analysis_type,
                    "conversation_state": {
                        "missing_fields": [],
                        "collected_fields": list((self.user_data or {}).keys()),
                        "next_intent": "collect_initial_symptoms",
                        "loop_guard_triggered": False,
                        "questions_selected": [],
                        "max_questions_per_turn": self.max_questions_per_turn
                    }
                }
            
            # Detectar entidades médicas
            self.entities = detect_entities(self.user_input)
            
            # Fix: init_context expects text, not user_data object
            # Pass the user_input as text for entity extraction
            context_result = init_context(self.user_input, user_data=self.user_data, existing_context=self.existing_context)
            
            # Extract context from the result
            if isinstance(context_result, dict):
                self.context = context_result.get('context', {})
                missing_questions = context_result.get('missing_questions', [])
            else:
                self.context = context_result
                missing_questions = []
            
            # Add medical entities to context
            if self.entities:
                self.context['medical_entities'] = self.entities
            
            # Fix: TriageClassification constructor expects specific parameters
            # Extract symptoms and pain level from entities or context
            symptoms = self._extract_symptoms_from_entities(self.entities)
            pain_level = self._extract_pain_level_from_context()
            
            # Add extracted information to context
            self.context['symptoms'] = symptoms
            self.context['pain_level'] = pain_level
            
            # Crear instancia de TriageClassification con los parámetros correctos
            self.triage = TriageClassification(
                symptoms=symptoms,
                pain_level=pain_level,
                environment=self.context.get('environment', 'general')
            )
            questions_selected = []

            prompt_context = self.context
            if self.user_id and self.conversation_id:
                prompt_context = self.context_service.build_prompt_context(
                    user_id=self.user_id,
                    conversation_id=self.conversation_id,
                    user_input=self.user_input,
                    current_context=self.context,
                    missing_questions=missing_questions,
                    questions_selected=questions_selected,
                    postgres_context=self.postgres_context,
                    triage_level=self.triage.triage_level,
                )
            else:
                prompt_context = {
                    **self.context,
                    "user_input": self.user_input,
                    "questions_selected": questions_selected,
                    "postgres_context": self.postgres_context,
                    "interaction_style": "turn_based",
                    "max_questions_per_turn": self.max_questions_per_turn,
                    "intro_mode": "brief_context_plus_one_question",
                }
            
            self.response = call_claude(
                prompt=prompt_context,
                triage_level=self.triage.triage_level,
                initial_prompt=self.initial_prompt
            )

            loop_guard_triggered = False
            if self.user_id and self.conversation_id:
                loop_guard_triggered = self.context_service.detect_loop(
                    self.user_id,
                    self.conversation_id,
                    self.response
                )
                if loop_guard_triggered:
                    if questions_selected:
                        questions_selected = questions_selected[:1]
                    self.response = (
                        "Para avanzar sin repetirnos, dame un ejemplo breve. "
                        "Por ejemplo: 'desde hace 2 días, empeora por la noche'."
                    )
            
            # Handle severe cases
            if self.triage.triage_level == 'Severo':
                emergency_response = self.triage.handle_severe_case(self.user_input)
                self.response = emergency_response
            
            # Extract additional triage information
            symptoms_pattern = TriageClassification.analyze_symptom_pattern(symptoms)
            
            return {
                "context": self.context,
                "triaje_level": self.triage.triage_level,
                "entities": self.entities,
                "response": self.response,
                "symptoms": symptoms,
                "symptoms_pattern": symptoms_pattern,
                "pain_scale": pain_level,
                "missing_questions": missing_questions,
                "analysis_type": analysis_type,
                "conversation_state": {
                    "missing_fields": [],
                    "collected_fields": [k for k, v in self.context.items() if v not in (None, "", [], {})],
                    "next_intent": "triage_recommendation" if self.triage.triage_level == 'Severo' else "collect_missing_data",
                    "loop_guard_triggered": loop_guard_triggered,
                    "questions_selected": questions_selected,
                    "max_questions_per_turn": self.max_questions_per_turn
                }
            }
        
        except Exception as e:
            logging.error(f"Error en la inicialización del chatbot: {e}")
            return {"error": "Ocurrió un problema al procesar la solicitud."}
    
    def _extract_symptoms_from_entities(self, entities):
        """Extract symptoms from medical entities"""
        symptoms = []
        if not entities:
            return symptoms
            
        for entity in entities:
            if isinstance(entity, dict):
                # Check if it's a symptom-related entity
                if entity.get('Category') == 'MEDICAL_CONDITION' or entity.get('Type') == 'DX_NAME':
                    symptoms.append(entity.get('Text', '').lower())
                elif entity.get('Category') == 'SYMPTOM':
                    symptoms.append(entity.get('Text', '').lower())
        
        return symptoms
    
    def _extract_pain_level_from_context(self):
        """Extract pain from current message; keep previous value when no new evidence."""
        explicit_pain = extract_pain_scale(self.user_input)
        if explicit_pain is not None:
            return explicit_pain

        previous_candidates = [
            self.existing_context.get("pain_level_reported"),
            self.existing_context.get("pain_level"),
            self.existing_context.get("pain_scale"),
        ]
        if isinstance(self.existing_context.get("hybrid_state"), dict):
            previous_candidates.append(self.existing_context["hybrid_state"].get("last_pain_scale"))

        for value in previous_candidates:
            if isinstance(value, int) and 0 <= value <= 10:
                return value

        # Do not assume pain intensity without explicit evidence.
        return 0

    def _is_first_clinical_turn(self):
        if not self.conversation_id:
            return True
        if not (self.user_id and self.conversation_id):
            return False
        recent = self.context_service.get_recent_window(self.user_id, self.conversation_id, n=1)
        return len(recent) == 0

    def _build_question_queue(self, missing_question_meta, missing_questions):
        if missing_question_meta:
            ordered = sorted(missing_question_meta, key=lambda item: item.get("priority", 99))
            return [item.get("question") for item in ordered if item.get("question")]
        return list(missing_questions or [])

    def _select_questions_for_turn(self, question_queue, is_first_turn):
        queue = list(dict.fromkeys(question_queue or []))
        if not queue:
            return []
        if is_first_turn:
            return queue[:1]
        if len(queue) <= self.max_questions_per_turn:
            return queue
        return queue[:self.max_questions_per_turn]

    def _compose_turn_response(self, base_response, questions_selected, is_first_turn, loop_guard_triggered):
        if not questions_selected:
            return base_response

        if loop_guard_triggered:
            header = "Vamos paso a paso para completar el triaje."
        elif is_first_turn:
            header = "Te ayudaré con unas preguntas cortas para orientarte mejor."
        else:
            header = "Gracias por la información. Para continuar:"

        if len(questions_selected) == 1:
            return f"{header}\n{questions_selected[0]}"
        return f"{header}\n1. {questions_selected[0]}\n2. {questions_selected[1]}"
