import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mobile"))
from repository import LocalJsonRepository, build_report


class LocalRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = LocalJsonRepository(Path(self.temp.name) / "data.json")
        self.p1 = self.repo.add_product("SKU-001", "Kopi", "pcs", "10")
        self.p2 = self.repo.add_product("SKU-002", "Gula", "kg", "20")

    def tearDown(self):
        self.temp.cleanup()

    def test_unique_sku_and_barcode(self):
        with self.assertRaises(ValueError):
            self.repo.add_product("sku-001", "Nama duplikat")
        self.repo.add_product("SKU-003", "Teh", barcode="12345")
        with self.assertRaises(ValueError):
            self.repo.add_product("SKU-004", "Teh lain", barcode="12345")

    def test_stock_snapshot_does_not_change_when_master_stock_changes(self):
        session = self.repo.create_session("Pagi", [self.p1["id"], self.p2["id"]])
        self.repo.update_product_stock(self.p1["id"], "99")
        snapshot_item = next(x for x in self.repo.get_session(session["session"]["id"])["items"] if x["sku"] == "SKU-001")
        self.assertEqual(snapshot_item["system_stock"], "10")

    def test_five_count_fields_and_difference_are_per_item(self):
        session = self.repo.create_session("Siang", [self.p1["id"], self.p2["id"]])
        sid = session["session"]["id"]
        self.repo.confirm_session(sid)
        self.repo.start_session(sid)
        items = self.repo.get_session(sid)["items"]
        item1 = next(x for x in items if x["sku"] == "SKU-001")
        item2 = next(x for x in items if x["sku"] == "SKU-002")
        self.repo.save_count(sid, item1["id"], ["2", "2", "2", "2", "0"])
        self.repo.save_count(sid, item2["id"], ["4", "4", "4", "4", "4"])
        saved = self.repo.get_session(sid)["items"]
        one = next(x for x in saved if x["sku"] == "SKU-001")
        two = next(x for x in saved if x["sku"] == "SKU-002")
        self.assertEqual(one["physical_total"], "8")
        self.assertEqual(one["difference"], "-2")
        self.assertEqual(two["physical_total"], "20")
        self.assertEqual(two["difference"], "0")
        self.assertNotEqual(one["difference"], "0")

    def test_cannot_complete_until_every_item_is_counted(self):
        session = self.repo.create_session("Malam", [self.p1["id"], self.p2["id"]])
        sid = session["session"]["id"]
        self.repo.confirm_session(sid)
        self.repo.start_session(sid)
        item = self.repo.get_session(sid)["items"][0]
        self.repo.save_count(sid, item["id"], ["0", None, None, None, None])
        with self.assertRaisesRegex(ValueError, "Belum semua"):
            self.repo.complete_session(sid)

    def test_completed_shift_analytics_contains_per_sku_details_not_net_difference(self):
        session = self.repo.create_session("Pagi", [self.p1["id"], self.p2["id"]])
        sid = session["session"]["id"]
        self.repo.confirm_session(sid)
        self.repo.start_session(sid)
        items = self.repo.get_session(sid)["items"]
        self.repo.save_count(sid, items[0]["id"], ["8", None, None, None, None])
        self.repo.save_count(sid, items[1]["id"], ["22", None, None, None, None])
        self.repo.complete_session(sid)
        result = self.repo.get_shift_analytics()
        self.assertEqual(len(result["items"]), 1)
        group = result["items"][0]
        self.assertEqual(group["shortage_items"], 1)
        self.assertEqual(group["surplus_items"], 1)
        self.assertEqual({x["sku"] for x in group["products"]}, {"SKU-001", "SKU-002"})
        self.assertFalse(any(key in group for key in ("total_difference", "net_difference", "sum_difference")))


    def test_data_persists_after_repository_reopen(self):
        path = Path(self.temp.name) / "data.json"
        reopened = LocalJsonRepository(path)
        self.assertEqual(len(reopened.list_products()), 2)

    def test_corrupt_data_is_preserved_in_backup_and_repository_recovers(self):
        path = Path(self.temp.name) / "broken.json"
        path.write_text("{not valid json", encoding="utf-8")
        recovered = LocalJsonRepository(path)
        self.assertTrue(recovered.recovery_warning)
        backups = list(Path(self.temp.name).glob("broken.json.damaged-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{not valid json")
        self.assertEqual(recovered.list_products(), [])

    def test_report_has_separate_lines_for_each_sku(self):
        session = self.repo.create_session("Pagi", [self.p1["id"]])
        sid = session["session"]["id"]
        self.repo.confirm_session(sid)
        self.repo.start_session(sid)
        item = self.repo.get_session(sid)["items"][0]
        self.repo.save_count(sid, item["id"], ["8", None, None, None, None])
        self.repo.complete_session(sid)
        report = build_report(self.repo.get_session(sid))
        self.assertIn("SKU-001", report)
        self.assertIn("KURANG -2 pcs", report)
        self.assertIn("TIDAK DIJUMLAHKAN ANTAR SKU", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
