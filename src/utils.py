import json

def string_to_json(text):
    """Convert HTML-encoded string to JSON"""
    try:
        if text.startswith('Task: '):
            text = text[6:]
        decoded = html.unescape(text)
        print(json.loads(decoded))
        return json.loads(decoded)
    except:
        return None