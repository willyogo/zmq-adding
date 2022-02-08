#!/usr/bin/python3

from daemons import Daemon, Wallet

import random
import time
import shutil
import os
from os import path
import asyncio
import glob
from datetime import datetime
import uuid

datadirectory="testdata"

def coins(*args):
    if len(args) != 1:
        return tuple(coins(x) for x in args)
    x = args[0]
    if type(x) in (tuple, list):
        return type(x)(coins(i) for i in x)
    return round(x * 1000000000)


def wait_for(callback, timeout=10):
    expires = time.time() + timeout
    while True:
        try:
            if callback():
                return
        except:
            pass
        if time.time() >= expires:
            raise RuntimeError("task timeout expired")
        time.sleep(.25)


verbose = True
def vprint(*args, timestamp=True, **kwargs):
    global verbose
    if verbose:
        if timestamp:
            print(datetime.now(), end=" ")
        print(*args, **kwargs)


class MNNetwork:
    def __init__(self, datadir, *, binpath='../../build/bin', mns=12, nodes=3):
        self.datadir = datadir
        if not os.path.exists(self.datadir):
            os.makedirs(self.datadir)
        self.binpath = binpath


        vprint("Using '{}' for data files and logs".format(datadir))

        nodeopts = dict(master=self.binpath+'/master', datadir=datadir)

        self.mns = [Daemon(master_node=True, **nodeopts) for _ in range(mns)]
        self.nodes = [Daemon(**nodeopts) for _ in range(nodes)]

        self.all_nodes = self.mns + self.nodes

        self.wallets = []
        for name in ('Alice', 'Bob', 'Mike'):
            self.wallets.append(Wallet(
                node=self.nodes[len(self.wallets) % len(self.nodes)],
                name=name,
                rpc_wallet=self.binpath+'/beldex-wallet-rpc',
                datadir=datadir))

        self.alice, self.bob, self.mike = self.wallets

        # Interconnections
        for i in range(len(self.all_nodes)):
            for j in (2, 3, 5, 7, 11):
                k = (i + j) % len(self.all_nodes)
                if i != k:
                    self.all_nodes[i].add_peer(self.all_nodes[k])

        vprint("Starting new master master nodes with RPC on {} ports".format(self.mns[0].listen_ip), end="")
        for mn in self.mns:
            vprint(" {}".format(mn.rpc_port), end="", flush=True, timestamp=False)
            mn.start()
        vprint(timestamp=False)
        vprint("Starting new regular master nodes with RPC on {} ports".format(self.nodes[0].listen_ip), end="")
        for d in self.nodes:
            vprint(" {}".format(d.rpc_port), end="", flush=True, timestamp=False)
            d.start()
        vprint(timestamp=False)

        vprint("Waiting for all master's to get ready")
        for d in self.all_nodes:
            d.wait_for_json_rpc("get_info")

        vprint("Beldexds are ready. Starting wallets")

        for w in self.wallets:
            vprint("Starting new RPC wallet {w.name} at {w.listen_ip}:{w.rpc_port}".format(w=w))
            w.start()
        for w in self.wallets:
            w.ready()
            w.refresh()
            vprint("Wallet {w.name} is ready: {a}".format(w=w, a=w.address()))

        for w in self.wallets:
            w.wait_for_json_rpc("refresh")

        # Mine some blocks; we need 100 per MN registration, and we can nearly 600 on fakenet before
        # it hits HF16 and kills mining rewards.  This lets us submit the first 5 MN registrations a
        # MN (at height 40, which is the earliest we can submit them without getting an occasional
        # spurious "Not enough outputs to use" error).
        # to unlock and the rest to have enough unlocked outputs for mixins), then more some more to
        # earn MN rewards.  We need 100 per MN registration, and each mined block gives us an input
        # of 18.9, which means each registration requires 6 inputs.  Thus we need a bare minimum of
        # 6(N-5) blocks, plus the 30 lock time on coinbase TXes = 6N more blocks (after the initial
        # 5 registrations).
        self.mine(100)
        vprint("Submitting first round of master node registrations: ", end="", flush=True)
        for mn in self.mns[0:5]:
            self.mike.register_mn(mn)
            vprint(".", end="", flush=True, timestamp=False)
        vprint(timestamp=False)
        if len(self.mns) > 5:
            vprint("Going back to mining", flush=True)

            self.mine(6*len(self.mns))

            self.print_wallet_balances()

            vprint("Submitting more master node registrations: ", end="", flush=True)
            for mn in self.mns[5:-1]:
                self.mike.register_mn(mn)
                vprint(".", end="", flush=True, timestamp=False)
            vprint(timestamp=False)
            vprint("Done.")

        self.print_wallet_balances()

        vprint("Mining 40 blocks (registrations + flash quorum lag) and waiting for nodes to sync")
        self.sync_nodes(self.mine(40))

        self.print_wallet_balances()

        vprint("Sending fake belnet/ss pings")
        for mn in self.mns:
            mn.ping()

        all_master_nodes_proofed = lambda mn: all(x['quorumnet_port'] > 0 for x in
                mn.json_rpc("get_n_master_nodes", {"fields":{"quorumnet_port":True}}).json()['result']['master_node_states'])

        vprint("Waiting for proofs to propagate: ", end="", flush=True)
        for mn in self.mns:
            wait_for(lambda: all_master_nodes_proofed(mn), timeout=120)
            vprint(".", end="", flush=True, timestamp=False)
        vprint(timestamp=False)
        for mn in self.mns[-1:]:
            self.mike.register_mn(mn)
            vprint(".", end="", flush=True, timestamp=False)
        self.sync_nodes(self.mine(1))
        time.sleep(10)
        for mn in self.mns:
            mn.send_uptime_proof()
        vprint("Done.")

        vprint("Local Devnet MN network setup complete!")
        vprint("Communicate with daemon on ip: {} port: {}".format(self.mns[0].listen_ip,self.mns[0].rpc_port))
        configfile=self.datadir+'config.py'
        with open(configfile, 'w') as filetowrite:
            filetowrite.write('#!/usr/bin/python3\n# -*- coding: utf-8 -*-\nlisten_ip=\"{}\"\nlisten_port=\"{}\"\nwallet_listen_ip=\"{}\"\nwallet_listen_port=\"{}\"\nwallet_address=\"{}\"\nexternal_address=\"{}\"'.format(self.mns[0].listen_ip,self.mns[0].rpc_port,self.mike.listen_ip,self.mike.rpc_port,self.mike.address(),self.bob.address()))




    def refresh_wallets(self, *, extra=[]):
        vprint("Refreshing wallets")
        for w in self.wallets + extra:
            w.refresh()
        vprint("All wallets refreshed")


    def mine(self, blocks=None, wallet=None, *, sync=False):
        """Mine some blocks to the given wallet (or self.mike if None) on the wallet's daemon.
        Returns the daemon's height after mining the blocks.  If blocks is omitted, mines enough to
        confirm regular transfers (i.e. 10 blocks).  If sync is specified, sync all nodes and then
        refresh all wallets after mining."""
        if wallet is None:
            wallet = self.mike
        if blocks is None:
            blocks = 10
        node = wallet.node
        vprint("Mining {} blocks to wallet {.name}".format(blocks, wallet))
        start_height = node.height()
        end_height = start_height + blocks
        node.mine_blocks(blocks, wallet)
        while node.rpc("/mining_status").json()["active"]:
            height = node.height()
            vprint("Mined {}/{}".format(height, end_height))
            time.sleep(0.05 if height >= end_height else 0.25)
        height = node.height()
        vprint("Mined {}/{}".format(height, end_height))

        if sync:
            self.sync_nodes(height)
            self.refresh_wallets()

        return height


    def sync_nodes(self, height=None, *, extra=[], timeout=10):
        """Waits for all nodes to reach the given height, typically invoked after mine()"""
        nodes = self.all_nodes + extra
        heights = [x.height() for x in nodes]
        if height is None:
            height = max(heights)
        if min(heights) >= height:
            vprint("All nodes already synced to height >= {}".format(height))
            return
        vprint("Waiting for all nodes to sync to height {}".format(height))
        last = None
        expiry = time.time() + timeout
        while nodes and time.time() < expiry:
            if heights[-1] < height:
                heights[-1] = nodes[-1].height()
            if heights[-1] >= height:
                heights.pop()
                nodes.pop()
                last = None
                continue
            if heights[-1] != last:
                vprint("waiting for {} [{} -> {}]".format(nodes[-1].name, heights[-1], height))
                last = heights[-1]
            time.sleep(0.1)
        if nodes:
            raise RuntimeError("Timed out waiting for node syncing")
        vprint("All nodes synced to height {}".format(height))


    def sync(self, extra_nodes=[], extra_wallets=[]):
        """Synchronizes everything: waits for all nodes to sync, then refreshes all wallets.  Can be
        given external wallets/nodes to sync."""
        self.sync_nodes(extra=extra_nodes)
        self.refresh_wallets(extra=extra_wallets)


    def print_wallet_balances(self):
        """Instructs the wallets to refresh and prints their balances (does nothing in non-verbose mode)"""
        global verbose
        if not verbose:
            return
        vprint("Balances:")
        for w in self.wallets:
            b = w.balances(refresh=True)
            vprint("    {:5s}: {:.9f} (total) with {:.9f} (unlocked)".format(
                w.name, b[0] * 1e-9, b[1] * 1e-9))


    def __del__(self):
        for n in self.all_nodes:
            n.terminate()
        for w in self.wallets:
            w.terminate()

mnn = None

def run():
    global mnn, verbose
    if not mnn:
        if path.isdir(datadirectory+'/'):
            shutil.rmtree(datadirectory+'/', ignore_errors=False, onerror=None)
        vprint("new MNN")
        mnn = MNNetwork(datadir=datadirectory+'/')
    else:
        vprint("reusing MNN")
        mnn.alice.new_wallet()
        mnn.bob.new_wallet()

        # Flush pools because some tests leave behind impossible txes
        for n in mnn.all_nodes:
            assert n.json_rpc("flush_txpool").json()['result']['status'] == 'OK'

        # Mine a few to clear out anything in the mempool that can be cleared
        mnn.mine(5, sync=True)

        vprint("Alice has new wallet: {}".format(mnn.alice.address()))
        vprint("Bob   has new wallet: {}".format(mnn.bob.address()))

    input("Use Ctrl-C to exit...")
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print(f'!!! AsyncApplication.run: got KeyboardInterrupt during start')
    finally:
        loop.close()


# Shortcuts for accessing the named wallets
def alice(net):
    return net.alice

def bob(net):
    return net.bob

def mike(net):
    return net.mike

if __name__ == '__main__':
    run()
