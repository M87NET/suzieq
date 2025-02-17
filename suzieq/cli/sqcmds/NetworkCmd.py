import time
from nubia import command
from suzieq.cli.nubia_patch import argument

from suzieq.cli.sqcmds.command import SqCommand
from suzieq.sqobjects.network import NetworkObj


@command("network", help="Act on network-wide data")
class NetworkCmd(SqCommand):
    """Advanced commands across all the network"""

    def __init__(
            self,
            engine: str = "",
            hostname: str = "",
            start_time: str = "",
            end_time: str = "",
            view: str = "",
            namespace: str = "",
            format: str = "",  # pylint: disable=redefined-builtin
            query_str: str = " ",
            columns: str = "default",
    ) -> None:
        super().__init__(
            engine=engine,
            hostname=hostname,
            start_time=start_time,
            end_time=end_time,
            view=view,
            namespace=namespace,
            columns=columns,
            format=format,
            query_str=query_str,
            sqobj=NetworkObj,
        )

    @command("find", help="find where an IP/MAC address is attached")
    @argument("address", type=str,
              description="IP/MAC addresses, in quotes, space separated")
    @argument("vrf", type=str,
              description="Find within this VRF, used for IP addr")
    @argument("vlan", type=str,
              description="Find MAC within this VLAN")
    def find(self, address: str = '', vrf: str = '',
             vlan: str = ''):
        """Find the network attach point of a given IP or MAC address.
        """
        now = time.time()

        df = self._invoke_sqobj(self.sqobj.find,
                                namespace=self.namespace,
                                hostname=self.hostname,
                                address=address.split(),
                                vlan=vlan,
                                vrf=vrf,
                                query_str=self.query_str,
                                )

        self.ctxt.exec_time = "{:5.4f}s".format(time.time() - now)

        return self._gen_output(df)

    @ command("help", help="show help for a command")
    @ argument("command", description="command to show help for",
               choices=['find'])
    # pylint: disable=redefined-outer-name
    def help(self, command: str = ''):
        return super().help(command)
