from openai import AsyncOpenAI


async def generate_dashboard_html(api_key: str, system_prompt: str, user_message: str) -> str:
    client = AsyncOpenAI(api_key=api_key)
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=8192,
    )
    return response.choices[0].message.content.strip()


async def continue_dashboard_chat(
    api_key: str,
    system_prompt: str,
    messages: list[dict],
    current_html: str,
) -> str:
    client = AsyncOpenAI(api_key=api_key)
    # Prepend current HTML as context
    context_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "assistant",
            "content": f"Here is the current dashboard HTML:\n\n{current_html}",
        },
        *messages,
    ]
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=context_messages,
        temperature=0.2,
        max_tokens=8192,
    )
    return response.choices[0].message.content.strip()


async def test_openai_key(api_key: str) -> bool:
    try:
        client = AsyncOpenAI(api_key=api_key)
        await client.models.list()
        return True
    except Exception:
        return False
