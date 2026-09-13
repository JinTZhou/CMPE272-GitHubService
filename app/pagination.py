# Author: Jin Ting Zhou
# Utilities for GitHub pagination headers.


def parse_link_header(
    header: str | None,
) -> dict[str, str]:

    if not header:
        return {}

    links = {}

    for part in header.split(","):
        section = part.strip()

        if "<" not in section or ">" not in section:
            continue

        url = section[
            section.index("<") + 1:
            section.index(">")
        ]

        if 'rel="' not in section:
            continue

        relation = section.split(
            'rel="'
        )[1].split('"')[0]

        links[relation] = url

    return links