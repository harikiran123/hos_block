from flask import Flask
from flask_login import LoginManager
from routes import main
from config import Config
from flask_login import current_user


app = Flask(__name__, static_folder='static')
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.find_by_username_and_role(user_id,None)

app.register_blueprint(main)
app.config['TEMPLATES_AUTO_RELOAD'] = True

