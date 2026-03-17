import json
import re


def inject_data(html: str, new_data: dict) -> str:
    """
    Replace only the `const DASHBOARD_DATA = { ... }` block in the HTML.
    Everything else in the file remains completely untouched.
    """
    new_data_json = json.dumps(new_data, indent=2)
    new_block = f"const DASHBOARD_DATA = {new_data_json};"

    # Pattern matches the full const DASHBOARD_DATA = { ... }; block
    # Handles nested braces by matching from the first { to the balanced closing }
    pattern = re.compile(
        r"const\s+DASHBOARD_DATA\s*=\s*(\{[\s\S]*?\});",
        re.MULTILINE,
    )

    match = pattern.search(html)
    if not match:
        raise ValueError("DASHBOARD_DATA block not found in HTML. Cannot inject data.")

    # Verify we matched balanced braces (greedy could cut short)
    # Walk from match start to find the real balanced closing brace
    start = match.start()
    brace_start = html.index("{", start)
    depth = 0
    end = brace_start
    for i, ch in enumerate(html[brace_start:], brace_start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    # The full block: from "const DASHBOARD_DATA" to the closing ";"
    # Find the semicolon right after the closing brace (optional whitespace)
    after_brace = html[end + 1:]
    semi_offset = re.match(r"\s*;", after_brace)
    block_end = end + 1 + (len(semi_offset.group()) if semi_offset else 0)

    original_block = html[start:block_end]
    updated_html = html[:start] + new_block + html[block_end:]
    return updated_html
