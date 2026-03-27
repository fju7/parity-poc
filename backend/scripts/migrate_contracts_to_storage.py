"""
One-time migration: move contract PDFs from billing_contracts.file_content
column to Supabase Storage bucket 'billing-contracts'.

For each row with file_content IS NOT NULL and storage_path IS NULL:
  1. Decode base64 → raw PDF bytes
  2. Upload to billing-contracts/{billing_company_id}/{contract_id}.pdf
  3. Set storage_path on the row
  4. Set file_content = NULL

Safe to run multiple times (skips rows that already have storage_path).

Usage:
  python3 backend/scripts/migrate_contracts_to_storage.py
"""

import base64
import os
import sys

from supabase import create_client


def migrate():
    url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not key:
        print("ERROR: Set SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY env var.")
        sys.exit(1)
    sb = create_client(url, key)

    # Find rows that still have file_content but no storage_path
    rows = sb.table("billing_contracts").select(
        "id, billing_company_id, file_content, filename"
    ).not_.is_("file_content", "null").is_("storage_path", "null").execute()

    if not rows.data:
        print("No contracts to migrate — all rows already use Storage.")
        return

    print(f"Found {len(rows.data)} contract(s) to migrate.")

    for row in rows.data:
        contract_id = row["id"]
        bc_id = row["billing_company_id"]
        file_b64 = row["file_content"]
        filename = row.get("filename") or "contract.pdf"

        storage_path = f"{bc_id}/{contract_id}.pdf"
        print(f"  Migrating {contract_id} ({filename}) → {storage_path} ...", end=" ")

        try:
            # Decode base64 → raw bytes
            pdf_bytes = base64.b64decode(file_b64)

            # Upload to Storage
            sb.storage.from_("billing-contracts").upload(
                path=storage_path,
                file=pdf_bytes,
                file_options={"content-type": "application/pdf"},
            )

            # Update row: set storage_path, clear file_content
            sb.table("billing_contracts").update({
                "storage_path": storage_path,
                "file_content": None,
            }).eq("id", contract_id).execute()

            print(f"OK ({len(pdf_bytes)} bytes)")
        except Exception as exc:
            print(f"FAILED: {exc}")

    print("Migration complete.")


if __name__ == "__main__":
    migrate()
