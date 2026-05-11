"""initial reservations schema

Revision ID: 202605110001
Revises:
Create Date: 2026-05-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605110001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_locations_id"), "locations", ["id"], unique=False)

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("location_id", "name", name="uq_rooms_location_name"),
    )
    op.create_index(op.f("ix_rooms_id"), "rooms", ["id"], unique=False)
    op.create_index(op.f("ix_rooms_location_id"), "rooms", ["location_id"], unique=False)

    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responsible", sa.String(length=180), nullable=False),
        sa.Column("coffee_required", sa.Boolean(), nullable=False),
        sa.Column("people_count", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=80), nullable=False),
        sa.Column("created_by_email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reservations_end_datetime"), "reservations", ["end_datetime"], unique=False)
    op.create_index(op.f("ix_reservations_id"), "reservations", ["id"], unique=False)
    op.create_index(op.f("ix_reservations_location_id"), "reservations", ["location_id"], unique=False)
    op.create_index(op.f("ix_reservations_room_id"), "reservations", ["room_id"], unique=False)
    op.create_index(op.f("ix_reservations_start_datetime"), "reservations", ["start_datetime"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reservations_start_datetime"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_room_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_location_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_end_datetime"), table_name="reservations")
    op.drop_table("reservations")
    op.drop_index(op.f("ix_rooms_location_id"), table_name="rooms")
    op.drop_index(op.f("ix_rooms_id"), table_name="rooms")
    op.drop_table("rooms")
    op.drop_index(op.f("ix_locations_id"), table_name="locations")
    op.drop_table("locations")
