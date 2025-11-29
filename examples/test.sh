#!/bin/bash

curl -X POST "http://localhost:3000/solve" \
  -H "Content-Type: application/json" \
  -d '{
  "email": "your-email@example.com",
  "secret": "secret1",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}'

echo "Request sent!"
