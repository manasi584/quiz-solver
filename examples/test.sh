#!/bin/bash

curl -X POST "http://localhost:3000/solve" \
  -H "Content-Type: application/json" \
  -d '{
  "email": "your-email@example.com",
  "secret": "secret1",
  "url": "http://127.0.0.1:5500/examples/sampleQuestion.html"
}'

echo "Request sent!"
