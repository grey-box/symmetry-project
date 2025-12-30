import json
import sys
from refine_compare import semantic_compare
import csv


def read_text_file(filepath):
    """Read and return the contents of a text file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        sys.exit(1)


def align_sentences_semantically(original_text, translated_text, source_lang, target_lang, sim_threshold=0.75):
    """
    Use semantic comparison to get sentence pairs from both texts.
    Returns the full comparison result including sentences and leftover info.
    """
    result = semantic_compare(
        original_blob=original_text,
        translated_blob=translated_text,
        source_language=source_lang,
        target_language=target_lang,
        sim_threshold=sim_threshold
    )

    if not result["success"]:
        print("Warning: Semantic comparison was not fully successful")
        print("Continuing with available data...")

    return result


def create_qna_pairs(original_sentences, translated_sentences, source_lang, target_lang):
    """
    Create QnA pairs from original and translated sentences.
    Returns a list of QnA dictionaries with:
    - Individual sentence pairs (1:1)
    - Batched sentence pairs (10:10)
    - Both directions (original->translated and translated->original)
    Optimized to process each sentence only once.
    """
    qna_dataset = []

    # Determine the minimum length to avoid index errors
    min_length = min(len(original_sentences), len(translated_sentences))

    # Process all individual sentences in one loop
    for i in range(min_length):
        # Original -> Translated
        qna_dataset.append({
            "question": f"Translate this article from {source_lang} to {target_lang}: {original_sentences[i]}",
            "answer": translated_sentences[i],
            "type": "single_sentence",
            "direction": f"{source_lang}_to_{target_lang}",
            "index": i
        })

        # Translated -> Original (Reverse)
        qna_dataset.append({
            "question": f"Translate this article from {target_lang} to {source_lang}: {translated_sentences[i]}",
            "answer": original_sentences[i],
            "type": "single_sentence",
            "direction": f"{target_lang}_to_{source_lang}",
            "index": i
        })

    # Process batched sentences
    batch_size = 10
    for i in range(0, min_length, batch_size):
        end_idx = min(i + batch_size, min_length)

        # Combine sentences once
        original_batch = " ".join(original_sentences[i:end_idx])
        translated_batch = " ".join(translated_sentences[i:end_idx])

        # Original -> Translated
        qna_dataset.append({
            "question": f"Translate this article from {source_lang} to {target_lang}: {original_batch}",
            "answer": translated_batch,
            "type": "batch_sentences",
            "direction": f"{source_lang}_to_{target_lang}",
            "batch_start": i,
            "batch_end": end_idx,
            "batch_size": end_idx - i
        })

        # Translated -> Original (Reverse) - reuse the same batch strings
        qna_dataset.append({
            "question": f"Translate this article from {target_lang} to {source_lang}: {translated_batch}",
            "answer": original_batch,
            "type": "batch_sentences",
            "direction": f"{target_lang}_to_{source_lang}",
            "batch_start": i,
            "batch_end": end_idx,
            "batch_size": end_idx - i
        })

    return qna_dataset


def create_leftover_json(comparison_result, source_lang, target_lang, output_file="leftover_sentences.json"):
    """
    Create a JSON file containing sentences that didn't pass the similarity threshold.
    No duplicates - each leftover sentence appears only once.
    """
    leftover_data = {
        "metadata": {
            "source_language": source_lang,
            "target_language": target_lang,
            "description": "Sentences that did not meet the similarity threshold"
        },
        "missing_from_translation": {
            "description": "Original sentences missing or poorly translated",
            "count": len(comparison_result["missing_info"]),
            "sentences": [
                {
                    "index": idx,
                    "text": sent
                }
                for idx, sent in zip(comparison_result["missing_info_indices"], comparison_result["missing_info"])
            ]
        },
        "extra_in_translation": {
            "description": "Translated sentences not found in original or added content",
            "count": len(comparison_result["extra_info"]),
            "sentences": [
                {
                    "index": idx,
                    "text": sent
                }
                for idx, sent in zip(comparison_result["extra_info_indices"], comparison_result["extra_info"])
            ]
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(leftover_data, f, ensure_ascii=False, indent=2)

    print(f"✓ Created leftover sentences JSON: {output_file}")
    print(f"  - Missing from translation: {leftover_data['missing_from_translation']['count']} sentences")
    print(f"  - Extra in translation: {leftover_data['extra_in_translation']['count']} sentences")

    return leftover_data


def create_rag_csv(original_sentences, translated_sentences, missing_indices, extra_indices,
                   source_lang, target_lang, output_file="rag_aligned_pairs.csv"):
    """
    Create a CSV file with aligned sentence pairs that passed the threshold.
    Only includes sentences that are semantically aligned (above threshold).
    Format: original_text, translated_text
    """
    # Create sets of indices to exclude
    missing_set = set(missing_indices)
    extra_set = set(extra_indices)

    # Determine the minimum length
    min_length = min(len(original_sentences), len(translated_sentences))

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([f'original_text_{source_lang}', f'translated_text_{target_lang}'])

        # Write only aligned pairs (sentences that passed the threshold)
        aligned_count = 0
        for i in range(min_length):
            # Only include if neither sentence is in the missing/extra lists
            if i not in missing_set and i not in extra_set:
                writer.writerow([original_sentences[i], translated_sentences[i]])
                aligned_count += 1

    print(f"✓ Created RAG CSV file: {output_file}")
    print(f"  - Aligned sentence pairs: {aligned_count}")

    return aligned_count


def generate_dataset(original_file, translated_file, source_lang, target_lang,
                     sim_threshold=0.75, output_file="dataset.json",
                     leftover_file="leftover_sentences.json",
                     rag_csv_file="rag_aligned_pairs.csv"):
    """
    Main function to generate QnA dataset from two text files using semantic comparison.
    Also creates leftover sentences JSON and RAG CSV file.
    """
    print(f"Reading original file: {original_file}")
    original_text = read_text_file(original_file)

    print(f"Reading translated file: {translated_file}")
    translated_text = read_text_file(translated_file)

    print(f"Performing semantic comparison between {source_lang} and {target_lang}...")
    print(f"Using similarity threshold: {sim_threshold}")

    comparison_result = align_sentences_semantically(
        original_text,
        translated_text,
        source_lang,
        target_lang,
        sim_threshold
    )

    original_sentences = comparison_result["original_sentences"]
    translated_sentences = comparison_result["translated_sentences"]

    print(f"Found {len(original_sentences)} sentences in original text")
    print(f"Found {len(translated_sentences)} sentences in translated text")

    print("\nGenerating QnA pairs...")
    qna_dataset = create_qna_pairs(original_sentences, translated_sentences, source_lang, target_lang)

    # Create output structure for main dataset
    output_data = {
        "metadata": {
            "source_language": source_lang,
            "target_language": target_lang,
            "original_file": str(original_file),
            "translated_file": str(translated_file),
            "similarity_threshold": sim_threshold,
            "original_sentence_count": len(original_sentences),
            "translated_sentence_count": len(translated_sentences),
            "total_qna_pairs": len(qna_dataset)
        },
        "qna_pairs": qna_dataset
    }

    print(f"\nWriting main dataset to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✓ Successfully generated dataset with {len(qna_dataset)} QnA pairs")
    print(f"  - Single sentence pairs: {len([q for q in qna_dataset if q['type'] == 'single_sentence'])}")
    print(f"  - Batch sentence pairs: {len([q for q in qna_dataset if q['type'] == 'batch_sentences'])}")

    # Create leftover sentences JSON
    print("\nCreating leftover sentences file...")
    leftover_data = create_leftover_json(
        comparison_result,
        source_lang,
        target_lang,
        leftover_file
    )

    # Create RAG CSV file with aligned pairs
    print("\nCreating RAG CSV file...")
    aligned_count = create_rag_csv(
        original_sentences,
        translated_sentences,
        comparison_result["missing_info_indices"],
        comparison_result["extra_info_indices"],
        source_lang,
        target_lang,
        rag_csv_file
    )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Main Dataset: {output_file}")
    print(f"  - Total QnA pairs: {len(qna_dataset)}")
    print(f"\nLeftover Sentences: {leftover_file}")
    print(f"  - Missing from translation: {len(comparison_result['missing_info'])}")
    print(f"  - Extra in translation: {len(comparison_result['extra_info'])}")
    print(f"\nRAG CSV: {rag_csv_file}")
    print(f"  - Aligned pairs (above threshold): {aligned_count}")
    print("=" * 60)

    return output_data, leftover_data, aligned_count


def main():
    # ============================================
    # CONFIGURE YOUR INPUT FILES HERE
    # ============================================

    original_file = "door_eng.txt"  # Path to original text file
    translated_file = "door_spanish.txt"  # Path to translated text file
    source_lang = "en"  # Source language code
    target_lang = "es"  # Target language code
    sim_threshold = 0.75  # Similarity threshold for semantic matching (0.0-1.0)

    # Output files
    output_file = "dataset.json"  # Main QnA dataset
    leftover_file = "leftover_sentences.json"  # Sentences that didn't pass threshold
    rag_csv_file = "rag_aligned_pairs.csv"  # CSV with aligned pairs for RAG

    # ============================================

    generate_dataset(
        original_file,
        translated_file,
        source_lang,
        target_lang,
        sim_threshold,
        output_file,
        leftover_file,
        rag_csv_file
    )


if __name__ == "__main__":
    main()
