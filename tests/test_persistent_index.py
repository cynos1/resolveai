import json

import pytest

from src.persistent_index import (
    build_index,
    get_or_build_index,
    index_is_valid,
    load_index,
    policy_fingerprint,
    search_persistent_index,
)


@pytest.fixture
def policy_file(tmp_path):
    path = tmp_path / "policy.md"

    path.write_text(
        "# Northstar Air Policy\n\n"
        "## Reporting\n"
        "Report delayed baggage.\n\n"
        "## Tracking\n"
        "Track suitcase status.\n",
        encoding="utf-8",
    )

    return path


def fake_embedder(texts):
    vectors = []

    for text in texts:
        lower = text.lower()

        if "tracking" in lower or "suitcase" in lower:
            vectors.append([0.0, 1.0])
        else:
            vectors.append([1.0, 0.0])

    return vectors


def test_fingerprint_changes_when_policy_changes(policy_file):
    before = policy_fingerprint(policy_file)

    policy_file.write_text(
        policy_file.read_text() + "\nUpdated policy.",
        encoding="utf-8",
    )

    after = policy_fingerprint(policy_file)

    assert before != after


def test_build_index(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    assert len(index["sections"]) == 2
    assert len(index["embeddings"]) == 2
    assert index["dimensions"] == 2


def test_index_is_valid(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    assert index_is_valid(index, policy_file)


def test_first_run_builds_index(policy_file, tmp_path):
    index_path = tmp_path / "index.json"

    index, status = get_or_build_index(
        policy_path=policy_file,
        index_path=index_path,
        embedder=fake_embedder,
    )

    assert status == "rebuilt"
    assert index_path.exists()
    assert len(index["sections"]) == 2


def test_second_run_reuses_index(policy_file, tmp_path):
    index_path = tmp_path / "index.json"

    get_or_build_index(
        policy_path=policy_file,
        index_path=index_path,
        embedder=fake_embedder,
    )

    def should_not_embed(texts):
        raise AssertionError("Index should be reused")

    _, status = get_or_build_index(
        policy_path=policy_file,
        index_path=index_path,
        embedder=should_not_embed,
    )

    assert status == "reused"


def test_policy_change_rebuilds_index(policy_file, tmp_path):
    index_path = tmp_path / "index.json"

    get_or_build_index(
        policy_path=policy_file,
        index_path=index_path,
        embedder=fake_embedder,
    )

    policy_file.write_text(
        policy_file.read_text() + "\nNew rule.",
        encoding="utf-8",
    )

    _, status = get_or_build_index(
        policy_path=policy_file,
        index_path=index_path,
        embedder=fake_embedder,
    )

    assert status == "rebuilt"


def test_corrupted_index_rebuilds(policy_file, tmp_path):
    index_path = tmp_path / "index.json"

    index_path.write_text(
        "{this is not valid json",
        encoding="utf-8",
    )

    _, status = get_or_build_index(
        policy_path=policy_file,
        index_path=index_path,
        embedder=fake_embedder,
    )

    assert status == "rebuilt"

    assert isinstance(load_index(index_path), dict)


def test_model_change_invalidates_index(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    assert not index_is_valid(
        index,
        policy_path=policy_file,
        model="another-embedding-model",
    )


def test_index_version_change_invalidates(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    index["index_version"] = 999

    assert not index_is_valid(index, policy_file)


def test_search_persistent_index(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    results = search_persistent_index(
        "Where is my suitcase?",
        index,
        top_k=1,
        embedder=fake_embedder,
    )

    assert results[0]["heading"] == "Tracking"


def test_invalid_query_dimension(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    with pytest.raises(ValueError):
        search_persistent_index(
            "Where is my suitcase?",
            index,
            embedder=lambda texts: [[1, 2, 3]],
        )


def test_invalid_embedding_count(policy_file):
    with pytest.raises(ValueError):
        build_index(
            policy_path=policy_file,
            embedder=lambda texts: [[1.0, 0.0]],
        )


def test_empty_query_skips_embedding(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    results = search_persistent_index(
        " ",
        index,
        embedder=lambda texts: (_ for _ in ()).throw(
            AssertionError("Should not embed empty query")
        ),
    )

    assert results == []


def test_invalid_top_k(policy_file):
    index = build_index(
        policy_path=policy_file,
        embedder=fake_embedder,
    )

    with pytest.raises(ValueError):
        search_persistent_index(
            "suitcase",
            index,
            top_k=0,
            embedder=fake_embedder,
        )
