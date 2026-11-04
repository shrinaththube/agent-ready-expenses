"""Receipts / FX worker API."""

import base64
import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .contracts_gen import FxQuote, ParsedReceipt
from .fx import FxService, RateNotFound
from .parser import parse_receipt
from .pdf import pdf_text

RATES_DIR = Path(os.environ.get("FX_RATES_DIR", Path(__file__).resolve().parents[3] / "fixtures" / "fx"))

app = FastAPI(title="Tally receipts")
fx = FxService(RATES_DIR)


class ParseRequest(BaseModel):
    text: str | None = None
    pdf_base64: str | None = None


class ConvertRequest(BaseModel):
    amount_minor: int
    source: str = Field(pattern="^[A-Z]{3}$")
    target: str = Field(default="USD", pattern="^[A-Z]{3}$")
    date: date


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/receipts/parse", response_model=ParsedReceipt)
def parse(req: ParseRequest) -> ParsedReceipt:
    if req.pdf_base64:
        try:
            text = pdf_text(base64.b64decode(req.pdf_base64))
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
    elif req.text is not None:
        text = req.text
    else:
        raise HTTPException(400, "text or pdf_base64 required")
    # Receipt text is untrusted input: it is parsed with regexes only, never executed or interpreted.
    return parse_receipt(text)


@app.post("/fx/convert", response_model=FxQuote)
def convert(req: ConvertRequest) -> FxQuote:
    try:
        return fx.convert(req.amount_minor, req.source, req.target, req.date)
    except RateNotFound as e:
        raise HTTPException(422, str(e)) from e
