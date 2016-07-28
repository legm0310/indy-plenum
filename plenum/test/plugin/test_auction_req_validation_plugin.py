from functools import partial
from uuid import uuid4

import pytest

from plenum.common.txn import TXN_TYPE,  DATA
from plenum.common.types import PLUGIN_TYPE_VERIFICATION
from plenum.server.node import Node
from plenum.server.plugin_loader import PluginLoader
from plenum.test.eventually import eventuallyAll
from plenum.test.helper import TestNodeSet, checkReqNack
from plenum.test.plugin.auction_req_validation.plugin_auction_req_validation import AMOUNT, \
    PLACE_BID, AUCTION_START, ID, AUCTION_END
from plenum.test.plugin.conftest import AUCTION_REQ_VALIDATION_PLUGIN_PATH_VALUE
from plenum.test.plugin.helper import pluginPath


@pytest.fixture(scope="module")
def pluginVerPath():
    return pluginPath(AUCTION_REQ_VALIDATION_PLUGIN_PATH_VALUE)


@pytest.fixture(scope="module")
def allPluginPaths(pluginVerPath):
    return [pluginVerPath]


@pytest.yield_fixture(scope="module")
def nodeSet(tdir, nodeReg, allPluginPaths):
    """
    Overrides the fixture from conftest.py
    """
    with TestNodeSet(nodeReg=nodeReg,
                     tmpdir=tdir,
                     pluginPaths=allPluginPaths) as ns:

        for n in ns:  # type: Node
            assert n.opVerifiers is not None
            assert len(n.opVerifiers) == 1
            opVerifier, = n.opVerifiers
            assert opVerifier.count == 0

        yield ns


def testAuctionReqValidationPlugin(looper, nodeSet, client1, tdir, pluginVerPath):
    # TODO: Test more cases
    plugin = PluginLoader(pluginVerPath)
    plugin = next(iter(plugin.plugins[PLUGIN_TYPE_VERIFICATION]))
    commonError = "client request invalid: AssertionError "
    allCoros = []
    req, = client1.submit({
        TXN_TYPE: "dummy",
        DATA: {
            AMOUNT: 30
        }})

    update = {'reason': '{}dummy is not a valid transaction type, must be one of {}'.
        format(commonError, ', '.join(plugin.validTxnTypes))}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
              for node in nodeSet]

    req, = client1.submit({
        TXN_TYPE: AUCTION_START,
    })

    update = {
        'reason': "{}{} attribute is missing or not in proper format" \
            .format(commonError, DATA)}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
             for node in nodeSet]

    req, = client1.submit({
        TXN_TYPE: PLACE_BID,
        })

    update = {
        'reason': "{}{} attribute is missing or not in proper format" \
            .format(commonError, DATA)}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
             for node in nodeSet]

    req, = client1.submit({
        TXN_TYPE: PLACE_BID,
        DATA: "some string"
    })

    update = {
        'reason': "{}{} attribute is missing or not in proper format" \
            .format(commonError, DATA)}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
             for node in nodeSet]

    req, = client1.submit({
        TXN_TYPE: PLACE_BID,
        DATA: {
            AMOUNT: 453
        }})

    update = {
        'reason': "{}No id provided for auction".format(commonError)}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
             for node in nodeSet]

    req, = client1.submit({
        TXN_TYPE: AUCTION_START,
        DATA: {
        }})

    update = {
        'reason': "{}No id provided for auction".format(commonError)}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
             for node in nodeSet]

    req, = client1.submit({
        TXN_TYPE: AUCTION_END,
        DATA: {
        }})

    update = {
        'reason': "{}No id provided for auction".format(commonError)}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
             for node in nodeSet]

    auctionId = str(uuid4())
    req, = client1.submit({
        TXN_TYPE: PLACE_BID,
        DATA: {
            ID: auctionId,
            AMOUNT: -3
        }})

    update = {
        'reason': "{}{} must be present and should be a number greater than 0"\
                    .format(commonError, AMOUNT)}

    allCoros += [partial(checkReqNack, client1, node, req.reqId, update)
              for node in nodeSet]

    looper.run(eventuallyAll(*allCoros, totalTimeout=5))

    for n in nodeSet:  # type: Node
        opVerifier, = n.opVerifiers
        assert opVerifier.count == 0