import time
from datetime import timedelta
from nubia import command, argument
import pandas as pd

from suzieq.cli.sqcmds.command import SqCommand
from suzieq.sqobjects.bgp import BgpObj


@command("bgp", help="Act on BGP data")
class BgpCmd(SqCommand):
    def __init__(
        self,
        engine: str = "",
        hostname: str = "",
        start_time: str = "",
        end_time: str = "",
        view: str = "latest",
        namespace: str = "",
        format: str = "",
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
            sqobj=BgpObj,
        )

    def _clean_output(self, df) -> pd.DataFrame:
        """Make upTime look good"""
        if df.empty:
            return df

        if "estdTime" in df.columns:
            df['estdTime'] = df.estdTime.apply(
                lambda x: str(timedelta(milliseconds=int(x))))
        elif 'upTimeStat' in df.columns:
            df.loc['upTimeStat'] = df \
              .loc['upTimeStat'] \
              .map(lambda x: [str(timedelta(milliseconds=int(i))) for i in x])

        return df.dropna(how='any')

    @command("show")
    @argument("vrf", description="vrf name to qualify")
    @argument("peer", description="IP address, in quotes, or the interface name, of peer to qualify output")
    @argument("status", description="status of the session to match",
              choices=["all", "pass", "fail"])
    def show(self, status: str = "all", vrf: str = '', peer: str = ''):
        """
        Show bgp info
        """
        if self.columns is None:
            return

        # Get the default display field names
        now = time.time()
        if self.columns != ["default"]:
            self.ctxt.sort_fields = None
        else:
            self.ctxt.sort_fields = []

        if status == "pass":
            state = "Established"
        elif status == "fail":
            state = "!Established"
        else:
            state = ''

        if (self.columns != ['default'] and self.columns != ['*'] and
                'state' not in self.columns):
            addnl_fields = ['state']
        else:
            addnl_fields = []

        df = self.sqobj.get(
            hostname=self.hostname, columns=self.columns,
            namespace=self.namespace, state=state, addnl_fields=addnl_fields,
            vrf=vrf.split(), peer=peer.split()
        )

        if 'estdTime' in df.columns:
            df['estdTime'] = pd.to_datetime(df.estdTime.astype(str), unit="ms",
                                            errors='ignore')

        self.ctxt.exec_time = "{:5.4f}s".format(time.time() - now)
        return self._gen_output(df)

    @command("summarize", help="Provide summary info about BGP per namespace")
    def summarize(self):
        """
        Summarize bgp info
        """
        self._init_summarize()
        return self._post_summarize()

    @command("assert")
    @argument("vrf", description="Only assert BGP state in this VRF")
    def aver(self, vrf: str = "") -> pd.DataFrame:
        """Assert BGP is functioning properly"""
        now = time.time()
        df = self.sqobj.aver(
            hostname=self.hostname,
            vrf=vrf.split(),
            namespace=self.namespace,
        )
        self.ctxt.exec_time = "{:5.4f}s".format(time.time() - now)

        return self._assert_gen_output(df)

    @command("top")
    @argument(
        "what", description="Field you want to see top for",
        choices=["flaps", "v4PrefixRx", "evpnPrefixRx", "v6PrefixRx",
                 "updatesRx", "updatesTx", "uptime"]
    )
    @argument("count", description="How many top entries")
    @argument("reverse", description="True see Bottom n",
              choices=["True", "False"])
    def top(self, what: str = "flaps", count: int = 5, reverse: str = "False"):
        """
        Show top n entries based on specific field
        """
        if self.columns is None:
            return

        now = time.time()

        what_map = {
            "flaps": "numChanges",
            "v4PrefixRx": "v4PfxRx",
            "evpnPrefixRx": "evpnPfxRx",
            "v6PrefixRx": "v6PfxRx",
            "updatesTx": "updatesTx",
            "updatesRx": "updatesRx",
            "uptime": "estdTime",
        }

        df = self.sqobj.top(
            hostname=self.hostname,
            what=what_map[what],
            n=count,
            reverse=reverse == "True" or False,
            columns=self.columns,
            namespace=self.namespace,
        )

        self.ctxt.exec_time = "{:5.4f}s".format(time.time() - now)
        return self._gen_output(self._clean_output(df))
