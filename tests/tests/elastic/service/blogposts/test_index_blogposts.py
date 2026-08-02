from datetime import datetime, timezone

from src.elastic import ElasticService
from tests.mocks.elastic_operations import ElasticOperations


async def test_index_blogposts_bulk(
    elastic_service: ElasticService,
    elastic_operations: ElasticOperations,
    data_generator,
):
    """Массовая индексация блогпостов."""
    blogposts = [
        data_generator.blogposts.blogpost(
            id=str(i),
            title=f"Post {i}",
            text=f"Text {i}",
            tags=["bulk"],
            updated_at=datetime(2025, 1, i, tzinfo=timezone.utc),
        )
        for i in range(1, 11)
    ]
    await elastic_service.blogposts.index_blogposts(blogposts)

    assert elastic_operations.blogposts.count() == 10
    bp = await elastic_service.blogposts.get("5")
    assert bp.title == "Post 5"
