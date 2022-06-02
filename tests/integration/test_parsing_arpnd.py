from ipaddress import ip_address
import re

import pytest

import pandas as pd
from suzieq.sqobjects import get_sqobject
from tests.conftest import validate_host_shape, DATADIR


def validate_arpnd_tbl(df: pd.DataFrame):
    '''Validate the ARPND table for all values'''

    # pylint: disable=unnecessary-lambda
    assert df.ipAddress.apply(lambda x: ip_address(x)).all()
    assert (df.state.isin(["permanent", 'reachable', 'router', 'noarp',
                           'failed'])).all()
    pass_df = df.query('state != "failed"')
    assert pass_df.macaddr.apply(
        lambda x: re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$",
                           x) is not None).all()
    assert not (pass_df.oif.isin(["", "None"])).all()  # noqa
    assert (pass_df.remote.isin([True, False])).all()
    validate_interfaces(pass_df)


def validate_interfaces(df: pd.DataFrame):
    '''Validate that each VRF/interface list is in interfaces table.

    This is to catch problems in parsing interfaces such that the different
    tables contain a different interface name than the interface table itself.
    For example, in parsing older NXOS, we got iftable with Eth1/1 and the
    route table with Ethernet1/1. The logic of ensuring this also ensures that
    the VRFs in the route table are all known to the interface table.
    '''

    # Create a new df of namespace/hostname/vrf to oif mapping
    only_oifs = df.groupby(by=['namespace', 'hostname'])['oif'] \
                  .unique() \
                  .reset_index() \
                  .explode('oif') \
                  .reset_index(drop=True)

    # Fetch the address table
    nslist = df.namespace.unique().tolist()
    if_df = get_sqobject('interface')().get(namespace=nslist)
    assert not if_df.empty

    if_oifs = if_df.groupby(by=['namespace', 'hostname'])['ifname'] \
                   .unique() \
                   .reset_index() \
                   .explode('ifname') \
                   .reset_index(drop=True)

    m_df = only_oifs.merge(if_oifs, how='left')
    # Verify we have no rows where the route table OIF has no corresponding
    # interface table info
    assert m_df.query('ifname.isna()').empty


@ pytest.mark.parsing
@ pytest.mark.arpnd
@ pytest.mark.parametrize('table', ['arpnd'])
@ pytest.mark.parametrize('datadir', DATADIR)
# pylint: disable=unused-argument
def test_arpnd_parsing(table, datadir, get_table_data):
    '''Main workhorse routine to test parsed output for ARPND table'''

    df = get_table_data

    ns_dict = {
        'eos': 14,
        'junos': 12,
        'nxos': 14,
        'ospf-ibgp': 14,
        'vmx': 5,
    }

    assert not df.empty
    validate_host_shape(df, ns_dict)
    validate_arpnd_tbl(df)
