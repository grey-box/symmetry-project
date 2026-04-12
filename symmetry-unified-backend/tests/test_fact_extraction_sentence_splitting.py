from app.ai import fact_extraction


def test_spacy_sentence_segmentation_handles_abbreviations():
    text = "Mr. Smith traveled to the U.S.A. and visited several cities. He was happy."
    sentences = fact_extraction._split_into_sentences(text)

    assert sentences == [
        "Mr. Smith traveled to the U.S.A. and visited several cities.",
        "He was happy.",
    ]


def test_spacy_sentence_segmentation_preserves_single_sentence():
    text = "This is a single sentence without abbreviations."
    sentences = fact_extraction._split_into_sentences(text)

    assert sentences == ["This is a single sentence without abbreviations."]
