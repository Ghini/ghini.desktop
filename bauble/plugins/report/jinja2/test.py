#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2018 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardín Botánico de Quito
# Copyright 2018 Tanager Botanical Garden <tanagertourism@gmail.com>
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
import logging
import os
from typing import Any

import pytest
from bauble.plugins.report import get_pertinent_objects
from bauble.plugins.report.jinja2 import Jinja2FormatterPlugin
from bauble.utils import natsort_key
from sqlalchemy import select

logger: Any = logging.getLogger(__name__)


# Centralize delayed imports
def dynamic_import(module_name, class_name):
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


@pytest.fixture(scope="module")
def populate_test_data(session) -> None:
    """
    Populates the database with test data.
    """
    Family = dynamic_import("bauble.plugins.plants", "Family")
    Genus = dynamic_import("bauble.plugins.plants", "Genus")
    Species = dynamic_import("bauble.plugins.plants", "Species")
    GeographicArea = dynamic_import("bauble.plugins.plants", "GeographicArea")
    SpeciesDistribution = dynamic_import("bauble.plugins.plants", "SpeciesDistribution")
    VernacularName = dynamic_import("bauble.plugins.plants", "VernacularName")
    Accession = dynamic_import("bauble.plugins.garden.models", "Accession")
    Location = dynamic_import("bauble.plugins.garden.models", "Location")
    Plant = dynamic_import("bauble.plugins.garden.models", "Plant")

    fctr = gctr = sctr = actr = pctr = 0
    for _f in range(2):
        fctr += 1
        family = Family(id=fctr, family=f"fam{fctr}")
        session.add(family)
        for _g in range(2):
            gctr += 1
            genus = Genus(id=gctr, family=family, genus=f"gen{gctr}")
            session.add(genus)
            for _s in range(2):
                sctr += 1
                sp = Species(id=sctr, genus=genus, sp=f"sp{sctr}")
                geo = GeographicArea(id=sctr, name=f"Mexico{sctr}")
                dist = SpeciesDistribution(geographic_area_id=sctr)
                sp.distribution.append(dist)
                vn = VernacularName(id=sctr, species=sp, name=f"name{sctr}")
                session.add_all([sp, geo, dist, vn])
                for _a in range(2):
                    actr += 1
                    acc = Accession(id=actr, species=sp, code=f"{actr}")
                    session.add(acc)
                    for _p in range(2):
                        pctr += 1
                        loc = Location(id=pctr, code=f"{pctr}", name=f"site{pctr}")
                        plant = Plant(
                            id=pctr,
                            accession=acc,
                            location=loc,
                            code=f"{pctr}",
                            quantity=1,
                        )
                        session.add_all([loc, plant])
    if session.in_transaction():
        session.commit()


@pytest.mark.usefixtures("populate_test_data")
def test_format_all_templates(session):
    """
    Tests the formatting of all Jinja2 templates.
    """
    Plant = dynamic_import("bauble.plugins.garden.models", "Plant")
    selection = session.execute(select(Plant)).scalars().all()

    templates_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "templates"
    )
    template_files = filter(lambda x: x.endswith(".jj2"), os.listdir(templates_dir))

    for template_name in template_files:
        template_path = os.path.join(templates_dir, template_name)
        domain = Jinja2FormatterPlugin.get_iteration_domain(template_path)

        if domain == "":
            assert template_name.startswith("base.")
            continue

        cls = {
            "plant": Plant,
            "accession": dynamic_import("bauble.plugins.garden", "Accession"),
            "species": dynamic_import("bauble.plugins.plants", "Species"),
            "location": dynamic_import("bauble.plugins.garden", "Location"),
        }.get(domain, Plant)

        if cls:
            todo = sorted(get_pertinent_objects(cls, selection), key=natsort_key)
        else:
            todo = selection

        logger.debug(f"Formatting template: {template_path}")
        report = Jinja2FormatterPlugin.format(todo, template=template_path)

        assert isinstance(report, bytes)
