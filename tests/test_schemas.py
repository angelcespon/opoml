import pytest
from pydantic import ValidationError

from app.schemas import TopicCreate


def test_topic_create_valid_name():
    topic = TopicCreate(name="Constitución")

    assert topic.name == "Constitución"
    assert topic.description is None


def test_topic_create_strips_name_spaces():
    topic = TopicCreate(name="  Constitución  ")

    assert topic.name == "Constitución"
    assert topic.description is None


def test_topic_create_missing_name():
    with pytest.raises(ValidationError):
        TopicCreate()


def test_topic_create_none_name():
    with pytest.raises(ValidationError):
        TopicCreate(name=None)


def test_topic_create_empty_name():
    with pytest.raises(ValidationError):
        TopicCreate(name="")


def test_topic_create_whitespace_name():
    with pytest.raises(ValidationError):
        TopicCreate(name="   ")


def test_topic_create_name_at_max_length():
    topic = TopicCreate(name="a" * 100)

    assert topic.name == "a" * 100


def test_topic_create_name_exceeds_max_length():
    with pytest.raises(ValidationError):
        TopicCreate(name="a" * 101)


def test_topic_create_description_at_max_length():
    topic = TopicCreate(
        name="Constitución",
        description="b" * 500,
    )

    assert topic.name == "Constitución"
    assert topic.description == "b" * 500


def test_topic_create_description_exceeds_max_length():
    with pytest.raises(ValidationError):
        TopicCreate(
            name="Constitución",
            description="b" * 501,
        )


def test_topic_create_rejects_extra_field():
    with pytest.raises(ValidationError):
        TopicCreate(
            name="Constitución",
            difficulty=3,
        )