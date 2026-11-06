import unittest

from app.engines.base import GenerationRequest
from app.engines.errors import AdapterTimeoutError
from app.engines.fake import FakeAdapter
from app.services.multi_engine import generate_from_engines


class MultiEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_prompt_reaches_three_engines(self):
        engines = [FakeAdapter(f"model-{i}") for i in range(3)]
        request = GenerationRequest(prompt="Explain solar energy")

        results = await generate_from_engines(request, engines)

        self.assertEqual(len(results), 3)
        self.assertEqual(
            [result.model for result in results],
            ["model-0", "model-1", "model-2"],
        )
        self.assertEqual(
            [result.text for result in results],
            ["echo: Explain solar energy"] * 3,
        )
        self.assertTrue(all(result.provider == "fake" for result in results))

    async def test_preserves_separate_answers(self):
        engines = [
            FakeAdapter("model-a", reply="First answer"),
            FakeAdapter("model-b", reply="Second answer"),
        ]

        results = await generate_from_engines(
            GenerationRequest(prompt="Compare these answers"),
            engines,
        )

        self.assertEqual(
            [result.text for result in results],
            ["First answer", "Second answer"],
        )

    async def test_rejects_fewer_than_two_engines(self):
        request = GenerationRequest(prompt="Hello")

        for engines in ([], [FakeAdapter("model-a")]):
            with (
                self.subTest(count=len(engines)),
                self.assertRaisesRegex(ValueError, "At least two"),
            ):
                await generate_from_engines(request, engines)

    async def test_rejects_duplicate_engines(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            await generate_from_engines(
                GenerationRequest(prompt="Hello"),
                [FakeAdapter("model-a"), FakeAdapter("model-a")],
            )

    async def test_adapter_error_propagates(self):
        with self.assertRaises(AdapterTimeoutError):
            await generate_from_engines(
                GenerationRequest(prompt="Hello"),
                [
                    FakeAdapter("model-a"),
                    FakeAdapter("model-b", fail="timeout"),
                ],
            )


if __name__ == "__main__":
    unittest.main()
