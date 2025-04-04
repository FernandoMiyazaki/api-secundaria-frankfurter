from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
api = Api(
    title="API Frankfurter",
    version="1.0",
    description="API para consulta de cotações de moedas",
    doc="/swagger"
)