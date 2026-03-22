# SnapAPI — Screenshot & PDF Generation API

Fast, reliable screenshots and PDFs from any URL or HTML. One API call, instant results.

**[Get your free API key →](https://snapapi.dev)** | **[API Docs →](https://snapapi.dev/docs)**

## Why SnapAPI?

- **Fast** — Screenshots in <2 seconds, PDFs in <3 seconds
- **Simple** — One POST request, get an image or PDF back
- **Reliable** — Chromium-based rendering, handles JavaScript, SPAs, dynamic content
- **Flexible** — Full page, element selector, dark mode, retina, custom viewport
- **Affordable** — Free tier included. Paid plans start at $9/mo

## Quick Start

```bash
# 1. Get your free API key
curl -X POST https://snapapi.dev/v1/keys \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com"}'

# 2. Take a screenshot
curl -X POST https://snapapi.dev/v1/screenshot \
  -H "Authorization: Bearer snap_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o screenshot.png

# 3. Generate a PDF
curl -X POST https://snapapi.dev/v1/pdf \
  -H "Authorization: Bearer snap_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' \
  -o output.pdf
```

## Features

### Screenshot Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | — | URL to capture |
| `html` | string | — | Raw HTML to render |
| `width` | int | 1280 | Viewport width (320–3840) |
| `height` | int | 720 | Viewport height (200–2160) |
| `full_page` | bool | false | Capture full scrollable page |
| `format` | string | "png" | Output: `png` or `jpeg` |
| `quality` | int | 90 | JPEG quality (1–100) |
| `delay` | int | 0 | Wait ms after load (0–10000) |
| `selector` | string | — | CSS selector for element capture |
| `dark_mode` | bool | false | Emulate dark color scheme |
| `device_scale_factor` | float | 1.0 | Retina scale (0.5–3.0) |

### PDF Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | — | URL to convert |
| `html` | string | — | Raw HTML to convert |
| `format` | string | "A4" | Page size: A4, Letter, Legal, A3 |
| `landscape` | bool | false | Landscape orientation |
| `print_background` | bool | true | Include backgrounds |
| `margin_*` | string | "20px" | Page margins (top/bottom/left/right) |
| `delay` | int | 0 | Wait ms after load |

## Use Cases

- **Social media previews** — Generate OG images dynamically
- **Invoice generation** — HTML template → PDF invoice
- **Web archiving** — Screenshot pages for records
- **Testing** — Visual regression testing screenshots
- **Reports** — Convert dashboards to PDF
- **E-commerce** — Product page screenshots for marketplaces
- **Documentation** — Auto-generate screenshots for docs

## Pricing

| Plan | Price | Screenshots/mo | Best For |
|------|-------|---------------|----------|
| Free | $0 | 500 | Testing & personal projects |
| Starter | $9/mo | 5,000 | Side projects & small apps |
| Pro | $29/mo | 25,000 | Growing SaaS & agencies |
| Business | $79/mo | 100,000 | High-volume applications |

Need more? [Contact us](mailto:kai@unstableentity.com) for custom plans.

## Code Examples

### Python

```python
import requests

API_KEY = "snap_your_key_here"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Screenshot
resp = requests.post("https://snapapi.dev/v1/screenshot", headers=headers, json={
    "url": "https://github.com",
    "width": 1280,
    "height": 720,
    "full_page": True
})
with open("github.png", "wb") as f:
    f.write(resp.content)
```

### JavaScript (Node.js)

```javascript
const response = await fetch("https://snapapi.dev/v1/screenshot", {
  method: "POST",
  headers: {
    "Authorization": "Bearer snap_your_key_here",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    url: "https://github.com",
    width: 1280,
    height: 720,
    full_page: true
  })
});

const buffer = await response.arrayBuffer();
fs.writeFileSync("github.png", Buffer.from(buffer));
```

### HTML to PDF (Invoice Example)

```bash
curl -X POST https://snapapi.dev/v1/pdf \
  -H "Authorization: Bearer snap_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<h1>Invoice #001</h1><p>Amount: €100.00</p>",
    "format": "A4",
    "print_background": true
  }' \
  -o invoice.pdf
```

## Self-Hosting

SnapAPI is open source. Run it yourself:

```bash
pip install fastapi uvicorn playwright
playwright install chromium

python app.py
# Running on http://localhost:8910
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/screenshot` | POST | Capture screenshot |
| `/v1/pdf` | POST | Generate PDF |
| `/v1/keys` | POST | Create free API key |
| `/v1/usage` | GET | Check usage & limits |
| `/health` | GET | Service health check |
| `/docs` | GET | Interactive API docs (Swagger) |

## Built With

- [Playwright](https://playwright.dev/) — Reliable browser automation
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [Chromium](https://www.chromium.org/) — Industry-standard rendering engine

## About

Built by [Unstable Entity Oy](https://unstableentity.com) — a Finnish software company building developer tools.

## License

MIT — use it however you want.
