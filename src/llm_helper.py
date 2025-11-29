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
    
    def _call_llm(self, prompt, system_prompt="You are a helpful quiz solver agent that responds only in valid JSON format.", use_schema=False):
        response_format = {"type": "json_object"}
        if use_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "task_extraction",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "INSTRUCTIONS": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "URLS": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "SUBMIT_URL": {"type": "string"}
                        },
                        "required": ["INSTRUCTIONS", "URLS", "SUBMIT_URL"],
                        "additionalProperties": False
                    }
                }
            }
        
        payload = {
            "model": self.model,
            "input": f"{system_prompt}\n\n{prompt}",
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
            # print(f"Response content: {response.text}")
            # print(f"Payload sent: {json.dumps(payload, indent=2)}")
            raise
        result = response.json()
        return result
    
    def analyze_data(self, content, question):
        prompt = f"""Analyze this data and answer the question. Return ONLY a JSON object with an 'answer' field containing the numeric result or string answer.

Data:
{content}

Question: {question}

Response (JSON only):"""
        
        try:
            result = self._call_llm(prompt)
            return json.loads(result)
        except Exception as e:
            return {'error': f'Data analysis failed: {str(e)}'}
    
    def find_submit_url(self, page_content, page_html):
        # First try regex for common patterns
        submit_match = re.search(r'POST this JSON to[^\n]*?([^\s<>"\']+/submit)', page_content)
        if submit_match:
            return submit_match.group(1)
        
        prompt = f"""Find the submit URL from this webpage content. Look for forms, links, or any URLs where quiz answers should be submitted.

Page Text:
{page_content[:2000]}

Page HTML (partial):
{page_html[:3000]}

Return ONLY a JSON object with 'submit_url' field containing the URL, or 'error' if not found:"""
        
        try:
            result = self._call_llm(prompt)
            parsed = json.loads(result)
            return parsed.get('submit_url')
        except Exception as e:
            # Fallback: extract URLs with regex
            urls = re.findall(r'https?://[^\s<>"\']+', page_html)
            for url in urls:
                if any(word in url.lower() for word in ["submit", "answer", "post", "check"]):
                    return url
            return None
    
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
            result = self._call_llm(prompt)
            return json.loads(result)
        except Exception as e:
            return {'error': f'Complex task analysis failed: {str(e)}'}
    
    def process_scraped_data(self, data, task_instructions):
        """Process scraped data according to task requirements"""
        prompt = f"""Process this scraped data according to the task instructions:

Task Instructions:
{task_instructions}

Scraped Data:
{data}

Perform the required processing (cleansing, transformation, analysis, etc.) and return JSON with 'answer' field:"""
        
        try:
            result = self._call_llm(prompt)
            return json.loads(result)
        except Exception as e:
            return {'error': f'Data processing failed: {str(e)}'}
    
    def generate_api_request(self, task_instructions, base_url=None):
        """Generate API request details from task instructions"""
        prompt = f"""Generate API request details from these instructions:

Instructions:
{task_instructions}

{f'Base URL: {base_url}' if base_url else ''}

Return JSON with:
- 'url': API endpoint URL
- 'method': HTTP method
- 'headers': required headers dict
- 'params': query parameters dict (if any)
- 'data': request body (if any)
"""
        
        try:
            result = self._call_llm(prompt)
            return json.loads(result)
        except Exception as e:
            return {'error': f'API request generation failed: {str(e)}'}

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
            result = self._call_llm(prompt, use_schema=True)
            # print(result)
            return result 
        except Exception as e:
            print(f"LLM call failed: {e}")
            try:
                result = self._call_llm(prompt, use_schema=False)
                return result
            except:
                return None

    async def categorize_task(self, task_text):
        prompt = f"""Categorize this task into one of these types:
- math: mathematical calculations, sums, arithmetic
- data_analysis: file analysis, CSV/PDF processing, data extraction
- text_processing: text manipulation, string operations
- logic: logical reasoning, pattern matching
- web_scraping: extracting data from web pages
- unknown: cannot determine

Task: {task_text}

Return JSON with 'category' field."""
        try:
            result = self._call_llm(prompt)
            parsed = json.loads(result)
            return parsed.get('category', 'unknown').strip().lower()
        except:
            return 'unknown'

    async def solve_with_llm(self, task_text):
        """Solve task directly using LLM"""
        prompt = f"""Solve this task and return the numeric answer in JSON format:\n\n{task_text}\n\nReturn JSON with 'answer' field containing the number."""
        try:
            result = self._call_llm(prompt)
            parsed = json.loads(result)
            return int(parsed.get('answer', 0))
        except:
            return None