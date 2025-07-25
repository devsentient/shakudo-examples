# Markdown to PDF Service

A FastAPI service that converts Markdown text to PDF documents using the `markdown-pdf` library.

## Installation

1. Clone or navigate to the project directory
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Dependencies

- `fastapi>=0.116.1` - Modern web framework for building APIs
- `markdown-pdf>=1.7` - Library for converting Markdown to PDF
- `uvicorn` - ASGI server for running FastAPI (install separately or use the command below)

## Running the Service

Start the FastAPI server using uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at:

- API: http://localhost:8000
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## API Endpoint

### POST /markdown-to-pdf/

Converts Markdown text to PDF and returns the PDF file as a download.

**Request:**

- Method: `POST`
- Content-Type: `application/json`
- Body:

```json
{
  "markdown_text": "# Your Markdown Content\n\nSome text here..."
}
```

**Response:**

- Content-Type: `application/pdf`
- Headers: `Content-Disposition: attachment; filename=Report.pdf`
- Body: PDF file bytes
