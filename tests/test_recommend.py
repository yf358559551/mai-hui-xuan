import copy
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("recommend", ROOT / "skills/mai-hui-xuan/scripts/recommend.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = datetime.fromisoformat("2026-10-13T12:00:00+08:00")


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "examples/demo.json").read_text())

    def run_case(self):
        return module.recommend(self.data, NOW)

    def test_ordinary_beats_activity(self):
        result = self.run_case()
        self.assertEqual(result["recommendations"][0]["id"], "ordinary")
        self.assertEqual(result["recommendations"][1]["verified_saving_yuan"], 7)
        self.assertIn("模拟", result["recommendations"][0]["label"])

    def test_keep_quantity_is_hard_constraint(self):
        self.data["required_items"]["demo-side-small"] = 2
        self.assertEqual(self.run_case()["recommendations"], [])

    def test_budget_includes_all_fees(self):
        self.data["budget_yuan"] = 24
        self.assertEqual([r["id"] for r in self.run_case()["recommendations"]], ["ordinary"])
        self.data["candidates"][1]["quote"]["all_fees_included"] = False
        self.assertEqual(self.run_case()["recommendations"], [])

    def test_unknown_nutrition_excluded_from_low_mode(self):
        self.data["candidates"][1]["items"][0]["kcal"] = None
        self.assertEqual(self.run_case()["recommendations"][0]["id"], "activity")
        self.data["low_calorie"] = False
        ordinary = next(r for r in self.run_case()["recommendations"] if r["id"] == "ordinary")
        self.assertIsNone(ordinary["kcal"])
        self.assertEqual(ordinary["heat_band"], "未知")

    def test_expired_activity_is_rejected(self):
        self.data["candidates"][0]["activity"]["ends_at"] = NOW.isoformat()
        self.assertNotIn("activity", [r["id"] for r in self.run_case()["recommendations"]])

    def test_wrong_store_and_stale_quote(self):
        for c in self.data["candidates"]:
            c["quote"]["store_id"] = "OTHER"
        self.assertEqual(self.run_case()["recommendations"], [])
        self.setUp()
        for c in self.data["candidates"]:
            c["quote"]["queried_at"] = "2026-10-13T11:00:00+08:00"
        self.assertEqual(self.run_case()["recommendations"], [])

    def test_avoid_is_hard_constraint(self):
        self.data["avoid"] = ["辣"]
        self.assertEqual(self.run_case()["recommendations"], [])

    def test_heat_boundaries(self):
        self.assertEqual(module.heat_band(500), "较低热量")
        self.assertEqual(module.heat_band(500.1), "中等热量")
        self.assertEqual(module.heat_band(800), "中等热量")
        self.assertEqual(module.heat_band(800.1), "较高热量")

    def test_wrong_comparison_contents_no_saving(self):
        self.data["candidates"][0]["same_contents_baseline"]["items"] = {"other": 1}
        deal = next(r for r in self.run_case()["recommendations"] if r["id"] == "activity")
        self.assertIsNone(deal["verified_saving_yuan"])

    def test_modify_original_can_be_over_budget(self):
        self.data.update(mode="modify", original_id="activity", budget_yuan=24)
        comparison = self.run_case()["comparison"]
        self.assertEqual(comparison["price_difference_yuan"], 2)
        self.assertEqual(comparison["kcal_difference"], -10)

    def test_nutrition_multiplies_portions(self):
        items = copy.deepcopy(self.data["candidates"][0]["items"])
        items[1]["quantity"] = 2
        self.assertEqual(module.nutrition(items)["kcal"], 630)

    def test_invalid_numeric_values_fail(self):
        for value in (True, -1, "NaN", "Infinity"):
            with self.subTest(value=value):
                self.data["budget_yuan"] = value
                with self.assertRaises(ValueError):
                    self.run_case()

    def test_duplicate_meal_returns_once(self):
        self.data["mode"] = "choose"
        duplicate = copy.deepcopy(self.data["candidates"][1])
        duplicate.update(id="duplicate", name="同内容另一报价")
        duplicate["quote"]["total_yuan"] = 24
        self.data["candidates"].append(duplicate)
        self.assertNotIn("duplicate", [r["id"] for r in self.run_case()["recommendations"]])

    def test_timezone_required(self):
        self.data["candidates"][0]["quote"]["queried_at"] = "2026-10-13T11:58:00"
        with self.assertRaises(ValueError):
            self.run_case()


if __name__ == "__main__":
    unittest.main()
