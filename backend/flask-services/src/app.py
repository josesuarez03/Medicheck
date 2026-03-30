from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from config.config import Config
import logging
from services.chatbot.input_validate import setup_nltk

logger = logging.getLogger(__name__)

setup_nltk()

def create_app(config_class=Config):
    """Crear y configurar la aplicación Flask con mejor soporte para WebSockets"""
    config_class.validate()
    from data.connect import mongo_client, redis_client
    from routes import init_app, socketio

    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configurar CORS con opciones más específicas
    CORS(app, resources={
        r"/chat/*": {"origins": "*"},
        r"/api/ws/*": {"origins": "*"}
    }, supports_credentials=True)
    
    # Registrar middleware para autenticar peticiones desde Django
    @app.before_request
    def validate_django_integration():
        if config_class.DJANGO_INTEGRATION:
            # Si viene de Django, verificar la autenticación
            request_signature = request.headers.get('X-Request-Signature')
            if not request_signature and app.config.get('DJANGO_VALIDATION_REQUIRED', False):
                logger.warning("Petición recibida sin firma de integración Django")

    @app.get("/health")
    def health():
        checks = {}
        status_code = 200

        try:
            mongo_client.admin.command("ping")
            checks["mongo"] = "ok"
        except Exception as exc:
            checks["mongo"] = f"error:{exc}"
            status_code = 503

        try:
            redis_client.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error:{exc}"
            status_code = 503

        return jsonify(
            {
                "status": "ok" if status_code == 200 else "degraded",
                "checks": checks,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ), status_code
    
    # Inicializar rutas y WebSockets con manejo de errores
    try:
        init_app(app)
        logger.info("Aplicación Flask inicializada correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar las rutas de Flask: {str(e)}")
    
    # Añadir soporte para manejar errores de WebSocket
    @socketio.on_error()
    def handle_socket_error(e):
        logger.error(f"Error en WebSocket: {str(e)}")
    
    return app

if __name__ == '__main__':
    app = create_app()
    from routes import socketio
    # Optimizar configuración de Socket.IO
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=Config.DEBUG,
        use_reloader=Config.DEBUG,
    )
