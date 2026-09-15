from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "093_whu_core_execution_receipts.sql"
)
SQL = MIGRATION.read_text(encoding="utf-8")


def test_receipt_tables_are_not_client_accessible():
    for table in ("whu_core_executions", "whu_core_execution_attempt_events"):
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in SQL
        assert f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY" in SQL
        assert f"REVOKE ALL ON public.{table} FROM PUBLIC, anon, authenticated" in SQL


def test_receipt_tables_are_append_only():
    assert "BEFORE UPDATE OR DELETE ON public.whu_core_executions" in SQL
    assert "BEFORE UPDATE OR DELETE ON public.whu_core_execution_attempt_events" in SQL


def test_storage_boundary_refuses_error_to_completed_transition():
    assert "previous.state <> 'RUNNING'" in SQL
    assert "NEW.state NOT IN ('COMPLETED', 'ERROR', 'CANCELLED')" in SQL


def test_unknown_pricing_cannot_carry_numeric_zero():
    assert "pricing_state = 'UNKNOWN' AND cost_usd IS NULL" in SQL
