import re

import pytest
import numpy as np
import pandas as pd
from suzieq.sqobjects import get_sqobject
from tests.conftest import DATADIR, validate_host_shape


def validate_macs(df: pd.DataFrame):
    '''Validate the mac table for all values'''

    assert (df.macaddr != '').all()
    assert (df.oif != '').all()
    assert (df.mackey != '').all()
    # Validate that the only MAC addresses there are fit the macaddr format
    assert df.macaddr.apply(
        lambda x: re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$",
                           x) is not None).all()
    # Ignore Linux HER entries and interface MAC entries, and some NXOS entries
    assert (df.query(
        'macaddr != "00:00:00:00:00:00" and flags != "permanent" and '
        '~(oif.isin(["cpu", "sup-eth1", "sup-eth1(R)"]) or flags == "router")')
        .vlan != 0).all()
    # Remote learnt MACs MUST have a non-zero VTEP IP
    assert (df.query('flags == "remote"').remoteVtepIp != '').all()
    # Verify all entries with a remoteVtepIp have the remote flag set_index
    # Linux/CL entries also have a permanent entry representing the HER
    # pylint: disable=use-a-generator
    assert all([x in ['dynamic', 'permanent', 'static', 'remote', 'offload']
                for x in sorted(df.query('remoteVtepIp != ""')
                                ['flags'].unique())])
    validate_interfaces(df)


def validate_interfaces(df: pd.DataFrame):
    '''Validate that each VLAN/interface list is in interfaces table.

    This is to catch problems in parsing interfaces such that the different
    tables contain a different interface name than face table itself.
    For example, in parsing older NXOS, we got iftable with Eth1/1 and the
    mac table with Ethernet1/1. The logic of ensuring this also ensures that
    the VLAN table is also validated as need to access it for trunk ports.
    '''

    # Create a new df of namespace/hostname/vrf to oif mapping
    # exclude interfaces such as cpu/sup-eth1 etc. which have vlan of 0
    only_oifs = df.groupby(by=['namespace', 'hostname', 'vlan'])['oif'] \
        .unique() \
        .reset_index() \
        .explode('oif') \
        .query('vlan != 0 and oif != "Router"') \
        .reset_index(drop=True)

    # Fetch the address table
    nslist = df.namespace.unique().tolist()
    if_df = get_sqobject('interface')() \
        .get(namespace=nslist,
             columns=['namespace', 'hostname', 'ifname', 'vlan', 'vlanList']) \
        .explode('vlanList') \
        .reset_index(drop=True)

    assert not if_df.empty

    if_df['vlan'] = np.where(~if_df.vlanList.isnull(), if_df.vlanList,
                             if_df.vlan)

    if_oifs = if_df[['namespace', 'hostname', 'vlan', 'ifname']] \
        .groupby(by=['namespace', 'hostname', 'vlan'])['ifname'] \
        .unique() \
        .reset_index() \
        .explode('ifname') \
        .reset_index(drop=True)

    merge_df = only_oifs.merge(if_oifs, how='left')
    # Verify we have no rows where the route table OIF has no corresponding
    # interface table info
    assert merge_df.query('ifname.isna()').empty


@ pytest.mark.parsing
@ pytest.mark.mac
@ pytest.mark.parametrize('table', ['macs'])
@ pytest.mark.parametrize('datadir', DATADIR)
# pylint: disable=unused-argument
def test_macs_parsing(table, datadir, get_table_data):
    '''Main workhorse routine to test parsed output for MAC table'''

    df = get_table_data

    ns_dict = {
        'eos': 11,
        'junos': 7,
        'nxos': 13,
        'ospf-ibgp': 7,
        'mixed': 2,
    }

    assert not df.empty
    validate_host_shape(df, ns_dict)
    validate_macs(df)
