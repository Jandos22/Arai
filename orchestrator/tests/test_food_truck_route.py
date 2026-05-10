"""Deterministic tests for the food-truck weekly route planner."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.food_truck_route import (
    CTA_TAIL,
    LIFT_FACTOR,
    LIFT_NEAR_RADIUS_MILES,
    SKU_COPY,
    Customer,
    build_route,
    draft_ig_post,
    draft_whatsapp_for_customer,
    haversine_miles,
    hero_sku_for_cluster,
    kmeans_geo,
    load_customers,
    project_uplift,
    render_markdown,
    route_to_dict,
    write_artifacts,
)


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "food_truck_customers.json"


def _customers() -> list[Customer]:
    return load_customers(FIXTURE)


def test_haversine_known_distance():
    # First Colony, Sugar Land → Sienna, Missouri City: ~7 miles by car, ~7mi crow.
    miles = haversine_miles(29.6017, -95.6253, 29.5031, -95.5304)
    assert 5.0 < miles < 10.0


def test_load_customers_roundtrip():
    customers = _customers()
    assert len(customers) == 25
    assert all(isinstance(c, Customer) for c in customers)
    assert all(c.id and c.name and c.address for c in customers)
    assert all(-180 < c.lng < 180 and -90 < c.lat < 90 for c in customers)


def test_kmeans_deterministic_and_partitions_all():
    customers = _customers()
    a = kmeans_geo(customers, k=5, seed=7)
    b = kmeans_geo(customers, k=5, seed=7)
    assert [(cl.label, cl.size, cl.centroid_lat, cl.centroid_lng) for cl in a] == \
           [(cl.label, cl.size, cl.centroid_lat, cl.centroid_lng) for cl in b]
    assert sum(cl.size for cl in a) == len(customers)
    # No empty clusters with this fixture
    assert all(cl.size > 0 for cl in a)
    # Sorted by size descending
    sizes = [cl.size for cl in a]
    assert sizes == sorted(sizes, reverse=True)


def test_kmeans_recovers_pearland_cluster():
    """Pearland customers (lng ~ -95.28, far east of Sugar Land) must group."""
    customers = _customers()
    clusters = kmeans_geo(customers, k=5, seed=7)
    pearland_ids = {c.id for c in customers if "Pearland" in c.address}
    # The cluster containing the first Pearland customer should contain them all.
    target = next(cl for cl in clusters if pearland_ids & {c.id for c in cl.customers})
    assert {c.id for c in target.customers} == pearland_ids


def test_kmeans_rejects_invalid_k():
    customers = _customers()
    with pytest.raises(ValueError):
        kmeans_geo(customers, k=0)
    with pytest.raises(ValueError):
        kmeans_geo(customers, k=999)


def test_hero_sku_picks_modal_favorite():
    customers = _customers()
    clusters = kmeans_geo(customers, k=5, seed=7)
    for cl in clusters:
        sku = hero_sku_for_cluster(cl)
        favs = [c.favoriteSku for c in cl.customers]
        # Hero must be the most common (or tied-most-common) SKU in the cluster
        assert favs.count(sku) == max(favs.count(f) for f in favs)


def test_ig_post_brand_voice():
    customers = _customers()
    clusters = kmeans_geo(customers, k=5, seed=7)
    cluster = clusters[0]
    post = draft_ig_post("Mon", cluster, "honey-whole")
    # Brand rules: HappyCake one word, slogan present, CTA tail present, no emoji,
    # no banned superlatives
    assert "HappyCake" in post
    assert "Happy Cake" not in post
    assert 'cake "Honey"' in post
    assert "the original taste of happiness" in post
    assert post.rstrip().endswith(CTA_TAIL)
    for banned in ("amazing", "awesome", "incredible", "unbelievable", "!!!"):
        assert banned.lower() not in post.lower()
    # No common emoji ranges
    assert all(ord(ch) < 0x1F000 for ch in post)


def test_whatsapp_template_personalises_favorite_when_different_from_hero():
    customers = _customers()
    clusters = kmeans_geo(customers, k=5, seed=7)
    cluster = clusters[0]
    # Find a customer whose favoriteSku differs from the cluster's hero
    hero = hero_sku_for_cluster(cluster)
    odd = next((c for c in cluster.customers if c.favoriteSku != hero), None)
    if odd is None:
        pytest.skip("No customer with non-hero favourite in this fixture cluster")
    body = draft_whatsapp_for_customer(odd, weekday="Tue", cluster=cluster, hero_sku=hero)
    assert f"Hi {odd.name}!" in body
    assert SKU_COPY[hero] in body
    assert SKU_COPY[odd.favoriteSku] in body
    assert "your usual" in body
    assert body.rstrip().endswith(CTA_TAIL)


def test_whatsapp_template_collapses_when_favorite_matches_hero():
    cluster_customer = Customer(
        id="+12815550999",
        name="Zara",
        channel="whatsapp",
        address="First Colony, Sugar Land, TX 77479",
        lat=29.6,
        lng=-95.625,
        favoriteSku="honey-whole",
        avgTicket=55,
        monthlyFreq=1.0,
        lastOrderAt="2026-04-01",
    )
    customers = _customers()
    cluster = kmeans_geo(customers, k=5, seed=7)[0]
    body = draft_whatsapp_for_customer(
        cluster_customer, weekday="Mon", cluster=cluster, hero_sku="honey-whole"
    )
    # Should not say "too" — just "your usual" once
    assert body.count("your usual") == 1
    assert "your usual" in body
    assert " too." not in body


def test_projection_lift_is_consistent():
    customers = _customers()
    clusters = kmeans_geo(customers, k=5, seed=7)
    for cl in clusters:
        baseline, projected, incremental, inc_revenue = project_uplift(cl)
        assert baseline > 0
        assert projected >= baseline
        assert incremental == pytest.approx(projected - baseline, abs=0.01)
        # Customers within radius lift × LIFT_FACTOR; outliers stay flat.
        # So projected must not exceed baseline × LIFT_FACTOR.
        assert projected <= baseline * LIFT_FACTOR + 0.01
        # Revenue uplift must be positive when at least one customer is within radius
        from orchestrator.food_truck_route import haversine_miles as _h
        within = any(
            _h(c.lat, c.lng, cl.centroid_lat, cl.centroid_lng) <= LIFT_NEAR_RADIUS_MILES
            for c in cl.customers
        )
        if within:
            assert inc_revenue > 0


def test_build_route_assigns_one_weekday_per_cluster():
    customers = _customers()
    stops = build_route(customers, k=5, seed=7)
    assert len(stops) == 5
    assert [s.weekday for s in stops] == ["Mon", "Tue", "Wed", "Thu", "Fri"]
    # Every customer appears in exactly one stop
    seen = [c.id for s in stops for c in s.cluster.customers]
    assert len(seen) == len(customers)
    assert len(set(seen)) == len(customers)


def test_route_summary_totals_match_per_stop_sums():
    customers = _customers()
    stops = build_route(customers, k=5, seed=7)
    route = route_to_dict(stops, generated_at="2026-05-10T08:00:00Z")
    s = route["summary"]
    assert s["customers"] == sum(st["cluster"]["customerCount"] for st in route["stops"])
    assert s["incrementalOrdersMonth"] == pytest.approx(
        sum(st["projection"]["incrementalOrdersMonth"] for st in route["stops"]),
        abs=0.05,
    )
    assert s["incrementalRevenueMonthUsd"] == pytest.approx(
        sum(st["projection"]["incrementalRevenueMonthUsd"] for st in route["stops"]),
        abs=0.05,
    )


def test_markdown_renders_all_stops_and_brand_voice():
    customers = _customers()
    stops = build_route(customers, k=5, seed=7)
    route = route_to_dict(stops, generated_at="2026-05-10T08:00:00Z")
    md = render_markdown(route)
    for day in ("Mon", "Tue", "Wed", "Thu", "Fri"):
        assert f"### {day}" in md
    assert "HappyCake" in md
    assert "Happy Cake on the road" not in md  # one-word wordmark only
    # Owner-approval section present
    assert "## Owner approval" in md
    # No emoji
    assert all(ord(ch) < 0x1F000 for ch in md)


def test_write_artifacts_creates_json_and_md(tmp_path: Path):
    customers = _customers()
    stops = build_route(customers, k=5, seed=7)
    json_path, md_path, route = write_artifacts(
        stops,
        out_dir=tmp_path,
        generated_at_iso="2026-05-10T08:00:00Z",
        file_stem="food-truck-route-test",
    )
    assert json_path.exists() and md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "marketing.food_truck_weekly_route"
    assert payload["agent"] == "marketing"
    assert payload["generatedAt"] == "2026-05-10T08:00:00Z"
    assert len(payload["stops"]) == 5
    md = md_path.read_text(encoding="utf-8")
    assert "Food-truck weekly route" in md
    assert "marketing-agent draft" in md
