"""仅使用标准库：不访问网络、不导入 pymilvus/torch、不写数据库。"""

import math
import os
import unittest
from unittest.mock import patch

from examples.evaluation_metrics import recall_at_k, reciprocal_rank_at_k
from examples.tutorial_common import (
    TOY_QUERY, build_filter, connection_options, cosine_similarity,
    load_json, validate_vectors,
)


class VectorTests(unittest.TestCase):
    def test_cosine_geometry(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [5, 0]), 1)
        self.assertAlmostEqual(cosine_similarity([1, 0], [0, 5]), 0)
        self.assertAlmostEqual(cosine_similarity([1, 0], [-5, 0]), -1)

    def test_invalid_vectors_rejected(self):
        for vectors in ([], [[1, 2]], [[0, 0, 0]], [[math.nan, 1, 0]], [[1, math.inf, 0]], [[True, 1, 0]]):
            with self.subTest(vectors=vectors), self.assertRaises(ValueError):
                validate_vectors(vectors, 3)

    def test_toy_ranking_and_filter_have_real_effect(self):
        rows = load_json("toy_vectors.json")
        validate_vectors([row["vector"] for row in rows], 3)
        ranked = sorted(rows, key=lambda row: cosine_similarity(row["vector"], TOY_QUERY), reverse=True)
        self.assertEqual(ranked[0]["id"], 901, "未过滤时其他租户应占第一位，才能体现过滤的意义。")
        filtered = [row for row in ranked if row["tenant"] == "tenant_a"]
        self.assertEqual(filtered[0]["id"], 101)
        self.assertNotIn(901, [row["id"] for row in filtered])


class DataTests(unittest.TestCase):
    def test_unique_ids_and_utf8_field_lengths(self):
        for filename in ("toy_vectors.json", "faq.json"):
            rows = load_json(filename)
            self.assertEqual(len(rows), len({row["id"] for row in rows}))
            for row in rows:
                self.assertIsInstance(row["id"], int)
                self.assertLessEqual(len(row["text"].encode("utf-8")), 4096)
                self.assertTrue(row["text"].strip())
                build_filter(row["tenant"], row["category"])

    def test_evaluation_labels_exist_in_correct_tenant(self):
        documents = {row["id"]: row for row in load_json("faq.json")}
        cases = load_json("evaluation.json")
        self.assertGreaterEqual(len(cases), 6)
        for case in cases:
            self.assertTrue(case["relevant_ids"])
            for identifier in case["relevant_ids"]:
                self.assertIn(identifier, documents)
                self.assertEqual(documents[identifier]["tenant"], case["tenant"])


class FilterAndConnectionTests(unittest.TestCase):
    def test_filter_keeps_tenant_when_adding_category(self):
        self.assertEqual(build_filter("tenant_a"), 'tenant == "tenant_a"')
        self.assertEqual(build_filter("tenant_a", "account"), 'tenant == "tenant_a" and category == "account"')

    def test_rejects_expression_injection(self):
        for tenant in ('tenant_a" or id > 0', "", "x" * 65, "tenant\n_a"):
            with self.subTest(tenant=tenant), self.assertRaises(ValueError):
                build_filter(tenant)
        with self.assertRaises(ValueError):
            build_filter("tenant_a", 'account" or true')

    def test_connection_defaults_and_token(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(connection_options()["uri"], "http://127.0.0.1:19530")
        with patch.dict(os.environ, {"MILVUS_URI": "https://example.invalid:19530", "MILVUS_TOKEN": "fake-test-token"}, clear=True):
            self.assertEqual(connection_options()["token"], "fake-test-token")

    def test_no_lite_or_credentials_in_uri(self):
        for uri in ("./milvus.db", "http://user:password@localhost:19530", "http://localhost:19530/?token=x"):
            with patch.dict(os.environ, {"MILVUS_URI": uri}, clear=True), self.assertRaises(ValueError):
                connection_options()


class MetricTests(unittest.TestCase):
    def test_recall_counts_distinct_relevant_documents(self):
        self.assertEqual(recall_at_k([1, 1, 8], [1, 2], 3), 0.5)
        self.assertEqual(recall_at_k([8, 2, 1], [1, 2], 2), 0.5)
        self.assertEqual(recall_at_k([1, 2], [1, 2], 10), 1)

    def test_mrr_uses_first_relevant_rank_and_cutoff(self):
        self.assertEqual(reciprocal_rank_at_k([9, 2, 1], [1, 2], 3), 0.5)
        self.assertEqual(reciprocal_rank_at_k([9, 2, 1], [1, 2], 1), 0)
        self.assertEqual(reciprocal_rank_at_k([], [1], 3), 0)

    def test_empty_labels_and_bad_k_are_not_silent(self):
        for metric in (recall_at_k, reciprocal_rank_at_k):
            with self.assertRaises(ValueError):
                metric([1], [], 3)
            with self.assertRaises(ValueError):
                metric([1], [1], 0)


if __name__ == "__main__":
    unittest.main()
