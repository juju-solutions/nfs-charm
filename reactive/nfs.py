import os

from charmhelpers.core import hookenv
from charmhelpers.core.host import service_start, service_running
from charmhelpers.fetch import apt_install
from charms.reactive import when, when_not, set_flag, clear_flag
from charms.reactive.relations import endpoint_from_flag

from subprocess import check_output, CalledProcessError

from charmhelpers.core.templating import render

EXPORT_CONFIG_PATH = os.path.join(os.sep, 'etc', 'exports.d')
EXPORT_FILENAME = os.path.join(EXPORT_CONFIG_PATH, 'nfs.exports')


@when_not('nfs_installed')
def install_nfs_deb():
    hookenv.status_set('maintenance', 'Installing NFS')
    apt_install('nfs-kernel-server')
    if not os.path.exists(EXPORT_CONFIG_PATH):
        os.makedirs(EXPORT_CONFIG_PATH)
    set_flag('nfs_installed')


@when('refresh_nfs_mounts')
def read_nfs_mounts():
    hookenv.status_set('maintenance', 'Updating NFS mounts')
    if service_running('nfs-kernel-server'):
        try:
            command = ['exportfs', '-ra']
            hookenv.log('Executing {}'.format(command))
            check_output(command)
            clear_flag('refresh_nfs_mounts')
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


@when_not('nfs.changed', 'nfs_refresh_mounts')
@when('nfs_installed')
def idle_status():
    hookenv.status_set('active', 'NFS ready')


@when('nfs.changed')
def nfs_relation_changed():
    hookenv.status_set('maintenance', 'Rendering nfs config for new relation')
    mount_interface = endpoint_from_flag('nfs.changed')
    config = hookenv.config()
    storage_root = config.get('storage_root')
    options = config.get('export_options')

    # get desired mounts
    mount_list = mount_interface.get_mount_requests()

    template_context = {}
    template_context['mounts'] = []

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

        template_context['mounts'].append({
            'export_name': mount['application_name'],
            'addresses': mount['addresses'],
            'mountpoint': path,
            'identifier': mount['identifier'],
            'fstype': 'nfs',
            'options': options,
        })

    if len(template_context['mounts']) == 0:
        os.remove(EXPORT_FILENAME)
    else:
        render('export.tpl', EXPORT_FILENAME, template_context)
        hookenv.log('rendering template to {}'.format(EXPORT_FILENAME))

    set_flag('refresh_nfs_mounts')
    mount_interface.configure(template_context['mounts'])
