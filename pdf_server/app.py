from fastapi import FastAPI, HTTPException, UploadFile, File
from fpdf import FPDF
from io import BytesIO
import base64
from fastapi.responses import StreamingResponse
import pypandoc
import pandas as pd
from markdown_pdf import Section
from markdown_pdf import MarkdownPdf
import fitz
import typing
import pathlib


app = FastAPI()
def save_to_bytesio(pdf_ins: MarkdownPdf) -> BytesIO:
    """Save pdf to a BytesIO stream."""
    pdf_ins.writer.close()
    doc = fitz.open("pdf", pdf_ins.out_file)
    doc.set_metadata(pdf_ins.meta)
    if pdf_ins.toc_level > 0:
        doc.set_toc(pdf_ins.toc)
    
    # Save the PDF to a BytesIO object instead of a file
    pdf_stream = BytesIO()
    doc.save(pdf_stream)
    doc.close()
    
    # Reset the stream position to the beginning
    pdf_stream.seek(0)
    return pdf_stream


def generate_pdf(content: str) -> bytes:
    pdf = FPDF()
    
    # Default font and size
    font_family = "Arial"
    font_size = 12
    pdf.set_font(font_family, size=font_size)
    
    # Standard A4 dimensions in mm (210x297)
    page_width, page_height = 210, 297
    margin = 15  # Margin size
    usable_width = page_width - 2 * margin
    usable_height = page_height - 2 * margin
    
    # Split content into lines and find the longest line
    lines = content.split('\n')
    longest_line = max(lines, key=len)
    max_line_width = pdf.get_string_width(longest_line)

    # Adjust font size to fit longest line within usable width
    while max_line_width > usable_width and font_size > 5:
        font_size -= 1
        pdf.set_font(font_family, size=font_size)
        max_line_width = pdf.get_string_width(longest_line)
    
    # Simulate line wrapping with the adjusted font size
    pdf.set_font(font_family, size=font_size)
    line_height = font_size * 0.5  # Approximate line height in mm
    required_height = len(lines) * line_height

    # If content exceeds page height, reduce font size further
    while required_height > usable_height and font_size > 5:
        font_size -= 1
        pdf.set_font(font_family, size=font_size)
        line_height = font_size * 0.5
        required_height = len(lines) * line_height

    # Final PDF generation with adjusted font
    pdf.add_page()
    pdf.set_font(font_family, size=font_size)
    pdf.set_auto_page_break(auto=False)  # Disable automatic page break
    pdf.set_margins(margin, margin)
    pdf.multi_cell(usable_width, line_height, content)

    pdf_buffer = pdf.output(dest='S').encode('latin-1')
    return pdf_buffer


@app.post("/generate-pdf/")
async def generate_pdf_endpoint(uploaded_file: UploadFile = File(...)):
    try:
        # Read the content of the uploaded file
        file_content = await uploaded_file.read()
        text_content = file_content.decode('utf-8')
        
        # Check if the uploaded file is empty
        if not text_content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        # Convert uploaded text content to a DataFrame using Pandas
        df = pd.read_csv(BytesIO(file_content), sep=",")  # Assuming the content is CSV format

        # Convert the DataFrame to a markdown table
        markdown_content = df.to_markdown(index=False)
        # Define the section title and markdown content
        section_title = "# CSV Data Table"
        styled_markdown = section_title + "\n\n" + markdown_content
        
        # Define custom CSS for table styling with truly alternating row background colors
        custom_css = """
        table {
        width: 100%;
        border-collapse: collapse;
        margin: 1em 0;
        /* Smaller font than before */
        font-size: 13px; 
        }

        th, td {
        /* Bottom border only, very light color */
        border-bottom: 1px solid #ccc; 
        padding: 4px;  /* Tighter padding for a compact table */
        text-align: left;
        }

        th {
        background-color: #f5f5f5; /* A light gray header */
        font-weight: bold;
        }
        """

        # Create a MarkdownPdf instance with a specified table of contents level
        pdf = MarkdownPdf(toc_level=2)
        # Add a section with the styled markdown content and custom CSS
        pdf.add_section(Section(styled_markdown), user_css=custom_css)
        
        # Set the metadata for the PDF
        pdf.meta["title"] = "CSV Data Attachment"
        pdf_stream = save_to_bytesio(pdf)
        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=generated.pdf"}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
