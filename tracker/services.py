import os
import json
from datetime import datetime
from collections import defaultdict
from tracker.utils import (
    generate_visitor_id,
    anonymize_ip,
    get_device_info,
    read_json_file,
    write_json_file,
    get_date_range
)


class VisitorService:
    def __init__(self, config):
        self.config = config
        self.data_dir = 'data'
        self.visits_file = os.path.join(self.data_dir, 'visits.json')
        self.events_file = os.path.join(self.data_dir, 'events.json')
        os.makedirs(self.data_dir, exist_ok=True)

    def record_visit(self, ip_address, user_agent, page_url, referrer,
                     screen_resolution, language, timestamp):
        anonymized_ip = anonymize_ip(ip_address) if self.config.get('anonymize_ip', True) else ip_address
        device_info = get_device_info(user_agent)

        visit_id = generate_visitor_id(ip_address, user_agent)

        visit_data = {
            'visit_id': visit_id,
            'ip_address': anonymized_ip,
            'user_agent': user_agent,
            'page_url': page_url,
            'referrer': referrer or '',
            'screen_resolution': screen_resolution or '',
            'language': language or '',
            'timestamp': timestamp or datetime.utcnow().isoformat(),
            'device': device_info,
            'session_id': visit_id
        }

        visits = read_json_file(self.visits_file)
        visits.append(visit_data)
        write_json_file(self.visits_file, visits)

        return visit_id, visit_data

    def record_event(self, event_type, event_data, visit_id, element_selector, timestamp):
        event = {
            'event_id': len(read_json_file(self.events_file)) + 1,
            'visit_id': visit_id,
            'event_type': event_type,
            'event_data': event_data or {},
            'element_selector': element_selector or '',
            'timestamp': timestamp or datetime.utcnow().isoformat()
        }

        events = read_json_file(self.events_file)
        events.append(event)
        write_json_file(self.events_file, events)

        return event['event_id']

    def get_visitor_stats(self, start_date=None, end_date=None, metric='overview'):
        visits = read_json_file(self.visits_file)
        events = read_json_file(self.events_file)

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                visits = [v for v in visits if datetime.fromisoformat(v['timestamp']) >= start_dt]
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                visits = [v for v in visits if datetime.fromisoformat(v['timestamp']) <= end_dt]
            except ValueError:
                pass

        stats = {
            'overview': self._calculate_overview(visits, events),
            'pageviews': self._calculate_pageviews(visits),
            'visitors': self._calculate_visitors(visits),
            'sources': self._calculate_sources(visits),
            'devices': self._calculate_devices(visits),
            'browsers': self._calculate_browsers(visits),
            'timeline': self._calculate_timeline(visits),
            'events': self._calculate_events_summary(events)
        }

        return stats.get(metric, stats['overview'])

    def _calculate_overview(self, visits, events):
        unique_visitors = len(set(v['visit_id'] for v in visits))

        daily_visits = defaultdict(int)
        for v in visits:
            date = v['timestamp'][:10]
            daily_visits[date] += 1

        avg_daily = 0
        if daily_visits:
            avg_daily = sum(daily_visits.values()) / len(daily_visits)

        return {
            'total_pageviews': len(visits),
            'unique_visitors': unique_visitors,
            'total_events': len(events),
            'avg_daily_visits': round(avg_daily, 2),
            'date_range': {
                'start': min(v['timestamp'][:10] for v in visits) if visits else None,
                'end': max(v['timestamp'][:10] for v in visits) if visits else None
            },
            'top_pages': self._get_top_pages(visits, 10)
        }

    def _calculate_pageviews(self, visits):
        pageviews = defaultdict(int)
        for v in visits:
            pageviews[v['page_url']] += 1

        sorted_pages = sorted(pageviews.items(), key=lambda x: x[1], reverse=True)

        return {
            'total': len(visits),
            'by_page': dict(sorted_pages[:50]),
            'top_pages': [{'url': url, 'views': count} for url, count in sorted_pages[:10]]
        }

    def _calculate_visitors(self, visits):
        visitors = defaultdict(lambda: {'visits': 0, 'first_seen': None, 'last_seen': None})
        for v in visits:
            vid = v['visit_id']
            visitors[vid]['visits'] += 1
            if not visitors[vid]['first_seen'] or v['timestamp'] < visitors[vid]['first_seen']:
                visitors[vid]['first_seen'] = v['timestamp']
            if not visitors[vid]['last_seen'] or v['timestamp'] > visitors[vid]['last_seen']:
                visitors[vid]['last_seen'] = v['timestamp']

        return {
            'unique_visitors': len(visitors),
            'returning_visitors': sum(1 for v in visitors.values() if v['visits'] > 1),
            'visitor_details': [
                {'visit_id': k, 'visit_count': v['visits']}
                for k, v in list(visitors.items())[:20]
            ]
        }

    def _calculate_sources(self, visits):
        sources = defaultdict(int)
        for v in visits:
            referrer = v.get('referrer', '') or 'Direct'
            if referrer:
                try:
                    from urllib.parse import urlparse
                    source = urlparse(referrer).netloc
                    if source:
                        sources[source] += 1
                        continue
                except:
                    pass
            sources['Direct'] += 1

        sorted_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)
        return {
            'by_source': dict(sorted_sources[:20]),
            'top_sources': [{'source': src, 'visits': count} for src, count in sorted_sources[:10]]
        }

    def _calculate_devices(self, visits):
        devices = defaultdict(int)
        os_count = defaultdict(int)

        for v in visits:
            device = v.get('device', {})
            devices[device.get('device', 'Unknown')] += 1
            os_count[device.get('os', 'Unknown')] += 1

        return {
            'devices': dict(sorted(devices.items(), key=lambda x: x[1], reverse=True)),
            'operating_systems': dict(sorted(os_count.items(), key=lambda x: x[1], reverse=True))
        }

    def _calculate_browsers(self, visits):
        browsers = defaultdict(int)

        for v in visits:
            device = v.get('device', {})
            browser = device.get('browser', 'Unknown')
            browsers[browser] += 1

        return dict(sorted(browsers.items(), key=lambda x: x[1], reverse=True))

    def _calculate_timeline(self, visits):
        daily = defaultdict(lambda: {'pageviews': 0, 'visitors': set()})

        for v in visits:
            date = v['timestamp'][:10]
            daily[date]['pageviews'] += 1
            daily[date]['visitors'].add(v['visit_id'])

        timeline = []
        for date in sorted(daily.keys()):
            data = daily[date]
            timeline.append({
                'date': date,
                'pageviews': data['pageviews'],
                'visitors': len(data['visitors'])
            })

        return timeline

    def _calculate_events_summary(self, events):
        event_types = defaultdict(int)
        for e in events:
            event_types[e['event_type']] += 1

        return {
            'total_events': len(events),
            'by_type': dict(event_types)
        }

    def _get_top_pages(self, visits, limit=10):
        pageviews = defaultdict(int)
        for v in visits:
            pageviews[v['page_url']] += 1

        sorted_pages = sorted(pageviews.items(), key=lambda x: x[1], reverse=True)
        return [{'url': url, 'views': count} for url, count in sorted_pages[:limit]]

    def get_http_logs(self, limit=100):
        log_file = self.config.get('log_file', 'data/http_access.log')
        if not os.path.exists(log_file):
            return []

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-limit:] if line.strip()]
        except IOError:
            return []

    def log_http_request(self, request_info):
        log_file = self.config.get('log_file', 'data/http_access.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'method': request_info.get('method', ''),
            'path': request_info.get('path', ''),
            'ip': request_info.get('ip', ''),
            'user_agent': request_info.get('user_agent', ''),
            'status_code': request_info.get('status_code', 200)
        }

        max_lines = self.config.get('max_log_lines', 10000)

        try:
            lines = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

            lines.append(json.dumps(log_entry, ensure_ascii=False) + '\n')

            if len(lines) > max_lines:
                lines = lines[-max_lines:]

            with open(log_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except IOError:
            pass

    def get_recent_visits(self, limit=20):
        visits = read_json_file(self.visits_file)
        sorted_visits = sorted(visits, key=lambda x: x.get('timestamp', ''), reverse=True)
        return sorted_visits[:limit]

    def cleanup_data(self, days=None):
        if days is None:
            days = self.config.get('data_retention_days', 90)

        cleanup_files = [
            (self.visits_file, days),
            (self.events_file, days)
        ]

        for filepath, retention_days in cleanup_files:
            if os.path.exists(filepath):
                cutoff_date = datetime.utcnow() - datetime.timedelta(days=retention_days)

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

        return True
