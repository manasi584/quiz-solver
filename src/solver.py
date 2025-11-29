import asyncio
import base64
import re
import json
import aiohttp
import os
import html
from playwright.async_api import async_playwright
from .llm_helper import LLMHelper




async def solve_task(email: str, secret: str, url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            task_text = await extract_task_from_page(page)
        
            if task_text:
                task_data = task_text
                submit_url = task_data.get("SUBMIT_URL")
                # print("Submit URL:", submit_url)
                urls=task_data.get("URLS", [])
                instructions = task_data.get("INSTRUCTIONS", [])
                answer = await process_task(instructions,urls)
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
        if llm_result:
            return llm_result
    except Exception as e:
        print(f"LLM extraction failed: {e}")
    return None

async def process_urls_content(urls_actions):
    """Process URLs based on their action values"""
    processed_data = {}
    download_folder = "downloads"
    os.makedirs(download_folder, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        for url, action in urls_actions.items():
            try:
                if action == "DOWNLOAD":
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            filename = url.split('/')[-1] or f"file_{hash(url)}"
                            filepath = os.path.join(download_folder, filename)
                            with open(filepath, 'wb') as f:
                                f.write(await resp.read())
                            processed_data[url] = f"Downloaded to: {filepath}"
                elif action == "SCRAPE":
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            processed_data[url] = await resp.text()
                elif action == "API":
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            processed_data[url] = await resp.json()
                elif action == "DONE":
                    processed_data[url] = "No action needed"
            except Exception as e:
                print(f"Error processing {url}: {e}")
                processed_data[url] = f"Error: {str(e)}"
    
    return processed_data

async def process_task(instructions, urls):
    try:
        llm = LLMHelper()
        category = await llm.categorize_task(instructions)
        print(f"Task category: {category}")
        
        urls_content = None
        if urls:
            urls_actions = await llm.process_urls(urls, instructions)
            if urls_actions:
                urls_content = await process_urls_content(urls_actions)
        
            return await llm.solve_with_llm(instructions,category,urls_content)
    except Exception as e:
        print(f"Categorization failed: {e}")

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
            if resp.status == 200:
                response_data = await resp.json()
                if response_data.get("correct") and "url" in response_data:
                    next_url = response_data["url"]
                    if next_url != original_url:
                        await solve_task(email, secret, next_url)
            else:
                response_text = await resp.text()
                print(f"Error response: {response_text}")
            return resp.status == 200