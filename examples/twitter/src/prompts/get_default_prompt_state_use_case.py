import random
from typing import Dict
from typing import List

from src.models import TwitterAgentConfig
from src.repository.database import DatabaseClient
from src.utils import format_timestamp


async def execute(
    agent: TwitterAgentConfig,
    database_client: DatabaseClient,
) -> Dict:
    topics = await _get_topics(agent, database_client)
    return {
        "recent_posts": await _get_recent_posts(agent, database_client),
        "knowledge": _get_formatted_knowledge(agent),
        "agent_name": agent.name,
        "twitter_user_name": agent.extra_fields.get("twitter_profile", {}).get(
            "username", "user"
        ),
        "bio": _get_formatted_bio(agent),
        "lore": _get_formatted_lore(agent),
        # This is kind of hacky, needed to get the "topics_data" to save it later
        "topics": _get_formatted_topics(agent, topics),
        "topics_data": topics,
        "post_directions": _get_formatted_post_directions(agent),
    }


async def _get_recent_posts(
    agent: TwitterAgentConfig,
    database_client: DatabaseClient,
) -> str:
    recent_posts: List[str] = []
    tweets = await database_client.get_tweets()
    for tweet in reversed(tweets):
        recent_posts.append(
            f"""Name: {agent.name} (@{agent.extra_fields.get("twitter_profile", {}).get(
                "username", "user"
            )})
ID: {tweet.id}
Date: {format_timestamp(tweet.timestamp)}
Text: {tweet.text}"""
        )
        if len(recent_posts) >= 10:
            break
    return "\n".join([t for t in reversed(recent_posts)])


async def _get_topics(
    agent: TwitterAgentConfig,
    database_client: DatabaseClient,
) -> List[str]:
    topics = agent.topics
    recently_used_topics = []
    latest_tweet = await database_client.get_latest_tweet()
    if latest_tweet and latest_tweet.topics:
        recently_used_topics = latest_tweet.topics
    available_topics = [topic for topic in topics if topic not in recently_used_topics]
    shuffled_topics = random.sample(available_topics, len(available_topics))

    return shuffled_topics[:5]


def _get_formatted_knowledge(agent: TwitterAgentConfig):
    shuffled_knowledge = random.sample(agent.knowledge, len(agent.knowledge))
    return "\n".join(shuffled_knowledge[:3])


def _get_formatted_bio(agent: TwitterAgentConfig) -> str:
    bio = agent.bio
    return " ".join(random.sample(bio, min(len(bio), 3)))


def _get_formatted_lore(agent: TwitterAgentConfig) -> str:
    lore = agent.lore
    shuffled_lore = random.sample(lore, len(lore))
    selected_lore = shuffled_lore[:10]
    return "\n".join(selected_lore)


def _get_formatted_topics(agent: TwitterAgentConfig, selected_topics: List[str]) -> str:
    formatted_topics = ""
    for index, topic in enumerate(selected_topics):
        if index == len(selected_topics) - 2:
            formatted_topics += topic + " and "
        elif index == len(selected_topics) - 1:
            formatted_topics += topic
        else:
            formatted_topics += topic + ", "
    return f"{agent.name} is interested in {formatted_topics}"


def _get_formatted_post_directions(agent: TwitterAgentConfig) -> str:
    style = agent.style
    merged_styles = "\n".join(style.get("all", []) + style.get("post", []))
    return _add_header(f"# Post Directions for {agent.name}", merged_styles)


def _add_header(header: str, body: str) -> str:
    if not body:
        return ""
    full_header = ""
    if header:
        full_header = header + "\n"
    return f"{full_header}{body}\n"
