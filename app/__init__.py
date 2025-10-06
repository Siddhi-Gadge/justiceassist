from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv


db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    load_dotenv() 
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///justice.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'super-secret-jwt' 
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    # app.config.from_object('config.Config')

    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    from app.routes.main_routes import main as main_blueprint
    from app.routes.auth_routes import auth as auth_blueprint
    from app.routes.ai_routes import ai as ai_blueprint
    from app.routes.report_routes import report as report_blueprint
    from app.routes.dashboard_route import dashboard


    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(report_blueprint, url_prefix='/report')
    app.register_blueprint(ai_blueprint, url_prefix='/ai')
    app.register_blueprint(dashboard)

    return app
