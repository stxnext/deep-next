import re


def extract_code_from_block(txt: str, code_type: str = "python") -> str:
    pattern = rf"```{code_type}\n(.*?)```"
    match = re.search(pattern, txt, flags=re.DOTALL)
    return match.group(1) if match else ""


def has_code_block(txt: str, code_type: str = "python") -> bool:
    return bool(extract_code_from_block(txt, code_type))


def parse_code_block(txt: str, code_type: str = "python") -> str:
    pattern = rf"```{code_type}\n.*?```"
    out = re.findall(pattern, txt, flags=re.DOTALL)
    if len(out) != 1:
        raise Exception("Unexpected no. of code blocks found")

    return out[0]


def extract_from_tag_block(txt: str, tag: str) -> str:
    pattern = rf"<{re.escape(tag)}>\n(.*?)\n</{re.escape(tag)}>"
    match = re.search(pattern, txt, flags=re.DOTALL)
    return match.group(1) if match else ""


def has_tag_block(txt: str, tag: str) -> bool:
    return bool(extract_from_tag_block(txt, tag))


def parse_tag_block(txt: str, tag: str) -> str:
    pattern = rf"<{re.escape(tag)}>\n.*?\n</{re.escape(tag)}>"
    out = re.findall(pattern, txt, flags=re.DOTALL)
    if len(out) != 1:
        raise Exception("Unexpected no. of code blocks found")

    return out[0]
