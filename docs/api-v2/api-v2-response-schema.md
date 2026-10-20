# Symmetry API v2: Published Schema

**Status:** Proposal, open for review · **Applies to:** `/symmetry/v2` · **Last updated:** 2026-10-09

## 1. Purpose and scope

This document defines the published schema for Symmetry API v2: the request body that v2 comparison endpoints accept, and the single response format that every comparison returns. It applies to every engine (embedding model, local small language model, cloud LLM, OpenRouter) and every comparison mode (text vs text, LLM vs Wikipedia, LLM vs LLM).

It covers:

- the comparison request: sources, engines, strategy and options
- the comparison result: per-statement label, confidence, evidence, and which engine produced it
- diff categories, alignment mappings and disagreements between the compared texts, including across languages
- the document structure clients need to render results (headings, paragraphs, block quotes, lists, tables, images)
- usage and timing metadata
- the error format, including partial failure
- the versioning approach
- a machine-readable JSON Schema of all of the above (section 12)

It does not cover endpoint paths, rate-limit values, or MCP transport details. Those are specified separately.

## 2. Problems with the v1 responses

v1 has four comparison endpoints with four unrelated response models:

| Endpoint                                        | Response model                |
| ----------------------------------------------- | ----------------------------- |
| `POST /symmetry/v1/articles/compare`          | `CompareResponse`           |
| `POST /symmetry/v1/comparison/semantic`       | `ArticleComparisonResponse` |
| `POST /symmetry/v1/articles/compare-sections` | `SectionCompareResponse`    |
| `POST /symmetry/v1/wiki/paragraph-diff`       | `ParagraphDiffResponse`     |

Issues v2 must fix:

1. **No common shape.** A client must know which endpoint was called to read the result.
2. **Scores without meaning.** Results carry raw similarity numbers (cosine, Levenshtein) but no label saying what was found, no confidence, and no evidence.
3. **Weak engine identity.** Three of the four echo the requested `model_name`; `ParagraphDiffResponse` has none. None reports the engine type or provider.
4. **Failures that look like success.** `/comparison/semantic` returns `200` with empty lists when the engine is unavailable or returns nothing, which is indistinguishable from "no differences". `/articles/compare` returns `200` with an `error_message` field.
5. **Two sources only.** v1 always compares exactly two texts. LLM vs LLM must compare outputs from two or more models.

## 3. Design principles

1. **One shape for everything.** Every engine and every mode returns `ComparisonResponse` (section 5). Engines adapt to the schema, never the reverse.
2. **The API layer owns the schema.** MCP tools accept `ComparisonRequest` and return `ComparisonResponse` as their structured result, so REST and MCP clients see identical data. The schema does not depend on the transport (REST, MCP stdio, MCP Streamable HTTP).
3. **The client renders, the API structures.** The response carries the document structure (section 5, `Block`), so user interfaces do not have to re-parse text to show paragraphs, quotes or tables.
4. **Failure is explicit.** An empty result is never returned as success (section 8).
5. **Additive evolution.** Within v2, fields and enum values may be added, never removed or renamed (section 9).
6. **Conventions.** Field names are `snake_case`. Enums are lowercase strings. In responses, optional fields are always present, set to `null` when not applicable, so clients never have to check whether a key exists. Lists that are always computed (e.g. `statements`, `errors`) are never `null`, only empty. Lists that are optional detail (`word_diff`, `blocks`) are `null` when not computed or not requested, which is different from empty ("computed, nothing found").
7. **Deterministic order.** `statements` are ordered by source, then `index`. `alignments` are ordered by `source_ref` position, with unpaired `added` items last. This keeps responses diffable and contract tests stable.

**Prior art.** FActScore splits generated text into atomic facts and labels each one against a knowledge source such as Wikipedia, which is the model for per-statement labels here. DeepEval returns a score and a reason for each metric, which is the model for `confidence` plus `evidence`.

## 4. Request

All v2 comparison endpoints accept the same request body. An endpoint may fix `mode` (for example an LLM vs Wikipedia endpoint), in which case a conflicting `mode` value is rejected.

### `ComparisonRequest`

| Field        | Type                  | Default      | Notes                                                                                                 |
| ------------ | --------------------- | ------------ | ----------------------------------------------------------------------------------------------------- |
| `mode`     | enum                  | required     | `text_vs_text`, `llm_vs_wikipedia`, `llm_vs_llm`                                                |
| `sources`  | `SourceInput[]`     | required     | 2 or more                                                                                             |
| `prompt`   | string or null        | `null`     | The prompt given to every source with`generate_with`. Required if any source uses `generate_with` |
| `engines`  | string[]              | `[]`       | Ids of the engines that compare. Empty means the server default for the mode                          |
| `strategy` | string or null        | `null`     | Id of a strategy in the server's registry, e.g. `semantic_similarity`, `factual_consistency`. `null` means the server default for the mode |
| `options`  | `ComparisonOptions` | all defaults | See below                                                                                             |

### `SourceInput`

| Field             | Type            | Default  | Notes                                                                        |
| ----------------- | --------------- | -------- | ---------------------------------------------------------------------------- |
| `id`            | string          | required | Unique in the request; reused in the response                                |
| `kind`          | enum            | required | `text`, `document`, `wikipedia`, `llm_output`                        |
| `language`      | string or null  | `null` | ISO 639-1 code.`null` means detect, or for Wikipedia, take it from the URL |
| `text`          | string or null  | `null` | Literal content                                                              |
| `url`           | string or null  | `null` | Wikipedia article URL                                                        |
| `title`         | string or null  | `null` | Wikipedia article title (with`language`)                                   |
| `revision_id`   | integer or null | `null` | A specific Wikipedia revision.`null` means the latest                      |
| `generate_with` | string or null  | `null` | Engine id that generates this source from`prompt`                          |

`text` is plain text. `document` is text whose layout (blank-line paragraphs, Markdown headings, quotes, lists) the server parses into `blocks`.

### `ComparisonOptions`

| Field                    | Type               | Default   | Notes                                                                                                                        |
| ------------------------ | ------------------ | --------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `similarity_threshold` | float 0–1 or null | `null`  | Pairing and labelling threshold for similarity-based engines (section 6).`null` means the server's configured default      |
| `partial_threshold`    | float 0–1 or null | `null`  | Optional lower band for`partial` (section 6). Must be below `similarity_threshold`                                       |
| `direction`            | enum or null       | `null`  | `both` or `first_to_second` (section 6). `null` means `first_to_second` for `llm_vs_wikipedia`, otherwise `both` |
| `pivot_language`       | string or null     | `null`  | Translate both texts to this language before comparing (section 7).`null` means compare directly                           |
| `include_source_text`  | boolean            | `true`  | When`false`, `Source.text` is `null` and spans are still valid against the original                                    |
| `include_blocks`       | boolean            | `true`  | When`false`, `Source.blocks` and `Statement.block_id` are `null`                                                     |
| `include_evidence`     | boolean            | `true`  | When`false`, every `evidence` list is empty                                                                              |
| `include_word_diff`    | boolean            | `false` | When`true`, paired alignments carry `word_diff` where possible (section 7)                                               |
| `timeout_seconds`      | number or null     | `null`  | Per-engine time limit.`null` means the server default                                                                      |

### Validation rules

Requests that break these rules are rejected with `invalid_request` (`422`), naming the failing fields in `details`.

1. At least two sources, with unique `id` values.
2. Each source sets exactly one of `text`, `url`, `title`, `generate_with`.
3. `url`, `title` and `revision_id` are only allowed for `kind: wikipedia`. `url` must be a Wikipedia article URL. **The server never fetches arbitrary URLs**; other documents are sent as `text`. This prevents the API from being used to reach internal or third-party addresses (server-side request forgery).
4. `generate_with` is only allowed for `kind: llm_output`, and requires `prompt`.
5. Sources must match the mode: `llm_vs_wikipedia` takes exactly one `llm_output` and one `wikipedia` source; `llm_vs_llm` takes two or more `llm_output` sources; `text_vs_text` takes two or more `text` or `document` sources.
6. If both thresholds are set, `partial_threshold` must be lower than `similarity_threshold`.

Unknown engine ids are rejected with `unsupported_engine`. A strategy id that is not in the registry, or an engine that cannot serve the requested strategy (section 6), is rejected with `unsupported_strategy`. Strategies are an open set: registering a new one does not change this schema or the routes.

## 5. Response envelope

### `ComparisonResponse`

| Field           | Type              | Notes                                                           |
| --------------- | ----------------- | --------------------------------------------------------------- |
| `api_version` | string            | e.g.`"2.0"`; the minor number increases with additive changes |
| `request_id`  | string            | Also sent as the`X-Request-ID` response header                |
| `status`      | enum              | `success`, `partial` (some work failed, see `errors`)     |
| `mode`        | enum              | As requested                                                    |
| `strategy`    | string            | Id of the strategy actually used                                |
| `prompt`      | string or null    | Echo of the request prompt                                      |
| `duration_ms` | integer           | Total server time for the request                               |
| `sources`     | `Source[]`      | Everything that was compared, in request order                  |
| `results`     | `Result[]`      | One per engine per pair of sources                              |
| `errors`      | `ErrorDetail[]` | Empty when`status` is `success`                             |

A fully failed request does not return this object; it returns `ErrorResponse` (section 8).

### `Source`

| Field            | Type                    | Notes                                                                                                                                          |
| ---------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`           | string                  | Same as in the request                                                                                                                         |
| `kind`         | enum                    | `text`, `document`, `wikipedia`, `llm_output`                                                                                          |
| `label`        | string or null          | Human-readable name, e.g. the article title or model name                                                                                      |
| `language`     | string or null          | ISO 639-1 code actually used                                                                                                                   |
| `url`          | string or null          | Where the text came from                                                                                                                       |
| `revision_id`  | integer or null         | The Wikipedia revision actually compared                                                                                                       |
| `license`      | string or null          | Content licence, e.g.`CC BY-SA 4.0` for Wikipedia                                                                                            |
| `attribution`  | string or null          | Attribution text that must accompany any reuse of the content                                                                                  |
| `generated_by` | `GeneratedBy` or null | For`llm_output` produced by the server: which engine produced it                                                                             |
| `text`         | string or null          | The exact original text that offsets refer to (section 6).`null` if the source could not be obtained or `include_source_text` is `false` |
| `blocks`       | `Block[]` or null     | Document structure for rendering (below).`null` for plain text or when `include_blocks` is `false`                                       |

Wikipedia content is licensed CC BY-SA. Any client that displays Wikipedia text or evidence must show `attribution` (title, link and licence) alongside it.

`generated_by` describes who **wrote** a source. `Result.engine` describes who **compared** the sources. In LLM vs LLM these are different models and must not be confused. If a generating engine fails, its source stays in `sources` with `text: null`, so clients can still show every output that was requested (section 8, rule 2).

### `GeneratedBy`

| Field         | Type              | Notes                          |
| ------------- | ----------------- | ------------------------------ |
| `engine_id` | string            | Engine that generated the text |
| `provider`  | string or null    | e.g.`ollama`, `openrouter` |
| `model`     | string            | Model name as used             |
| `usage`     | `Usage` or null | Cost of generating this source |

### `Result`

| Field                   | Type                 | Notes                                                                                              |
| ----------------------- | -------------------- | -------------------------------------------------------------------------------------------------- |
| `source_ids`          | `[string, string]` | The pair compared, e.g.`["a", "b"]`. With 3 sources there are 3 pairs                            |
| `engine`              | `Engine`           | Who produced this result                                                                           |
| `status`              | enum                 | `ok`, `failed`                                                                                 |
| `direction`           | enum                 | `both` or `first_to_second`, as applied (section 6)                                            |
| `comparison_language` | string or null       | Pivot language if texts were translated before comparing;`null` if compared directly (section 7) |
| `overall_score`       | float 0–1 or null   | Summary score (section 6).`null` when `failed`                                                 |
| `score_basis`         | enum or null         | What the scores mean (section 6).`null` when `failed`                                          |
| `statements`          | `Statement[]`      | Empty when`failed`                                                                               |
| `alignments`          | `Alignment[]`      | Empty when`failed`                                                                               |
| `usage`               | `Usage` or null    | Cost of producing this result                                                                      |

### `Engine`

| Field             | Type           | Notes                                                                                         |
| ----------------- | -------------- | --------------------------------------------------------------------------------------------- |
| `id`            | string         | Stable id from the engine registry                                                            |
| `type`          | enum           | `embedding`, `local_slm`, `cloud_llm`, `openrouter`                                   |
| `provider`      | string or null | e.g.`huggingface`, `ollama`, `openrouter`                                               |
| `model`         | string         | Model name as used                                                                            |
| `fallback_from` | string or null | If this engine stood in for another (e.g. offline fallback), the id of the engine it replaced |

### `Usage`

| Field                  | Type            | Notes                                                             |
| ---------------------- | --------------- | ----------------------------------------------------------------- |
| `latency_ms`         | integer         | Wall-clock time spent in the engine                               |
| `input_tokens`       | integer or null | `null` for engines without tokens (e.g. embedding models)       |
| `output_tokens`      | integer or null | As above                                                          |
| `estimated_cost_usd` | float or null   | Provider cost estimate;`null` for local engines or when unknown |

### `Block` (document structure)

Blocks describe how a source is laid out, so a client can render paragraphs, quotes, tables and images, and place each statement inside them. Sentences are the statements themselves (section 6); blocks are the containers around them.

| Field           | Type             | Notes                                                                                        |
| --------------- | ---------------- | -------------------------------------------------------------------------------------------- |
| `id`          | string           | e.g.`b-p0`                                                                                 |
| `type`        | enum             | `heading`, `paragraph`, `blockquote`, `list`, `table`, `image`                   |
| `span`        | `Span` or null | Location in`Source.text`; `null` for blocks with no text (e.g. an image without caption) |
| `section_ref` | string or null   | Title of the section containing the block                                                    |
| `level`       | integer or null  | Heading level (1 = top);`null` for other types                                             |
| `url`         | string or null   | Image location;`null` for other types                                                      |
| `caption`     | string or null   | Image or table caption                                                                       |

Blocks are listed in document order and do not overlap. A table's `span` covers its plain-text rendering; cell-level table structure is not part of this version.

## 6. Statements: label, confidence, evidence

A statement is one sentence-level claim taken from one source of the pair. Every statement id used in an alignment or in evidence must appear in the same result's `statements`. Statement ids are unique within a result.

### `Statement`

| Field                     | Type               | Notes                                                                                                                                                                         |
| ------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                    | string             | e.g.`a-0` (source id + index)                                                                                                                                               |
| `source_id`             | string             | One of the result's`source_ids`                                                                                                                                             |
| `index`                 | integer            | 0-based position in the source                                                                                                                                                |
| `text`                  | string             | The statement text, in the original language                                                                                                                                  |
| `translated_text`       | string or null     | The text actually compared, when the result has a`comparison_language`; otherwise `null`                                                                                  |
| `span`                  | `Span`           | Location in the original`Source.text` (rules below)                                                                                                                         |
| `section_ref`           | string or null     | Section title, for structured sources such as Wikipedia                                                                                                                       |
| `block_id`              | string or null     | The`Block` containing the statement; `null` when the source has no blocks                                                                                                 |
| `label`                 | enum or null       | Outcome compared with the other source in the pair.`null` means not judged (see Direction)                                                                                  |
| `confidence`            | float 0–1 or null | The engine's certainty in`label`. Only set when `score_basis` is `model_reported`; `null` otherwise, and always `null` for `unverifiable` and unjudged statements |
| `best_match_similarity` | float 0–1 or null | Highest similarity to any statement in the other source, when the engine computes one                                                                                         |
| `evidence`              | `Evidence[]`     | Why the engine chose the label. May be empty                                                                                                                                  |

### `Span`

| Field     | Type    | Notes              |
| --------- | ------- | ------------------ |
| `start` | integer | 0-based, inclusive |
| `end`   | integer | Exclusive          |

Offsets count Unicode code points (Python `str` indexing) in the original `Source.text`, so `Source.text[start:end] == Statement.text`. They always refer to the original text, even when the comparison used a translation. JavaScript clients must convert, because JS strings index by UTF-16 code units and differ for characters outside the Basic Multilingual Plane.

### `label`

| Value            | Meaning                                              |
| ---------------- | ---------------------------------------------------- |
| `supported`    | The other source states the same thing               |
| `partial`      | The other source overlaps but differs in some detail |
| `contradicted` | The other source states something incompatible       |
| `not_found`    | The other source does not mention it                 |
| `unverifiable` | The engine could not reach a decision                |

`supported`, `contradicted` and `not_found` are the outcomes required for LLM vs Wikipedia. `partial` and `unverifiable` exist so that an engine is never forced to pick one of those three when neither fits.

### `score_basis` and which labels an engine may emit

Engines measure certainty differently, so raw numbers are not comparable across engines. Each result declares its basis, which also limits the labels it may use:

| `score_basis`       | Typical engine                               | Labels it may emit                        | `confidence`               |
| --------------------- | -------------------------------------------- | ----------------------------------------- | ---------------------------- |
| `cosine_similarity` | `embedding`                                | `supported`, `partial`, `not_found` | `null`                     |
| `rule_based`        | heuristics (thresholds, edit distance)       | `supported`, `partial`, `not_found` | `null`                     |
| `model_reported`    | `local_slm`, `cloud_llm`, `openrouter` | all five                                  | set (except`unverifiable`) |

**Labelling rule for similarity-based engines.** With `s` = `best_match_similarity`, `T` = `similarity_threshold`, `P` = `partial_threshold`:

- `s >= T` → `supported`
- `P` is set and `P <= s < T` → `partial`
- otherwise → `not_found`

**Similarity is not truth.** Embedding and rule-based engines never emit `contradicted`: "It is 400 metres tall" and "It is 330 metres tall" are highly similar, so a similarity engine labels that pair `supported`. For these engines, `supported` means "the other source says something very similar", not "the other source agrees". Detecting contradictions requires the `factual_consistency` strategy, which only `model_reported` engines can serve. A request combining `factual_consistency` with an embedding or rule-based engine is rejected with `unsupported_strategy`.

### `overall_score`

| `score_basis`                       | Definition                                                                                                                   |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `cosine_similarity`, `rule_based` | Mean`best_match_similarity` over judged statements                                                                         |
| `model_reported`                    | Share of judged statements labelled`supported`, ignoring `unverifiable`. `null` if every statement is `unverifiable` |

### Direction

| `direction`       | Which statements are judged                                                                                                                                                                                                                      |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `both`            | Every statement in both sources is labelled against the other. Needed when gaps in either text matter: text vs text, and LLM vs LLM                                                                                                              |
| `first_to_second` | Only statements in the first source are labelled. Statements from the second source appear only when an alignment or evidence refers to them, with`label`, `confidence` and `best_match_similarity` set to `null` and empty `evidence` |

`first_to_second` is the default for LLM vs Wikipedia: the question is whether the LLM's claims hold, and labelling every sentence of the article would roughly double the response size.

### `Evidence`

| Field            | Type           | Notes                                                                 |
| ---------------- | -------------- | --------------------------------------------------------------------- |
| `kind`         | enum           | `counterpart_statement`, `wikipedia_passage`, `model_rationale` |
| `source_id`    | string or null | Source the evidence comes from;`null` for `model_rationale`       |
| `statement_id` | string or null | Matching statement, if any                                            |
| `text`         | string         | Quoted passage, or the model's explanation                            |
| `url`          | string or null | Link, e.g. to the Wikipedia revision                                  |

Evidence quoted from Wikipedia falls under the source's `license` and `attribution`.

## 7. Alignments, disagreements and cross-language comparison

An alignment links a statement in the first source of the pair to one in the second, or marks a statement that has no partner.

### `Alignment`

| Field          | Type                    | Notes                                                                          |
| -------------- | ----------------------- | ------------------------------------------------------------------------------ |
| `id`         | string                  | Unique within the result                                                       |
| `source_ref` | string or null          | Statement id from`source_ids[0]`; `null` for `added`                     |
| `target_ref` | string or null          | Statement id from`source_ids[1]`; `null` for `missing`                   |
| `category`   | enum                    | See below                                                                      |
| `similarity` | float 0–1 or null      | `null` when unpaired, or when the engine does not compute a similarity       |
| `word_diff`  | `WordToken[]` or null | Word-level detail for paired statements;`null` unless requested and possible |

### `category`

| Value        | Pairing                | Meaning                                                        |
| ------------ | ---------------------- | -------------------------------------------------------------- |
| `equal`    | statement ↔ statement | The first statement is labelled`supported`                   |
| `modified` | statement ↔ statement | The first statement is labelled`partial`, `contradicted` or `unverifiable` |
| `missing`  | statement ↔ null      | Only in the first source                                       |
| `added`    | null ↔ statement      | Only in the second source                                      |

`category` describes the structural diff; `label` describes the outcome. A pair can be structurally matched (`modified`) while the statements contradict each other.

### `WordToken`

Same token model as v1 `paragraph-diff`, so the existing word-diff algorithm can be reused unchanged:

| Field    | Type           | Notes                                          |
| -------- | -------------- | ---------------------------------------------- |
| `type` | enum           | `equal`, `insert`, `delete`, `replace` |
| `text` | string or null | Set for`equal`, `insert`, `delete`       |
| `old`  | string or null | Set for`replace`                             |
| `new`  | string or null | Set for`replace`                             |

### Disagreements

The disagreements between two sources (the "highlighted disagreements" of LLM vs LLM) are, by definition:

- alignments with `category` `modified`, `missing` or `added`, and
- statements labelled `contradicted`, `partial` or `not_found`.

Clients highlight them using each statement's `span`. They are not repeated in a separate list, so they cannot drift out of sync with the alignments.

### Cross-language comparison

Sources may be in different languages; comparing Wikipedia articles across languages is Symmetry's original use case.

- **Direct comparison.** Multilingual engines (e.g. LaBSE embeddings, multilingual LLMs) compare the original texts. `comparison_language` is `null` and `translated_text` is `null`.
- **Pivot translation.** When `pivot_language` is requested, or the engine needs it, both texts are translated first. `comparison_language` names the pivot language and each statement's `translated_text` holds the text actually compared.
- **Spans** always point into the original text, so clients highlight the source the user is reading.
- **`word_diff`** is only meaningful within one language. It is computed on `translated_text` when present, on the original text when both sources share a language, and is `null` otherwise.

## 8. Errors and partial failure

### `ErrorDetail`

| Field         | Type           | Notes                                                                                                                        |
| ------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `code`      | enum           | Stable machine-readable code (table below)                                                                                   |
| `message`   | string         | Human-readable; safe to show to users                                                                                        |
| `scope`     | enum           | `request`, `source`, `engine`                                                                                          |
| `source_id` | string or null | Set when`scope` is `source`                                                                                              |
| `engine_id` | string or null | Set when`scope` is `engine`; also set with `scope: source` when the source failed because its generating engine failed |
| `retryable` | boolean        | Whether the same request could succeed later                                                                                 |
| `details`   | object or null | Extra structured context. Never stack traces                                                                                 |

### `ErrorResponse` (whole request failed)

| Field           | Type                             |
| --------------- | -------------------------------- |
| `api_version` | string                           |
| `request_id`  | string                           |
| `status`      | `"failed"`                     |
| `errors`      | `ErrorDetail[]` (at least one) |

### Codes and HTTP status

| Code                     | HTTP status when fatal | Retryable |
| ------------------------ | ---------------------- | --------- |
| `invalid_request`      | 422                    | no        |
| `unsupported_engine`   | 422                    | no        |
| `unsupported_strategy` | 422                    | no        |
| `source_not_found`     | 404                    | no        |
| `rate_limited`         | 429                    | yes       |
| `engine_bad_output`    | 502                    | yes       |
| `engine_unavailable`   | 503                    | yes       |
| `engine_timeout`       | 504                    | yes       |
| `internal_error`       | 500                    | yes       |

### Rules

1. **Everything succeeded:** `200`, `status: "success"`, `errors: []`.
2. **Some work failed:** `200`, `status: "partial"`. Each failed comparing engine still appears in `results` with `status: "failed"`, and each failure has an entry in `errors`. If a source could not be obtained (e.g. in LLM vs LLM one of three models did not answer), it stays in `sources` with `text: null`, results involving it are omitted, and an error with `scope: "source"`, its `source_id` and the generating `engine_id` is listed. The request still succeeds as long as at least one result is usable.
3. **Nothing usable:** `ErrorResponse` with the HTTP status from the table. If all failures share one code, use that code's status; otherwise use `502`.
4. **Request validation** errors also use `ErrorResponse` (`422`, `invalid_request`), with the failing field paths in `details`. This replaces FastAPI's default `{"detail": [...]}` body for v2 only.
5. **`429`** responses include `Retry-After`. Rate-limit state is reported in `RateLimit-Limit`, `RateLimit-Remaining` and `RateLimit-Reset` headers.
6. `200` with `status: "partial"` is used instead of `207 Multi-Status`: it is simpler for HTTP clients, MCP clients and OpenAPI tooling.

**Implementation note.** FastAPI exception handlers are registered app-wide, and v1 already has global handlers. v2 error handling must be scoped to v2 routes (for example, a v2 sub-application mounted at `/symmetry/v2`) so that v1 error bodies do not change.

## 9. Versioning

**Decision: version in the URL path (`/symmetry/v2/...`).**

| Criterion                                        | URL path        | Header (`Accept` / custom) |
| ------------------------------------------------ | --------------- | ---------------------------- |
| Consistent with existing`/symmetry/v1`         | yes             | no                           |
| Visible in logs, browser, curl, Swagger UI       | yes             | no                           |
| Separate OpenAPI document per version            | straightforward | awkward                      |
| Configuration needed in each client and MCP tool | base URL only   | header on every call         |
| Resource URLs stay the same across versions      | no              | yes                          |

Rules:

1. v1 remains available and unchanged while v2 is introduced.
2. Within v2, only additive changes: new optional fields, new endpoints, new enum values. **Clients must tolerate unknown fields and unknown enum values**, otherwise adding a value would break them.
3. Removing or renaming anything, or changing a field's meaning, requires v3.
4. Every response carries `api_version`.
5. Before v1 is retired, its responses carry `Deprecation` and `Sunset` headers.

## 10. Examples

Values are illustrative.

### 10.1 Request: LLM vs LLM

Two models answer the same prompt; a third model's answer is requested too. An embedding engine compares them.

```json
{
  "mode": "llm_vs_llm",
  "prompt": "When was the Eiffel Tower completed?",
  "sources": [
    {"id": "a", "kind": "llm_output", "generate_with": "model-a"},
    {"id": "b", "kind": "llm_output", "generate_with": "model-b"},
    {"id": "c", "kind": "llm_output", "generate_with": "model-c"}
  ],
  "engines": ["labse"],
  "strategy": "semantic_similarity",
  "options": {"similarity_threshold": 0.65}
}
```

### 10.2 Response: LLM vs LLM, one generating model failed

`model-c` was unavailable, so source `c` has no text and only the `a`–`b` pair was compared. `b-1` exists only in `b`, so it is a disagreement (`added`, `not_found`).

```json
{
  "api_version": "2.0",
  "request_id": "req_41c2e8",
  "status": "partial",
  "mode": "llm_vs_llm",
  "strategy": "semantic_similarity",
  "prompt": "When was the Eiffel Tower completed?",
  "duration_ms": 2140,
  "sources": [
    {
      "id": "a", "kind": "llm_output", "label": "model-a", "language": "en",
      "url": null, "revision_id": null, "license": null, "attribution": null,
      "generated_by": {"engine_id": "model-a", "provider": "example-provider", "model": "model-a",
                       "usage": {"latency_ms": 900, "input_tokens": 12, "output_tokens": 11, "estimated_cost_usd": 0.0001}},
      "text": "The Eiffel Tower was completed in 1889.",
      "blocks": null
    },
    {
      "id": "b", "kind": "llm_output", "label": "model-b", "language": "en",
      "url": null, "revision_id": null, "license": null, "attribution": null,
      "generated_by": {"engine_id": "model-b", "provider": "openrouter", "model": "model-b",
                       "usage": {"latency_ms": 1300, "input_tokens": 12, "output_tokens": 19, "estimated_cost_usd": 0.0002}},
      "text": "The tower was completed in 1889. It was built for the 1889 World's Fair.",
      "blocks": null
    },
    {
      "id": "c", "kind": "llm_output", "label": "model-c", "language": null,
      "url": null, "revision_id": null, "license": null, "attribution": null,
      "generated_by": {"engine_id": "model-c", "provider": "ollama", "model": "model-c", "usage": null},
      "text": null,
      "blocks": null
    }
  ],
  "results": [
    {
      "source_ids": ["a", "b"],
      "engine": {"id": "labse", "type": "embedding", "provider": "huggingface", "model": "sentence-transformers/LaBSE", "fallback_from": null},
      "status": "ok",
      "direction": "both",
      "comparison_language": null,
      "overall_score": 0.76,
      "score_basis": "cosine_similarity",
      "statements": [
        {
          "id": "a-0", "source_id": "a", "index": 0,
          "text": "The Eiffel Tower was completed in 1889.", "translated_text": null,
          "span": {"start": 0, "end": 39}, "section_ref": null, "block_id": null,
          "label": "supported", "confidence": null, "best_match_similarity": 0.93,
          "evidence": [
            {"kind": "counterpart_statement", "source_id": "b", "statement_id": "b-0",
             "text": "The tower was completed in 1889.", "url": null}
          ]
        },
        {
          "id": "b-0", "source_id": "b", "index": 0,
          "text": "The tower was completed in 1889.", "translated_text": null,
          "span": {"start": 0, "end": 32}, "section_ref": null, "block_id": null,
          "label": "supported", "confidence": null, "best_match_similarity": 0.93,
          "evidence": [
            {"kind": "counterpart_statement", "source_id": "a", "statement_id": "a-0",
             "text": "The Eiffel Tower was completed in 1889.", "url": null}
          ]
        },
        {
          "id": "b-1", "source_id": "b", "index": 1,
          "text": "It was built for the 1889 World's Fair.", "translated_text": null,
          "span": {"start": 33, "end": 72}, "section_ref": null, "block_id": null,
          "label": "not_found", "confidence": null, "best_match_similarity": 0.41,
          "evidence": []
        }
      ],
      "alignments": [
        {"id": "m-0", "source_ref": "a-0", "target_ref": "b-0", "category": "equal", "similarity": 0.93, "word_diff": null},
        {"id": "m-1", "source_ref": null, "target_ref": "b-1", "category": "added", "similarity": null, "word_diff": null}
      ],
      "usage": {"latency_ms": 85, "input_tokens": null, "output_tokens": null, "estimated_cost_usd": null}
    }
  ],
  "errors": [
    {
      "code": "engine_unavailable", "message": "The engine that generates this source is not available.",
      "scope": "source", "source_id": "c", "engine_id": "model-c",
      "retryable": true, "details": null
    }
  ]
}
```

### 10.3 Response: LLM vs Wikipedia, one comparing engine failed

Two engines check an LLM answer against Wikipedia. The cloud LLM answered; the OpenRouter engine timed out. The default direction for this mode is `first_to_second`, so Wikipedia statements appear only where they are referenced, unjudged.

```json
{
  "api_version": "2.0",
  "request_id": "req_7f3a9c",
  "status": "partial",
  "mode": "llm_vs_wikipedia",
  "strategy": "factual_consistency",
  "prompt": null,
  "duration_ms": 31250,
  "sources": [
    {
      "id": "a", "kind": "llm_output", "label": "Model answer", "language": "en",
      "url": null, "revision_id": null, "license": null, "attribution": null,
      "generated_by": null,
      "text": "The Eiffel Tower was completed in 1889. It is 400 metres tall.",
      "blocks": null
    },
    {
      "id": "b", "kind": "wikipedia", "label": "Eiffel Tower", "language": "en",
      "url": "https://en.wikipedia.org/wiki/Eiffel_Tower", "revision_id": 1234567890,
      "license": "CC BY-SA 4.0",
      "attribution": "From the Wikipedia article \"Eiffel Tower\" (revision 1234567890), licensed under CC BY-SA 4.0.",
      "generated_by": null,
      "text": "The Eiffel Tower was completed in 1889. The tower is 330 metres tall.",
      "blocks": [
        {"id": "b-p0", "type": "paragraph", "span": {"start": 0, "end": 69}, "section_ref": "Introduction",
         "level": null, "url": null, "caption": null}
      ]
    }
  ],
  "results": [
    {
      "source_ids": ["a", "b"],
      "engine": {"id": "cloud-default", "type": "cloud_llm", "provider": "example-provider", "model": "example-judge", "fallback_from": null},
      "status": "ok",
      "direction": "first_to_second",
      "comparison_language": null,
      "overall_score": 0.5,
      "score_basis": "model_reported",
      "statements": [
        {
          "id": "a-0", "source_id": "a", "index": 0,
          "text": "The Eiffel Tower was completed in 1889.", "translated_text": null,
          "span": {"start": 0, "end": 39}, "section_ref": null, "block_id": null,
          "label": "supported", "confidence": 0.96, "best_match_similarity": 0.99,
          "evidence": [
            {"kind": "wikipedia_passage", "source_id": "b", "statement_id": "b-0",
             "text": "The Eiffel Tower was completed in 1889.", "url": "https://en.wikipedia.org/wiki/Eiffel_Tower"}
          ]
        },
        {
          "id": "a-1", "source_id": "a", "index": 1,
          "text": "It is 400 metres tall.", "translated_text": null,
          "span": {"start": 40, "end": 62}, "section_ref": null, "block_id": null,
          "label": "contradicted", "confidence": 0.91, "best_match_similarity": 0.74,
          "evidence": [
            {"kind": "wikipedia_passage", "source_id": "b", "statement_id": "b-1",
             "text": "The tower is 330 metres tall.", "url": "https://en.wikipedia.org/wiki/Eiffel_Tower"},
            {"kind": "model_rationale", "source_id": null, "statement_id": null,
             "text": "The reference gives the height as 330 metres, not 400.", "url": null}
          ]
        },
        {
          "id": "b-0", "source_id": "b", "index": 0,
          "text": "The Eiffel Tower was completed in 1889.", "translated_text": null,
          "span": {"start": 0, "end": 39}, "section_ref": "Introduction", "block_id": "b-p0",
          "label": null, "confidence": null, "best_match_similarity": null,
          "evidence": []
        },
        {
          "id": "b-1", "source_id": "b", "index": 1,
          "text": "The tower is 330 metres tall.", "translated_text": null,
          "span": {"start": 40, "end": 69}, "section_ref": "Introduction", "block_id": "b-p0",
          "label": null, "confidence": null, "best_match_similarity": null,
          "evidence": []
        }
      ],
      "alignments": [
        {"id": "m-0", "source_ref": "a-0", "target_ref": "b-0", "category": "equal", "similarity": 0.99, "word_diff": null},
        {"id": "m-1", "source_ref": "a-1", "target_ref": "b-1", "category": "modified", "similarity": 0.74, "word_diff": null}
      ],
      "usage": {"latency_ms": 2900, "input_tokens": 410, "output_tokens": 160, "estimated_cost_usd": 0.0021}
    },
    {
      "source_ids": ["a", "b"],
      "engine": {"id": "openrouter-default", "type": "openrouter", "provider": "openrouter", "model": "example-model-2", "fallback_from": null},
      "status": "failed",
      "direction": "first_to_second",
      "comparison_language": null,
      "overall_score": null,
      "score_basis": null,
      "statements": [],
      "alignments": [],
      "usage": {"latency_ms": 30000, "input_tokens": null, "output_tokens": null, "estimated_cost_usd": null}
    }
  ],
  "errors": [
    {
      "code": "engine_timeout", "message": "The engine did not respond in time.",
      "scope": "engine", "source_id": null, "engine_id": "openrouter-default",
      "retryable": true, "details": {"timeout_seconds": 30}
    }
  ]
}
```

## 11. Mapping from v1

| v1                                                               | v2                                                                                               |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `missing_info[]`                                               | Statements from the first source with`label: not_found`; alignments with `category: missing` |
| `extra_info[]`                                                 | Statements from the second source with`label: not_found`; alignments with `category: added`  |
| `MissingInfo.similarity_score`, `ExtraInfo.similarity_score` | `statements[].best_match_similarity`                                                           |
| `ParagraphDiff.similarity_score`                               | `alignments[].similarity`                                                                      |
| `levenshtein_score`                                            | Not exposed; an engine may use it internally (`score_basis: rule_based`)                       |
| `section_similarity`                                           | No direct equivalent; statements are grouped by`section_ref`                                   |
| `overall_similarity`                                           | `results[].overall_score`                                                                      |
| `status: matched / missing_in_target / added_in_target`        | `category: equal or modified / missing / added`                                                |
| `model_name`                                                   | `results[].engine.model`                                                                       |
| `similarity_threshold`                                         | Request option`options.similarity_threshold`                                                   |
| `error_message`                                                | `errors[]` plus a real HTTP status                                                             |
| `word_diff` tokens                                             | `alignments[].word_diff` (same token model)                                                    |
| `comparisons[].details`                                        | Replaced by alignments and evidence                                                              |

Granularity changes: v1 `compare-sections` compares **paragraphs**; v2 compares **statements** (sentence-level). A v1-compatible view can be rebuilt by grouping statements by `section_ref`.

## 12. Machine-readable schema

[`api-v2-schema.json`](./api-v2-schema.json) is the JSON Schema (draft 2020-12) of `ComparisonRequest`, `ComparisonResponse` and `ErrorResponse`. It is the contract: the server's models must produce JSON that validates against it, and contract tests run every v2 response through it.

- It has no root type. Validate each payload against its definition: `#/$defs/ComparisonRequest`, `#/$defs/ComparisonResponse` or `#/$defs/ErrorResponse`.
- It marks which fields are required. In responses every field is required, nullable ones included, per principle 6.
- It sets `additionalProperties: false`, so the server cannot emit undocumented fields. **This strictness applies to the server only.** Clients must not validate this strictly (section 9, rule 2). For `ComparisonRequest` it also means that requests with unknown fields are rejected with `invalid_request`.
- Section-level rules that a JSON Schema cannot express (unique ids, references that resolve, spans that match the text, labels allowed per `score_basis`) are checked by contract tests in addition to the schema.
