import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

POLICY_PATH = (
    PROJECT_ROOT
    / "data"
    / "policies"
    / "delayed_baggage_policy.md"
)


def load_policy(policy_path=POLICY_PATH):
    """Read a policy document from disk."""

    return Path(policy_path).read_text(encoding="utf-8")


def split_into_sections(document):
    """Split a Markdown document into headed sections."""

    sections = []
    current_heading = "Introduction"
    current_lines = []

    def save_section():
        content = "\n".join(current_lines).strip()

        if content:
            sections.append({
                "heading": current_heading,
                "content": content,
            })

    for line in document.splitlines():
        if re.match(r"^#{1,6}\s+", line):
            save_section()

            current_heading = re.sub(
                r"^#{1,6}\s+",
                "",
                line
            ).strip()

            current_lines = []
        else:
            current_lines.append(line)

    save_section()

    return sections


def tokenize(text):
    """Convert text into normalized search terms."""

    return set(
        re.findall(r"[a-z0-9]+", text.lower())
    )


def search_policy(query, policy_path=POLICY_PATH, top_k=3):
    """Return policy sections ranked by keyword overlap."""

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    document = load_policy(policy_path)
    sections = split_into_sections(document)

    query_terms = tokenize(query)

    if not query_terms:
        return []

    results = []

    for section in sections:
        searchable_text = (
            section["heading"] + " " + section["content"]
        )

        section_terms = tokenize(searchable_text)

        score = len(query_terms & section_terms)

        if score > 0:
            results.append({
                "heading": section["heading"],
                "content": section["content"],
                "score": score,
            })

    results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    return results[:top_k]
