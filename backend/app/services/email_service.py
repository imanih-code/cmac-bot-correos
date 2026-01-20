from exchangelib import Credentials, Account, Message, Mailbox, DELEGATE, Configuration
from exchangelib.properties import ConversationId
from app.core.config import settings
import re

CID_PATTERN = re.compile(r"^@([^:]+):(.+)$")

class EmailService:
    def __init__(self):
        self.sessions: dict[str, Account] = {}
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
        self.sessions[session_id] = account
        self.email_to_session[email] = session_id

        print(account)
        
        return session_id

    def _get_account(self, session_id: str) -> Account:
        if session_id not in self.sessions:
            raise Exception("Invalid or expired session ID.")
        return self.sessions[session_id]

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
