import os
import json
import requests
import aiohttp
import re

class LLMHelper:
    def __init__(self, model="openai/gpt-5-mini", timeout=30):
        self.url = "https://aipipe.org/openrouter/v1/responses"
        self.token = os.getenv('AIPIPE_TOKEN')
        self.model = model
        self.timeout = timeout
    
 
    
    def _call_llm(self, input_text, response_format={"type": "json_object"}):
        payload = {
            "model": self.model,
            "input": input_text,
            "response_format": response_format
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            print(f"Response content: {response.text}")
            print(f"Payload sent: {json.dumps(payload, indent=2)}")
            raise
        result = response.json()
        return result
    
    def solve_complex_task(self, page_content, page_html, scraped_data=None):
        """Solve complex tasks: scraping, API calls, data processing, analysis, visualization"""
        prompt = f"""Analyze this quiz page and determine what task needs to be performed. Tasks can include:
1. Scraping websites for information
2. API calls with specific headers
3. Data cleansing (text/PDF/files)
4. Data processing (transformation, transcription, vision)
5. Analysis (filtering, sorting, aggregating, statistical/ML models, geo-spatial)
6. Visualization (charts, narratives, slides)

Page Content:
{page_content}

Page HTML:
{page_html[:2000]}

{f'Scraped Data: {scraped_data}' if scraped_data else ''}

Return JSON with:
- 'task_type': one of ['scraping', 'api', 'data_processing', 'analysis', 'visualization', 'simple_answer']
- 'instructions': detailed task instructions
- 'answer': final answer if determinable
- 'submit_url': where to submit the answer
- 'next_action': what action to take next (if any)
"""
        
        try:
            result = self._call_llm(f"You are a helpful quiz solver agent.\n\n{prompt}")
            return json.loads(result)
        except Exception as e:
            return {'error': f'Complex task analysis failed: {str(e)}'}


    async def extract_task_with_llm(self, html_content):
        prompt = f"""
        Extract task instructions from HTML.
        Return only: 
        1. Task instruction steps 
        2. URLs and anything within anchor tags
        3. the submit URL/endpoint. 
        
        All the responses should be in one JSON with keys "INSTRUCTIONS" , "URLS" , "SUBMIT_URL".
        Do not respond with anything other than JSON object.

        HTML content :
        {html_content}
        """
        try:
            schema_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "task_extraction",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "INSTRUCTIONS": {"type": "array", "items": {"type": "string"}},
                            "URLS": {"type": "array", "items": {"type": "string"}},
                            "SUBMIT_URL": {"type": "string"}
                        },
                        "required": ["INSTRUCTIONS", "URLS", "SUBMIT_URL"],
                        "additionalProperties": False
                    }
                }
            }
            result = self._call_llm(f"You are a helpful quiz solver agent.\n\n{prompt}", schema_format)
            return json.loads(self.extract_llm_response(result)) 
        except Exception as e:
            print(f"LLM call failed: {e}")
            return None

    async def categorize_task(self, task_text):
        prompt = f"""Categorize these intructions for a task into one of these types:
- math: mathematical calculations, sums, arithmetic
- data_analysis: file analysis, CSV/PDF processing, data extraction
- text_processing: text manipulation, string operations
- logic: logical reasoning, pattern matching
- web_scraping: extracting data from web pages
- other: cannot determine

Task: {task_text}

Return JSON with 'category' field."""
        try:
            schema_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "task_category",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"}
                        },
                        "required": ["category"],
                        "additionalProperties": False
                    }
                }
            }
            result = self._call_llm(f"You are a helpful quiz solver agent.\n\n{prompt}", schema_format)
            parsed = json.loads(self.extract_llm_response(result))
            # print(f"LLM response: {parsed}")
            return parsed.get('category', 'other').strip().lower()
        except Exception as e:
            print(f"categorize_task failed: {e}")
            return 'unknown'

    async def process_urls(self, urls, instructions):
        prompt = f"""Given these URLs and task instructions, determine what needs to be done with each URL.
        
URLs: {urls}
Instructions: {instructions}
        
For each URL, determine the action needed:
- DOWNLOAD: if URL contains data files (PDF, CSV, Excel, etc.)
- API: if URL is an API endpoint that needs a request
- DONE: if URL has no functionality and doesn't need exploration
- SCRAPE: if URL needs web scraping for data extraction

Return JSON with each URL as key and the required action as value."""
        
        try:
            schema_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "url_processing",
                    "schema": {
                        "type": "object",
                        "patternProperties": {
                            "^https?://.*": {
                                "type": "string",
                                "enum": ["DOWNLOAD", "API", "DONE", "SCRAPE"]
                            }
                        },
                        "additionalProperties": False
                    }
                }
            }
            result = self._call_llm(f"You are a helpful quiz solver agent.\n\n{prompt}", schema_format)
            return json.loads(self.extract_llm_response(result))
        except Exception as e:
            print(f"process_urls failed: {e}")
            return None
    
    async def solve_with_llm(self, instructions,category, urls_content=None):
        prompt = f"""Solve this task and return the answer in JSON format:\n\n{instructions}. 
        The task belongs to category {category}"""
        
        if urls_content:
            prompt += "\n\nAdditional data from URLs:\n"
            for url, content in urls_content.items():
                if isinstance(content, str) and content.startswith("Downloaded to:"):
                    filepath = content.replace("Downloaded to: ", "")
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            file_content = f.read()[:5000]  # Limit to first 5000 chars
                        prompt += f"\n{url} (file content):\n{file_content}\n"
                    except:
                        prompt += f"\n{url}: {content}\n"
                else:
                    prompt += f"\n{url}:\n{str(content)[:5000]}\n"
            prompt += "\n\nNote: You have been provided with all necessary data from external websites and files above. Do not attempt to access external URLs or download files as the data is already included in this prompt."
        
        try:
            schema_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "task_answer",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"}
                        },
                        "required": ["answer"],
                        "additionalProperties": False
                    }
                }
            }
            result = self._call_llm(f"You are a helpful quiz solver agent.\n\n{prompt}", schema_format)
            parsed = self.extract_llm_response(result)
            print(parsed)
            return parsed
        except Exception as e:
            print(f"solve_with_llm failed: {e}")
            return None

    def extract_llm_response(self, llm_result):
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