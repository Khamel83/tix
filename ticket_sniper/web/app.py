from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Ticket-Sniper Operations")
templates = Jinja2Templates(directory="ticket_sniper/web/templates")

@app.get("/health")
def health_check():
    return JSONResponse({"status": "healthy"})

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})
