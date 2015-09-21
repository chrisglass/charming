# Copyright 2014-2015 Canonical Limited.
#
# This file is part of charming, a python library to make charms easier to
# write.
#
# charming is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# charming is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with charming.  If not, see <http://www.gnu.org/licenses/>.

"Interactions with the Juju environment"
# Copyright 2015 Christopher Glass.
#
# Authors:
#  Charm Helpers Developers <juju@lists.ubuntu.com>
#  Christopher Glass <tribaal@ubuntu.com>

from __future__ import print_function
from distutils.version import LooseVersion
import glob
import os
import json
import yaml
import subprocess
import tempfile
from subprocess import CalledProcessError

from charming.juju.execute import execute_command


class UnregisteredHookError(Exception):
    """Raised when an undefined hook is called"""
    pass



class Environment(object):
    """
    A class representing the juju environment available to the charm hook.
    """

    charm_dir_key = "CHARM_DIR"
    hook_name_key = "JUJU_HOOK_NAME"
    local_unit_name_key = "JUJU_UNIT_NAME"
    relation_id_key = "JUJU_RELATION_ID"
    relation_key = "JUJU_RELATION"
    remote_unit_name_key = "JUJU_REMOTE_UNIT"

    def __init__(self, environment_dict=os.environ,
                 command_runner=execute_command):
        self.environment = environment_dict.copy()
        self.command_runner = command_runner
        self.metadata = None

    def get_charm_dir(self):
        """Return the root directory of the current charm"""
        return self.environment.get('CHARM_DIR')

    def get_metadata(self):
        """Get the current charm metadata.yaml contents as a python object"""
        if self.metadata is None:
            metadata_path = os.path.join(self.get_charm_dir(), "metadata.yaml")
            with open(metadata_path, "r") as md:
                self.metadata = yaml.safe_load(md)
        return self.metadata

    def charm_name(self):
        """Get the name of the current charm as is specified on metadata.yaml"""
        return self.get_metadata().get('name')


    def unit_get(self, attribute):
        """Get the passed unit's attribute.

        @param attribute: The Attribute to get for the current unit."""
        cmd = ['unit-get', '--format=json', attribute]
        try:
            result = self.command_runner(cmd)
            return json.loads(result)
        except ValueError:
            return None

    def get_local_unit_name(self):
        """
        Return the name of the local Unit or None if run outside of a juju
        context.
        """
        return self.environment.get(self.local_unit_name_key)

    def get_local_service_name(self):
        """
        Return the name of the service the caller is a unit of.

        Exemple: calling from the unit "mysql/0" will return "mysql"
        """
        return self.get_local_unit_name().split('/')[0]

    def get_juju_hook_name(self):
        """
        Return the name of the currently executing juju hook.
        """
        return self.environment.get(self.hook_name_key)

    # COULD BE A RELATIONS CLASS

    def is_in_relation_hook(self):
        """
        Is the process calling this executed in a hook environment as part of
        a hook relation?
        """
        return self.relation_key in self.environment

    def get_remote_unit_name(self):
        """
        When run from within a relation hook, return the name of the remote
        unit.
        """
        return self.environment.get(self.remote_unit_name_key)

    def get_remote_service_name(self, relation_id):
        """
        Return the remote's service name for a given relation ID, or None for
        invlaide relation ids.
        """
        units = self.get_related_units(relation_id)
        if not units:
            return None
        return units[0].split('/')[0]  # The name of the service.

    def get_current_relation_id(self):
        """Return the current relation's ID."""
        return self.environment.get(self.relation_id_key)

    def get_relation_id(self, relation_name, service_or_unit):
        """
        Return the relation ID for the given relation name and service.

        @param relation_name: the relation name to get the ID for.
        @param service_or_unit: the name of the juju service or unit to get the
            relation ID for.
        """
        service_name = service_or_unit.split('/')[0]
        for relid in self.get_relation_ids(relation_name):
            remote_service = self.get_remote_service_name(relid)
            if remote_service == service_name:
                return relid
        return None  # Relation ID was not found.

    def get_relation_type(self):
        """
        Return the type of relation the called process is in, or None if this
        isn't called as part of a relation.
        """
        return self.environment.get(self.relation_key)

    def relation_get(self, attribute=None, unit=None, relation_id=None):
        """Get the key-value information the other unit has set on the
        selected relation, or None if it has not yet done so.

        @param attribute: If provided, narrows down the returned value to the
            specific attribute, if set in the relation data.
        @param unit: If provided, narrows down the output data to only data
            provided by this specific unit.
        @param relation_id: If provided, narrows down the result to only the
            information provided for this specific relation ID.
        @returns A dict representation of the values set in the relation data,
            or None in case the relation data set is empty.
        """

        cmd = ['relation-get', '--format=json']
        if relation_id:
            cmd.append('-r')
            cmd.append(relation_id)
        cmd.append(attribute or '-')
        if unit:
            cmd.append(unit)
        try:
            result = self.command_runner(cmd)
            return json.loads(result)
        except ValueError:
            return None
        except CalledProcessError as e:
            if e.returncode == 2:
                return None
            raise

    def relation_set(self, relation_id=None, data=None, **kwargs):
        """Set relation information for the current unit.

        All extra keyword parameters to this function will be appended to the
        data dictionnary.

        @param data: A dict representation of the data to set on the relation.
        """
        data = data if data else {}
        cmd = ['relation-set']
        help_output = self.command_runner(cmd + ["--help"])
        accepts_file = "--file" in help_output

        if relation_id is not None:
            cmd.extend(('-r', relation_id))

        relation_data = data.copy()
        relation_data.update(kwargs)

        # Force value to be a string: it always should, but some call sites
        # might pass in things like dicts or numbers.
        for key, value in relation_data.items():
            if value is not None:
                relation_data[key] = "{}".format(value)

        if accepts_file:
            # --file was introduced in Juju 1.23.2. Use it by default if
            # available, since otherwise we'll break if the relation data is
            # too big. Ideally we should tell relation-set to read the data
            # from stdin, but that feature is broken in 1.23.2: Bug #1454678.
            with tempfile.NamedTemporaryFile(delete=False) as settings_file:
                settings_file.write(
                    yaml.safe_dump(relation_data).encode("utf-8"))
            self.command_runner(cmd + ["--file", settings_file.name])
            os.remove(settings_file.name)
        else:
            for key, value in relation_data.items():
                if value is None:
                    cmd.append('{}='.format(key))
                else:
                    cmd.append('{}={}'.format(key, value))
            self.command_runner(cmd)

    def relation_clear(self, relation_id):
        """Clears any relation data already set on relation "relation_id".

        This method preserves the "public-address" and "private-address" fields
        of the relation data, since removing those is undefined behavior.
        """
        data = self.relation_get(rid=relation_id,
                                     unit=self.local_unit())
        for entry in data:
            if entry not in ['public-address', 'private-address']:
                data[entry] = None
        self.relation_set(relation_id=relation_id, **data)

    def get_relation_ids(self, relation_type=None):
        """A list of relation_ids."""
        relation_type = relation_type or self.get_relation_type()
        if relation_type is None:
            return []
        relid_cmd_line = ['relation-ids', '--format=json']
        relid_cmd_line.append(relation_type)
        result = self.command_runner(relid_cmd_line)
        return json.loads(result or [])

    def get_related_units(self, relation_id=None):
        """Get a list of unit names related to the caller.

        @param relation_id: If specified, filter the returned list of units and
            return only units from the given relation ID."""
        relation_id = relation_id or self.get_relation_id()

        cmd = ['relation-list', '--format=json']
        if relation_id is not None:
            cmd.extend(('-r', relation_id))
        result = self.command_runner(cmd)
        return json.loads(result) or []

    # NOTE: FIGURE OUT WTF THIS IS USEFUL FOR
    def get_relation_for_unit(self, unit=None, rid=None):
        """Get the json represenation of a unit's relation"""
        unit = unit or self.get_remote_unit()
        relation_data = self.relation_get(unit=unit, rid=rid)
        for key in relation_data:
            if key.endswith('-list'):
                relation_data[key] = relation_data[key].split()
        relation_data['__unit__'] = unit
        return relation_data





def relation_types():
    """Get a list of relation types supported by this charm"""
    rel_types = []
    md = metadata()
    for key in ('provides', 'requires', 'peers'):
        section = md.get(key)
        if section:
            rel_types.extend(section.keys())
    return rel_types


def relation_to_interface(relation_name):
    """
    Given the name of a relation, return the interface that relation uses.

    :returns: The interface name, or ``None``.
    """
    return relation_to_role_and_interface(relation_name)[1]


def relation_to_role_and_interface(relation_name):
    """
    Given the name of a relation, return the role and the name of the interface
    that relation uses (where role is one of ``provides``, ``requires``, or ``peer``).

    :returns: A tuple containing ``(role, interface)``, or ``(None, None)``.
    """
    _metadata = metadata()
    for role in ('provides', 'requires', 'peer'):
        interface = _metadata.get(role, {}).get(relation_name, {}).get('interface')
        if interface:
            return role, interface
    return None, None


def role_and_interface_to_relations(role, interface_name):
    """
    Given a role and interface name, return a list of relation names for the
    current charm that use that interface under that role (where role is one
    of ``provides``, ``requires``, or ``peer``).

    :returns: A list of relation names.
    """
    _metadata = metadata()
    results = []
    for relation_name, relation in _metadata.get(role, {}).items():
        if relation['interface'] == interface_name:
            results.append(relation_name)
    return results


def interface_to_relations(interface_name):
    """
    Given an interface, return a list of relation names for the current
    charm that use that interface.

    :returns: A list of relation names.
    """
    results = []
    for role in ('provides', 'requires', 'peer'):
        results.extend(role_and_interface_to_relations(role, interface_name))
    return results



def relations():
    """Get a nested dictionary of relation data for all related units"""
    rels = {}
    for reltype in relation_types():
        relids = {}
        for relid in relation_ids(reltype):
            units = {local_unit(): relation_get(unit=local_unit(), rid=relid)}
            for unit in related_units(relid):
                reldata = relation_get(unit=unit, rid=relid)
                units[unit] = reldata
            relids[relid] = units
        rels[reltype] = relids
    return rels


def is_relation_made(relation, keys='private-address'):
    '''
    Determine whether a relation is established by checking for
    presence of key(s).  If a list of keys is provided, they
    must all be present for the relation to be identified as made
    '''
    if isinstance(keys, str):
        keys = [keys]
    for r_id in relation_ids(relation):
        for unit in related_units(r_id):
            context = {}
            for k in keys:
                context[k] = relation_get(k, rid=r_id,
                                          unit=unit)
            if None not in context.values():
                return True
    return False


def translate_exc(from_exc, to_exc):
    def inner_translate_exc1(f):
        def inner_translate_exc2(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except from_exc:
                raise to_exc

        return inner_translate_exc2

    return inner_translate_exc1


def juju_version():
    """Full version string (eg. '1.23.3.1-trusty-amd64')"""
    # Per https://bugs.launchpad.net/juju-core/+bug/1455368/comments/1
    jujud = glob.glob('/var/lib/juju/tools/machine-*/jujud')[0]
    return subprocess.check_output([jujud, 'version'],
                                   universal_newlines=True).strip()


def has_juju_version(minimum_version):
    """Return True if the Juju version is at least the provided version"""
    return LooseVersion(juju_version()) >= LooseVersion(minimum_version)


_atexit = []
_atstart = []


def atstart(callback, *args, **kwargs):
    '''Schedule a callback to run before the main hook.

    Callbacks are run in the order they were added.

    This is useful for modules and classes to perform initialization
    and inject behavior. In particular:

        - Run common code before all of your hooks, such as logging
          the hook name or interesting relation data.
        - Defer object or module initialization that requires a hook
          context until we know there actually is a hook context,
          making testing easier.
        - Rather than requiring charm authors to include boilerplate to
          invoke your helper's behavior, have it run automatically if
          your object is instantiated or module imported.

    This is not at all useful after your hook framework as been launched.
    '''
    global _atstart
    _atstart.append((callback, args, kwargs))


def atexit(callback, *args, **kwargs):
    '''Schedule a callback to run on successful hook completion.

    Callbacks are run in the reverse order that they were added.'''
    _atexit.append((callback, args, kwargs))


def _run_atstart():
    '''Hook frameworks must invoke this before running the main hook body.'''
    global _atstart
    for callback, args, kwargs in _atstart:
        callback(*args, **kwargs)
    del _atstart[:]


def _run_atexit():
    '''Hook frameworks must invoke this after the main hook body has
    successfully completed. Do not invoke it if the hook fails.'''
    global _atexit
    for callback, args, kwargs in reversed(_atexit):
        callback(*args, **kwargs)
    del _atexit[:]


#LATER
def get_execution_environment(environment):
    """A convenient bundling of the current execution context"""
    context = {}
    context['conf'] = config()
    if environment.get_relation_id():
        context['reltype'] = environment.get_relation_type()
        context['relid'] = environment.get_relation_id()
        context['rel'] = relation_get()
    context['unit'] = environment.get_local_unit_name()
    context['rels'] = relations()
    context['env'] = environment.environment
    return context

# TODO: NOT USEFUL?
def relations_for_id(relid=None):
    """Get relations of a specific relation ID"""
    relation_data = []
    relid = relid or relation_ids()
    for unit in related_units(relid):
        unit_data = relation_for_unit(unit, relid)
        unit_data['__relid__'] = relid
        relation_data.append(unit_data)
    return relation_data


# TODO: NOT USEFUL?
def relations_of_type(reltype=None):
    """Get relations of a specific type"""
    relation_data = []
    reltype = reltype or relation_type()
    for relid in relation_ids(reltype):
        for relation in relations_for_id(relid):
            relation['__relid__'] = relid
            relation_data.append(relation)
    return relation_data


