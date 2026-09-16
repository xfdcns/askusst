"""反馈闭环（第4周）：用户对一次回答点赞/点踩，落库攒 badcase。
这些数据后续直接作为论文 RAGAS 人工评测集和 badcase 分析的来源。"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db.engine import engine
from app.db.models import Conversation, Feedback, User

router = APIRouter(tags=["feedback"])


class FeedbackIn(BaseModel):
    conversation_id: int
    question: str
    answer: str
    rating: str            # "up" / "down"
    comment: str = ""


@router.post("/feedback")
def feedback(body: FeedbackIn,
             x_user_id: int = Header(alias="X-User-Id")):
    if body.rating not in ("up", "down"):
        raise HTTPException(422, "rating 只能是 up 或 down")

    with Session(engine) as s:
        if not s.get(User, x_user_id):
            raise HTTPException(401, "用户不存在，请先登录")
        conv = s.get(Conversation, body.conversation_id)
        if not conv or conv.user_id != x_user_id:
            raise HTTPException(403, "无权对该会话反馈")

        row = Feedback(
            user_id=x_user_id,
            conversation_id=body.conversation_id,
            question=body.question,
            answer=body.answer,
            rating=body.rating,
            comment=body.comment,
        )
        s.add(row)
        s.commit()
        s.refresh(row)
        return {"feedback_id": row.id, "status": "saved"}
