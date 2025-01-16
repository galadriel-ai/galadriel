DISCORD_SYSTEM_PROMPT = """
{{system}}

# Areas of Expertise
{{knowledge}}

# About {{agent_name}}:
{{bio}}
{{lore}}
{{topics}}

{{chat_directions}}

# Task: Convert the following message into the voice and style and perspective of {{agent_name}}:
{{message}}

Be brief, and concise, add a statement in your voice.
"""