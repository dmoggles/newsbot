import os
import pytest
from storage import RedisStorage, Story, PostStatus

REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")

@pytest.fixture(scope="function")
def storage():
    s = RedisStorage(url=REDIS_URL)
    # Clean up before each test
    for key in s.client.keys("story:*"):
        s.client.delete(key)
    yield s
    # Clean up after each test
    for key in s.client.keys("story:*"):
        s.client.delete(key)

def test_save_and_get_story(storage):
    story = Story(
        story_id="abc123",
        title="Test Title",
        url="http://example.com",
        date="2025-06-20",
        source="Test Source",
        byline="Test Byline",
        decoded_url="http://example.com/real",
        full_text="Full text here.",
        summary="Summary here.",
        post_status=PostStatus.posted
    )
    storage.save_story(story)
    loaded = storage.get_story("abc123")
    assert loaded is not None
    assert loaded.story_id == story.story_id
    assert loaded.title == story.title
    assert loaded.full_text == story.full_text
    assert loaded.post_status == PostStatus.posted

def test_story_exists(storage):
    story = Story(
        story_id="exists1",
        title="Exists Test",
        url="http://exists.com",
        date="2025-06-20",
        source="Test Source"
    )
    storage.save_story(story)
    assert storage.story_exists("exists1")
    assert not storage.story_exists("notfound")

def test_update_story(storage):
    story = Story(
        story_id="update1",
        title="Old Title",
        url="http://update.com",
        date="2025-06-20",
        source="Test Source"
    )
    storage.save_story(story)
    updated = story.model_copy(update={"title": "New Title"})
    storage.update_story(updated)
    loaded = storage.get_story("update1")
    assert loaded is not None
    assert loaded.title == "New Title"

def test_get_all_stories(storage):
    stories = [
        Story(story_id=f"id{i}", title=f"T{i}", url=f"u{i}", date="2025-06-20", source="S")
        for i in range(3)
    ]
    for s in stories:
        storage.save_story(s)
    all_stories = storage.get_all_stories()
    assert len(all_stories) == 3
    ids = {s.story_id for s in all_stories}
    for s in stories:
        assert s.story_id in ids
