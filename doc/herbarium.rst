Ghini for herbaria
===========================

Ghini 1.1 can be used by botanic gardens, herbariums, or collectors. We here
focus on ghini for herbaria and collectors.  It is just a configuration
setting separating the version for herbariums and collectors.

Database view for herbaria and collectors
----------------------------------------------

.. figure:: images/schemas/ghini-herbarium-11.svg

            core structure

The focus of a ``herbarium`` is on plant material collected by
``collectors`` and sent to the herbarium for reference, or preservation.

The focus of a ``collector`` is on the plant material they collected, which
is possibly partly distributed across several ``herbaria`` as well as still
in their possession.

Plant material is collected during field ``expeditions``. A group of people
participate to a field ``expedition`` to a specific ``place``, and for a
specific period of time.

Collected material is organized in ``accessions``. An ``accession`` is
relative to a single plant specimen observed during a single ``expedition``
by one ``collector``, who decides which and how many ``samples`` are needed
to completely describe the specimen. The ``collector`` generally performs
the first ``verification``, associating the ``accession`` to a ``taxon``.
Later ``verifications`` will be added by taxonomists studying a herbarium or
collector's collection.

expedición de varias PERSONAS, se escogen LUGARES en que todavía no hay
datos botánicos, el grupo se queda varios DÍAS, el campo tiene COORDENADAS
conocidas, puede ser que se hagan PARCELAS(?) (permanentes o menos, pero que
está georeferenciada), puede ser que se colecte recorriendo trochas, o
rutas. si se hace parcela, puede ser que no sea toda el mismo
ECOSISTEMA. recorriendo trochas o rutas igual cada PLANTA colectada hay que
anotar en qué clase de ECOSISTEMA fue encontrada. si está en parcela(?), tienes
las COORDENADAS relativas CARTESIANAS al interior de la parcela, si está en
la trocha, tienes las coordenadas GPS.

tu vas por ahí ves algo interesante lo colectas (en cuantos juegos, tres si
posible, más si no hace daño, uno para el herbario, otro para el colectante,
el tercero opcional para la entidad externa si hay), se prensa, se seca, en
alcól o no, si no hay secadora se coloca en alcól, si hay secadora se prensa
y se pone a la secadora.

descripción de las condiciones en que se preparó el especímen, y de toda
información que no va a encontrarse en el voucher. el especimen puede haber
pasado por alcol. anotar colores porque se pierden si pasan por
alcol. también hay colores que se pierden en el secado, por eso se anotan
todos los colores. se tomaron foto? 

al momento de colectar, anotar presencia de latex, si está fertil, si tiene
flores, si tiene frutos, botones.

le haces corte al tronco para observar olores o resina. por ejemplo mango, o
marañón, tienen olor fuerte. es una descripción personal, no hay standard.

cualquier otra caracteristica que piensas se pueda perder al secarse.

anotar el habito de la planta. árbol, arbusto, ...

DAP, altura estimados.

asociación con otras plantas.

montar especímenes
=======================
