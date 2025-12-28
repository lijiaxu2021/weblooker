from flask import Blueprint, request, jsonify, Response
from tracker.services import VisitorService
from tracker.utils import validate_visitor_data, rate_limit_check

tracker_bp = Blueprint('tracker', __name__)


def get_config():
    from flask import current_app
    return current_app.config.get('TRACKER_CONFIG', {})


def get_visitor_service():
    config = get_config()
    return VisitorService(config.get('tracking', {}))


@tracker_bp.route('/visit', methods=['POST'])
def track_visit():
    if not rate_limit_check(request.remote_addr):
        return jsonify({'error': 'Rate limit exceeded', 'message': '请求过于频繁'}), 429

    data = request.get_json()
    validation = validate_visitor_data(data)

    if not validation['valid']:
        return jsonify({'error': validation['message']}), 400

    service = get_visitor_service()
    visit_id, visit_data = service.record_visit(
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', ''),
        page_url=data.get('pageUrl', ''),
        referrer=data.get('referrer', ''),
        screen_resolution=data.get('screenResolution', ''),
        language=data.get('language', ''),
        timestamp=data.get('timestamp', '')
    )

    service.log_http_request({
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'status_code': 201
    })

    return jsonify({
        'status': 'success',
        'visit_id': visit_id,
        'message': '访问记录成功'
    }), 201


@tracker_bp.route('/event', methods=['POST'])
def track_event():
    if not rate_limit_check(request.remote_addr):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    event_type = data.get('eventType')
    if not event_type:
        return jsonify({'error': 'Missing eventType'}), 400

    service = get_visitor_service()
    event_id = service.record_event(
        event_type=event_type,
        event_data=data.get('eventData', {}),
        visit_id=data.get('visitId', ''),
        element_selector=data.get('elementSelector', ''),
        timestamp=data.get('timestamp', '')
    )

    service.log_http_request({
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'status_code': 201
    })

    return jsonify({
        'status': 'success',
        'event_id': event_id,
        'message': '事件记录成功'
    }), 201


@tracker_bp.route('/events', methods=['POST'])
def track_events_batch():
    if not rate_limit_check(request.remote_addr):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    data = request.get_json()
    events = data.get('events', []) if data else []

    if not events:
        return jsonify({'error': 'No events provided'}), 400

    service = get_visitor_service()
    recorded_count = 0

    for event_data in events:
        service.record_event(
            event_type=event_data.get('eventType', 'unknown'),
            event_data=event_data.get('eventData', {}),
            visit_id=event_data.get('visitId', ''),
            element_selector=event_data.get('elementSelector', ''),
            timestamp=event_data.get('timestamp', '')
        )
        recorded_count += 1

    return jsonify({
        'status': 'success',
        'recorded': recorded_count,
        'message': f'成功记录 {recorded_count} 个事件'
    }), 201


@tracker_bp.route('/stats', methods=['GET'])
def get_statistics():
    service = get_visitor_service()

    metric = request.args.get('metric', 'overview')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    stats = service.get_visitor_stats(
        start_date=start_date,
        end_date=end_date,
        metric=metric
    )

    service.log_http_request({
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'status_code': 200
    })

    return jsonify({
        'status': 'success',
        'metric': metric,
        'data': stats
    }), 200


@tracker_bp.route('/stats/overview', methods=['GET'])
def get_overview():
    service = get_visitor_service()

    stats = service.get_visitor_stats(metric='overview')

    return jsonify({
        'status': 'success',
        'data': stats
    }), 200


@tracker_bp.route('/stats/pageviews', methods=['GET'])
def get_pageviews():
    service = get_visitor_service()

    stats = service.get_visitor_stats(metric='pageviews')

    return jsonify({
        'status': 'success',
        'data': stats
    }), 200


@tracker_bp.route('/stats/visitors', methods=['GET'])
def get_visitors():
    service = get_visitor_service()

    stats = service.get_visitor_stats(metric='visitors')

    return jsonify({
        'status': 'success',
        'data': stats
    }), 200


@tracker_bp.route('/logs', methods=['GET'])
def get_logs():
    service = get_visitor_service()

    limit = request.args.get('limit', 100)
    try:
        limit = int(limit)
    except ValueError:
        limit = 100

    logs = service.get_http_logs(limit=limit)

    return jsonify({
        'status': 'success',
        'count': len(logs),
        'logs': logs
    }), 200


@tracker_bp.route('/logs/recent', methods=['GET'])
def get_recent_visits():
    service = get_visitor_service()

    limit = request.args.get('limit', 20)
    try:
        limit = int(limit)
    except ValueError:
        limit = 20

    visits = service.get_recent_visits(limit=limit)

    return jsonify({
        'status': 'success',
        'count': len(visits),
        'visits': visits
    }), 200


@tracker_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'visitor-tracker',
        'version': '1.0.0'
    }), 200


@tracker_bp.route('/cleanup', methods=['POST'])
def cleanup_data():
    service = get_visitor_service()
    service.cleanup_data()

    return jsonify({
        'status': 'success',
        'message': '数据清理完成'
    }), 200


@tracker_bp.route('/export', methods=['GET'])
def export_data():
    service = get_visitor_service()

    metric = request.args.get('metric', 'overview')
    format_type = request.args.get('format', 'json')

    stats = service.get_visitor_stats(metric=metric)

    if format_type == 'json':
        response = Response(
            json.dumps(stats, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=stats_{metric}.json'}
        )
        return response

    return jsonify({
        'status': 'success',
        'data': stats
    }), 200
