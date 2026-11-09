#!/usr/bin/env python3
"""Offline contract tests; no network or GitHub Actions required."""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import autocatalog as ac


def example_catalog():
    dolls = [{"canonicalId": f"legacy:{n}", "name": f"Doll {n}", "seriesCode": "legacy"}
             for n in range(713)]
    return {
        "dolls": dolls,
        "collections": [{"officialCode": "GM-COL-MUSIC-FESTIVAL"}, {"officialCode": "GM-COL-HELLO-KITTY"}],
        "series": [{"officialCode": "GM-SER-MUSIC-FESTIVAL-OMG"},
                   {"officialCode": "GM-SER-HELLO-KITTY-OMG"}],
    }


def product(title, handle="lol-tyla", product_id="42", verified=True):
    return {"title": title, "handle": handle, "productId": product_id,
            "url": "https://shop.mgae.com/products/" + handle,
            "feedVerified": verified, "sku": "249641",
            "image": "https://shop.mgae.com/cdn/shop/files/tyla-doll.png"}


class AutoCatalogTest(unittest.TestCase):
    def test_named_official_omg_doll_is_new(self):
        catalog = example_catalog()
        p = product("LOL Surprise OMG Music Festival Featuring Tyla – Fashion Doll with Collectible Poster")
        added, review = ac.reconcile([p], catalog)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["name"], "Tyla")
        self.assertIsNone(added[0]["officialCode"])
        self.assertEqual(added[0]["canonicalId"], "mga:product:42")
        self.assertEqual(review[0]["status"], "automatic")
        self.assertEqual(len(catalog["dolls"]), 713)

    def test_hello_kitty_individual(self):
        p = product("LOL Surprise OMG Loves Hello Kitty® & Friends - Kuromi™", "lol-kuromi", "843")
        added, _ = ac.reconcile([p], example_catalog())
        self.assertEqual(added[0]["name"], "Kuromi")
        self.assertEqual(added[0]["seriesCode"], "GM-SER-HELLO-KITTY-OMG")

    def test_no_duplicate_name_in_series(self):
        catalog = example_catalog()
        catalog["dolls"][0].update({"name": "Tyla", "seriesCode": "GM-SER-MUSIC-FESTIVAL-OMG"})
        added, review = ac.reconcile(
            [product("LOL Surprise OMG Music Festival Featuring Tyla – Fashion Doll")], catalog
        )
        self.assertFalse(added)
        self.assertEqual(review[0]["status"], "existing")

    def test_group_pack_requires_review(self):
        p = product("LOL Surprise Loves Dr. Seuss Tots", "lol-dr-seuss", "124")
        added, review = ac.reconcile([p], example_catalog())
        self.assertFalse(added)
        self.assertEqual(review[0]["status"], "review_required")

    def test_html_fallback_never_auto_publishes(self):
        p = product("LOL Surprise OMG Music Festival Featuring Tyla – Fashion Doll", verified=False)
        added, review = ac.reconcile([p], example_catalog())
        self.assertFalse(added)
        self.assertEqual(review[0]["status"], "review_required")

    def test_prevent_unofficial_image_and_duplicate_identity(self):
        self.assertEqual(ac.safe_image("https://evil.example/cdn/shop/doll.jpg"), "")
        self.assertEqual(ac.safe_image("https://shop.mgae.com/cdn/shop/files/MGA-logo.png"), "")
        catalog = example_catalog()
        catalog["dolls"][0]["canonicalId"] = catalog["dolls"][1]["canonicalId"]
        with self.assertRaises(ValueError):
            ac.reconcile([], catalog)

    def test_version_increment(self):
        self.assertEqual(ac.next_version("5.3.6-global-final"), "5.3.7-global-auto")
        self.assertEqual(ac.next_version("5.3.9-global-auto"), "5.3.10-global-auto")

    def test_official_feed_and_deduplicated_collections(self):
        import json
        def fake_get(url):
            if "products.json" in url:
                if "page=1" in url:
                    return json.dumps({"products": [{"id": 42, "handle": "lol-tyla",
                        "title": "LOL Surprise OMG Music Festival Featuring Tyla – Fashion Doll",
                        "variants": [{"sku": "123"}], "images": []}]}).encode()
                return b'{"products":[]}'
            raise AssertionError("Unexpected source " + url)
        found = ac.fetch_products(fake_get)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0]["feedVerified"])

    def test_zero_products_fails_closed(self):
        with self.assertRaises(RuntimeError):
            ac.fetch_products(lambda url: b'{"products":[]}')


if __name__ == "__main__":
    unittest.main()
