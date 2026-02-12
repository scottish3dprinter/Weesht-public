from flask import Flask

from .db import initDB

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')

    initDB(app)

    from .routes import main
    app.register_blueprint(main)

    return app
