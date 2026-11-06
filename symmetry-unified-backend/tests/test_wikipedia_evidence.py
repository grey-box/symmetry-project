import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.engines.fake import FakeAdapter
from app.services.wikipedia_evidence import (
    WikipediaEvidenceError,
    compare_with_wikipedia,
)

FETCH_PATH = "app.services.wikipedia_evidence.resolve_and_fetch_article"


def make_article(*texts):
    return SimpleNamespace(
        title="Example",
        lang="en",
        sections=[
            SimpleNamespace(title=f"Section {index}", clean_content=text)
            for index, text in enumerate(texts)
        ],
    )


def make_adapter(label, evidence="", confidence=0.9):
    return FakeAdapter(
        "test-judge",
        reply=json.dumps(
            {"label": label, "confidence": confidence, "evidence": evidence}
        ),
    )


class WikipediaEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_labels_and_attaches_evidence(self):
        article = make_article("The tower is in Paris.")
        cases = [
            ("supported", "The tower is in Paris."),
            ("contradicted", "The tower is in Rome."),
            ("not_found", "The tower has a swimming pool."),
        ]
        for label, statement in cases:
            evidence = "" if label == "not_found" else "The tower is in Paris."
            with (
                self.subTest(label=label),
                patch(FETCH_PATH, new=AsyncMock(return_value=article)),
            ):
                result = await compare_with_wikipedia(
                    statement, "Example", make_adapter(label, evidence)
                )
                row = result["statements"][0]
                self.assertEqual(row["label"], label)
                self.assertEqual(row["confidence"], 0.9)
                if evidence:
                    self.assertEqual(row["evidence"][0]["text"], evidence)
                    self.assertTrue(row["evidence"][0]["url"].endswith("/Example"))
                else:
                    self.assertEqual(row["evidence"], [])

    async def test_unverified_evidence_is_unverifiable(self):
        with patch(
            FETCH_PATH,
            new=AsyncMock(return_value=make_article("The tower is in Paris.")),
        ):
            result = await compare_with_wikipedia(
                "The tower is in Rome.",
                "Example",
                make_adapter("contradicted", "An invented quote."),
            )
        row = result["statements"][0]
        self.assertEqual(row["label"], "unverifiable")
        self.assertIsNone(row["confidence"])
        self.assertEqual(row["evidence"], [])

    async def test_retrieves_relevant_later_section(self):
        article = make_article(
            "Apples grow on trees.",
            "Boats cross the ocean.",
            "Birds build nests.",
            "The tower is in Paris.",
        )
        with patch(FETCH_PATH, new=AsyncMock(return_value=article)):
            result = await compare_with_wikipedia(
                "The tower is in Paris.",
                "Example",
                make_adapter("supported", "The tower is in Paris."),
            )
        row = result["statements"][0]
        self.assertEqual(row["retrieved_passages"][0]["text"], "The tower is in Paris.")
        self.assertTrue(row["reference_is_subset"])

    async def test_empty_article_is_retrieval_error(self):
        with (
            patch(FETCH_PATH, new=AsyncMock(return_value=make_article(""))),
            self.assertRaises(WikipediaEvidenceError),
        ):
            await compare_with_wikipedia(
                "A statement.", "Example", make_adapter("not_found")
            )

    async def test_empty_input_does_not_fetch(self):
        with patch(FETCH_PATH, new_callable=AsyncMock) as fetch:
            with self.assertRaises(ValueError):
                await compare_with_wikipedia("", "Example", make_adapter("not_found"))
            fetch.assert_not_awaited()

    async def test_fetch_failure_propagates(self):
        with (
            patch(FETCH_PATH, new=AsyncMock(side_effect=RuntimeError("offline"))),
            self.assertRaisesRegex(RuntimeError, "offline"),
        ):
            await compare_with_wikipedia(
                "A statement.", "Example", make_adapter("not_found")
            )


if __name__ == "__main__":
    unittest.main()
