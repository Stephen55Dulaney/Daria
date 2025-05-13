from flask import Blueprint

langchain_blueprint = Blueprint('langchain_features', __name__, url_prefix='/langchain', 
                               template_folder='templates')

# Import the prompt manager blueprint
from langchain_features.prompt_manager.routes import prompt_blueprint

# Register the prompt manager blueprint with the main blueprint
langchain_blueprint.register_blueprint(prompt_blueprint)

from langchain_features import routes 