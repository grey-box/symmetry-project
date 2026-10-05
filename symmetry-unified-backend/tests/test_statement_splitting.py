import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.statements import router
from app.services.statement_splitting import MAX_TEXT_LENGTH, split_statements


class StatementSplittingTests(unittest.TestCase):
    def test_sentences(self):
        self.assertEqual(
            split_statements("Paris is in France. Berlin is in Germany."),
            ["Paris is in France.", "Berlin is in Germany."],
        )

    def test_abbreviations_and_decimals(self):
        self.assertEqual(
            split_statements("Dr. Smith visited the U.S.A. in 2020. It cost $3.14."),
            [
                "Dr. Smith visited the U.S.A. in 2020.",
                "It cost $3.14.",
            ],
        )

    def test_bullet_list(self):
        self.assertEqual(
            split_statements("- First statement\n- Second statement"),
            ["First statement", "Second statement"],
        )

    def test_numbered_list(self):
        self.assertEqual(
            split_statements("1. First statement\n2) Second statement"),
            ["First statement", "Second statement"],
        )

    def test_paragraphs_and_wrapped_lines(self):
        self.assertEqual(
            split_statements("Paris is\nin France.\n\nBerlin is in Germany."),
            ["Paris is in France.", "Berlin is in Germany."],
        )

    def test_empty_input(self):
        self.assertEqual(split_statements(" \n\t"), [])

    def test_repeated_statements(self):
        self.assertEqual(
            split_statements("It works. It works."),
            ["It works.", "It works."],
        )

    def test_compound_sentence_preserved(self):
        text = "Paris is in France and Berlin is in Germany."
        self.assertEqual(split_statements(text), [text])


class StatementApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_response(self):
        response = self.client.post(
            "/symmetry/v1/statements/split",
            json={"text": "First sentence. Second sentence."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"statements": ["First sentence.", "Second sentence."]},
        )

    def test_empty_text(self):
        response = self.client.post(
            "/symmetry/v1/statements/split",
            json={"text": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"statements": []})

    def test_invalid_input(self):
        for payload in ({}, {"text": None}, {"text": 42}):
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/symmetry/v1/statements/split",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422)

    def test_oversized_input(self):
        response = self.client.post(
            "/symmetry/v1/statements/split",
            json={"text": "x" * (MAX_TEXT_LENGTH + 1)},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
