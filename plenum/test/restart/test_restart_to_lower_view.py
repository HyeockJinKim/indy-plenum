import pytest

from plenum.test import waits
from plenum.test.helper import sdk_send_random_and_check
from plenum.test.node_request.helper import sdk_ensure_pool_functional
from plenum.test.restart.helper import restart_nodes
from plenum.test.view_change.helper import ensure_view_change_complete


@pytest.fixture(scope="module")
def tconf(tconf):
    old_network_3pc_watcher_state = tconf.ENABLE_NETWORK_I3PC_WATCHER
    tconf.ENABLE_NETWORK_I3PC_WATCHER = True
    yield tconf
    tconf.ENABLE_NETWORK_I3PC_WATCHER = old_network_3pc_watcher_state


def test_restart_to_lower_view(looper, txnPoolNodeSet, tconf, tdir, allPluginsPath,
                               sdk_pool_handle, sdk_wallet_client):
    # Add transaction to ledger
    sdk_send_random_and_check(looper, txnPoolNodeSet, sdk_pool_handle, sdk_wallet_client, 1)

    # Move to higher view
    ensure_view_change_complete(looper, txnPoolNodeSet)

    # Restart all nodes except last
    all_except_last = txnPoolNodeSet[:-1]
    last_node = txnPoolNodeSet[-1]
    tm = tconf.ToleratePrimaryDisconnection + waits.expectedPoolElectionTimeout(len(txnPoolNodeSet))
    restart_nodes(looper, txnPoolNodeSet, all_except_last, tconf, tdir, allPluginsPath,
                  after_restart_timeout=tm, start_one_by_one=False, wait_for_elections=False)

    # Check that last node is aware that there might be inconsistent 3PC state
    assert last_node.spylog.count(last_node.on_inconsistent_3pc_state) == 1

    # Restart last node
    restart_nodes(looper, txnPoolNodeSet, [last_node], tconf, tdir, allPluginsPath,
                  after_restart_timeout=tm, start_one_by_one=False)

    # Check that all nodes are still functional
    sdk_ensure_pool_functional(looper, txnPoolNodeSet, sdk_wallet_client, sdk_pool_handle)
