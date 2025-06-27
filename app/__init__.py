from flask import Flask
from .routes import main
from .auth import auth
from .db import close_db

def create_app():
    app = Flask(__name__)
    app.config['DATABASE'] = 'database/kardex.db'
    app.secret_key = 'clave_super_secreta'

    app.register_blueprint(main)
    app.register_blueprint(auth)

    app.teardown_appcontext(close_db)

    return app
