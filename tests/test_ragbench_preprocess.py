"""Cover the one place `datasets` is used, without downloading RAGBench.

`preprocess_ragbench.py` calls `load_dataset(repo, config)` and then reads each
sample as a mapping with a particular shape. Both halves can break on a major
`datasets` release, and neither was covered — which is why bumping the pin had no
evidence behind it beyond "the import still works".

The dataset here is built in memory by `datasets` itself, so this needs no
network and no RAGBench: it exercises the real call form and the real
`create_sample` against the schema the script assumes.
"""

import pytest

from verbatim_core.extractor_models.preprocess_ragbench import create_sample

pytestmark = pytest.mark.requires_full_stack

SAMPLE = {
    "id": "sample-1",
    "question": "What does dense retrieval do?",
    "documents_sentences": [
        [
            ["0a", "Dense retrieval maps queries into a vector space."],
            ["0b", "The cafeteria closes at two."],
        ],
        [["1a", "Recall at k ignores ordering."]],
    ],
    "all_relevant_sentence_keys": ["0a", "1a"],
}


class TestCreateSample:
    def test_builds_one_document_per_group(self):
        sample = create_sample(SAMPLE, "covidqa", "train")

        assert len(sample.documents) == 2
        assert [len(d.sentences) for d in sample.documents] == [2, 1]

    def test_marks_exactly_the_listed_sentences_relevant(self):
        sample = create_sample(SAMPLE, "covidqa", "train")

        relevant = [s.text for d in sample.documents for s in d.sentences if s.relevant]
        assert relevant == [
            "Dense retrieval maps queries into a vector space.",
            "Recall at k ignores ordering.",
        ]

    def test_carries_the_question_and_the_labels_through(self):
        sample = create_sample(SAMPLE, "covidqa", "dev")

        assert sample.question == SAMPLE["question"]
        assert sample.dataset_name == "covidqa"
        assert sample.split == "dev"

    def test_a_sample_without_sentences_is_skipped_not_crashed(self):
        assert create_sample({**SAMPLE, "documents_sentences": None}, "covidqa", "train") is None


class TestDatasetsCallForm:
    """The library half: `load_dataset(path, name)` still has to behave."""

    def test_a_named_config_round_trips_through_load_dataset(self, tmp_path):
        from datasets import load_dataset

        data_file = tmp_path / "ragbench-like.json"
        data_file.write_text(f"[{__import__('json').dumps(SAMPLE)}]")

        loaded = load_dataset("json", data_files=str(data_file))

        # A DatasetDict keyed by split, each row a mapping — what the script walks.
        assert "train" in loaded
        row = loaded["train"][0]
        assert row["question"] == SAMPLE["question"]
        assert create_sample(row, "covidqa", "train").documents[0].sentences[0].relevant is True
