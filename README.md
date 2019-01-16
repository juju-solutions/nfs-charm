# Overview

This is the NFS charm with support for trusty, xenial, and bionic. It creates an NFSv4(http://nfs.sourceforge.net/)
server using the local filesystem as a backing store. There is no clustering or
federation, so multiple units would result in multiple nfs servers. This is NOT
a highly available server.

# Usage

To deploy an NFS server:

```juju deploy nfs```

Each relation to the NFS charm will result in a new export for the units in that
application. The default location of data is /srv/data

Note that the NFS charm will *NOT* destroy data. This means if you remove a relation
to an application, you will need to manually destroy the data saved by that application
in the local data location.

### Kubernetes

	conjure-up canonical-kubernetes
	juju deploy nfs
	juju add-relation nfs kubernetes-worker

### Owncloud

	juju deploy nfs
	juju deploy mysql
	juju deploy owncloud
	juju add-relation mysql:owncloud
	juju add-relation nfs:nfs owncloud:shared-fs

The above example deploys OwnCloud personal cloud storage, and provides remote storage via the NFS host.

### Wordpress

	juju deploy nfs
	juju deploy mysql
	juju deploy wordpress
	juju add-relation mysql:db wordpress:db
	juju add-relation nfs:nfs wordpress:nfs

## Migrating Storage

To migrate storage from one NFS unit to another, first add the new unit in
such a way as to avoid publishing it before it's ready:

	juju config nfs active_units=<old unit ID>
	juju add-unit nfs

Now start the downtime:

	juju config nfs active_units=none

Wait for all clients to unmount, then move the underlying storage to the new
unit in whatever way is appropriate for your deployment.

Finish the downtime by publishing the new unit:

	juju config nfs active_units=<new unit ID>

After clients have mounted the new unit and you've checked that all is well,
you can remove the old unit:

	juju remove-unit <old unit ID>
	juju config nfs active_units=

## Known Limitations and Issues

No high availability story

At present the charms consuming an NFS relationship only account for a single host. Most charms assume the first incoming NFS mount-point is the sole replacement, and subsequent NFS relationship-join requests are ignored.

If you are attempting to deploy NFS to an LXC container, such as the juju local provider, there are additional steps that need to be taken prior to deploying the NFS charm.

On the LXC host:

	apt-get install nfs-common
	modprobe nfsd
	mount -t nfsd nfsd /proc/fs/nfsd

Edit /etc/apparmor.d/lxc/lxc-default and add the following three lines to it:

	mount fstype=nfs,
	mount fstype=nfs4,
	mount fstype=nfsd,
	mount fstype=rpc_pipefs,

after which:

	sudo /etc/init.d/apparmor restart

Finally:

	juju deploy nfs

# Configuration

 - storage_root: The root path where exported directories will be created
 - export_options: The default export options. Ships with rw,sync,no_root_squash,no_all_squash
 - mount_options: The default client mount options

# Contact Information

Mike Wilson <mike.wilson@canonical.com>

## Upstream NFS Project

- To view the source: https://github.com/hyperbolic2346/nfs-charm
