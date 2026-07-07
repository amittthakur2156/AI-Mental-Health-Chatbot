from flask import Flask, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_sock import Sock

from config import config
from services.db_service import init_db
from services.ai_service import build_ai_reply
from services.auth_service import get_user_id_from_request
from routes.chat_routes import chat_bp
from routes.dashboard_routes import dashboard_bp
from routes.journal_routes import journal_bp
from routes.safety_routes import safety_bp
from routes.voice_routes import voice_bp
from routes.call_routes import call_bp, init_twilio_socket
from routes.connect_routes import connect_bp
from routes.admin_routes import admin_bp

socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
sock = Sock()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app)
    init_db(config.DATABASE_URL)

    app.register_blueprint(chat_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(safety_bp)
    app.register_blueprint(voice_bp)
    app.register_blueprint(call_bp)
    app.register_blueprint(connect_bp)
    app.register_blueprint(admin_bp)

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/chat")
    def chat_page():
        return render_template("chat.html")

    @app.get("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.get("/journal")
    def journal_page():
        return render_template("journal.html")

    @app.get("/safety")
    def safety_page():
        return render_template("safety.html")

    @app.get("/resources")
    def resources_page():
        return render_template("resources.html")

    @app.get("/connect")
    def connect_page():
        return render_template("connect.html")

    @app.get("/vcall")
    def vcall_page():
        return render_template("connect.html")

    @app.get("/admin")
    def admin_page():
        return render_template("admin.html")

    socketio.init_app(app)
    sock.init_app(app)
    init_twilio_socket(sock)
    return app


@socketio.on("voice_text")
def handle_voice_text(payload):
    """Socket.IO browser voice loop. Frontend STT sends transcript; backend replies; frontend TTS speaks it."""
    class _FakeReq:
        headers = {}
        args = {}
    user_id = (payload or {}).get("user_id") or "demo_user"
    message = ((payload or {}).get("message") or "").strip()
    session_id = (payload or {}).get("session_id")
    if not message:
        emit("voice_reply", {"error": "Empty voice transcript."})
        return
    preferred_language = (payload or {}).get("preferred_language")
    result = build_ai_reply(user_id=user_id, message=message, session_id=session_id, input_type="voice", preferred_language=preferred_language)
    emit("voice_reply", result)


app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)
