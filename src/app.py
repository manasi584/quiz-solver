# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "requests",
# ]
# ///

import sys
import json
import tempfile
import os
import requests

try:
    import pandas as pd
except ImportError as e:
    print(json.dumps({'error': f'pandas not installed: {e}'}))
    sys.exit(1)

def get_data_content(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    
    if url.lower().endswith(('.csv', '.xlsx', '.xls')):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(r.content)
            tmp.flush()
            try:
                df = pd.read_csv(tmp.name)
            except:
                df = pd.read_excel(tmp.name)
            
            try:
                os.unlink(tmp.name)
            except:
                pass
            return f"Data (first 100 rows):\n{df.head(100).to_string()}"
    
    return r.text[:10000]  

def analyze_with_llm(content, question):
    url = os.getenv('AIPIPE_URL', 'https://aipipe.org/openrouter/v1/responses')
    token = os.getenv('AIPIPE_TOKEN')
    
    prompt = f"""Analyze this data and answer the question. Return ONLY a JSON object with an 'answer' field containing the numeric result or string answer.

Data:
{content}

Question: {question}

Response (JSON only):"""
    
    payload = {
        "model": "openai/gpt-5-mini",
        "input": prompt
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()['output'].strip()
        return json.loads(result)
    except Exception as e:
        return {'error': f'LLM analysis failed: {str(e)}'}

def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception as e:
        print(json.dumps({'error': f'Invalid JSON: {str(e)}'}))
        sys.exit(1)
    
    url = payload.get('url')
    question = payload.get('analysisSpec', {}).get('questionText', '')
    
    if not url:
        print(json.dumps({'error': 'No URL provided'}))
        sys.exit(1)
    
    try:
        content = get_data_content(url)
        result = analyze_with_llm(content, question)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    main()