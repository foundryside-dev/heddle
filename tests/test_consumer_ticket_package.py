from __future__ import annotations

from pathlib import Path

CONSUMERS = ["Loomweave", "Charter", "Legis", "Wardline", "Filigree"]


def test_consumer_ticket_package_exists_for_every_pairwise_story() -> None:
    text = Path("docs/integration/post-admission-consumer-tickets.md").read_text(
        encoding="utf-8"
    )
    for consumer in CONSUMERS:
        assert f"## {consumer}" in text
    assert "owner admission" in text
    assert "Do not patch sibling repos from Heddle delivery work" in text


def test_consumer_ticket_package_keeps_authorities_separate() -> None:
    text = Path("docs/integration/post-admission-consumer-tickets.md").read_text(
        encoding="utf-8"
    )
    assert "Loomweave owns current structure" in text
    assert "Charter owns obligations" in text
    assert "Legis owns governance" in text
    assert "Wardline owns trust policy" in text
    assert "Filigree owns work state" in text
