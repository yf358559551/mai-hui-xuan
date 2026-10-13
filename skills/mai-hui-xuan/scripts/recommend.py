#!/usr/bin/env python3
"""Rank normalized, evidence-backed meal candidates. No network or ordering."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys


def number(value, label):
    if isinstance(value, bool) or value is None:
        raise ValueError(label + " 必须是非负数")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(label + " 必须是非负数")
    if not result.is_finite() or result < 0:
        raise ValueError(label + " 必须是有限非负数")
    return result


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("时间必须包含时区")
    return result


def strings(value, label):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(label + " 必须是非空字符串的列表")
    return value


def nutrition(items):
    totals = {}
    for field in ("kcal", "protein_g", "fat_g"):
        vals = [item.get(field) for item in items]
        # Unknown components invalidate the whole-meal total for that nutrient.
        totals[field] = None if any(v is None for v in vals) else float(sum(
            (number(v, field) * item["quantity"] for v, item in zip(vals, items)), Decimal(0)))
    return totals


def heat_band(kcal):
    if kcal is None:
        return "未知"
    return "较低热量" if kcal <= 500 else "中等热量" if kcal <= 800 else "较高热量"


def recommend(data, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("当前时间必须含时区")
    mode = data.get("mode", "choose")
    if mode not in ("choose", "modify", "deals"):
        raise ValueError("mode 必须为 choose、modify 或 deals")
    if not isinstance(data.get("demo", False), bool) or not isinstance(data.get("low_calorie", False), bool):
        raise ValueError("demo、low_calorie 必须是布尔值")
    budget = number(data["budget_yuan"], "budget_yuan") if data.get("budget_yuan") is not None else None
    cap = number(data.get("low_kcal_max", 500), "low_kcal_max")
    likes = set(strings(data.get("likes", []), "likes"))
    avoid = set(strings(data.get("avoid", []), "avoid"))
    required = data.get("required_items", {})
    if not isinstance(required, dict) or any(not isinstance(k, str) or not k or type(v) is not int or v < 1 for k, v in required.items()):
        raise ValueError("required_items 必须映射规格 ID 到正整数数量")
    store, channel = data["store_id"], data["channel"]
    accepted, rejected, ids = [], [], set()
    for candidate in data["candidates"]:
        cid = candidate["id"]
        if not isinstance(cid, str) or not cid or cid in ids:
            raise ValueError("候选 ID 必须非空且唯一")
        ids.add(cid)
        reasons = []
        if candidate.get("available") is not True:
            reasons.append("当前不可售或可售状态未核验")
        if candidate.get("meal_complete") is not True:
            reasons.append("不构成一餐")
        items = candidate["items"]
        if not items:
            raise ValueError("候选必须有组件")
        counts, tags = Counter(), set()
        for item in items:
            if type(item["quantity"]) is not int or item["quantity"] < 1:
                raise ValueError("餐品数量必须是正整数")
            counts[item["id"]] += item["quantity"]
            tags.update(strings(item.get("tags", []), "tags"))
            for field in ("kcal", "protein_g", "fat_g"):
                if item.get(field) is not None:
                    number(item[field], field)
        if any(counts[k] < v for k, v in required.items()):
            reasons.append("缺少必须保留的餐品或数量")
        if tags & avoid:
            reasons.append("包含明确忌口")
        quote = candidate["quote"]
        price = number(quote["total_yuan"], "total_yuan")
        if quote.get("verified") is not True or quote.get("all_fees_included") is not True:
            reasons.append("实付总价未完整核验")
        if quote.get("store_id") != store or quote.get("channel") != channel:
            reasons.append("报价门店或就餐渠道不符")
        quoted_at = timestamp(quote["queried_at"])
        if not 0 <= (now - quoted_at).total_seconds() <= 900:
            reasons.append("报价过期或来自未来")
        if quote.get("expires_at") and now >= timestamp(quote["expires_at"]):
            reasons.append("报价或优惠已失效")
        if budget is not None and price > budget:
            reasons.append("超出预算")
        nutrients = nutrition(items)
        if data.get("low_calorie") and (nutrients["kcal"] is None or Decimal(str(nutrients["kcal"])) > cap):
            reasons.append("热量未知或超过低卡上限")
        activity = candidate.get("activity")
        if activity:
            if (activity.get("verified") is not True
                    or not timestamp(activity["starts_at"]) <= now < timestamp(activity["ends_at"])
                    or activity.get("store_id") != store or activity.get("channel") != channel):
                reasons.append("活动当前适用性未核验")
        if reasons:
            rejected.append({"id": cid, "reasons": reasons})
            continue
        # This basis is restricted to the SAME contents and context.
        baseline = candidate.get("same_contents_baseline")
        saving = None
        if baseline:
            age = (now - timestamp(baseline["queried_at"])).total_seconds()
            if (baseline.get("verified") is True and baseline.get("all_fees_included") is True
                    and baseline.get("store_id") == store and baseline.get("channel") == channel
                    and baseline.get("items") == dict(counts) and 0 <= age <= 900):
                delta = number(baseline["total_yuan"], "baseline.total_yuan") - price
                if delta >= 0:
                    saving = float(delta)
        accepted.append({"id": cid, "name": candidate["name"], "items": items,
                         "total_yuan": float(price), **nutrients,
                         "heat_band": heat_band(nutrients["kcal"]),
                         "matched_likes": sorted(tags & likes),
                         "verified_saving_yuan": saving, "activity": activity,
                         "queried_at": quote["queried_at"],
                         "label": "模拟数据，不可下单" if data.get("demo") else "按提供的核验证据筛选"})
    def usual(c):
        return (-len(c["matched_likes"]), c["total_yuan"], c["kcal"] if c["kcal"] is not None else float("inf"), c["id"])
    accepted.sort(key=usual)
    note = "仅比较本次已核验候选，不代表全局最低价。"
    if mode == "deals":
        deals = sorted((c for c in accepted if c["activity"]), key=lambda c: (
            -(c["verified_saving_yuan"] or 0), *usual(c)))
        ordinary = sorted((c for c in accepted if not c["activity"]), key=usual)
        if deals:
            best = deals[0]
            cheaper = [c for c in ordinary if c["total_yuan"] <= best["total_yuan"]
                       and len(c["matched_likes"]) >= len(best["matched_likes"])]
            if cheaper:
                first = cheaper[0]
                accepted = [first, best] + [c for c in accepted if c["id"] not in (first["id"], best["id"])]
                note = "普通方案价格不高于活动方案且口味匹配不差，优先推荐普通方案；活动作为备选。"
            else:
                accepted = [best] + [c for c in accepted if c["id"] != best["id"]]
        else:
            note = "没有核验通过的当前活动，以下为普通方案；未放宽预算和低卡约束。"
    # Deduplicate identical meal contents, preserving the preferred first quote.
    unique, signatures = [], set()
    for c in accepted:
        counts = Counter()
        for item in c["items"]:
            counts[item["id"]] += item["quantity"]
        signature = tuple(sorted(counts.items()))
        if signature not in signatures:
            unique.append(c)
            signatures.add(signature)
    if not unique:
        note = "没有满足全部约束的方案，请根据排除原因选择一项约束调整；未自动放宽。"
    result = {"demo": data.get("demo", False), "recommendations": unique[:3], "rejected": rejected, "note": note}
    if mode == "modify":
        original = next((c for c in accepted if c["id"] == data.get("original_id")), None)
        # An original over budget can still be a valid comparison, so evaluate it without optional filters.
        if original is None and data.get("original_id"):
            subset = [c for c in data["candidates"] if c["id"] == data["original_id"]]
            neutral = dict(data, mode="choose", budget_yuan=None, low_calorie=False, avoid=[], required_items={}, candidates=subset)
            originals = recommend(neutral, now)["recommendations"]
            original = originals[0] if originals else None
        if original and unique:
            top = unique[0]
            result["comparison"] = {"original_id": original["id"], "recommended_id": top["id"],
                "price_difference_yuan": float(Decimal(str(original["total_yuan"])) - Decimal(str(top["total_yuan"]))),
                "kcal_difference": None if original["kcal"] is None or top["kcal"] is None else round(original["kcal"] - top["kcal"], 2),
                "label": "方案差价（原方案减新方案），非同款优惠"}
        else:
            result["comparison"] = {"label": "缺少可核验的原方案或推荐方案，无法计算差价"}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--demo-now", help="仅模拟数据可指定时钟，ISO 8601")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if args.demo_now and data.get("demo") is not True:
            raise ValueError("--demo-now 仅允许 demo=true 的数据")
        result = recommend(data, timestamp(args.demo_now) if args.demo_now else None)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError, AttributeError) as exc:
        print("输入错误：" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
