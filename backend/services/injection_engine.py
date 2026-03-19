import json
import re


def _find_dashboard_data_block(html: str) -> tuple[int, int]:
    """
    Locate the full `const DASHBOARD_DATA = { ... };` block.
    Returns (block_start_index, block_end_index) where html[start:end] is the entire block.
    Raises ValueError if not found.
    """
    match = re.search(r"const\s+DASHBOARD_DATA\s*=\s*", html)
    if not match:
        raise ValueError("DASHBOARD_DATA block not found in HTML.")

    keyword_start = match.start()
    brace_start = html.index("{", match.end())

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

    after_brace = html[end + 1:]
    semi_offset = re.match(r"\s*;", after_brace)
    block_end = end + 1 + (len(semi_offset.group()) if semi_offset else 0)
    return keyword_start, block_end


def convert_to_jinja_template(html: str) -> str:
    """
    Replace the `const DASHBOARD_DATA = { ... }` block with a Jinja2 placeholder.
    The rendered template expects: template.render(asana_data_json=json.dumps(data))
    """
    start, end = _find_dashboard_data_block(html)
    jinja_block = "const DASHBOARD_DATA = {{ asana_data_json }};"
    return html[:start] + jinja_block + html[end:]


def inject_data(html: str, new_data: dict) -> str:
    """
    Replace only the `const DASHBOARD_DATA = { ... }` block in the HTML.
    Everything else in the file remains completely untouched.
    """
    new_data_json = json.dumps(new_data, indent=2)
    new_block = f"const DASHBOARD_DATA = {new_data_json};"
    start, end = _find_dashboard_data_block(html)
    return html[:start] + new_block + html[end:]
