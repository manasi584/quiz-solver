# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "requests",
# ]
# ///

import sys, json
import tempfile
import os

from pathlib import Path

try:
    import pandas as pd
except Exception as e:
    print(json.dumps({'error': 'pandas not installed: ' + str(e)}))
    sys.exit(1)

import requests

def answer_for_csv_from_url(url, question_text):
    r = requests.get(url)
    r.raise_for_status()
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(r.content)
    tmp.flush()
    tmp.close()
    try:
        # try read as csv or excel
        try:
            df = pd.read_csv(tmp.name)
        except Exception:
            df = pd.read_excel(tmp.name)

        # Heuristic: if question mentions 'sum' and column name in quotes, find it
        import re
        m = re.search(r"sum of the \"([^\"]+)\" column", question_text, re.I)
        if m:
            col = m.group(1)
            if col in df.columns:
                s = df[col].sum()
                return {'answer': float(s)}

        # fallback: if there is a column named 'value' sum it
        if 'value' in df.columns:
            return {'answer': float(df['value'].sum())}

        # else return descriptive stats
        stats = df.describe().to_dict()
        return {'answer': stats}
    finally:
        try:
            os.unlink(tmp.name)
        except:
            pass

def main():
    inp = sys.stdin.read()
    try:
        payload = json.loads(inp)
    except Exception as e:
        print(json.dumps({'error': 'invalid json input to python analyze: ' + str(e)}))
        sys.exit(1)

    url = payload.get('url')
    analysisSpec = payload.get('analysisSpec', {})
    question = analysisSpec.get('questionText', '')

    if not url:
        print(json.dumps({'error': 'no url provided'}))
        sys.exit(1)

    try:
        res = answer_for_csv_from_url(url, question)
        print(json.dumps(res))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    main()
