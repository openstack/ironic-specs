.. ironic-specs documentation master file

==============================
OpenStack Ironic Project Plans
==============================

Priorities
==========

During each PTG (before Pike - each design summit), we agree what the whole
community wants to focus on for the upcoming release. This is the output of
those discussions:

.. toctree::
   :glob:
   :maxdepth: 1

   priorities/queens-priorities
   priorities/pike-priorities
   priorities/ocata-priorities
   priorities/newton-priorities
   priorities/mitaka-priorities


Specifications
==============

Specifications for the ironic project are available here. Specifications
begin life in the "approved" tree. They stay there (possibly beyond the
development cycle in which they had been approved), and once implemented,
are moved to the "implemented" tree for that development cycle.
Additionally, a "backlog" of ideas is maintained to indicate
the agreed-upon goals for the project which have no specific work being done
on them at this time.

Approved specifications
=======================

These specifications have been approved but have not been completely
implemented:

.. toctree::
   :glob:
   :maxdepth: 1

   specs/not-implemented/*


Back-log of ideas
=================
These specifications are ideas and features that are desirable but do not
have anyone working on them:

.. toctree::
   :glob:
   :maxdepth: 1

   specs/backlog/*


Implemented specifications
==========================

These specifications have been implemented and are grouped in the
development cycles in which they were completed.

Queens
------

9.2
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/9.2/*

Pike
------

9.1
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/9.1/*

9.0
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/9.0/*

8.0
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/8.0/*

Ocata
------

7.0
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/7.0/*

Newton
------

6.2
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/6.2/*

6.1
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/6.1/*

6.0
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/6.0/*

Mitaka
------

5.1
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/5.1/*

5.0
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/5.0/*

4.3
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/4.3/*

Liberty
-------

4.2
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/4.2/*

4.0
~~~

.. toctree::
   :glob:
   :maxdepth: 1

   specs/4.0/*

Kilo
----

.. toctree::
   :glob:
   :maxdepth: 1

   specs/kilo-implemented/*

Juno
----

.. toctree::
   :glob:
   :maxdepth: 1

   specs/juno-implemented/*

..
   ----------------
   The locations of specs were changed during the Liberty development
   cycle.  These are placeholders and specs in the old locations.
   They need to be available because there may be external references
   to them, but we don't want to explicitly provide links to them.

.. toctree::
   :glob:
   :hidden:

   specs/liberty/*
   specs/liberty-implemented/*
   specs/kilo/*
   specs/juno/*

..
   ----------------
   As of the start of the Mitaka development cycle, all approved specs
   will reside in specs/approved (not-yet-implemented as well as implemented
   specs). The files will not be moved (we hope). Instead, we will create
   directories with links to these files. The specs/approved directory
   will be hidden.

.. toctree::
   :glob:
   :hidden:

   specs/approved/*

==================
Indices and tables
==================

* :ref:`search`
