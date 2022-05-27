import warnings

import pytest
import pandas as pd

from suzieq.sqobjects import get_sqobject
from tests.conftest import DATADIR, validate_host_shape


def validate_vlan_tbl(df: pd.DataFrame):
    '''Validate the VLAN table for all values'''

    assert (df.vlan != 0).all()
    if not (df.query('vlan != 1').interfaces.str.len() != 0).all():
        warnings.warn('Some VLANs not assigned to any interface')
    assert (df.state.isin(['active', 'unsupported'])).all()
    assert (df.vlanName != '').all()
    validate_interfaces(df)


def validate_interfaces(df: pd.DataFrame):
    '''Validate that each interface list is in interfaces table.

    This is to catch problems in parsing interfaces such that the different
    tables contain a different interface name than the interface table itself.
    For example, in parsing older NXOS, we got iftable with Eth1/1 and the
    route table with Ethernet1/1. This also validates the vlan/vlanList field
    parsing
    '''

    # Create a new df of namespace/hostname/vrf to oif mapping
    only_oifs = df[['namespace', 'hostname', 'vlan', 'interfaces']] \
        .explode('interfaces') \
        .dropna() \
        .query('interfaces != ""') \
        .reset_index(drop=True) \
        .groupby(by=['namespace', 'hostname', 'vlan'])['interfaces'] \
        .unique() \
        .reset_index() \
        .explode('interfaces') \
        .reset_index(drop=True)

    # Fetch the address table
    nslist = df.namespace.unique().tolist()
    if_df = get_sqobject('interface')().get(
        namespace=nslist,
        columns=['namespace', 'hostname', 'ifname', 'vlan', 'vlanList'])
    assert not if_df.empty

    if_df.apply(lambda x: x['vlanList'].extend([x['vlan']])
                if x['vlan'] else x['vlanList'], axis=1)

    if_oifs = if_df[['namespace', 'hostname', 'ifname', 'vlanList']] \
        .explode('vlanList') \
        .reset_index() \
        .rename(columns={'vlanList': 'vlan'}) \
        .groupby(by=['namespace', 'hostname', 'vlan'])['ifname'] \
        .unique() \
        .reset_index() \
        .explode('ifname') \
        .reset_index(drop=True)

    m_df = only_oifs.merge(if_oifs, how='left')
    # Verify we have no rows where the route table OIF has no corresponding
    # interface table info
    assert m_df.query('ifname.isna()').empty


@ pytest.mark.parsing
@ pytest.mark.vlan
@ pytest.mark.parametrize('table', ['vlan'])
@ pytest.mark.parametrize('datadir', DATADIR)
# pylint: disable=unused-argument
def test_vlan_parsing(table, datadir, get_table_data):
    '''Main workhorse routine to test parsed output for VLAN table'''

    df = get_table_data

    ns_dict = {
        'eos': 9,
        'junos': 7,
        'nxos': 9,
        'ospf-ibgp': 6,
        'mixed': 6,
    }

    assert not df.empty

    validate_host_shape(df, ns_dict)
    validate_vlan_tbl(df)
