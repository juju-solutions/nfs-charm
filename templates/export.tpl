{% for mount in mounts %}{{ mount.mountpoint }}{% for addr in mount.addresses %} {{ addr }}(rw,sync,no_subtree_check){% endfor %}
{% endfor %}