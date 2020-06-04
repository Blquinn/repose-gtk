from datetime import timedelta

import requests


def parse_content_type(content_type_header: str) -> str:
    return content_type_header.split(';')[0]


def get_content_type(response: requests.Response) -> str:
    return parse_content_type(response.headers.get('content-type', ''))


language_map = {
    'text': 'text',
    'text-plain': 'text',
    'json': 'json',
    'js': 'js',
    'xml-application': 'xml',
    'xml-text': 'xml',
    'html': 'html',
}
content_type_map = {
    'text-plain': 'text/plain',
    'json': 'application/json',
    'js': 'application/javascript',
    'xml-application': 'application/xml',
    'xml-text': 'text/xml',
    'html': 'text/html',
}
content_type_map_reverse = {v: k for k, v in content_type_map.items()}


def get_language_for_mime_type(mime_type: str) -> str:
    """
    Gets the GtkSource.LanguageManager language id for a given mime type.
    Falls back to text if not found.
    """
    return language_map[content_type_map_reverse.get(mime_type) or 'text']


def sizeof_fmt(num: float, suffix='B') -> str:
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def timedelta_fmt(delta: timedelta) -> str:
    ts = delta.total_seconds()

    if ts >= 1:
        for unit in ['s', 'M', 'H']:
            if abs(ts) < 60:
                return '%3.1f %s' % (ts, unit)
            ts /= 60
    else:
        mcs = delta.microseconds
        for unit in ['μs', 'ms']:
            if mcs < 1000:
                return '%d %s' % (mcs, unit)
            mcs /= 1000

    return str(delta)


def format_response_size(response: requests.Response) -> str:
    cl = response.headers.get('content-length')
    if cl:
        return sizeof_fmt(float(cl))
    return sizeof_fmt(float(len(response.content)))