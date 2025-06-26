from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['DATABASE'] = 'database/kardex.db'

    # Registrar rutas
    from .routes import main
    app.register_blueprint(main)

    # Cierre de conexión a la base de datos
    from .db import close_db
    app.teardown_appcontext(close_db)

    return app
