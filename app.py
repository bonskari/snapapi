"""
SnapAPI — Screenshot & PDF Generation API
by Unstable Entity Oy

Fast, reliable screenshots and PDFs from any URL or HTML.
"""

import asyncio
import hashlib
import hmac
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
import uvicorn

# --- Config ---

DATA_DIR = Path(os.getenv("SNAPAPI_DATA_DIR", "/home/b1s/github/money-maker/projects/screenshot-api/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MASTER_API_KEY = os.getenv("SNAPAPI_MASTER_KEY", "")  # Admin key for managing API keys
PORT = int(os.getenv("SNAPAPI_PORT", "8910"))

# Rate limits per tier (requests per month)
TIER_LIMITS = {
    "free": 500,
    "starter": 5000,
    "pro": 25000,
    "business": 100000,
}

# --- API Key Storage (file-based for MVP) ---

KEYS_FILE = DATA_DIR / "api_keys.json"

import json

def load_keys() -> dict:
    if KEYS_FILE.exists():
        return json.loads(KEYS_FILE.read_text())
    return {}

def save_keys(keys: dict):
    KEYS_FILE.write_text(json.dumps(keys, indent=2))

def get_key_data(api_key: str) -> Optional[dict]:
    keys = load_keys()
    return keys.get(api_key)

def create_api_key(tier: str = "free", email: str = "") -> str:
    keys = load_keys()
    key = "snap_" + secrets.token_hex(24)
    keys[key] = {
        "tier": tier,
        "email": email,
        "created": datetime.now(timezone.utc).isoformat(),
        "usage_this_month": 0,
        "usage_month": datetime.now(timezone.utc).strftime("%Y-%m"),
    }
    save_keys(keys)
    return key

def increment_usage(api_key: str) -> tuple[bool, int, int]:
    """Returns (allowed, current_usage, limit)"""
    keys = load_keys()
    data = keys.get(api_key)
    if not data:
        return False, 0, 0

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    if data.get("usage_month") != current_month:
        data["usage_this_month"] = 0
        data["usage_month"] = current_month

    limit = TIER_LIMITS.get(data["tier"], 500)
    if data["usage_this_month"] >= limit:
        return False, data["usage_this_month"], limit

    data["usage_this_month"] += 1
    keys[api_key] = data
    save_keys(keys)
    return True, data["usage_this_month"], limit

# --- Playwright Browser Pool ---

_browser = None
_playwright = None

async def get_browser():
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
    return _browser

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch browser
    await get_browser()
    yield
    # Shutdown: close browser
    global _browser, _playwright
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()

# --- FastAPI App ---

app = FastAPI(
    title="SnapAPI",
    description="Fast, reliable screenshots and PDFs from any URL or HTML. By Unstable Entity Oy.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request/Response Models ---

class ScreenshotRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL to capture")
    html: Optional[str] = Field(None, description="Raw HTML to render and capture")
    width: int = Field(1280, ge=320, le=3840, description="Viewport width")
    height: int = Field(720, ge=200, le=2160, description="Viewport height")
    full_page: bool = Field(False, description="Capture full scrollable page")
    format: str = Field("png", description="Output format: png or jpeg")
    quality: int = Field(90, ge=1, le=100, description="JPEG quality (ignored for PNG)")
    delay: int = Field(0, ge=0, le=10000, description="Wait ms after page load before capture")
    selector: Optional[str] = Field(None, description="CSS selector to capture specific element")
    dark_mode: bool = Field(False, description="Emulate dark color scheme")
    device_scale_factor: float = Field(1.0, ge=0.5, le=3.0, description="Device scale factor (retina)")

class PDFRequest(BaseModel):
    url: Optional[str] = Field(None, description="URL to convert to PDF")
    html: Optional[str] = Field(None, description="Raw HTML to convert to PDF")
    format: str = Field("A4", description="Page format: A4, Letter, Legal, A3")
    landscape: bool = Field(False, description="Landscape orientation")
    print_background: bool = Field(True, description="Include background colors/images")
    margin_top: str = Field("20px", description="Top margin")
    margin_bottom: str = Field("20px", description="Bottom margin")
    margin_left: str = Field("20px", description="Left margin")
    margin_right: str = Field("20px", description="Right margin")
    delay: int = Field(0, ge=0, le=10000, description="Wait ms after page load before capture")

class APIKeyRequest(BaseModel):
    email: str = Field(..., description="Email for the API key owner")

class APIKeyResponse(BaseModel):
    api_key: str
    tier: str
    monthly_limit: int
    message: str

# --- Auth ---

def verify_api_key(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(401, "Missing API key. Pass it as 'Authorization: Bearer snap_xxx' header.")

    key = authorization.replace("Bearer ", "").strip()
    data = get_key_data(key)
    if not data:
        raise HTTPException(401, "Invalid API key.")

    allowed, usage, limit = increment_usage(key)
    if not allowed:
        raise HTTPException(429, f"Rate limit exceeded. Used {usage}/{limit} this month. Upgrade at https://api.usesnapapi.com/pricing")

    return data

# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "service": "SnapAPI",
        "version": "1.0.0",
        "docs": "/docs",
        "description": "Fast screenshots and PDFs from any URL or HTML",
        "endpoints": {
            "POST /v1/screenshot": "Capture a screenshot",
            "POST /v1/pdf": "Generate a PDF",
            "POST /v1/keys": "Get a free API key",
            "GET /v1/usage": "Check your usage",
        }
    }

@app.post("/v1/keys", response_model=APIKeyResponse)
async def create_key(req: APIKeyRequest):
    """Get a free API key. 500 screenshots/month included."""
    # Check if email already has a key
    keys = load_keys()
    for k, v in keys.items():
        if v.get("email") == req.email:
            return APIKeyResponse(
                api_key=k,
                tier=v["tier"],
                monthly_limit=TIER_LIMITS[v["tier"]],
                message="API key already exists for this email."
            )

    key = create_api_key(tier="free", email=req.email)
    return APIKeyResponse(
        api_key=key,
        tier="free",
        monthly_limit=500,
        message="Your free API key is ready! 500 screenshots/month included."
    )

@app.get("/v1/usage")
async def get_usage(authorization: str = Header(None)):
    """Check your current usage and limits."""
    key_str = (authorization or "").replace("Bearer ", "").strip()
    data = get_key_data(key_str)
    if not data:
        raise HTTPException(401, "Invalid API key.")

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = data["usage_this_month"] if data.get("usage_month") == current_month else 0
    limit = TIER_LIMITS.get(data["tier"], 500)

    return {
        "tier": data["tier"],
        "usage_this_month": usage,
        "monthly_limit": limit,
        "remaining": limit - usage,
        "billing_period": current_month,
    }

@app.post("/v1/screenshot")
async def take_screenshot(req: ScreenshotRequest, authorization: str = Header(None)):
    """Capture a screenshot of a URL or HTML content."""
    verify_api_key(authorization)

    if not req.url and not req.html:
        raise HTTPException(400, "Either 'url' or 'html' must be provided.")

    try:
        browser = await get_browser()
        context = await browser.new_context(
            viewport={"width": req.width, "height": req.height},
            device_scale_factor=req.device_scale_factor,
            color_scheme="dark" if req.dark_mode else "light",
        )
        page = await context.new_page()

        if req.url:
            await page.goto(req.url, wait_until="networkidle", timeout=30000)
        else:
            await page.set_content(req.html, wait_until="networkidle", timeout=30000)

        if req.delay > 0:
            await asyncio.sleep(req.delay / 1000)

        screenshot_opts = {
            "type": req.format if req.format in ("png", "jpeg") else "png",
            "full_page": req.full_page,
        }
        if req.format == "jpeg":
            screenshot_opts["quality"] = req.quality

        if req.selector:
            element = await page.query_selector(req.selector)
            if not element:
                raise HTTPException(400, f"Selector '{req.selector}' not found on page.")
            image_bytes = await element.screenshot(**screenshot_opts)
        else:
            image_bytes = await page.screenshot(**screenshot_opts)

        await context.close()

        content_type = "image/png" if req.format == "png" else "image/jpeg"
        return Response(content=image_bytes, media_type=content_type, headers={
            "X-SnapAPI-Size": str(len(image_bytes)),
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Screenshot failed: {str(e)}")

@app.post("/v1/pdf")
async def generate_pdf(req: PDFRequest, authorization: str = Header(None)):
    """Generate a PDF from a URL or HTML content."""
    verify_api_key(authorization)

    if not req.url and not req.html:
        raise HTTPException(400, "Either 'url' or 'html' must be provided.")

    try:
        browser = await get_browser()
        context = await browser.new_context()
        page = await context.new_page()

        if req.url:
            await page.goto(req.url, wait_until="networkidle", timeout=30000)
        else:
            await page.set_content(req.html, wait_until="networkidle", timeout=30000)

        if req.delay > 0:
            await asyncio.sleep(req.delay / 1000)

        pdf_bytes = await page.pdf(
            format=req.format,
            landscape=req.landscape,
            print_background=req.print_background,
            margin={
                "top": req.margin_top,
                "bottom": req.margin_bottom,
                "left": req.margin_left,
                "right": req.margin_right,
            }
        )

        await context.close()

        return Response(content=pdf_bytes, media_type="application/pdf", headers={
            "X-SnapAPI-Size": str(len(pdf_bytes)),
            "Content-Disposition": "inline; filename=output.pdf",
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"PDF generation failed: {str(e)}")

@app.get("/pricing")
async def pricing():
    """View available plans and upgrade links."""
    return {
        "plans": [
            {
                "tier": "free",
                "price": "$0/mo",
                "limit": "500 screenshots/month",
                "features": ["PNG & JPEG screenshots", "PDF generation", "Custom viewport sizes"],
            },
            {
                "tier": "starter",
                "price": "$9/mo",
                "limit": "5,000 screenshots/month",
                "features": ["Everything in Free", "Priority rendering", "Email support"],
                "checkout_url": "https://buy.stripe.com/test_4gM5kFfKfb1N1kMf1fafS00",
            },
            {
                "tier": "pro",
                "price": "$29/mo",
                "limit": "25,000 screenshots/month",
                "features": ["Everything in Starter", "Full-page captures", "Webhook notifications"],
                "checkout_url": "https://buy.stripe.com/test_00weVf55B0n97Jaf1fafS01",
            },
            {
                "tier": "business",
                "price": "$79/mo",
                "limit": "100,000 screenshots/month",
                "features": ["Everything in Pro", "Dedicated support", "Custom integrations"],
                "checkout_url": "https://buy.stripe.com/test_3cI6oJ1Tp3zl4wYaKZafS02",
            },
        ]
    }

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for subscription management."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # For now, just log the event
    try:
        event = json.loads(payload)
        event_type = event.get("type", "")

        if event_type == "checkout.session.completed":
            session = event.get("data", {}).get("object", {})
            customer_email = session.get("customer_details", {}).get("email", "")
            # Find API key by email and upgrade tier
            keys = load_keys()
            for k, v in keys.items():
                if v.get("email") == customer_email:
                    # Determine tier from the price
                    amount = session.get("amount_total", 0)
                    if amount >= 7900:
                        v["tier"] = "business"
                    elif amount >= 2900:
                        v["tier"] = "pro"
                    elif amount >= 900:
                        v["tier"] = "starter"
                    save_keys(keys)
                    break

        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(400, f"Webhook error: {str(e)}")

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
