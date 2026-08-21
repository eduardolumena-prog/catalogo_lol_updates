from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

VERSION = "5.3.3-global-final"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "packages" / "5.3.2-global-final" / "catalog.json"
BASELINE_PATH = ROOT / "catalog.v5.2.5-global-final.json"
PACKAGE_DIR = ROOT / "packages" / VERSION
PACKAGE_JSON = PACKAGE_DIR / "catalog.json"
PACKAGE_ZIP = PACKAGE_DIR / "catalog_package.zip"
ROOT_JSON = ROOT / f"catalog.{VERSION}.json"
MANIFEST_PATH = ROOT / "manifest.json"
AUDIT_DIR = ROOT / "audit"
AUDIT_PATH = AUDIT_DIR / "AUTOPILOT_5_3_3_AUDIT.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def first(obj: dict, *keys, default=None):
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


def as_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_record(src: dict) -> dict:
    canonical = str(first(src, "canonicalId", "canonical_id", "id", default="")).strip()
    official = str(first(src, "officialCode", "official_code", "codigoOficial", "codigo_oficial", default="")).strip()
    name = str(first(src, "name", "nombre", default="")).strip()
    series = str(first(src, "seriesCode", "series_code", "series", "serie", default="")).strip()
    collection = str(first(src, "collectionCode", "collection_code", "collection", "coleccion", default=series)).strip() or series
    rarity = str(first(src, "rarity", "rareza", default="")).strip()
    year = as_int(first(src, "releaseYear", "release_year", "year", "anio", "año"))
    description = str(first(src, "description", "descripcion", default="")).strip()
    club = str(first(src, "club", default="")).strip()
    ball_type = str(first(src, "ballType", "ball_type", "tipo", "type", default="")).strip()
    manufacturer_sku = str(first(src, "manufacturerSku", "manufacturer_sku", "sku", default="")).strip()
    image = str(first(src, "officialImage", "official_image", "image", "imagen", default="")).strip()
    revision = as_int(first(src, "revision", default=1)) or 1
    source_ref = first(src, "sourceRef", "source_ref")
    if not source_ref:
        refs = first(src, "sourceRefs", "source_refs", default=[])
        if isinstance(refs, list) and refs:
            source_ref = str(refs[0])
        else:
            source_ref = ""
    metadata = first(src, "metadata", default={})
    if not isinstance(metadata, dict):
        metadata = {"legacyMetadata": metadata}

    if not canonical:
        canonical = f"legacy:{official or name}"

    return {
        "canonicalId": canonical,
        "officialCode": official,
        "manufacturerSku": manufacturer_sku,
        "collectionCode": collection,
        "seriesCode": series,
        "name": name,
        "releaseYear": year,
        "rarity": rarity,
        "description": description,
        "club": club,
        "ballType": ball_type,
        "officialImage": image,
        "sourceRef": str(source_ref or ""),
        "isActive": True,
        "revision": revision,
        "metadata": metadata,
    }


def main() -> None:
    source = read_json(SOURCE_PATH)
    baseline = read_json(BASELINE_PATH)

    records = source.get("master_records") or source.get("masterRecords") or source.get("records")
    if not isinstance(records, list):
        raise RuntimeError("Source catalog does not contain master_records/masterRecords/records list")
    if len(records) != 713:
        raise RuntimeError(f"Expected 713 source records, got {len(records)}")

    dolls = [normalize_record(r) for r in records]
    if len(dolls) != 713:
        raise RuntimeError("Normalized doll count is not 713")

    source_ids = [str(first(r, "canonicalId", "canonical_id", "id", default="")).strip() for r in records]
    source_ids = [x or f"legacy:{str(first(r, 'officialCode', 'codigoOficial', 'name', 'nombre', default='')).strip()}" for x, r in zip(source_ids, records)]
    output_ids = [d["canonicalId"] for d in dolls]

    if len(set(source_ids)) != 713:
        raise RuntimeError(f"Source canonical identity set is not unique: {len(set(source_ids))}")
    if len(set(output_ids)) != 713:
        raise RuntimeError(f"Output canonical identity set is not unique: {len(set(output_ids))}")
    if set(source_ids) != set(output_ids):
        raise RuntimeError("Identity set changed during normalization")

    teezy_matches = [d for d in dolls if d.get("officialCode") == "BOYS-311" or d.get("name") == "$teezy"]
    if len(teezy_matches) != 1:
        raise RuntimeError(f"Expected exactly one $teezy/BOYS-311 record, got {len(teezy_matches)}")
    teezy = teezy_matches[0]
    teezy_before = dict(teezy)
    teezy.update({
        "officialCode": "BOYS-311",
        "name": "$teezy",
        "collectionCode": "CG-07",
        "seriesCode": "CG-07",
        "rarity": "ULTRA_RARE",
        "releaseYear": 2020,
        "club": "Glee Club",
        "officialImage": "",
    })
    teezy_metadata = dict(teezy.get("metadata") or {})
    teezy_metadata.update({
        "imageCertification": "NO_CERTIFIED_INDIVIDUAL_PRIMARY_IMAGE",
        "imageCorrection": "INVALID_PRIMARY_IMAGE_CLEARED",
        "evidence": ["guide:guide_27", "guide:guide_27:product-signature"],
    })
    teezy["metadata"] = teezy_metadata

    collections_map = {}
    series_map = {}
    for d in dolls:
        cc = str(d.get("collectionCode") or "").strip()
        sc = str(d.get("seriesCode") or "").strip()
        if cc:
            collections_map.setdefault(cc, {
                "code": cc,
                "name": cc,
                "description": "",
                "isActive": True,
                "revision": 1,
                "metadata": {},
            })
        if sc:
            series_map.setdefault(sc, {
                "code": sc,
                "collectionCode": cc or sc,
                "name": sc,
                "description": "",
                "releaseYear": None,
                "isActive": True,
                "revision": 1,
                "metadata": {},
            })

    accessories = baseline.get("accessories", []) if isinstance(baseline.get("accessories", []), list) else []
    doll_accessories = baseline.get("dollAccessories", []) if isinstance(baseline.get("dollAccessories", []), list) else []
    relations = baseline.get("relations", []) if isinstance(baseline.get("relations", []), list) else []
    tags = baseline.get("tags", []) if isinstance(baseline.get("tags", []), list) else []
    doll_tags = baseline.get("dollTags", []) if isinstance(baseline.get("dollTags", []), list) else []
    replace_images = baseline.get("replaceImages", []) if isinstance(baseline.get("replaceImages", []), list) else []

    cleaned_replacements = []
    for item in replace_images:
        if not isinstance(item, dict):
            continue
        if str(item.get("dollCode", "")) == "BOYS-311":
            continue
        cleaned_replacements.append(item)
    cleaned_replacements.append({"dollCode": "BOYS-311", "images": []})

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload = {
        "format": "lol-catalog-update-v1",
        "catalogVersion": VERSION,
        "schemaVersion": 2,
        "publishedAt": now,
        "notes": "713-record app-compatible maintenance publication. $teezy invalid primary image cleared; no personal data touched.",
        "collections": sorted(collections_map.values(), key=lambda x: x["code"]),
        "series": sorted(series_map.values(), key=lambda x: x["code"]),
        "dolls": dolls,
        "accessories": accessories,
        "dollAccessories": doll_accessories,
        "replaceImages": cleaned_replacements,
        "relations": relations,
        "tags": tags,
        "dollTags": doll_tags,
    }

    if len(payload["dolls"]) != 713:
        raise RuntimeError("Payload doll count mismatch")
    if len({d["canonicalId"] for d in payload["dolls"]}) != 713:
        raise RuntimeError("Payload identity uniqueness failed")
    if teezy.get("officialImage") != "":
        raise RuntimeError("$teezy officialImage was not cleared")

    write_json(PACKAGE_JSON, payload)
    write_json(ROOT_JSON, payload)

    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PACKAGE_JSON, arcname="catalog.json")

    with zipfile.ZipFile(PACKAGE_ZIP, "r") as zf:
        names = zf.namelist()
        if names != ["catalog.json"]:
            raise RuntimeError(f"Unexpected ZIP contents: {names}")
        zipped_catalog = json.loads(zf.read("catalog.json").decode("utf-8"))
        if zipped_catalog.get("catalogVersion") != VERSION or len(zipped_catalog.get("dolls", [])) != 713:
            raise RuntimeError("ZIP catalog validation failed")

    package_sha = sha256_file(PACKAGE_ZIP)
    catalog_sha = sha256_file(PACKAGE_JSON)

    package_url = f"https://raw.githubusercontent.com/eduardolumena-prog/catalogo_lol_updates/main/packages/{VERSION}/catalog_package.zip"
    catalog_url = f"https://raw.githubusercontent.com/eduardolumena-prog/catalogo_lol_updates/main/catalog.{VERSION}.json"
    manifest = {
        "baseCount": 713,
        "baseVersion": "5.3.2-global-final",
        "catalogFile": f"catalog.{VERSION}.json",
        "catalogPath": f"catalog.{VERSION}.json",
        "catalogSha256": catalog_sha,
        "catalogUrl": catalog_url,
        "catalogVersion": VERSION,
        "downloadUrl": package_url,
        "format": "lol-catalog-update-v1",
        "identityCorrections": 0,
        "metadata": {
            "canonicalIdCount": 713,
            "catalogJsonSha256": catalog_sha,
            "dollCount": 713,
            "generatedBy": "AUTOPILOT_PUBLISH_5_3_3",
            "imageCorrections": 1,
            "teezyPrimaryImageCleared": True,
        },
        "newRecords": 0,
        "notes": "5.3.3 maintenance release. 713 identities unchanged. $teezy invalid primary image cleared; app-compatible payload.",
        "packageFile": f"packages/{VERSION}/catalog_package.zip",
        "packageUrl": package_url,
        "publishedAt": now,
        "recordCount": 713,
        "schemaVersion": 2,
        "seedIntegrated": True,
        "sha256": package_sha,
        "zipUrl": package_url,
    }
    write_json(MANIFEST_PATH, manifest)

    audit = {
        "version": VERSION,
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "sourceCount": len(records),
        "outputCount": len(dolls),
        "sourceUniqueIdentities": len(set(source_ids)),
        "outputUniqueIdentities": len(set(output_ids)),
        "identitySetEqual": set(source_ids) == set(output_ids),
        "duplicateCanonicalIds": len(output_ids) - len(set(output_ids)),
        "teezy": {
            "canonicalId": teezy.get("canonicalId"),
            "officialCode": teezy.get("officialCode"),
            "beforeOfficialImage": teezy_before.get("officialImage", ""),
            "afterOfficialImage": teezy.get("officialImage", ""),
            "collectionCode": teezy.get("collectionCode"),
            "seriesCode": teezy.get("seriesCode"),
            "rarity": teezy.get("rarity"),
            "releaseYear": teezy.get("releaseYear"),
            "club": teezy.get("club"),
            "replaceImagesCleared": True,
        },
        "packageSha256": package_sha,
        "catalogSha256": catalog_sha,
        "zipFiles": ["catalog.json"],
        "manifestPackageShaMatches": manifest["sha256"] == package_sha,
        "recordCount713": len(dolls) == 713,
        "result": "PASS",
    }
    write_json(AUDIT_PATH, audit)

    print("AUTOPILOT_5_3_3_RESULT=PASS")
    print(f"CATALOG_VERSION={VERSION}")
    print("RECORD_COUNT=713")
    print("UNIQUE_IDENTITIES=713")
    print("IDENTITY_SET_EQUAL=true")
    print("TEEZY_PRIMARY_IMAGE_CLEARED=true")
    print(f"PACKAGE_SHA256={package_sha}")
    print(f"CATALOG_SHA256={catalog_sha}")


if __name__ == "__main__":
    main()

# trigger diagnostic-enabled autopilot run
