# utils/json_utils.py (crear este archivo)
import json
from datetime import datetime

def safe_json_dumps(obj):
    """JSON serializer seguro"""
    def default(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, '__dict__'):
            return str(o)
        return str(o)
    
    return json.dumps(obj, ensure_ascii=False, default=default)