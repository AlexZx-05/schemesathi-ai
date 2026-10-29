from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migration_upgrade_and_downgrade_profile_table(tmp_path, monkeypatch) -> None:
    database = tmp_path / "phase4_migrations.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database.as_posix()}")
    config = Config("backend\\alembic.ini")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    tables = set(inspect(engine).get_table_names())
    assert {
        "users",
        "user_profiles",
        "schemes",
        "scheme_categories",
        "scheme_eligibility_rules",
        "scheme_knowledge_chunks",
        "user_scheme_document_progress",
        "scheme_documents",
        "scheme_sources",
        "scheme_deadlines",
        "saved_schemes",
        "application_tracking",
        "notifications",
        "notification_preferences",
        "conversations",
        "conversation_messages",
        "scheme_reports",
        "audit_logs",
    }.issubset(tables)
    assert "profiles" not in tables
    assert "scheme_review_history" in tables
    eligibility_columns = {
        column["name"]
        for column in inspect(engine).get_columns("scheme_eligibility_rules")
    }
    assert {"rule_data", "source_id"}.issubset(eligibility_columns)
    assert "is_admin" in {
        column["name"] for column in inspect(engine).get_columns("users")
    }
    assert "reviewed_by_user_id" in {
        column["name"] for column in inspect(engine).get_columns("schemes")
    }
    assert "reviewed_by_user_id" in {
        column["name"] for column in inspect(engine).get_columns("scheme_sources")
    }
    assert {"reviewed_by_user_id", "review_notes"}.issubset(
        {
            column["name"]
            for column in inspect(engine).get_columns("scheme_reports")
        }
    )
    assert {"citations", "feedback"}.issubset(
        {
            column["name"]
            for column in inspect(engine).get_columns("conversation_messages")
        }
    )
    application_columns = {
        column["name"] for column in inspect(engine).get_columns("application_tracking")
    }
    assert {"submitted_at", "status_changed_at"}.issubset(application_columns)
    deadline_columns = {
        column["name"] for column in inspect(engine).get_columns("scheme_deadlines")
    }
    assert {"source_id", "last_verified_at"}.issubset(deadline_columns)
    notification_columns = {
        column["name"] for column in inspect(engine).get_columns("notifications")
    }
    assert {
        "dedupe_key",
        "deadline_at",
        "email_delivery_status",
        "email_attempts",
        "is_valid",
    }.issubset(notification_columns)
    preference_columns = {
        column["name"]
        for column in inspect(engine).get_columns("notification_preferences")
    }
    assert {
        "reminders_enabled",
        "deadline_reminders_enabled",
        "timezone",
    }.issubset(preference_columns)

    command.downgrade(config, "0003_onboarding_auth_workflows")
    tables = set(inspect(engine).get_table_names())
    assert "profiles" in tables
    assert "schemes" not in tables

    command.upgrade(config, "head")
    assert "user_profiles" in set(inspect(engine).get_table_names())
    engine.dispose()
