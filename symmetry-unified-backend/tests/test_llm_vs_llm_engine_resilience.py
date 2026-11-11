"""Resilience tests for multi-engine LLM generation.

Covers the LLM-vs-LLM prerequisite that multiple engines can receive the
same prompt while one engine failure is isolated from successful outputs.
"""

import unittest

from app.engines.base import GenerationRequest
from app.engines.fake import FakeAdapter
from app.services.multi_engine import generate_from_engines


class LlmVsLlmEngineResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_engines_return_independent_answers(self):
        outcome = await generate_from_engines(
            GenerationRequest(prompt="Describe the Eiffel Tower."),
            [
                FakeAdapter("model-a", reply="The Eiffel Tower is in Paris."),
                FakeAdapter(
                    "model-b",
                    reply="The Eiffel Tower was completed in 1889.",
                ),
            ],
        )

        self.assertEqual(
            [result.model for result in outcome.results],
            ["model-a", "model-b"],
        )
        self.assertEqual(
            [result.text for result in outcome.results],
            [
                "The Eiffel Tower is in Paris.",
                "The Eiffel Tower was completed in 1889.",
            ],
        )
        self.assertEqual(outcome.errors, [])
        self.assertTrue(outcome.ok)

    async def test_three_engines_receive_the_same_prompt(self):
        prompt = "Give one fact about solar energy."

        outcome = await generate_from_engines(
            GenerationRequest(prompt=prompt),
            [
                FakeAdapter("model-a"),
                FakeAdapter("model-b"),
                FakeAdapter("model-c"),
            ],
        )

        self.assertEqual(len(outcome.results), 3)
        self.assertEqual(
            [result.model for result in outcome.results],
            ["model-a", "model-b", "model-c"],
        )
        self.assertEqual(
            [result.text for result in outcome.results],
            [f"echo: {prompt}"] * 3,
        )
        self.assertEqual(outcome.errors, [])
        self.assertTrue(outcome.ok)

    async def test_one_engine_down_does_not_fail_other_engines(self):
        outcome = await generate_from_engines(
            GenerationRequest(prompt="Compare these model answers."),
            [
                FakeAdapter("model-a", reply="Answer from A"),
                FakeAdapter("model-b", fail="timeout"),
                FakeAdapter("model-c", reply="Answer from C"),
            ],
        )

        self.assertEqual(
            [result.model for result in outcome.results],
            ["model-a", "model-c"],
        )
        self.assertEqual(
            [result.text for result in outcome.results],
            ["Answer from A", "Answer from C"],
        )

        self.assertEqual(len(outcome.errors), 1)
        error = outcome.errors[0]

        self.assertEqual(error["provider"], "fake")
        self.assertEqual(error["model"], "model-b")
        self.assertEqual(error["error"], "AdapterTimeoutError")
        self.assertTrue(error["retryable"])
        self.assertFalse(outcome.ok)


if __name__ == "__main__":
    unittest.main()