from sqlalchemy.orm import Session
from models import ConversationState

def save_pending_matches(
    user_id: int,
    matches: list[dict],
    db: Session
):
    state = db.query(ConversationState).filter(
        ConversationState.user_id == user_id
    ).first()
    if state is None:
        state = ConversationState(user_id=user_id)
        db.add(state)

    state.pending_action = "add_to_watchlist"
    state.pending_matches = matches
    db.commit()
    db.refresh(state)

def get_conversation_state(
    user_id: int,
    db: Session
):
    return db.query(ConversationState).filter(
        ConversationState.user_id == user_id
    ).first()