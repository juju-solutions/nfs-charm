{% for mount in mounts %}{{ mount.mountpoint }}{% for addr in mount.addresses %} {{ addr }}({{mount.export_options}}){% endfor %}
{% endfor %}