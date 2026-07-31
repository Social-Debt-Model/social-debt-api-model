# Social Debt API Model

API for identifying and classifying Social Debt in software engineering communications (e.g. GitHub comments) using NLP and Semantic Matching.

## Overview
This API takes developer comments as input and identifies the presence of Social Debt by:
1. Filtering operational noise using local NLP techniques.
2. Classifying valid comments into Macro-causes (e.g. A, B, C) using an LLM (OpenAI).
3. Semantically matching the comment against an RDF Ontology using SentenceTransformers (`all-MiniLM-L6-v2`) to detect specific Micro-causes (e.g. COG-009).
4. Providing a Social Debt Index (SDI) metric for batches of comments grouped by Issue.

## Endpoints

* `POST /classify/text`: Synchronously classify a single comment.
* `POST /classify/batch`: Asynchronously process a CSV/XLSX file of comments grouped by issue. Returns a `job_id`.
* `GET /classify/batch/{job_id}`: Poll the progress and retrieve the final classifications and SDI metrics for the batch.

## Test Scripts

* `test_single_comment.py`: Tests the single comment synchronous endpoint.
* `test_batch_comments.py`: Tests the batch processing with a mock 10-comment dataset.
* `test_issue_metrics_and_performance.py`: Tests the full pipeline including Issue grouping, SDI generation, and estimates performance for large datasets.

## Requirements

* Python 3.10+
* 2GB RAM minimum (for PyTorch semantic matching)
* OpenAI API Key in `.env`