from fastapi import FastAPI, HTTPException
from edgar import set_identity, Company
import uvicorn

# Set your SEC identity (required by SEC regulations)
set_identity("test@shakudo.io")

app = FastAPI()

@app.get("/filing_latest")
async def get_filing_latest(company: str, form: str):
    """
    Fetch the latest filing for a given company and form.
    
    Query Parameters:
      - company: The stock ticker or company identifier (e.g., "DX").
      - form: The SEC form type (e.g., "10-K", "10-Q", or "4").
      
    Returns:
      A JSON object with the filing text.
    """
    try:
        comp = Company(company)
        filings = comp.get_filings()
        filtered = filings.filter(form=form).latest()
        filing_text = filtered.text()
        return {
            "company": company,
            "form": form,
            "filing_text": filing_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/filing_date_range")
async def get_filing_from_date_range(company: str, form: str, startDate: str, endDate: str):
    """
    Fetch filings for a given company, form, and date range.
    
    Query Parameters:
      - company: The stock ticker or company identifier (e.g., "DX").
      - form: The SEC form type (e.g., "10-K", "10-Q", "4").
      - startDate: The start date in format YYYY-MM-DD.
      - endDate: The end date in format YYYY-MM-DD.
      
    Returns:
      A JSON object with the company, form, and a list of filing texts.
    """
    try:
        comp = Company(company)
        filings = comp.get_filings()
        # Note: Verify that the edgar library accepts the date format as "YYYY-MM-DD:YYYY-MM-DD"
        filtered_filings = filings.filter(form=form, date=f"{startDate}:{endDate}")
        filings_texts = [filing.text() for filing in filtered_filings]
        
        return {
            "company": company,
            "form": form,
            "filings": filings_texts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8787)
