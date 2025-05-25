from flask import request
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_request_logging(app):
    @app.before_request
    def log_request_info():
        logger.info('Request: %s %s', request.method, request.url)

    @app.after_request
    def log_response_info(response):
        logger.info('Response: %s %s %s', request.method, request.url, response.status)
        return response 