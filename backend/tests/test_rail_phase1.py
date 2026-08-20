from __future__ import annotations

import os
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.database import query, clear_demo_data, init_db
from app.database.seed_demo_data import seed_demo_dataset, DEMO_DATA_DIR
from app.core.security import create_access_token

class RailPhase1Tests(unittest.TestCase):
    def setUp(self) -> None:
        init_db()
        clear_demo_data()
        self.client = TestClient(app)
        # Create token for authentication
        self.token = create_access_token("reliability@forgemind.ai", "reliability_engineer")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_rail_usage_seeding_and_idempotency(self) -> None:
        # 1. Seeding and counts
        result = seed_demo_dataset()
        self.assertEqual(result["status"], "demo_seed_complete")
        
        # Check CSV rows vs DB rows
        csv_file = DEMO_DATA_DIR / "rail" / "rail_usage.csv"
        self.assertTrue(csv_file.exists())
        with open(csv_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # CSV has header, so row count is lines - 1 (if no trailing newline issues)
        csv_row_count = sum(1 for line in lines if line.strip()) - 1
        
        db_rows = query("SELECT * FROM asset_usage")
        db_row_count = len(db_rows)
        
        print(f"\n[TEST INFO] CSV row count: {csv_row_count}")
        print(f"[TEST INFO] DB asset_usage row count: {db_row_count}")
        
        self.assertEqual(csv_row_count, db_row_count)
        self.assertEqual(db_row_count, 11)  # We saw 11 data rows in rail_usage.csv
        
        # Test idempotency (run seed twice)
        result_second = seed_demo_dataset()
        db_rows_second = query("SELECT * FROM asset_usage")
        print(f"[TEST INFO] DB asset_usage row count after second seed: {len(db_rows_second)}")
        self.assertEqual(len(db_rows_second), db_row_count)

    def test_evidence_ingestion(self) -> None:
        seed_demo_dataset()
        
        # Verify rail_usage.csv is ingested as a document and has chunks
        doc_rows = query("SELECT * FROM documents WHERE filename = 'rail_usage.csv'")
        self.assertEqual(len(doc_rows), 1)
        doc = doc_rows[0]
        print(f"[TEST INFO] Document filename: {doc['filename']}, type: {doc['doc_type']}, ID: {doc['id']}")
        
        chunk_rows = query("SELECT * FROM chunks WHERE document_id = ?", (doc["id"],))
        print(f"[TEST INFO] Chunk count for rail_usage.csv: {len(chunk_rows)}")
        self.assertTrue(len(chunk_rows) > 0)

    def test_asset_360_retrieval(self) -> None:
        seed_demo_dataset()
        from app.services.maintenance_service import asset_360
        
        # TRK-001 is a rail asset
        details = asset_360("TRK-001")
        self.assertIsNotNone(details["asset"])
        self.assertEqual(details["asset"]["tag"], "TRK-001")
        
        # Verify usage data is returned in the asset_360 response
        self.assertTrue(len(details["usage"]) > 0)
        print(f"[TEST INFO] TRK-001 usage records count in Asset 360: {len(details['usage'])}")
        for record in details["usage"]:
            self.assertEqual(record["asset_tag"], "TRK-001")

    def test_asset_360_api(self) -> None:
        seed_demo_dataset()
        response = self.client.get("/api/assets/TRK-001", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["asset"]["tag"], "TRK-001")
        self.assertTrue(len(data["usage"]) > 0)
        print(f"[TEST INFO] API /api/assets/TRK-001 returned {len(data['usage'])} usage records")

    def test_asset_usage_api(self) -> None:
        seed_demo_dataset()
        response = self.client.get("/api/assets/TRK-001/usage", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data) > 0)
        self.assertEqual(data[0]["asset_tag"], "TRK-001")
        print(f"[TEST INFO] API /api/assets/TRK-001/usage returned {len(data)} usage records")

    def test_copilot_retrieval_success(self) -> None:
        seed_demo_dataset()
        from app.services.copilot_service import ask_copilot
        
        # Test real query: "What was the gross tonnage for TRK-001 in 2025-Q4?"
        res = ask_copilot("What was the gross tonnage for TRK-001 in 2025-Q4?", user_role="plant_manager")
        self.assertNotEqual(res["confidence"], 0.12)
        self.assertTrue(len(res["citations"]) > 0)
        self.assertIn("TRK-001", res["direct_answer"])
        self.assertIn("13200000", res["direct_answer"].replace(",", "").replace(" ", ""))
        print(f"[TEST INFO] Copilot direct answer for TRK-001 in 2025-Q4 query: {res['direct_answer']}")
        print(f"[TEST INFO] Copilot citations count: {len(res['citations'])}")
        print(f"[TEST INFO] Citation quote: {res['citations'][0]['quote']}")
        print(f"[TEST INFO] Citation filename: {res['citations'][0]['filename']}")

    def test_copilot_abstention(self) -> None:
        seed_demo_dataset()
        from app.services.copilot_service import ask_copilot
        
        # Test query for a nonexistent asset tag: "What is the inspection frequency of XYZ-999?"
        res = ask_copilot("What is the inspection frequency of XYZ-999?", user_role="plant_manager")
        self.assertEqual(res["confidence"], 0.12)
        self.assertEqual(res["evidence_strength"], "insufficient")
        self.assertIn("I don't know", res["direct_answer"])
        self.assertEqual(len(res["citations"]), 0)
        print(f"[TEST INFO] Copilot abstention for XYZ-999 query works (Direct Answer: '{res['direct_answer']}')")

if __name__ == "__main__":
    unittest.main()
