from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_pymongo import PyMongo
from .config import config
import os

# Initialize extensions
mongo = PyMongo()
jwt = JWTManager()


def create_app(config_name='default'):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Enable CORS with proper configuration
    CORS(app,
         origins=["http://localhost:3000", "http://localhost:3001"],
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

    # Initialize extensions
    mongo.init_app(app)
    jwt.init_app(app)

    # Register blueprints
    from .controllers.auth_controller import auth_bp
    from .controllers.daily_question_controller import daily_question_bp
    from .controllers.quiz_controller import quiz_bp
    from .controllers.messages_controller import messages_bp
    from .controllers.calendar_controller import calendar_bp
    from .controllers.agent_controller import agent_bp
    from .controllers.internal_controller import internal_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(daily_question_bp, url_prefix="/api/daily-question")
    app.register_blueprint(quiz_bp, url_prefix="/api/quiz")
    app.register_blueprint(messages_bp, url_prefix="/api/messages")
    app.register_blueprint(calendar_bp, url_prefix="/api/calendar")
    app.register_blueprint(agent_bp, url_prefix="/api/agent")
    app.register_blueprint(internal_bp, url_prefix="/api/internal")

    @app.after_request
    def add_cache_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Health check endpoint
    @app.route("/api/health")
    def health_check():
        return {"status": "healthy", "message": "Together API is running"}, 200

    return app


# Allow legacy imports like `from app import app`
app = create_app(os.environ.get("FLASK_CONFIG", "default"))
