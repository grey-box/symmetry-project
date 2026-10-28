import asyncio
import json

import httpx
import pytest

from app.engines import (
    AdapterConfigError,
    AdapterRequestError,
    AdapterTimeoutError,
    GenerationRequest,
)
from app.engines.selection import ModelSelector, ModelSpec, load_selector

REQUEST = GenerationRequest(prompt="hi")


# Runs a coroutine to completion.
def run(coro):
    return asyncio.run(coro)


# A catalog entry backed by the offline fake adapter; price is the total USD per 1M tokens.
def fake(id, price, tier=1, **config):
    return ModelSpec(
        id=id,
        provider="fake",
        model=id,
        tier=tier,
        price_per_1m_input=price,
        config=config,
    )


# A catalog entry backed by cloud_llm with a mocked endpoint.
def cloud(id, price, handler, key_env="SELECTOR_KEY", **config):
    return ModelSpec(
        id=id,
        provider="cloud_llm",
        model=id,
        price_per_1m_input=price,
        config={
            "base_url": "https://llm.test/v1",
            "api_key_env": key_env,
            "transport": httpx.MockTransport(handler),
            **config,
        },
    )


def reply(content="ok", usage=None):
    body = {"choices": [{"message": {"content": content}}]}
    if usage:
        body["usage"] = usage
    return lambda request: httpx.Response(200, json=body)


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("SELECTOR_KEY", "selector-test-key")
    monkeypatch.delenv("LLM_MODELS_PATH", raising=False)


def ids(specs):
    return [s.id for s in specs]


# --- ordering ---------------------------------------------------------------


@pytest.mark.unit
def test_candidates_are_cheapest_first():
    selector = ModelSelector([fake("mid", 2), fake("cheap", 0.5), fake("pricey", 10)])
    assert ids(selector.candidates()) == ["cheap", "mid", "pricey"]


@pytest.mark.unit
def test_price_is_input_plus_output_and_ties_go_to_lower_tier_then_id():
    both = ModelSpec(
        id="both",
        provider="fake",
        model="m",
        price_per_1m_input=1,
        price_per_1m_output=1,
    )
    selector = ModelSelector(
        [
            fake("b-high", 2, tier=2),
            both,
            fake("a-high", 2, tier=2),
            fake("c-low", 2, tier=1),
        ]
    )
    assert ids(selector.candidates()) == ["both", "c-low", "a-high", "b-high"]


# --- language pair overrides ------------------------------------------------


@pytest.mark.unit
def test_override_replaces_the_default_for_its_pair_only():
    selector = ModelSelector(
        [fake("cheap", 1), fake("strong", 9)],
        {"en->sw": ["strong"]},
    )
    assert ids(selector.candidates("en", "sw")) == ["strong"]
    assert ids(selector.candidates("en", "fr")) == ["cheap", "strong"]
    assert ids(selector.candidates("sw", "en")) == ["cheap", "strong"]
    assert ids(selector.candidates()) == ["cheap", "strong"]


@pytest.mark.unit
def test_override_matching_ignores_case_and_spaces_and_keeps_order():
    selector = ModelSelector(
        [fake("cheap", 1), fake("mid", 5), fake("strong", 9)],
        {" EN -> Sw ": ["strong", "mid"]},
    )
    assert ids(selector.candidates("en", "SW")) == ["strong", "mid"]


@pytest.mark.unit
def test_regional_language_codes_are_not_split():
    selector = ModelSelector([fake("a", 1), fake("b", 2)], {"pt-BR->en": ["b"]})
    assert ids(selector.candidates("pt-br", "en")) == ["b"]
    assert ids(selector.candidates("pt", "en")) == ["a", "b"]


# --- selecting and skipping unusable models ---------------------------------


@pytest.mark.unit
def test_select_returns_the_cheapest_adapter():
    adapter = ModelSelector([fake("pricey", 9), fake("cheap", 1)]).select()
    assert adapter.get_model_name() == "cheap"


@pytest.mark.unit
def test_select_skips_a_model_whose_key_is_missing(monkeypatch):
    monkeypatch.delenv("NO_KEY_SET", raising=False)
    selector = ModelSelector(
        [
            cloud("cheap", 0.1, reply(), key_env="NO_KEY_SET"),
            cloud("next", 0.5, reply()),
        ]
    )
    assert selector.select().get_model_name() == "next"


@pytest.mark.unit
def test_select_with_nothing_usable_lists_why(monkeypatch):
    monkeypatch.delenv("NO_KEY_SET", raising=False)
    selector = ModelSelector([cloud("only", 0.1, reply(), key_env="NO_KEY_SET")])
    with pytest.raises(AdapterConfigError) as exc:
        selector.select()
    assert "only" in exc.value.message and "NO_KEY_SET" in exc.value.message
    assert "selector-test-key" not in str(exc.value)


@pytest.mark.unit
def test_empty_catalog_is_a_clear_error():
    with pytest.raises(AdapterConfigError, match="no models are configured"):
        ModelSelector([]).select()
    with pytest.raises(AdapterConfigError, match="no models are configured"):
        run(ModelSelector([]).generate(REQUEST))


# --- generate and fallback --------------------------------------------------


@pytest.mark.unit
def test_generate_uses_the_cheapest_model_and_names_it():
    selector = ModelSelector(
        [fake("pricey", 9, reply="expensive"), fake("cheap", 1, reply="cheap answer")]
    )
    result = run(selector.generate(REQUEST))
    assert result.text == "cheap answer" and result.model == "cheap"


@pytest.mark.unit
def test_generate_uses_the_override_model_for_its_pair():
    selector = ModelSelector(
        [fake("cheap", 1, reply="c"), fake("strong", 9, reply="s")],
        {"en->sw": ["strong"]},
    )
    assert run(selector.generate(REQUEST, "en", "sw")).model == "strong"
    assert run(selector.generate(REQUEST, "en", "fr")).model == "cheap"


# Without fallback, a failure of the cheapest model is raised, never silently upgraded.
@pytest.mark.unit
def test_failure_raises_by_default_without_trying_a_pricier_model():
    selector = ModelSelector([fake("cheap", 1, fail="timeout"), fake("strong", 9)])
    with pytest.raises(AdapterTimeoutError):
        run(selector.generate(REQUEST))


@pytest.mark.unit
def test_fallback_moves_to_the_next_model_on_a_retryable_failure():
    selector = ModelSelector(
        [fake("cheap", 1, fail="timeout"), fake("strong", 9, reply="rescued")]
    )
    result = run(selector.generate(REQUEST, fallback=True))
    assert result.model == "strong" and result.text == "rescued"


@pytest.mark.unit
def test_fallback_does_not_hide_a_non_retryable_failure():
    rejected = cloud("cheap", 1, lambda r: httpx.Response(400, json={"error": "bad"}))
    selector = ModelSelector([rejected, fake("strong", 9)])
    with pytest.raises(AdapterRequestError):
        run(selector.generate(REQUEST, fallback=True))


@pytest.mark.unit
def test_fallback_exhausted_raises_the_last_error():
    selector = ModelSelector(
        [fake("a", 1, fail="timeout"), fake("b", 2, fail="timeout")]
    )
    with pytest.raises(AdapterTimeoutError) as exc:
        run(selector.generate(REQUEST, fallback=True))
    assert exc.value.model == "b"


@pytest.mark.unit
def test_fallback_stays_inside_an_override_list():
    selector = ModelSelector(
        [fake("cheap", 1, reply="c"), fake("strong", 9, fail="timeout")],
        {"en->sw": ["strong"]},
    )
    with pytest.raises(AdapterTimeoutError):
        run(selector.generate(REQUEST, "en", "sw", fallback=True))


@pytest.mark.unit
def test_fallback_skips_models_with_missing_keys(monkeypatch):
    monkeypatch.delenv("NO_KEY_SET", raising=False)
    selector = ModelSelector(
        [
            fake("first", 1, fail="timeout"),
            cloud("no-key", 2, reply(), key_env="NO_KEY_SET"),
            fake("last", 3, reply="done"),
        ]
    )
    assert run(selector.generate(REQUEST, fallback=True)).model == "last"


# The catalog prices flow through to the adapter so results report their cost.
@pytest.mark.unit
def test_result_reports_cost_from_catalog_prices():
    usage = {"prompt_tokens": 1000, "completion_tokens": 1000}
    spec = ModelSpec(
        id="m",
        provider="cloud_llm",
        model="m",
        price_per_1m_input=0.5,
        price_per_1m_output=1.5,
        config={
            "base_url": "https://llm.test/v1",
            "api_key_env": "SELECTOR_KEY",
            "transport": httpx.MockTransport(reply(usage=usage)),
        },
    )
    result = run(ModelSelector([spec]).generate(REQUEST))
    assert result.usage["cost_usd"] == pytest.approx(0.002)


# --- building a selector from catalog data ----------------------------------


def catalog(**overrides):
    base = {
        "models": [
            {
                "id": "cheap",
                "provider": "cloud_llm",
                "model": "small",
                "price_per_1m_input": 0.1,
                "price_per_1m_output": 0.4,
                "base_url": "https://llm.test/v1",
                "api_key_env": "SELECTOR_KEY",
            },
            {
                "id": "strong",
                "provider": "cloud_llm",
                "model": "large",
                "tier": 2,
                "price_per_1m_input": 3,
                "price_per_1m_output": 9,
                "base_url": "https://llm.test/v1",
                "api_key_env": "SELECTOR_KEY",
            },
        ],
        "language_overrides": {"en->sw": ["strong"]},
    }
    return {**base, **overrides}


@pytest.mark.unit
def test_from_dict_builds_specs_and_passes_extra_keys_to_the_adapter():
    selector = ModelSelector.from_dict(catalog())
    assert ids(selector.candidates()) == ["cheap", "strong"]
    assert ids(selector.candidates("en", "sw")) == ["strong"]
    spec = selector.specs["cheap"]
    assert spec.model == "small" and spec.tier == 1
    assert spec.config == {
        "base_url": "https://llm.test/v1",
        "api_key_env": "SELECTOR_KEY",
    }
    assert selector.select().get_model_name() == "small"


@pytest.mark.unit
def test_local_models_may_omit_prices_and_sort_first():
    data = {
        "models": [
            {
                "id": "paid",
                "provider": "fake",
                "model": "p",
                "price_per_1m_input": 1,
                "price_per_1m_output": 1,
            },
            {"id": "local", "provider": "local_slm", "model": "qwen2.5:1.5b"},
        ]
    }
    assert ids(ModelSelector.from_dict(data).candidates()) == ["local", "paid"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["models"][0].pop("price_per_1m_output"),
        lambda c: c["models"][0].pop("price_per_1m_input"),
        lambda c: c["models"][0].update(price_per_1m_input=-1),
        lambda c: c["models"][0].update(price_per_1m_input="cheap"),
        lambda c: c["models"][0].update(price_per_1m_input=True),
        lambda c: c["models"][0].update(tier="high"),
        lambda c: c["models"][0].update(tier=True),
        lambda c: c["models"][0].pop("id"),
        lambda c: c["models"][0].pop("provider"),
        lambda c: c["models"][0].update(model="  "),
        lambda c: c["models"].append(dict(c["models"][0])),
        lambda c: c["models"].append("not a table"),
        lambda c: c["language_overrides"].update({"en->fr": ["ghost"]}),
        lambda c: c["language_overrides"].update({"en->fr": []}),
        lambda c: c["language_overrides"].update({"enfr": ["cheap"]}),
        lambda c: c["language_overrides"].update({"->fr": ["cheap"]}),
    ],
)
def test_invalid_catalog_is_a_config_error(mutate):
    data = catalog()
    mutate(data)
    with pytest.raises(AdapterConfigError):
        ModelSelector.from_dict(data)


# --- loading the catalog from a file ----------------------------------------


TOML = """
[[models]]
id = "cheap"
provider = "fake"
model = "cheap"
price_per_1m_input = 0.1
price_per_1m_output = 0.4
reply = "from file"

[language_overrides]
"en->sw" = ["cheap"]
"""


@pytest.mark.unit
def test_load_selector_reads_a_toml_file(tmp_path):
    path = tmp_path / "models.toml"
    path.write_text(TOML, encoding="utf-8")
    selector = load_selector(path)
    assert run(selector.generate(REQUEST, "en", "sw")).text == "from file"


@pytest.mark.unit
def test_load_selector_uses_the_environment_path(tmp_path, monkeypatch):
    path = tmp_path / "elsewhere.toml"
    path.write_text(TOML, encoding="utf-8")
    monkeypatch.setenv("LLM_MODELS_PATH", str(path))
    assert ids(load_selector().candidates()) == ["cheap"]


@pytest.mark.unit
def test_missing_catalog_file_gives_an_empty_selector(tmp_path):
    assert load_selector(tmp_path / "nope.toml").candidates() == []


@pytest.mark.unit
def test_broken_toml_is_a_config_error(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text("[[models]\nid = ", encoding="utf-8")
    with pytest.raises(AdapterConfigError, match="bad.toml"):
        load_selector(path)


# The catalog holds only the NAME of each key variable, so the file is safe to commit.
@pytest.mark.unit
def test_catalog_entries_never_hold_the_key_itself():
    selector = ModelSelector.from_dict(catalog())
    assert "selector-test-key" not in json.dumps(
        {i: s.config for i, s in selector.specs.items()}
    )


# The shipped example catalog stays valid and keeps secrets out of the file.
@pytest.mark.unit
def test_example_catalog_parses_and_holds_no_secrets():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "llm_models.example.toml"
    selector = load_selector(path)
    assert len(selector.specs) == 4
    assert all(
        s.config["api_key_env"].endswith("_API_KEY") for s in selector.specs.values()
    )
    assert "sk-" not in path.read_text(encoding="utf-8")
