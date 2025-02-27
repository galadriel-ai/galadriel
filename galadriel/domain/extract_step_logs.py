from typing import Optional
import re

from galadriel.entities import LogMessage
from smolagents import ActionStep


async def pull_messages_from_step(
    step_log, conversation_id: Optional[str] = None, additional_kwargs: Optional[dict] = None
):
    """Extract Message objects from agent steps with proper nesting"""

    if not isinstance(step_log, ActionStep):
        return

    # Output the step number
    step_number = f"Step {step_log.step_number}" if step_log.step_number is not None else ""
    yield LogMessage(content=f"**{step_number}**", conversation_id=conversation_id, additional_kwargs=additional_kwargs)

    # First yield the thought/reasoning from the LLM
    if hasattr(step_log, "model_output") and step_log.model_output is not None:
        # Clean up the LLM output
        model_output = step_log.model_output.strip()
        # Remove any trailing <end_code> and extra backticks
        model_output = re.sub(r"```\s*<end_code>", "```", model_output)
        model_output = re.sub(r"<end_code>\s*```", "```", model_output)
        model_output = re.sub(r"```\s*\n\s*<end_code>", "```", model_output)
        model_output = model_output.strip()
        yield LogMessage(content=model_output, conversation_id=conversation_id, additional_kwargs=additional_kwargs)

    # For tool calls
    if hasattr(step_log, "tool_calls") and step_log.tool_calls is not None:
        first_tool_call = step_log.tool_calls[0]
        used_code = first_tool_call.name == "python_interpreter"

        # Handle tool call arguments
        args = first_tool_call.arguments
        if isinstance(args, dict):
            content = str(args.get("answer", str(args)))
        else:
            content = str(args).strip()

        if used_code:
            # Clean up the content
            content = re.sub(r"```.*?\n", "", content)
            content = re.sub(r"\s*<end_code>\s*", "", content)
            content = content.strip()
            if not content.startswith("```python"):
                content = f"```python\n{content}\n```"

        # Tool call message
        tool_kwargs = {**(additional_kwargs or {}), "tool_name": first_tool_call.name, "status": "pending"}
        yield LogMessage(content=content, conversation_id=conversation_id, additional_kwargs=tool_kwargs)

        # Execution logs
        if hasattr(step_log, "observations") and step_log.observations and step_log.observations.strip():
            log_content = step_log.observations.strip()
            log_content = re.sub(r"^Execution logs:\s*", "", log_content)
            log_kwargs = {**(additional_kwargs or {}), "type": "execution_logs", "status": "done"}
            yield LogMessage(content=log_content, conversation_id=conversation_id, additional_kwargs=log_kwargs)

        # Tool errors
        if hasattr(step_log, "error") and step_log.error is not None:
            error_kwargs = {**(additional_kwargs or {}), "type": "error", "status": "done"}
            yield LogMessage(content=str(step_log.error), conversation_id=conversation_id, additional_kwargs=error_kwargs)

        # Final tool status
        tool_kwargs["status"] = "done"
        yield LogMessage(
            content="Tool execution completed", conversation_id=conversation_id, additional_kwargs=tool_kwargs
        )

    # Handle standalone errors
    elif hasattr(step_log, "error") and step_log.error is not None:
        error_kwargs = {**(additional_kwargs or {}), "type": "error"}
        yield LogMessage(content=str(step_log.error), conversation_id=conversation_id, additional_kwargs=error_kwargs)

    # Step summary with tokens and duration
    step_footnote = f"{step_number}"
    if hasattr(step_log, "input_token_count") and hasattr(step_log, "output_token_count"):
        token_str = f"\nInput-tokens:{step_log.input_token_count:,} | Output-tokens:{step_log.output_token_count:,}"
        step_footnote += token_str
    if hasattr(step_log, "duration"):
        step_duration = f" | Duration: {round(float(step_log.duration), 2)}\n" if step_log.duration else None
        step_footnote += step_duration  # type: ignore

    summary_kwargs = {**(additional_kwargs or {}), "type": "step_summary"}
    yield LogMessage(content=step_footnote, conversation_id=conversation_id, additional_kwargs=summary_kwargs)

    # Step separator
    yield LogMessage(content="-----\n```\n", conversation_id=conversation_id, additional_kwargs=additional_kwargs)
