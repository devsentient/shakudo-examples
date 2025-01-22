from fastapi import FastAPI, HTTPException
from fpdf import FPDF
from io import BytesIO
import base64
from fastapi.responses import StreamingResponse

app = FastAPI()

def generate_pdf(content: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, content)

    pdf_buffer = pdf.output(dest='S').encode('latin-1')  # 'F' indicates writing to a file-like object
    # pdf_buffer = open('output_cache.pdf', 'rb')
    # pdf_buffer.seek(0)
    print(type(pdf_buffer))

    return pdf_buffer


@app.post("/generate-pdf/")
async def generate_pdf_endpoint(request_data: dict):
    try:
        content = request_data.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="No content provided")

        pdf_bytes = generate_pdf(content)

        pdf_stream = BytesIO(pdf_bytes)
        pdf_stream.seek(0)

        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=generated.pdf"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
