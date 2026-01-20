from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from app.services.email_service import email_service  

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str
    server: Optional[str] = None

class SendEmailRequest(BaseModel):
    session_id: str
    to_recipients: list[str]
    cc_recipients: list[str]
    subject: str
    html_body: str
    attachments: list[tuple[str, bytes]]
    save_copy: Optional[bool] = True

class GetEmailRequest(BaseModel):
    session_id: str
    folder: str = "inbox"
    item_id: str
    change_key: str

class GetResponsesRequest(BaseModel):
    session_id: str
    conversation_id: str

@router.post("/login")
def login(request: LoginRequest):
    try:
        session_id = email_service.login(
            email=request.email,
            password=request.password,
            server=request.server
        )
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send")
def send_email(request: SendEmailRequest):
    try:
        result = email_service.send_email(
            session_id=request.session_id,
            to_recipients=request.to_recipients,
            cc_recipients=request.cc_recipients,
            subject=request.subject,
            html_body=request.html_body,
            attachments=request.attachments,
            save_copy=request.save_copy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-email")
def get_email(request: GetEmailRequest):
    try:
        results = email_service.get_email(
            session_id=request.session_id,
            folder=request.folder,
            item_id=request.item_id,
            change_key=request.change_key
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/get-responses")
def get_responses(request: GetResponsesRequest):
    try:
        results = email_service.get_responses_to_email(
            session_id=request.session_id,
            conversation_id=request.conversation_id
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
