from __future__ import annotations

import unittest

from app.database import DatabaseRow, _postgres_statement


class DatabaseAdapterTests(unittest.TestCase):
    def test_postgres_translation_preserves_insert_id(self) -> None:
        statement, returns_id = _postgres_statement(
            "INSERT INTO documents(filename, doc_type) VALUES (?, ?)",
            return_insert_id=True,
        )

        self.assertEqual(
            statement,
            "INSERT INTO documents(filename, doc_type) VALUES (%s, %s) RETURNING id",
        )
        self.assertTrue(returns_id)

    def test_insert_or_ignore_uses_postgres_conflict_handling(self) -> None:
        statement, returns_id = _postgres_statement(
            "INSERT OR IGNORE INTO assets(tag, name) VALUES (?, ?)",
            return_insert_id=False,
        )

        self.assertEqual(
            statement,
            "INSERT INTO assets(tag, name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        )
        self.assertFalse(returns_id)

    def test_database_row_supports_mapping_and_numeric_access(self) -> None:
        row = DatabaseRow(id=7, filename="evidence.txt")

        self.assertEqual(row[0], 7)
        self.assertEqual(row["filename"], "evidence.txt")


if __name__ == "__main__":
    unittest.main()
