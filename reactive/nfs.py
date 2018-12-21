from collections import defaultdict
import os

from charmhelpers.core import hookenv
from charmhelpers.core.host import (
    service_restart,
    service_running,
    service_start,
    service_stop,
)
from charmhelpers.fetch import apt_install
from charms.reactive import when, when_not, when_any, set_flag, clear_flag
from charms.reactive.relations import endpoint_from_flag

from subprocess import check_output, CalledProcessError

from charmhelpers.core.templating import render

EXPORT_CONFIG_PATH = os.path.join(os.sep, 'etc', 'exports.d')
EXPORT_FILENAME = os.path.join(EXPORT_CONFIG_PATH, 'nfs.exports')
CONFIG_FILENAME = os.path.join(os.sep, 'etc', 'default', 'nfs-kernel-server')

@when_not('nfs_installed')
def install_nfs_deb():
    hookenv.status_set('maintenance', 'Installing NFS')
    apt_install('nfs-kernel-server')
    if not os.path.exists(EXPORT_CONFIG_PATH):
        os.makedirs(EXPORT_CONFIG_PATH)

    update_config()
    set_flag('nfs_installed')


@when('config.changed.initial_daemon_count')
@when('nfs_installed')
def update_config():
    hookenv.status_set('maintenance', 'Updating config')
    try:
        config = hookenv.config()
        command = ['sudo',
                   'sed',
                   '-i',
                   '-e',
                   's/RPCNFSDCOUNT.*/RPCNFSDCOUNT={}/'.format(
                       config.get('initial_daemon_count')),
                   '{}'.format(CONFIG_FILENAME)]
        hookenv.log('Executing {}'.format(command))
        check_output(command)
    except CalledProcessError as e:
        hookenv.log(e)
        hookenv.log('Failed to update config!')
        hookenv.status_set('blocked', 'Unable to update config file!')
    if service_running('nfs-kernel-server'):
        service_restart('nfs-kernel-server')


@when_any('refresh_nfs_mounts',
          'config.changed.mount_options',
          'config.changed.active_units')
def read_nfs_mounts():
    mount_interface = endpoint_from_flag('endpoint.nfs.joined')
    if mount_interface is None:
        hookenv.log('No mount interface, bailing')
        return

    hookenv.status_set('maintenance', 'Updating NFS mounts')
    if service_running('nfs-kernel-server'):
        try:
            command = ['exportfs', '-ra']
            hookenv.log('Executing {}'.format(command))
            check_output(command)
        except CalledProcessError as e:
            hookenv.log(e)
            hookenv.log('Failed to reread nfs mounts. Will attempt again next update.')  # noqa
            return
    else:
        try:
            service_start('nfs-kernel-server')
        except CalledProcessError as e:
            hookenv.log(e)
            hookenv.log('Unable to start service nfs-kernel-server! Will attempt again next update.') # noqa
            return

    config = hookenv.config()
    active_units = config.get('active_units', '')
    if not active_units or hookenv.local_unit() in active_units.split(','):
        storage_root = config.get('storage_root')
        mount_options = config.get('mount_options')
        mount_responses = []
        for mount in mount_interface.get_mount_requests():
            if not mount['application_name']:
                continue
            path = os.path.join(storage_root, mount['application_name'])
            mount_responses.append({
                'export_name': mount['application_name'],
                'mountpoint': path,
                'identifier': mount['identifier'],
                'fstype': 'nfs',
                'options': mount_options,
            })
        mount_interface.configure(mount_responses)
    else:
        hookenv.log('Disabled (not in active_units)')
        for relation in mount_interface.relations:
            relation.to_publish_raw.update({
                'mountpoint': None,
                'hostname': None,
                'fstype': None,
                'options': None,
            })
        if service_running('nfs-kernel-server'):
            service_stop('nfs-kernel-server')

    clear_flag('refresh_nfs_mounts')


@when_not('nfs.changed', 'refresh_nfs_mounts')
@when('nfs_installed')
def idle_status():
    hookenv.status_set('active', 'NFS ready')


@when('endpoint.nfs.joined')
@when_any('nfs.changed',
          'config.changed.storage_root',
          'config.changed.export_options')
def nfs_relation_changed():
    hookenv.status_set('maintenance', 'Rendering nfs config for new relation')
    mount_interface = endpoint_from_flag('endpoint.nfs.joined')
    if mount_interface is None:
        hookenv.log('No mount interface, bailing')
        return

    config = hookenv.config()
    storage_root = config.get('storage_root')
    export_options = config.get('export_options')

    # get desired mounts
    mount_list = mount_interface.get_mount_requests()

    mount_addresses = defaultdict(set)

    for mount in mount_list:
        if not mount['application_name']:
            continue

        path = os.path.join(storage_root, mount['application_name'])
        if not os.path.exists(path):
            hookenv.log('creating export data path {}'.format(path))
            os.makedirs(path)
            # my soul hurts, but without something like LDAP to make user
            # id's consistent, we can't really know what user will need
            # to read/write to this path. Unfortunately we don't really
            # have a choice.
            os.chmod(path, 0o777)

        mount_addresses[path].update(mount['addresses'])

    if mount_addresses:
        template_context = {
            'mounts': [{
                'mountpoint': path,
                'addresses': sorted(mount_addresses[path]),
                'export_options': export_options,
            } for path in sorted(mount_addresses)],
        }
        render('export.tpl', EXPORT_FILENAME, template_context)
        hookenv.log('rendering template to {}'.format(EXPORT_FILENAME))
    else:
        os.remove(EXPORT_FILENAME)

    set_flag('refresh_nfs_mounts')
