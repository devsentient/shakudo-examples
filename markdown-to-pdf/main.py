from fastapi import FastAPI, Request, Response
from markdown_pdf import MarkdownPdf, Section
import tempfile

app = FastAPI()

@app.post("/markdown-to-pdf/")
async def markdown_to_pdf(request: Request):
    data = await request.json()
    markdown_text = data.get("markdown_text")
    if not markdown_text:
        return {"error": "Missing 'markdown_text' in request body"}

    pdf = MarkdownPdf(toc_level=2, optimize=True)
    pdf.add_section(Section(markdown_text))

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as temp_file:
        pdf.save(temp_file.name)
        with open(temp_file.name, 'rb') as f:
            pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Report.pdf"}
    )
