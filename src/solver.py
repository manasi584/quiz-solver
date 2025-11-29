import asyncio
import base64
import re
import json
import aiohttp
import os
import html
from playwright.async_api import async_playwright
from llm_helper import LLMHelper
from utils import string_to_json



async def solve_task(email: str, secret: str, url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            task_text = await extract_task_from_page(page)
        
            if task_text:
                task_data = json.loads(task_text)
                submit_url = task_data.get("SUBMIT_URL")
                print("Submit URL:", submit_url)
                instructions = task_data.get("INSTRUCTIONS", [])
                task_text = " ".join(instructions) if isinstance(instructions, list) else str(instructions)
                
                answer = await process_task(task_text)
                print("Answer:", answer)
                
                if submit_url and answer is not None:
                    await submit_answer(submit_url, email, secret, url, answer)
                
                return {"success": True, "answer": answer}
            
            return {"success": False, "error": "Failed to extract task"}
            
        finally:
            await browser.close()

async def extract_task_from_page(page):
    await page.wait_for_timeout(1000)
    
    try:
        page_html = await page.content()
        llm = LLMHelper()
        llm_result = await llm.extract_task_with_llm(page_html)
        # print("llm result : ",llm_result)
        if llm_result:
            # Extract the JSON text from the response
            extracted_text = extract_llm_response(llm_result)
            return extracted_text
    except Exception as e:
        print(f"LLM extraction failed: {e}")
    return None


def extract_llm_response(llm_result):
    if not llm_result:
        return ''
    try:
        if 'output' in llm_result and len(llm_result['output']) > 1:
            content = llm_result['output'][1].get('content', [])
            if content and len(content) > 0:
                return content[0].get('text', '')
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error extracting LLM response: {e}")
    return ''

# def extract_submit_url(text):
#     # Look for submit URL pattern
#     match = re.search(r'Post.*?to\s+(https?://[^\s<]+)', text, re.IGNORECASE)
#     return match.group(1) if match else None

async def process_task(task_text):
    # Categorize task using LLM
    try:
        llm = LLMHelper()
        category = await llm.categorize_task(task_text)
        # print(f"Task category: {category}")
        
        # Route to appropriate solver
        if category == 'data_analysis':
            return await solve_data_analysis(task_text)
        elif category == 'math':
            return await solve_math(task_text)
        elif category == 'text_processing':
            return await solve_text_processing(task_text)
        elif category == 'logic':
            return await solve_logic(task_text)
        else:
            return await llm.solve_with_llm(task_text)
    except Exception as e:
        print(f"Categorization failed: {e}")

async def process_file_task(task_text, file_urls):
    import subprocess
    import tempfile
    
    try:
        for file_url in file_urls:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        
                        # Save to temp file
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
                            f.write(content)
                            temp_path = f.name
                        
                        # Call Python analyzer
                        result = subprocess.run([
                            'python', '../python_worker/analyze.py', 
                            temp_path, task_text
                        ], capture_output=True, text=True, cwd='/Users/manasiq/Downloads/quiz-solver/src')
                        
                        if result.returncode == 0:
                            return int(result.stdout.strip())
    except Exception as e:
        print(f"File processing error: {e}")
    
    return None

async def solve_data_analysis(task_text):
    import subprocess
    import tempfile
    
    # Extract file URLs
    file_matches = re.findall(r'href="([^"]+\.(pdf|csv|xlsx?))"', task_text)
    
    if file_matches:
        file_urls = [match[0] for match in file_matches]
        
        # Try LLM + Python combination
        for file_url in file_urls:
            try:
                # Download file
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            
                            # Save to temp file
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
                                f.write(content)
                                temp_path = f.name
                            
                            # First try Python analyzer
                            result = subprocess.run([
                                'python', '../python_worker/analyze.py', 
                                temp_path, task_text
                            ], capture_output=True, text=True, cwd='/Users/manasiq/Downloads/quiz-solver/src')
                            
                            if result.returncode == 0 and result.stdout.strip():
                                return int(result.stdout.strip())
                            
                            # Fallback to LLM analysis
                            llm = LLMHelper()
                            with open(temp_path, 'rb') as f:
                                file_content = f.read()[:5000]  # First 5KB
                            
                            llm_result = llm.analyze_data(str(file_content), task_text)
                            if 'answer' in llm_result:
                                return int(llm_result['answer'])
                                
            except Exception as e:
                print(f"File processing error: {e}")
    
    # No files found, try LLM direct analysis
    llm = LLMHelper()
    return await llm.solve_with_llm(task_text)

async def solve_math(task_text):
    numbers = re.findall(r'\b\d+\b', task_text)
    if 'sum' in task_text.lower() and numbers:
        return sum(int(n) for n in numbers)
    elif 'product' in task_text.lower() and numbers:
        result = 1
        for n in numbers:
            result *= int(n)
        return result
    llm = LLMHelper()
    return await llm.solve_with_llm(task_text)

async def solve_text_processing(task_text):
    if 'count' in task_text.lower():
        words = re.findall(r'\b\w+\b', task_text)
        return len(words)
    llm = LLMHelper()
    return await llm.solve_with_llm(task_text)

async def solve_logic(task_text):
    llm = LLMHelper()
    return await llm.solve_with_llm(task_text)

async def process_text_task(task_text):
    numbers = re.findall(r'\b\d+\b', task_text)
    if numbers and 'sum' in task_text.lower():
        return sum(int(n) for n in numbers)
    return None

async def submit_answer(submit_url, email, secret, original_url, answer):
    payload = {
        "email": email,
        "secret": secret,
        "url": original_url,
        "answer": answer
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(submit_url, json=payload) as resp:
            print(f"Submit response: {resp.status}")
            return resp.status == 200