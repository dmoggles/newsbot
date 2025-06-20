from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
import redis
import json

class PostStatus(str, Enum):
    posted = "posted"
    failed = "failed"
    skipped = "skipped"
    pending = "pending"

class Story(BaseModel):
    story_id: str
    title: str
    url: str
    date: str
    source: str
    byline: Optional[str] = None
    decoded_url: Optional[str] = None
    full_text: Optional[str] = None
    summary: Optional[str] = None
    post_status: Optional[PostStatus] = None
    # Add more fields as needed

class RedisStorage:
    def __init__(self, url: str = "redis://localhost:6379/0"):
        self.client: redis.Redis = redis.Redis.from_url(url)

    def save_story(self, story: Story) -> None:
        # Serialize each field as JSON for consistency
        data = {k: json.dumps(v) for k, v in story.model_dump().items()}
        # Ensure all values are str, as required by redis-py type hints
        data_str = {k: str(v) for k, v in data.items()}
        self.client.hset(f"story:{story.story_id}", mapping=data_str)

    def get_story(self, story_id: str) -> Optional[Story]:
        result = self.client.hgetall(f"story:{story_id}")
        if not result:
            return None
        data: Dict[str, Any] = {k.decode(): json.loads(v) for k, v in result.items()}
        return Story(**data)

    def story_exists(self, story_id: str) -> bool:
        return self.client.exists(f"story:{story_id}") == 1

    def update_story(self, story: Story) -> None:
        self.save_story(story)

    def get_all_stories(self) -> List[Story]:
        keys: List[bytes] = self.client.keys("story:*")
        stories: List[Story] = []
        for key in keys:
            story_id = key.decode().split(":", 1)[1]
            story = self.get_story(story_id)
            if story:
                stories.append(story)
        return stories
