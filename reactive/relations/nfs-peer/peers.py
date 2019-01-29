from charmhelpers.core import hookenv
from charms.reactive import Endpoint


class NFSPeer(Endpoint):

    def get_peer_info(self, address_key='private-address'):
        """Return peer information mapped by unit names.

        An example return value is:

        {
            'nfs/0': {'address': '172.16.0.1'},
            'nfs/1': {'address': '172.16.0.2'},
        }

        :param address_key: the key to use to fetch the remote unit's
            address.
        :return: a dict mapping unit names to dicts containing peer
            information, including the address.
        """
        info = {
            hookenv.local_unit(): {'address': hookenv.unit_get(address_key)},
        }
        for unit in self.all_joined_units:
            info[unit.unit_name] = {
                'address': unit.received_raw.get(address_key),
            }
        return info
