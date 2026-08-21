from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

VERSION = "5.3.3-global-final"
ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "packages" / "5.3.2-global-final" / "catalog.json"
PACKAGE_DIR = ROOT / "packages" / VERSION
PACKAGE_JSON = PACKAGE_DIR / "catalog.json"
PACKAGE_ZIP = PACKAGE_DIR / "catalog_package.zip"
ROOT_JSON = ROOT / f"catalog.{VERSION}.json"
MANIFEST_PATH = ROOT / "manifest.json"
AUDIT_PATH = ROOT / "audit" / "AUTOPILOT_5_3_3_AUDIT.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_identity(d: dict) -> str:
    value = str(d.get("canonicalId") or "").strip()
    if value:
        return value
    code = str(d.get("officialCode") or "").strip()
    name = str(d.get("name") or "").strip()
    return f"legacy:{code or name}"


def main() -> None:
    source = read_json(SOURCE_PATH)
    source_dolls = source.get("dolls")
    if not isinstance(source_dolls, list):
        raise RuntimeError("Certified 5.3.2 source does not contain dolls[]")
    if len(source_dolls) != 713:
        raise RuntimeError(f"Expected 713 dolls, got {len(source_dolls)}")

    source_ids = [canonical_identity(d) for d in source_dolls]
    if len(set(source_ids)) != 713:
        raise RuntimeError(f"Source identity uniqueness failed: {len(set(source_ids))}/713")

    payload = copy.deepcopy(source)
    payload["format"] = "lol-catalog-update-v1"
    payload["catalogVersion"] = VERSION
    payload["schemaVersion"] = 2
    payload["publishedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload["notes"] = "713-record maintenance publication. $teezy invalid primary image cleared; identities and personal data preserved."

    dolls = payload["dolls"]
    teezy_matches = [d for d in dolls if str(d.get("officialCode") or "") == "BOYS-311" or str(d.get("name") or "") == "$teezy"]
    if len(teezy_matches) != 1:
        raise RuntimeError(f"Expected exactly one $teezy/BOYS-311, got {len(teezy_matches)}")

    teezy = teezy_matches[0]
    before_image = str(teezy.get("officialImage") or "")
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
    md = teezy.get("metadata")
    if not isinstance(md, dict):
        md = {}
    md.update({
        "imageCertification": "NO_CERTIFIED_INDIVIDUAL_PRIMARY_IMAGE",
        "imageCorrection": "INVALID_PRIMARY_IMAGE_CLEARED",
        "evidence": ["guide:guide_27", "guide:guide_27:product-signature"],
    })
    teezy["metadata"] = md

    replacements = payload.get("replaceImages")
    if not isinstance(replacements, list):
        replacements = []
    replacements = [r for r in replacements if not (isinstance(r, dict) and str(r.get("dollCode") or "") == "BOYS-311")]
    replacements.append({"dollCode": "BOYS-311", "images": []})
    payload["replaceImages"] = replacements

    output_ids = [canonical_identity(d) for d in dolls]
    if len(dolls) != 713:
        raise RuntimeError("Output doll count changed")
    if len(set(output_ids)) != 713:
        raise RuntimeError("Output identity uniqueness failed")
    if set(source_ids) != set(output_ids):
        raise RuntimeError("Identity set changed")
    if teezy.get("officialImage") != "":
        raise RuntimeError("$teezy officialImage was not cleared")

    # Preserve required updater arrays even when empty.
    for key in ("collections", "series", "accessories", "dollAccessories", "relations", "tags", "dollTags"):
        if key not in payload or not isinstance(payload[key], list):
            payload[key] = []

    write_json(PACKAGE_JSON, payload)
    write_json(ROOT_JSON, payload)

    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(PACKAGE_JSON, arcname="catalog.json")

    with zipfile.ZipFile(PACKAGE_ZIP, "r") as zf:
        if zf.namelist() != ["catalog.json"]:
            raise RuntimeError(f"Unexpected ZIP contents: {zf.namelist()}")
        zipped = json.loads(zf.read("catalog.json").decode("utf-8"))
        if zipped.get("catalogVersion") != VERSION:
            raise RuntimeError("ZIP catalogVersion mismatch")
        if len(zipped.get("dolls") or []) != 713:
            raise RuntimeError("ZIP doll count mismatch")

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
            "teezyPrimaryImageCleared": True
        },
        "newRecords": 0,
        "notes": "5.3.3 maintenance release. 713 identities unchanged. $teezy invalid primary image cleared; app-compatible payload.",
        "packageFile": f"packages/{VERSION}/catalog_package.zip",
        "packageUrl": package_url,
        "publishedAt": payload["publishedAt"],
        "recordCount": 713,
        "schemaVersion": 2,
        "seedIntegrated": True,
        "sha256": package_sha,
        "zipUrl": package_url
    }
    write_json(MANIFEST_PATH, manifest)

    audit = {
        "version": VERSION,
        "source": str(SOURCE_PATH.relative_to(ROOT)),
        "sourceCount": 713,
        "outputCount": 713,
        "sourceUniqueIdentities": len(set(source_ids)),
        "outputUniqueIdentities": len(set(output_ids)),
        "identitySetEqual": set(source_ids) == set(output_ids),
        "duplicateCanonicalIds": len(output_ids) - len(set(output_ids)),
        "teezy": {
            "canonicalId": teezy.get("canonicalId"),
            "officialCode": teezy.get("officialCode"),
            "beforeOfficialImage": before_image,
            "afterOfficialImage": teezy.get("officialImage"),
            "collectionCode": teezy.get("collectionCode"),
            "seriesCode": teezy.get("seriesCode"),
            "rarity": teezy.get("rarity"),
            "releaseYear": teezy.get("releaseYear"),
            "club": teezy.get("club"),
            "replaceImagesCleared": True
        },
        "packageSha256": package_sha,
        "catalogSha256": catalog_sha,
        "zipFiles": ["catalog.json"],
        "manifestPackageShaMatches": manifest["sha256"] == package_sha,
        "recordCount713": True,
        "result": "PASS"
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
