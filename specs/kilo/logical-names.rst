..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Ironic Logical Names
====================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/ironic/+spec/logical-names

Everything that is tracked in Ironic is done via UUID.  This isn't very
friendly to humans.  We should support nodes being referenced by a logical
name, in addition to the current method of being able to refer to them via
UUID.  This should be supported in the REST API and in our command-line client.


Problem description
===================

Operators, and other humans, that use Ironic find it awkward and error-prone
to use UUIDs to refer to entities that are tracked by Ironic.

However computers, and extremely geekly people, prefer to track things by the
canonical identifier - the UUID.

While humans are more likely to use the command-line tools, computers
are more likely to use the REST API.  However the opposite is also true,
consequently both the API and command-line client require updating to
support logical names for nodes.

It's useful to be able to assign semantic meaning to nodes - for example
datacenter location (i.e. 'DC6'), or node function (i.e. 'database') - to
assist operators in managing nodes in their network. The semantic identifier
of a node is analogous to the hostname for the node, and may indeed correlate.

An example of this might be where the logical name 'DC6-db-17' is associated
with a node with UUID '9e592cbe-e492-4e4f-bf8f-4c9e0ad1868f'.  In all
interactions with ironic, the node's UUID or logical name can be used to
identify the specific node.

Proposed change
===============

We propose adding a new concept to ironic, that being the <logical name>,
which can be used interchangeably with the <node uuid>.  Everywhere a
<node uuid> can be specified, we should be able to instead specify a
<logical name>, if such an association exists for that node.  This should be
the case for the REST API and python-ironicclient.

At the REST API level, the mechanisms to set/retrieve node fields
will be used to set/retrieve the logical name for a node.

At the python-ironiclient level, support will be added to manage associations
between a node and a <logical-name>.  See further details below.

Where a change in the interface is required, such as a new attribute on an
object, a new key in a dictionary, or a new field in POST data, the
<logical name> will be referred to as "name" (unless that is already used).
This is for consistency with other OpenStack APIs.

Alternatives
------------

None

Data model impact
-----------------

There should be a 1:1 mapping between a <logical name> and a <node uuid>.
We can consider a <logical name> as an alias for a <node uuid>.

When the version of ironic that includes these changes is run against an
existing installation, the database will be upgraded to support the addition
of the <logical name> field to the node object.

The association between logical-name and UUID will need to be stored as
a new attribute on the node object.

In the case where no logical name has been set, this field will be None.

What is a logical name?
~~~~~~~~~~~~~~~~~~~~~~~
This change introduces the concept of a <logical name> to ironic so that a
human readable name can be associated with nodes.  This <logical name> should
be hostname safe, that is, the node logical name should also be usable as the
hostname for the instance.  For this to be true, the following references
should be used to define what is a valid <logical name>: [wikipedia:hostname],
[RFC952] and [RFC1123].

In simple english, what this means is that <logical names>s can be between
1 and 63 characters long, with the valid characters being [a-z0-9] and '-',
except that a <logical name> cannot begin or end with a '-'.

As a regular expression, this can be represented as:
<logical name> == [a-z0-9]([a-z0-9\-]{0,61}[a-z0-9]|[a-z0-9]{0,62})?

Note: It is recognised that a valid <logical name> could also be a valid
<node uuid>, which could lead to confusion.  As a consequence, logical
names will be rejected as invalid if they are valid UUIDs.

Search Ordering (implementation hint)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
As we now have two options to specify a node - the logical name and the node
uuid - it is suggested that the following search order be implemented
to define the behaviour of ironic. The following pseudo-code is provided to
assist implementation:

  if is_uuid_like(value):
    # handle it like a UUID
  else if is_hostname_like(value):
    # handle it like a logical name
  else:
    # invalid format, raise error

REST API impact
---------------

A number of existing APIs will need to be modified to support the use of
<logical_name>.

The following APIs will add in a new JSON body parameter named "name":

* DELETE /v1/nodes
* PATCH /v1/nodes
* GET /v1/nodes/validate

The following APIs will add in a new response body field named "name":

* GET /v1/nodes

The following APIs will reflect the existing node_uuid version of this
API, along with adding support to specify logical_name instead of node_uuid
in the URL:

* GET /v1/nodes/(node_logical_name)
* PUT /v1/nodes/(node_logical_name)/maintenance
* DELETE /v1/nodes/(node_logical_name)/maintenance
* GET /v1/nodes/(node_logical_name)/management/boot_device
* PUT /v1/nodes/(node_logical_name)/management/boot_device
* GET /v1/nodes/(node_logical_name)/management/boot_device/supported
* GET /v1/nodes/(node_logical_name)/states
* PUT /v1/nodes/(node_logical_name)/states/power
* PUT /v1/nodes/(node_logical_name)/states/provision
* GET /v1/nodes/(node_logical_name)/states/console
* PUT /v1/nodes/(node_logical_name)/states/console
* POST /v1/nodes/(node_logical_name)/vendor_passthru

RPC API impact
--------------
None

Driver API impact
-----------------
None

Nova driver impact
------------------
This change as specified here is wholly contained with ironic itself.  It is
most probably beneficial to expose the concept of a logical name to outside
ironic for use in the Nova API.

If required, this will be addressed in an independent spec.

Security impact
---------------
None

Other end user impact
---------------------
If Horizon allows a user to enter a node UUID, and validates it as conforming
to a particular regex, then this will most likely require change to support
either a <node uuid> or <logical name>.

python-ironicclient
~~~~~~~~~~~~~~~~~~~
In each sub-command in python-ironicclient where a node UIUD can be specified,
we will need to be able to support a logical name in its place.  Please see
the detailed changes in the REST API section for an idea of the scope of
change required.

Scalability impact
------------------
None

Performance Impact
------------------
None

Other deployer impact
---------------------
None

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------
Primary assignee:
  mrda - Michael Davies <michael@the-davies.net>

Work Items
----------
1. REST API additions and modifications
2. python-ironicclient additions and modifications

Dependencies
============
None

Testing
=======
Unit testing will be sufficient to verify the veracity of this change

Upgrades and Backwards Compatibility
====================================
As mentioned above, when the code that includes this change is run against a
previous Ironic install that does not have this change, the database will
need to have it's schema updated to add in the additional field 'name'.

Documentation Impact
====================
Online documentation for both the Ironic API and python-ironicclient will need
to be updated to accompany this change.

References
==========
The need for this change was discussed at the Kilo Summit in Paris
(ref https://etherpad.openstack.org/p/kilo-ironic-making-it-simple)

* [wikipedia:hostname] - http://en.wikipedia.org/wiki/Hostname

* [RFC952] - http://tools.ietf.org/html/rfc952

* [RFC1123] - http://tools.ietf.org/html/rfc1123

