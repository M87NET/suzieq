import re
import warnings
from ipaddress import ip_address

import pytest

import numpy as np
import pandas as pd
from suzieq.sqobjects import get_sqobject
from tests.conftest import DATADIR, validate_host_shape


def validate_mlag_tbl(df: pd.DataFrame):
    '''Validate the MLAG table for all values'''

    assert (df.state.isin(['active', 'disabled', 'inactive'])).all()
    assert (df.role != '').all()
    # pylint: disable=unnecessary-lambda
    assert df.peerAddress.apply(lambda x: ip_address(x)).all()
    assert (df.peerLink != '').all()
    assert (df.query('backupActive == True').backupIP != '').all()
    for row in df.itertuples():
        # Have seen this on older NXOS. Why? Don't know
        if not re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$",
                        row.peerMacAddress):
            warnings.warn(f'Empty peerMacAddress for {row.namespace}, '
                          f'{row.hostname}')
    assert df.systemId.apply(
        lambda x: re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$",
                           x) is not None).all()

    assert (df.mlagDualPortsCnt == df.mlagDualPortsList.str.len()).all()
    assert (df.mlagSinglePortsCnt == df.mlagSinglePortsList.str.len()).all()
    assert (df.mlagErrorPortsCnt == df.mlagErrorPortsList.str.len()).all()

    noncl_df = df.query('os != "cumulus"')
    assert (noncl_df.configSanity.isin(['consistent', 'inconsistent'])).all()
    assert (noncl_df.domainId != '').all()
    assert noncl_df.usesLinkLocal.empty or not (noncl_df.usesLinkLocal).all()
    assert (noncl_df.peerLinkStatus.isin(['up', 'down'])).all()
    validate_interfaces(df)


def validate_interfaces(df: pd.DataFrame):
    '''Validate that all interfaces in various lists are in interfaces table.

    This is to catch problems in parsing interfaces such that the different
    tables contain a different interface name than face table itself.
    In case of MLAG, old and new NXOS seem to provide interface names that
    are the shortened versions.
    '''

    # Create a new df of namespace/hostname/vrf to oif mapping
    # exclude interfaces such as cpu/sup-eth1 etc. which have vlan of 0
    for field in ['mlagDualPortsList', 'mlagErrorPortsList',
                  'mlagSinglePortsList']:
        only_oifs = df.explode(field) \
                      .groupby(by=['namespace', 'hostname'])[field] \
                      .unique() \
                      .reset_index()

        # Fetch the address table
        nslist = df.namespace.unique().tolist()
        if_df = get_sqobject('interface')() \
            .get(namespace=nslist,
                 columns=['namespace', 'hostname', 'ifname']) \
            .reset_index(drop=True)

        assert not if_df.empty

        if_oifs = if_df[['namespace', 'hostname', 'ifname']] \
            .groupby(by=['namespace', 'hostname'])['ifname'] \
            .unique() \
            .reset_index() \
            .explode('ifname') \
            .reset_index(drop=True)

        merge_df = only_oifs.merge(if_oifs, how='left')
        # Verify we have no rows where the route table OIF has no corresponding
        # interface table info
        assert merge_df.query('ifname.isna()').empty


@ pytest.mark.parsing
@ pytest.mark.mlag
@ pytest.mark.parametrize('table', ['mlag'])
@ pytest.mark.parametrize('datadir', DATADIR)
# pylint: disable=unused-argument
def test_mlag_parsing(table, datadir, get_table_data):
    '''Main workhorse routine to test parsed output for MLAG table'''

    df = get_table_data

    ns_dict = {
        'eos': 4,
        'junos': 4,
        'nxos': 4,
        'ospf-ibgp': 4,
    }

    assert not df.empty
    validate_host_shape(df, ns_dict)
    validate_mlag_tbl(df)
