from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.database.database import Base


class MetaCampaignCell(Base):
    """
    Durable mapping between an MMI campaign cell and
    the corresponding live Meta objects.

    One cell represents one:

        campaign plan
        × audience / campaign variant
        × creative asset

    Meta IDs may be empty before the campaign is launched.
    """

    __tablename__ = "meta_campaign_cells"

    __table_args__ = (
        UniqueConstraint(
            "meta_campaign_variant_id",
            "asset_id",
            name="uq_meta_campaign_cell_variant_asset",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    meta_campaign_plan_id = Column(
        Integer,
        ForeignKey(
            "meta_campaign_plans.id"
        ),
        nullable=False,
        index=True,
    )

    meta_campaign_variant_id = Column(
        Integer,
        ForeignKey(
            "meta_campaign_variants.id"
        ),
        nullable=False,
        index=True,
    )

    asset_id = Column(
        Integer,
        ForeignKey(
            "assets.id"
        ),
        nullable=False,
        index=True,
    )

    meta_campaign_id = Column(
        String,
        nullable=True,
        index=True,
    )

    meta_adset_id = Column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )

    status = Column(
        String,
        nullable=False,
        default="planned",
    )
