"""用户认证 API — 注册（用户名+邮箱+密码+验证码）+ 登录（用户名/邮箱+密码）"""

import random
import smtplib
import hashlib
from email.mime.text import MIMEText
from datetime import datetime
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.models import get_db, User
from utils.auth import create_token, get_current_user, require_user
from utils.redis_client import set_verification_code, get_verification_code, delete_verification_code, blacklist_token, get_redis
from utils.logger import logger
from config import settings

router = APIRouter()


class SendCodeRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    code: str


class LoginRequest(BaseModel):
    account: str  # 用户名 or 邮箱
    password: str


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


def _generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _hash_password(password: str) -> str:
    """SHA256 加密密码"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _send_email(to: str, code: str) -> bool:
    smtp_host = getattr(settings, "smtp_host", "")
    if not smtp_host:
        logger.info(f"[开发模式] 验证码: {code} → {to}")
        return True
    try:
        msg = MIMEText(f"您的 TripCraft 验证码是：{code}\n\n验证码 5 分钟内有效。", "plain", "utf-8")
        msg["Subject"] = "TripCraft 验证码"
        msg["From"] = settings.smtp_user
        msg["To"] = to
        with smtplib.SMTP(smtp_host, 587) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, [to], msg.as_string())
        logger.info(f"验证码邮件已发送: {to}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


@router.post("/api/auth/send-code")
async def send_code(req: SendCodeRequest):
    """发送验证码 — Redis 存储"""
    email = req.email.strip()
    if not email or "@" not in email:
        return {"error": "邮箱格式不正确"}

    r = get_redis()
    if r:
        rate_key = f"rate:{email}"
        if r.exists(rate_key):
            return {"error": "验证码已发送，请 60 秒后重试"}
        r.setex(rate_key, 60, "1")

    code = _generate_code()
    if not set_verification_code(email, code, expire=300):
        logger.warning("Redis 不可用，验证码仅日志输出")

    sent = _send_email(email, code)
    if not sent:
        return {"error": "验证码发送失败"}

    return {"status": "ok", "message": "验证码已发送", "dev_code": code if not getattr(settings, "smtp_host", "") else None}


@router.post("/api/auth/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册 — 用户名 + 邮箱 + 密码 + 验证码"""
    username = req.username.strip()
    email = req.email.strip()
    password = req.password
    code = req.code.strip()

    # 校验
    if len(username) < 2:
        return {"error": "用户名至少 2 个字符"}
    if len(password) < 6:
        return {"error": "密码至少 6 个字符"}
    if not email or "@" not in email:
        return {"error": "邮箱格式不正确"}

    # 检查验证码
    stored_code = get_verification_code(email)
    if not stored_code:
        return {"error": "验证码已过期或未发送"}
    if stored_code != code:
        return {"error": "验证码不正确"}

    # 检查用户名/邮箱是否已注册
    existing = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if existing:
        if existing.email == email:
            return {"error": "该邮箱已注册"}
        return {"error": "该用户名已被使用"}

    # 创建用户
    user = User(
        email=email,
        username=username,
        password_hash=_hash_password(password),
        nickname=username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    delete_verification_code(email)
    logger.info(f"新用户注册: {username} ({email})")

    token = create_token(user.id, user.email)
    return {
        "status": "ok",
        "token": token,
        "user": {"id": user.id, "email": user.email, "username": user.username, "nickname": user.nickname, "avatar": user.avatar},
    }


@router.post("/api/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """登录 — 用户名或邮箱 + 密码"""
    account = req.account.strip()
    password = req.password

    if not account or not password:
        return {"error": "请输入账号和密码"}

    # 按用户名或邮箱查找
    user = db.query(User).filter((User.email == account) | (User.username == account)).first()
    if not user:
        return {"error": "账号不存在"}
    if not user.password_hash:
        return {"error": "账号未设置密码，请使用验证码登录"}

    if user.password_hash != _hash_password(password):
        return {"error": "密码不正确"}

    user.last_login_at = datetime.utcnow()
    db.commit()
    logger.info(f"用户登录: {user.username} ({user.email})")

    token = create_token(user.id, user.email)
    return {
        "status": "ok",
        "token": token,
        "user": {"id": user.id, "email": user.email, "username": user.username, "nickname": user.nickname, "avatar": user.avatar},
    }


@router.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """退出登录 — token 加入 Redis 黑名单"""
    if not authorization or not authorization.startswith("Bearer "):
        return {"status": "ok"}
    token = authorization[7:]
    blacklist_token(token)
    logger.info("用户退出登录，token 已加入黑名单")
    return {"status": "ok"}


@router.get("/api/auth/me")
async def get_me(user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """获取当前用户信息"""
    user_record = db.query(User).filter(User.id == user["user_id"]).first()
    if not user_record:
        return {"error": "用户不存在"}
    return {
        "id": user_record.id,
        "email": user_record.email,
        "username": user_record.username,
        "nickname": user_record.nickname,
        "avatar": user_record.avatar,
        "created_at": user_record.created_at.strftime("%Y-%m-%d") if user_record.created_at else "",
    }


@router.put("/api/auth/profile")
async def update_profile(req: UpdateProfileRequest, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """修改昵称/头像"""
    user_record = db.query(User).filter(User.id == user["user_id"]).first()
    if not user_record:
        return {"error": "用户不存在"}
    if req.nickname is not None:
        user_record.nickname = req.nickname
    if req.avatar is not None:
        user_record.avatar = req.avatar
    db.commit()
    return {"status": "ok", "user": {"nickname": user_record.nickname, "avatar": user_record.avatar}}