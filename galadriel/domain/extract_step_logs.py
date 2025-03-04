from typing import Optional
import re

from galadriel.entities import Message
from smolagents import ActionStep


async def pull_messages_from_step(
    step_log,
    conversation_id: Optional[str] = None,
    additional_kwargs: Optional[dict] = None,
    show_tool_code: bool = False,
    show_execution_logs: bool = False,
    show_tool_errors: bool = False,
    show_step_errors: bool = False,
    show_token_counts: bool = False,
    show_code_in_thinking: bool = False,
):
    """Extract Message objects from agent steps with proper nesting in OpenAI-compatible format"""

    if not isinstance(step_log, ActionStep):
        return

    # Output the step number
    step_number = f"\n**Step {step_log.step_number}** \n" if step_log.step_number is not None else ""
    yield Message(
        content=step_number,
        conversation_id=conversation_id,
        additional_kwargs={**(additional_kwargs or {}), "role": "assistant", "type": "step_header"},
    )

    # First yield the thought/reasoning from the LLM
    if hasattr(step_log, "model_output") and step_log.model_output is not None:
        # Clean up the LLM output
        model_output = step_log.model_output.strip()
        # Remove any trailing <end_code> and extra backticks
        model_output = re.sub(r"```\s*<end_code>", "```", model_output)
        model_output = re.sub(r"<end_code>\s*```", "```", model_output)
        model_output = re.sub(r"```\s*\n\s*<end_code>", "```", model_output)

        # If we don't want to show code in thinking, remove code blocks and "Code:" labels
        if not show_code_in_thinking:
            # Remove "Code:" labels followed by code blocks
            model_output = re.sub(r"Code:\s*```.*?```", "", model_output, flags=re.DOTALL)
            # Also remove any standalone code blocks
            model_output = re.sub(r"```.*?```", "", model_output, flags=re.DOTALL)
            # Clean up any extra newlines that might have been created
            model_output = re.sub(r"\n{3,}", "\n\n", model_output)

        # Replace tool names with bold formatting, excluding code blocks
        model_output = re.sub(r"(?<=\s)`(\w+)`(?=\s)", r" **\1** ", model_output)
        model_output = model_output.strip()
        model_output += "\n"
        yield Message(
            content=f"\n{model_output}",
            conversation_id=conversation_id,
            additional_kwargs={**(additional_kwargs or {}), "role": "assistant", "type": "thinking"},
        )

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
            # Ensure code block is properly closed
            if not content.endswith("```"):
                content += "\n```"

        # Tool call message
        tool_kwargs = {
            **(additional_kwargs or {}),
            "role": "assistant",
            "tool_name": first_tool_call.name,
            "status": "pending",
            "type": "tool_call",
        }
        if show_tool_code:
            yield Message(content=content, conversation_id=conversation_id, additional_kwargs=tool_kwargs)

        # Execution logs
        if (
            show_execution_logs
            and hasattr(step_log, "observations")
            and step_log.observations
            and step_log.observations.strip()
        ):
            log_content = step_log.observations.strip()
            log_content = re.sub(r"^Execution logs:\s*", "", log_content)
            # Fix markdown structure to avoid nesting issues - use a different format to avoid code block issues
            log_content = f"**Tool Output:**\n\n{log_content}"
            log_kwargs = {**(additional_kwargs or {}), "role": "assistant", "type": "tool_output"}
            yield Message(content=log_content, conversation_id=conversation_id, additional_kwargs=log_kwargs)

        # Tool errors
        if show_tool_errors and hasattr(step_log, "error") and step_log.error is not None:
            error_kwargs = {**(additional_kwargs or {}), "role": "assistant", "type": "error", "status": "done"}
            yield Message(content=str(step_log.error), conversation_id=conversation_id, additional_kwargs=error_kwargs)

    # Handle standalone errors
    elif show_step_errors and hasattr(step_log, "error") and step_log.error is not None:
        error_kwargs = {**(additional_kwargs or {}), "role": "assistant", "type": "error"}
        yield Message(content=str(step_log.error), conversation_id=conversation_id, additional_kwargs=error_kwargs)

    # Step summary with tokens and duration
    if show_token_counts:
        step_footnote = "\n"
        if hasattr(step_log, "input_token_count") and hasattr(step_log, "output_token_count"):
            token_str = f"Input-tokens:{step_log.input_token_count:,} | Output-tokens:{step_log.output_token_count:,}"
            step_footnote += token_str
        if hasattr(step_log, "duration"):
            step_duration = f" | Duration: {round(float(step_log.duration), 2)}" if step_log.duration else ""
            step_footnote += step_duration  # type: ignore
        step_footnote += "\n\n"

        summary_kwargs = {**(additional_kwargs or {}), "role": "assistant", "type": "step_summary"}
        yield Message(content=step_footnote, conversation_id=conversation_id, additional_kwargs=summary_kwargs)
