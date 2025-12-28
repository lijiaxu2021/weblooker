import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from tracker import tracker_bp


def load_config(config_path='config.json'):
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def create_app(config=None):
    app = Flask(__name__)

    if config is None:
        config = load_config()

    app_config = config.get('app', {})
    app.config['SECRET_KEY'] = app_config.get('secret_key', 'dev-secret-key')
    app.config['TRACKER_CONFIG'] = config

    app.config['JSON_AS_ASCII'] = False
    app.config['JSON_SORT_KEYS'] = False

    domains_config = config.get('domains', {})
    cors_origins = domains_config.get('cors_origins', ['*'])

    CORS(app,
         origins=cors_origins,
         methods=['GET', 'POST', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
         supports_credentials=False)

    app.register_blueprint(tracker_bp, url_prefix='/api/tracker')

    os.makedirs('static', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    @app.route('/')
    def index():
        return jsonify({
            'service': 'Visitor Tracker API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'tracker_js': '/tracker.js',
                'track_visit': 'POST /api/tracker/visit',
                'track_event': 'POST /api/tracker/event',
                'stats': 'GET /api/tracker/stats',
                'logs': 'GET /api/tracker/logs',
                'health': 'GET /api/tracker/health'
            }
        })

    @app.route('/tracker.js')
    def serve_tracker_js():
        static_dir = os.path.join(os.getcwd(), 'static')
        if os.path.exists(os.path.join(static_dir, 'tracker.js')):
            response = send_from_directory(static_dir, 'tracker.js', mimetype='application/javascript')
            response.headers['Cache-Control'] = 'public, max-age=3600'
            return response
        else:
            return jsonify({'error': 'tracker.js not found'}), 404

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    @app.after_request
    def log_request(response):
        if config.get('logging', {}).get('enable_http_logging', True):
            if request.path.startswith('/api/tracker'):
                try:
                    from tracker.services import VisitorService
                    service = VisitorService(config.get('tracking', {}))
                    service.log_http_request({
                        'method': request.method,
                        'path': request.path,
                        'ip': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'status_code': response.status_code
                    })
                except Exception:
                    pass

        return response

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not found',
            'message': f'Endpoint {request.path} not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'error': 'Method not allowed',
            'message': f'Method {request.method} not allowed for this endpoint'
        }), 405

    return app


app = create_app()


if __name__ == '__main__':
    config = load_config()
    app_config = config.get('app', {})

    host = app_config.get('host', '0.0.0.0')
    port = app_config.get('port', 5000)
    debug = app_config.get('debug', False)

    print(f"Starting Visitor Tracker API on {host}:{port}")
    print(f"Tracker JS available at: http://{host}:{port}/tracker.js")

    app.run(host=host, port=port, debug=debug)
