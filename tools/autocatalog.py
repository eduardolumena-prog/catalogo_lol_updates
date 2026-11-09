#!/usr/bin/env python3
"""ELM AutoCatalog: descubrimiento oficial y publicación incremental segura.

La CLI sin --publish solo descubre. El modo --publish añade únicamente
muñecas individuales identificadas explícitamente en productos oficiales.
No usa ni modifica datos personales de la app.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlparse, urlsplit
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
HOST = "shop.mgae.com"
COLLECTIONS = ("new-l-o-l-surprise", "l-o-l-surprise")
FORMAT = "lol-catalog-update-v1"
MAX_PAGES = 4
MAX_BYTES = 4_000_000
SOURCE_BASE = "https://shop.mgae.com"
OUT_CANDIDATES = ROOT / "autocatalog" / "candidates.json"

# Solo series ya presentes en la base certificada; jamás inventar códigos.
PATTERNS = (
    (re.compile(r"^LOL Surprise OMG Music Festival Featuring\s+(.+?)\s+[–-]\s+Fashion Doll", re.I),
     "GM-COL-MUSIC-FESTIVAL", "GM-SER-MUSIC-FESTIVAL-OMG"),
    (re.compile(r"^LOL Surprise OMG Loves Hello Kitty.*?\s+[–-]\s+([^–-]+?)\s*$", re.I),
     "GM-COL-HELLO-KITTY", "GM-SER-HELLO-KITTY-OMG"),
)
REJECT = re.compile(r"plush|house|playset|blind|surprise ball|assort|pack|furniture|calendar|bus|camper|car-pool", re.I)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(data: dict | list) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def normalized(value: str) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def clean_name(name: str) -> str:
    return html.unescape(name).strip().rstrip("™® ").strip()


def handle_from_url(url: str) -> str:
    bits = urlsplit(url).path.split("/")
    return bits[bits.index("products") + 1].lower() if "products" in bits and len(bits) > bits.index("products") + 1 else ""


def official_product_url(handle: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", handle):
        raise ValueError("Invalid official product handle")
    return f"{SOURCE_BASE}/products/{handle}"


def get_bytes(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != HOST:
        raise ValueError("Only the official MGA shop is permitted")
    req = Request(url, headers={"User-Agent": "ELM-AutoCatalog/1.0 (catalogue metadata)", "Accept": "application/json,text/html"})
    with urlopen(req, timeout=20) as response:
        blob = response.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError("Response exceeded size limit")
    return blob


class ProductLinks(HTMLParser):
    """HTML fallback is discovery-only; not sufficient to certify doll identity."""
    def __init__(self) -> None:
        super().__init__()
        self.links: dict[str, str] = {}
        self.current = ""
        self.text_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        handle = handle_from_url(href)
        if handle:
            self.current = handle
            self.text_parts = []

    def handle_data(self, data):
        if self.current:
            self.text_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            title = " ".join(" ".join(self.text_parts).split())
            if title and "LOL" in title.upper():
                self.links[self.current] = title
            self.current = ""
            self.text_parts = []


def fetch_products(fetch=get_bytes) -> list[dict]:
    found: dict[str, dict] = {}
    valid_json = 0
    for collection in COLLECTIONS:
        try:
            for page in range(1, MAX_PAGES + 1):
                url = f"{SOURCE_BASE}/collections/{collection}/products.json?limit=250&page={page}"
                body = json.loads(fetch(url))
                products = body.get("products")
                if not isinstance(products, list):
                    raise ValueError("Shopify products[] missing")
                valid_json += 1
                for p in products:
                    if not isinstance(p, dict):
                        continue
                    handle = str(p.get("handle") or "").lower()
                    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", handle):
                        continue
                    title = str(p.get("title") or "")
                    if "lol" not in title.casefold():
                        continue
                    found[handle] = {
                        "handle": handle, "title": title,
                        "productId": str(p.get("id") or ""),
                        "url": official_product_url(handle),
                        "feedVerified": True,
                        "sku": str(((p.get("variants") or [{}])[0] or {}).get("sku") or "") if len(p.get("variants") or []) == 1 else "",
                        "image": str(((p.get("images") or [{}])[0] or {}).get("src") or ""),
                    }
                if len(products) < 250:
                    break
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            # Fallback preserves discovery but cannot auto-publish from HTML titles.
            try:
                parser = ProductLinks()
                parser.feed(fetch(f"{SOURCE_BASE}/collections/{collection}").decode("utf-8"))
                for handle, title in parser.links.items():
                    found.setdefault(handle, {"handle": handle, "title": title,
                        "productId": "", "url": official_product_url(handle),
                        "feedVerified": False, "sku": "", "image": ""})
            except (OSError, ValueError, UnicodeError):
                pass
    if not found:
        raise RuntimeError("No official products fetched. Fail closed: publication blocked.")
    return sorted(found.values(), key=lambda p: p["handle"])


def individual_candidate(product: dict, catalog: dict) -> tuple[str, str, str] | None:
    title = product["title"]
    if not product.get("feedVerified") or not product.get("productId") or REJECT.search(title):
        return None
    for rx, collection_code, series_code in PATTERNS:
        match = rx.search(title)
        if match:
            name = clean_name(match.group(1))
            if not name or len(name) > 80 or normalized(name) in {"", "friends"}:
                return None
            if collection_code not in {c.get("officialCode") for c in catalog["collections"]}:
                return None
            if series_code not in {s.get("officialCode") for s in catalog["series"]}:
                return None
            return name, collection_code, series_code
    return None


def safe_image(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"shop.mgae.com", "cdn.shopify.com"}:
        return ""
    if "logo" in parsed.path.lower() or "/cdn/shop/" not in parsed.path.lower():
        return ""
    return url


def reconcile(products: list[dict], catalog: dict) -> tuple[list[dict], list[dict]]:
    dolls = catalog.get("dolls")
    if not isinstance(dolls, list) or len(dolls) < 713:
        raise ValueError("Master catalog is missing certified 713 identities")
    ids = [str(d.get("canonicalId") or "") for d in dolls]
    if len(ids) != len(set(ids)) or not all(ids):
        raise ValueError("Duplicate or blank canonicalId in original master")
    existing_pairs = {(normalized(d.get("name", "")), d.get("seriesCode")) for d in dolls}
    existing_handles = {handle_from_url(str(d.get("sourceRef") or "")) for d in dolls}
    additions, reviewed = [], []
    used = set(ids)
    for p in products:
        evidence = individual_candidate(p, catalog)
        status = "review_required"
        reason = "Product is not a uniquely identified individual doll in verified product feed"
        if p["handle"] in existing_handles:
            status, reason = "existing", "Official product URL already linked"
        elif evidence:
            name, col, series = evidence
            pair = (normalized(name), series)
            if pair in existing_pairs:
                status, reason = "existing", "Name + series already in master"
            else:
                canonical = "mga:product:" + p["productId"]
                if canonical in used or any(d.get("sourceRef") == p["url"] for d in additions):
                    status, reason = "review_required", "Ambiguous product identity"
                else:
                    row = {
                        "canonicalId": canonical, "name": name, "officialCode": None,
                        "collectionCode": col, "seriesCode": series, "releaseYear": None,
                        "rarity": None, "club": None, "recordType": "doll",
                        "manufacturerSku": p["sku"] or None,
                        "officialImage": safe_image(p["image"]),
                        "sourceRef": p["url"],
                        "origin": "official-mga-autocatalog",
                        "metadata": {"productTitle": p["title"], "productId": p["productId"],
                                     "verifiedSource": "MGA_OFFICIAL_SHOP_PRODUCT_FEED",
                                     "officialCodeStatus": "not-published-by-manufacturer"},
                    }
                    additions.append(row)
                    existing_pairs.add(pair)
                    used.add(canonical)
                    status, reason = "automatic", "Unique named doll from official product record"
        reviewed.append({"handle": p["handle"], "title": p["title"], "url": p["url"],
                         "status": status, "reason": reason})
    return additions, reviewed


def next_version(previous: str) -> str:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", previous)
    if not match:
        raise ValueError("Unexpected manifest version")
    major, minor, patch = map(int, match.groups())
    return f"{major}.{minor}.{patch + 1}-global-auto"


def publish(catalog: dict, manifest: dict, new_dolls: list[dict]) -> str:
    if not new_dolls:
        return ""
    previous_count = len(catalog["dolls"])
    previous_ids = {d["canonicalId"] for d in catalog["dolls"]}
    if any(d["canonicalId"] in previous_ids for d in new_dolls):
        raise ValueError("Refusing duplicate identity")
    payload = copy.deepcopy(catalog)
    version = next_version(manifest["catalogVersion"])
    payload["dolls"].extend(new_dolls)
    payload.update({"format": FORMAT, "schemaVersion": 2, "catalogVersion": version,
                    "publishedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "notes": f"AutoCatalog: {len(new_dolls)} newly verified individual dolls."})
    ids = [d["canonicalId"] for d in payload["dolls"]]
    if len(set(ids)) != len(ids) or len(ids) < previous_count:
        raise ValueError("Refusing identity corruption")
    for field in ("collections", "series", "accessories", "dollAccessories", "relations", "tags", "dollTags", "replaceImages"):
        if not isinstance(payload.get(field), list):
            raise ValueError("Missing compatible catalog array: " + field)
    raw = dump(payload)
    package_path = f"packages/{version}/catalog_package.zip"
    data_path = f"catalog.{version}.json"
    package_folder = ROOT / "packages" / version
    package_folder.mkdir(parents=True, exist_ok=False)
    (package_folder / "catalog.json").write_bytes(raw)
    (ROOT / data_path).write_bytes(raw)
    with ZipFile(ROOT / package_path, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("catalog.json", raw)
    with ZipFile(ROOT / package_path) as zf:
        if zf.namelist() != ["catalog.json"] or zf.read("catalog.json") != raw:
            raise ValueError("Package verification failed")
    package_hash = sha256((ROOT / package_path).read_bytes())
    catalog_hash = sha256(raw)
    updated = copy.deepcopy(manifest)
    root_url = "https://raw.githubusercontent.com/eduardolumena-prog/catalogo_lol_updates/main/"
    updated.update({
        "baseCount": previous_count, "baseVersion": manifest["catalogVersion"],
        "catalogFile": data_path, "catalogPath": data_path, "catalogSha256": catalog_hash,
        "catalogUrl": root_url + data_path, "catalogVersion": version,
        "downloadUrl": root_url + package_path, "packageFile": package_path,
        "packageUrl": root_url + package_path, "zipUrl": root_url + package_path,
        "format": FORMAT, "schemaVersion": 2, "sha256": package_hash,
        "newRecords": len(new_dolls), "recordCount": len(payload["dolls"]),
        "publishedAt": payload["publishedAt"], "notes": payload["notes"],
        "metadata": {"generatedBy": "ELM_AUTOCATALOG", "dollCount": len(payload["dolls"]),
                     "canonicalIdCount": len(ids), "catalogJsonSha256": catalog_hash},
    })
    (ROOT / "manifest.json").write_bytes(dump(updated))
    return version


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--publish", action="store_true", help="Build a full compatible release for verified dolls")
    args = cli.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    catalog_path = ROOT / manifest["catalogFile"]
    if catalog_path.parent != ROOT:
        raise ValueError("Unsafe catalog path in manifest")
    raw = catalog_path.read_bytes()
    if sha256(raw) != manifest.get("catalogSha256"):
        raise ValueError("Certified source catalog SHA-256 does not match manifest")
    catalog = json.loads(raw)
    if len(catalog["dolls"]) != int(manifest["recordCount"]):
        raise ValueError("Manifest count differs from certified source")
    products = fetch_products()
    additions, reviews = reconcile(products, catalog)
    OUT_CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    OUT_CANDIDATES.write_bytes(dump({"source": SOURCE_BASE, "productCount": len(products),
                                     "candidates": [r for r in reviews if r["status"] != "existing"]}))
    version = publish(catalog, manifest, additions) if args.publish else ""
    print(json.dumps({"productsSeen": len(products), "verifiedNewDolls": len(additions),
                      "reviewRequired": sum(r["status"] == "review_required" for r in reviews),
                      "publishedVersion": version or None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
