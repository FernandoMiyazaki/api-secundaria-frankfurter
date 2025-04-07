import os
from flask import Flask
from .extensions import db, migrate, cors, api
from .routes import main, ns_cotacao, ns_transacoes
from .config import config

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Inicializa extensões
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # Registra blueprints
    app.register_blueprint(main)
    
    # Inicializa API com Swagger
    api.init_app(app)
    
    # Adiciona namespaces à API
    api.add_namespace(ns_cotacao)
    api.add_namespace(ns_transacoes)
    
    # Cria tabelas do banco de dados (em ambiente de desenvolvimento)
    with app.app_context():
        db.create_all()
    
    return app