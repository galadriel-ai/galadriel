from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional


@dataclass
class TwitterAgentConfig:
    name: str
    settings: Dict
    system: str
    bio: List[str]
    lore: List[str]
    adjectives: List[str]
    topics: List[str]
    style: Dict
    goals_template: List[str]
    facts_template: List[str]
    knowledge: List[str]
    search_queries: Dict[str, List[str]]

    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def required_fields(cls):
        return [
            "name",
            "settings",
            "system",
            "bio",
            "lore",
            "adjectives",
            "topics",
            "style",
            "goals_template",
            "facts_template",
            "knowledge",
            "search_queries",
        ]

    @classmethod
    def from_json(cls, data: Dict):
        # Separate known fields and extra fields
        kwargs = {
            key: value
            for key, value in data.items()
            if key in TwitterAgentConfig.required_fields()
        }
        extra_fields = {
            key: value
            for key, value in data.items()
            if key not in TwitterAgentConfig.required_fields()
        }
        # Pass known fields to the dataclass, and store extra fields
        return cls(**kwargs, extra_fields=extra_fields)


@dataclass
class Memory:
    id: str
    conversation_id: Optional[str]
    type: Literal["tweet", "tweet_excluded"]
    text: str
    topics: List[str]
    timestamp: int
    search_topic: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    quoted_tweet_username: Optional[str] = None
    reply_to_id: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict) -> "Memory":
        return Memory(
            id=data["id"],
            conversation_id=data.get("conversation_id"),
            type=data["type"],
            text=data["text"],
            topics=data.get("topics", []),
            timestamp=data["timestamp"],
            search_topic=data.get("search_topic"),
            quoted_tweet_id=data.get("quoted_tweet_id"),
            quoted_tweet_username=data.get("quoted_tweet_username"),
            reply_to_id=data.get("reply_to_id"),
        )

    def to_dict(self) -> Dict:
        return self.__dict__


@dataclass
class TwitterPost:
    type: Literal["tweet", "tweet_excluded"]
    conversation_id: Optional[str]
    text: str

    topics: List[str] = None
    search_topic: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    quoted_tweet_username: Optional[str] = None
    reply_to_id: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict) -> "TwitterPost":
        return TwitterPost(
            type=data["type"],
            conversation_id=data["conversation_id"],
            text=data["text"],
            topics=data.get("topics"),
            search_topic=data.get("search_topic"),
            quoted_tweet_id=data.get("quoted_tweet_id"),
            quoted_tweet_username=data.get("quoted_tweet_username"),
            reply_to_id=data.get("reply_to_id"),
        )

    def to_dict(self) -> Dict:
        return self.__dict__
