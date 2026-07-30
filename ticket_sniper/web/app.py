from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import func

from ticket_sniper.db.models import AlertDecision, AlertOutbox, EventPriceSnapshot, ListingCurrent, PollRun, SourceEvent
from ticket_sniper.db.session import SessionLocal
from ticket_sniper.profiles.preferences import load_active_profile
from ticket_sniper.scheduler.event_polling import poll_event_ticket_data

app = FastAPI(title="Ticket-Sniper Operations")
templates = Jinja2Templates(directory="ticket_sniper/web/templates")

@app.get("/health")
def health_check():
    return JSONResponse({"status": "healthy"})

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    selected_source = request.query_params.get("source") or "seatgeek"
    selected_event_id = request.query_params.get("source_event_id")
    session = SessionLocal()
    try:
        events = session.query(SourceEvent).filter_by(status="active").order_by(SourceEvent.starts_at_utc.asc()).all()
        if selected_event_id is None and events:
            selected_source = events[0].source
            selected_event_id = events[0].source_event_id
        listings = []
        if selected_event_id:
            listings = (
                session.query(ListingCurrent)
                .filter_by(source=selected_source, source_event_id=selected_event_id)
                .order_by(ListingCurrent.unit_price_all_in.asc())
                .all()
            )
        poll_runs = session.query(PollRun).order_by(PollRun.started_at.desc()).limit(10).all()
        snapshots = session.query(EventPriceSnapshot).order_by(EventPriceSnapshot.observed_at.desc()).limit(10).all()
        decisions = session.query(AlertDecision).order_by(AlertDecision.decided_at.desc()).limit(10).all()
        outbox_counts = {
            status: count
            for status, count in session.query(AlertOutbox.status, func.count(AlertOutbox.id))
            .group_by(AlertOutbox.status)
            .all()
        }
        profile = await load_active_profile()
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "profile": profile,
                "events": events,
                "selected_source": selected_source,
                "selected_event_id": selected_event_id,
                "listings": listings,
                "poll_runs": poll_runs,
                "snapshots": snapshots,
                "decisions": decisions,
                "outbox_counts": outbox_counts,
            },
        )
    finally:
        session.close()


@app.post("/events/{source}/{source_event_id}/poll")
async def manual_event_poll(source: str, source_event_id: str):
    await poll_event_ticket_data(source, source_event_id, tier=2)
    return RedirectResponse(f"/?source={source}&source_event_id={source_event_id}", status_code=303)
