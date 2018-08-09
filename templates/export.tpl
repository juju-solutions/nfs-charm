{% for mount in mounts %}{{ mount.mountpoint }}{% for addr in mount.addresses %} {{ addr }}({{mount.options}}){% endfor %}
{% endfor %}