# bauble/plugins/garden/models/voucher.py

from bauble.db import Base
from sqlalchemy import Boolean, ForeignKey, Integer, Unicode
from sqlalchemy.orm import Mapped, mapped_column


class Voucher(Base):
    """
    :Table name: voucher

    :Columns:
      herbarium: :class:`sqlalchemy.types.Unicode`
        The name of the herbarium.
      code: :class:`sqlalchemy.types.Unicode`
        The herbarium code for the voucher.
      parent_material: :class:`sqlalchemy.types.Boolean`
        Is this voucher relative to the parent material of the accession.
      accession_id: :class:`sqlalchemy.types.Integer`
        Foreign key to the :class:`Accession` .


    """

    __tablename__: str = "voucher"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    herbarium: Mapped[str] = mapped_column(Unicode(5), nullable=False)
    code: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    parent_material: Mapped[bool] = mapped_column(Boolean, default=False)
    accession_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accession.id"), nullable=False
    )
