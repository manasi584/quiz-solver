import asyncio
import json
import subprocess
import os
from playwright.async_api import async_playwright
import aiohttp

async def run_python_analyze(url, local_path=None, analysis_spec=None):
    process = await asyncio.create_subprocess_exec(
        'python3', os.path.join(os.path.dirname(__file__), 'python_worker', 'analyze.py'),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    input_data = json.dumps({"url": url, "localPath": local_path, "analysisSpec": analysis_spec})
    stdout, stderr = await process.communicate(input_data.encode())
    
    if process.returncode != 0:
        raise Exception(f"Python analyze failed: {stderr.decode()}")
    
    return json.loads(stdout.decode())

async def post_answer(submit_url, payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(submit_url, json=payload) as response:
            return await response.json()

async def solve_task(email, secret, url):
    print(f"Starting solve for {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = await browser.new_page()
        page.set_default_navigation_timeout(90000)
        
        try:
            await page.goto(url, wait_until='networkidle')
            await page.wait_for_timeout(500)
            
            text = await page.evaluate("() => document.body.innerText")
            pre_text = await page.evaluate("() => { const p = document.querySelector('pre'); return p ? p.innerText : null; }")
            
            instruction = None
            if pre_text:
                try:
                    instruction = json.loads(pre_text)
                except:
                    pass
            
            # Find submit URL
            submit_url = await page.evaluate("""() => {
                const forms = Array.from(document.querySelectorAll('form'));
                if (forms.length) {
                    const f = forms.find(x => x.action);
                    if (f) return f.action;
                }
                
                const anchors = Array.from(document.querySelectorAll('a'));
                for (const a of anchors) {
                    if (/submit/i.test(a.innerText) || /submit/i.test(a.href)) return a.href;
                }
                
                const pres = Array.from(document.querySelectorAll('pre'));
                for (const p of pres) {
                    try {
                        const j = JSON.parse(p.innerText);
                        if (j.submit) return j.submit;
                        if (j.url && j.answer !== undefined) return j.url;
                    } catch(e) {}
                }
                return null;
            }""")
            
            # Try to decode base64 instructions
            decoded_instruction = await page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script'));
                for (const s of scripts) {
                    const txt = s.innerText || '';
                    const m = txt.match(/atob\\(`([A-Za-z0-9+/=\\n]+)`\\)/m);
                    if (m) return atob(m[1]);
                }
                return null;
            }""")
            
            parsed_json = None
            if decoded_instruction:
                import re
                json_match = re.search(r'\{[\s\S]*\}', decoded_instruction)
                if json_match:
                    try:
                        parsed_json = json.loads(json_match.group(0))
                    except:
                        pass
            
            # Handle file analysis case
            if parsed_json and parsed_json.get('url') and 'answer' not in parsed_json:
                file_url = parsed_json['url']
                analysis = await run_python_analyze(file_url, analysis_spec={"questionText": text})
                answer = analysis['answer']
                
                submit = parsed_json.get('submit') or submit_url
                if not submit:
                    raise Exception("No submit URL found")
                
                payload = {"email": email, "secret": secret, "url": url, "answer": answer}
                print(f"Posting answer to {submit}: {payload}")
                submit_resp = await post_answer(submit, payload)
                print(f"Submit response: {submit_resp}")
                
                if submit_resp and submit_resp.get('url'):
                    return await solve_task(email, secret, submit_resp['url'])
                
                await browser.close()
                return submit_resp
            
            # Fallback: look for download links
            download_link = await page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a'));
                for (const a of anchors) {
                    if (/download|file|pdf|csv|xls|xlsx/i.test(a.innerText) || /download|file|pdf|csv|xls|xlsx/i.test(a.href)) 
                        return a.href;
                }
                return null;
            }""")
            
            if download_link:
                analysis = await run_python_analyze(download_link, analysis_spec={"questionText": text})
                answer = analysis['answer']
                
                found_submit = await page.evaluate("""() => {
                    const anchors = Array.from(document.querySelectorAll('a'));
                    for (const a of anchors) {
                        if (/submit/i.test(a.innerText) && a.href) return a.href;
                    }
                    return null;
                }""")
                
                if not found_submit:
                    raise Exception("No submit URL found")
                
                payload = {"email": email, "secret": secret, "url": url, "answer": answer}
                submit_resp = await post_answer(found_submit, payload)
                await browser.close()
                
                if submit_resp and submit_resp.get('url'):
                    return await solve_task(email, secret, submit_resp['url'])
                
                return submit_resp
            
            await browser.close()
            return {"correct": False, "reason": "Could not parse quiz page", "textSnippet": text[:500]}
            
        except Exception as err:
            await browser.close()
            raise err