import numpy as np
from typing import Tuple
from sqlalchemy.orm import Session
from ticket_sniper.db.models import FeeModel, FeeObservation, utcnow_str

class FeeEstimator:
    @staticmethod
    def estimate_all_in(session: Session, source: str, venue_id: int, listed_price: float) -> Tuple[float, float, str]:
        model = session.query(FeeModel).filter_by(source=source, venue_id=venue_id).first()
        if not model:
            model = session.query(FeeModel).filter_by(source=source, venue_id=None).first()
        rate = model.fee_rate_pct if model else 1.28
        fixed = model.fee_fixed if model else 3.50
        confidence = model.confidence if model else "low"
        est_all_in = (listed_price * rate) + fixed
        return round(est_all_in, 2), round(est_all_in - listed_price, 2), confidence
