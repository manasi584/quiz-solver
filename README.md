# Quiz Solver — Autonomous Quiz Solving Agent

This project exposes a POST endpoint `/solve` that accepts JSON payloads from the grader. It validates the provided secret, launches a headless browser to render the quiz page, parses instructions, performs basic data sourcing/analysis (via a Python helper when needed), constructs the required `answer` value, and posts back to the submit URL stated on the quiz page. The whole quiz flow (including retries or follow-up URLs) is handled automatically and must finish within 3 minutes of the incoming POST.

## Quick start (local)
1. Install Node.js (v18+ recommended) and Python (3.9+).
2. Clone repo.
3. Create `.env` from `.env.example` and set `QUIZ_SECRET` and `PORT`.
4. Install Node deps:
   ```bash
   npm install
   ```
5. Install Python deps:
   ```bash
   pip install -r python_worker/requirements.txt
   ```
6. Start server:
   ```bash
   node server.js
   ```

## Usage
Send a POST to `/solve` with JSON body:
```json
{
  "email": "your-email@example.com",
  "secret": "your-secret",
  "url": "https://example.com/quiz-834"
}
```

- The server responds `400` for invalid JSON, `403` for invalid secret, and `200` when accepted and solving has started.
- The solver will attempt to solve the quiz and submit results to the provided submit URL.

## Notes
- The server uses Puppeteer to run a headless Chromium and execute page JavaScript.
- For data-heavy tasks (CSV/Excel/PDF), the server calls a Python script `python_worker/analyze.py` which uses pandas.
- Keep your `QUIZ_SECRET` private. The grader will use this to verify your endpoint.

## Files
- `server.js` - Express server + request validation and task orchestration.
- `solver.js` - Puppeteer-based page renderer & quiz parser/solver (JS-side logic).
- `python_worker/analyze.py` - Python helper for CSV/Excel/PDF analysis.

## Testing
Use the sample test payload in `examples/test_payload.json` or the demo URL `https://tds-llm-analysis.s-anand.net/demo` described in the assignment.

## License
MIT — see `LICENSE` file.
