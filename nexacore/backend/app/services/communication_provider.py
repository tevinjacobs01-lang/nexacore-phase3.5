"""Provider contract and safe mock email adapter; no network or credentials."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class NormalizedAttachment:
    filename: str
    provider_attachment_id: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    storage_key: str | None = None
    external_url: str | None = None


@dataclass
class NormalizedMessage:
    provider: str
    account_identifier: str
    external_message_id: str | None
    external_thread_id: str | None
    channel: str
    direction: str
    sender_name: str | None = None
    sender_address: str | None = None
    recipients: list[str] = field(default_factory=list)
    subject: str | None = None
    body: str = ""
    timestamp: datetime | None = None
    contact_id: object | None = None
    lead_id: object | None = None
    property_id: object | None = None
    attachments: list[NormalizedAttachment] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class CommunicationProvider(ABC):
    @abstractmethod
    def connect(self): ...
    @abstractmethod
    def disconnect(self): ...
    @abstractmethod
    def health_check(self) -> bool: ...
    @abstractmethod
    def fetch_threads(self) -> list[NormalizedMessage]: ...
    @abstractmethod
    def fetch_messages(self, external_thread_id: str) -> list[NormalizedMessage]: ...
    @abstractmethod
    def send_message(self, message: NormalizedMessage) -> NormalizedMessage: ...
    @abstractmethod
    def mark_read(self, external_message_id: str) -> None: ...


class MockEmailProvider(CommunicationProvider):
    """An in-memory adapter used to exercise the pipeline without a real email service."""
    def __init__(self):
        self.messages: list[NormalizedMessage] = []
        self.connected = False

    def connect(self): self.connected = True
    def disconnect(self): self.connected = False
    def health_check(self) -> bool: return True
    def fetch_threads(self) -> list[NormalizedMessage]: return list(self.messages)
    def fetch_messages(self, external_thread_id: str) -> list[NormalizedMessage]:
        return [m for m in self.messages if m.external_thread_id == external_thread_id]
    def send_message(self, message: NormalizedMessage) -> NormalizedMessage:
        message.external_message_id = message.external_message_id or f"mock-{uuid4()}"
        message.external_thread_id = message.external_thread_id or f"mock-thread-{uuid4()}"
        message.timestamp = message.timestamp or datetime.now(timezone.utc)
        self.messages.append(message)
        return message
    def mark_read(self, external_message_id: str) -> None:
        return None
