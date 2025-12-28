import json
import hashlib
import time
import os
from datetime import datetime, timedelta
from collections import deque


class RateLimiter:
    def __init__(self, max_requests=100, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}

    def is_allowed(self, identifier):
        now = time.time()
        if identifier not in self.requests:
            self.requests[identifier] = deque()

        while self.requests[identifier] and \
                self.requests[identifier][0] <= now - self.time_window:
            self.requests[identifier].popleft()

        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(now)
            return True

        return False


rate_limiter = RateLimiter(max_requests=100, time_window=60)


def rate_limit_check(ip_address):
    return rate_limiter.is_allowed(ip_address)


def generate_visitor_id(ip_address, user_agent):
    combined = f"{ip_address}-{user_agent}"
    return hashlib.md5(combined.encode()).hexdigest()[:16]


def anonymize_ip(ip_address):
    if not ip_address:
        return ''
    parts = ip_address.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.xxx.xxx"
    return ip_address


def get_device_info(user_agent):
    from ua_parser import user_agent_parser

    parsed = user_agent_parser.Parse(user_agent)
    return {
        'browser': parsed.get('user_agent', {}).get('family', 'Unknown'),
        'browser_version': parsed.get('user_agent', {}).get('major', ''),
        'os': parsed.get('os', {}).get('family', 'Unknown'),
        'os_version': parsed.get('os', {}).get('major', ''),
        'device': parsed.get('device', {}).get('family', 'Desktop')
    }


def validate_visitor_data(data):
    if not data:
        return {'valid': False, 'message': 'No data provided'}

    page_url = data.get('pageUrl')
    if not page_url:
        return {'valid': False, 'message': 'Missing required field: pageUrl'}

    if not isinstance(page_url, str) or len(page_url) > 2048:
        return {'valid': False, 'message': 'Invalid page URL format'}

    return {'valid': True, 'message': 'Validation passed'}


def get_date_range(days=30):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def read_json_file(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def write_json_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cleanup_old_data(filepath, days=90):
    if not os.path.exists(filepath):
        return

    cutoff_date = datetime.utcnow() - timedelta(days=days)
    data = read_json_file(filepath)

    cleaned_data = []
    for item in data:
        timestamp = item.get('timestamp', '')
        if timestamp:
            try:
                item_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if item_date >= cutoff_date:
                    cleaned_data.append(item)
            except ValueError:
                cleaned_data.append(item)

    write_json_file(filepath, cleaned_data)
