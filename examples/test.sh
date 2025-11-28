#!/bin/bash

curl -X POST "http://localhost:3000/solve" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "123@gmail.com",
    "secret": "secret1",
    "url": "https://example.com/quiz-834"
  }'

echo "Request sent!"
