"""最简登录：用学号换 user_id。本周不做密码/JWT，仅用于多用户隔离演示。"""
from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db.engine import engine
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    student_id: str
    nickname: str = ""


@router.post("/login")
def login(body: LoginIn):
    with Session(engine) as s:
        user = s.exec(select(User).where(User.student_id == body.student_id)).first()
        if not user:
            user = User(student_id=body.student_id, nickname=body.nickname)
            s.add(user)
            s.commit()
            s.refresh(user)
        elif body.nickname and user.nickname != body.nickname:
            user.nickname = body.nickname
            s.add(user)
            s.commit()
        return {"user_id": user.id, "student_id": user.student_id,
                "nickname": user.nickname}
