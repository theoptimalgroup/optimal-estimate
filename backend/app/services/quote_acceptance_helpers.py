from app.models.calculation_session import CalculationSession
from app.schemas.quote_acceptance import EworksAcceptanceSyncRead, PublicQuoteAcceptanceRead, QuoteAcceptanceStatusRead


def is_quote_accepted(session: CalculationSession) -> bool:
    return session.client_accepted_at is not None


def eworks_sync_from_session(session: CalculationSession) -> EworksAcceptanceSyncRead:
    return EworksAcceptanceSyncRead(
        status=session.eworks_acceptance_sync_status,
        synced_at=session.eworks_acceptance_synced_at,
        error=session.eworks_acceptance_sync_error,
        attempts=int(session.eworks_acceptance_sync_attempts or 0),
    )


def staff_acceptance_from_session(session: CalculationSession) -> QuoteAcceptanceStatusRead:
    return QuoteAcceptanceStatusRead(
        accepted=is_quote_accepted(session),
        accepted_at=session.client_accepted_at,
        name=session.client_acceptance_name,
        email=session.client_acceptance_email,
        notes=session.client_acceptance_notes,
        eworks_sync=eworks_sync_from_session(session),
    )


def public_acceptance_from_session(session: CalculationSession) -> PublicQuoteAcceptanceRead:
    return PublicQuoteAcceptanceRead(
        accepted=is_quote_accepted(session),
        accepted_at=session.client_accepted_at,
        name=session.client_acceptance_name,
    )
