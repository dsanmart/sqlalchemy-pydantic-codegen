import re


def extract_model_name(type_str: str) -> str:
    """
    Return the bare class name from a container/union annotation string.

    Examples:
      'Reference'                     -> 'Reference'
      'list[Reference]'               -> 'Reference'
      'list["Reference"] | None'      -> 'Reference'
      'set[FooBar] | None'            -> 'FooBar'
      'tuple[Foo, Bar] | None'        -> 'Foo'  # first arg
    """
    s = type_str.strip()

    # strip optional union suffixes like "| None" or " | None"
    s = re.sub(r"\s*\|\s*None\s*$", "", s)

    # strip quotes around a single name
    if re.fullmatch(r"""['"][A-Za-z_][A-Za-z0-9_]*['"]""", s):
        return s[1:-1]

    # list[...] / set[...] / tuple[...]
    m = re.match(
        r"""^(?:list|set|tuple)\[\s*['"]?([A-Za-z_][A-Za-z0-9_]*)['"]?""",
        s,
    )
    if m:
        return m.group(1)

    # plain bare name
    m = re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s)
    if m:
        return s

    return s  # fallback
