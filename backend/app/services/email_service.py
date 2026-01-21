from exchangelib import Credentials, Account, Message, Mailbox, DELEGATE, Configuration
from exchangelib.properties import ConversationId
from app.core.config import settings
import asyncio
from datetime import datetime, timedelta, timezone
import re

CID_PATTERN = re.compile(r"^@([^:]+):(.+)$")

class EmailService:
    def __init__(self):
        self.sessions: dict[str, dict[str, Account|datetime]] = {}
        self.email_to_session: dict[str, str] = {}

    def login(self, email: str, password: str, server: str = None) -> str:
        if email in self.email_to_session:
            return self.email_to_session[email]

        if not server:
            server = settings.EXCHANGE_SERVER
            
        credentials = Credentials(email, password)
        config = Configuration(server=server, credentials=credentials)
        account = Account(
            primary_smtp_address=email, 
            config=config,
            autodiscover=False, 
            access_type=DELEGATE
        )
        
        import uuid
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {"account": account, "last_used": datetime.now(timezone.utc)}
        self.email_to_session[email] = session_id
        
        return session_id

    def _get_account(self, session_id: str) -> Account:
        if session_id not in self.sessions:
            raise Exception("Invalid or expired session ID.")
        return self.sessions[session_id].get("account")
    
    def _update_session_last_used(self, session_id: str):
        if session_id not in self.sessions:
            raise Exception("Invalid or expired session ID.")
        self.sessions[session_id]["last_used"] = datetime.now(timezone.utc)

    def send_email(self, session_id: str, to_recipients: list[str], cc_recipients: list[str], 
        subject: str, html_body: str, attachments: list[tuple[str, bytes]], save_copy: bool):
        account = self._get_account(session_id)
        
        from exchangelib import HTMLBody, FileAttachment
        m = Message(
            folder=account.sent,
            account=account,
            subject=subject,
            to_recipients=[Mailbox(email_address=to_email) for to_email in to_recipients],
            cc_recipients=[Mailbox(email_address=cc_email) for cc_email in cc_recipients],
            body=HTMLBody(html_body)
        )

        for attachment_name, attachment_data in attachments:
            attachment_info = {
                "name": attachment_name,
                "content": attachment_data
            }

            match_pattern = CID_PATTERN.match(attachment_name)
            if match_pattern:
                attachment_info["content_id"] = match_pattern.group(1)
                attachment_info["name"] = match_pattern.group(2)

            m.attach(
                FileAttachment(
                    **attachment_info
                )
            )
        
        m.save()
        
        item_id = m.id
        change_key = m.changekey
    
        m.send(save_copy=save_copy)

        self._update_session_last_used(session_id)
        
        return {
            "item_id": item_id, 
            "change_key": change_key
        }

    def get_email(self, session_id: str, folder: str, item_id: str, change_key: str):
        account = self._get_account(session_id)
        
        if hasattr(account, folder):
            target_folder = getattr(account, folder)
        else:
            try:
                target_folder = account.root.get_folder_by_name(folder)
            except:
                raise Exception(f"Folder '{folder}' not found")
        
        qs = target_folder.all()
        
        item: Message = qs.get(id=item_id, changekey=change_key)

        self._update_session_last_used(session_id)
        
        return {
            "subject": str(item.subject),
            "sender": item.sender.email_address if item.sender else "Unknown",
            "conversation_id": str(item.conversation_id.id),
            "received_at": item.datetime_received.isoformat() if item.datetime_received else None,
            "body": str(item.body),
            "attachments": [
                {
                    "filename": attachment.name, 
                    "bytes": bytes(attachment.content)
                } 
                for attachment in list(item.attachments)
            ]
        }
    
    def get_responses_to_email(self, session_id: str, conversation_id: str):
        account = self._get_account(session_id)
    
        conversation = account.inbox.filter(
            conversation_id=ConversationId(id=conversation_id)
        ).order_by('-datetime_sent')

        self._update_session_last_used(session_id)

        return {
            "conversation": [{
                "subject": item.subject,
                "sender": item.sender,
                "datetime_sent": item.datetime_sent,
                "item_id": item.id,
                "change_key": item.change_key
            } for item in conversation]
        }
    
email_service = EmailService()

async def cleanup_expired_sessions():
    while True:
        try:
            now = datetime.now(timezone.utc)
            expired_sessions = []

            for email, session_id in list(email_service.email_to_session.items()):
                session_data = email_service.sessions.get(session_id)

                if session_data:
                    last_used = session_data.get("last_used")
                    if now - last_used > timedelta(seconds=settings.SESSION_TIME_LIMIT):
                        expired_sessions.append((email, session_id))

            for email, session_id in expired_sessions:
                email_service.email_to_session.pop(email, None)
                email_service.sessions.pop(session_id, None)
                print(f"Session {session_id} deleted (inactivity).")

            #print(f"Current alive sessions: {email_service.sessions}")

        except Exception as e:
            print(f"Error: {e}")
            
        await asyncio.sleep(5)