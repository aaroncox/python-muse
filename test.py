from datetime import datetime
from muse import Muse
from pymongo import MongoClient
from pprint import pprint
from time import gmtime, strftime
from apscheduler.schedulers.background import BackgroundScheduler
import collections
import time
import sys
import os

dct = Muse(node='ws://muse.peerplaysdb.com')
rpc = dct.rpc

# mongo = MongoClient("mongodb://mongo")
# db = mongo.peerplaysdb

# misses = {}

# Command to check how many blocks a witness has missed
# def check_misses():
#     global misses
#     witnesses = rpc.get_witnesses_by_vote('', 100)
#     for witness in witnesses:
#         owner = str(witness['owner'])
#         # Check if we have a status on the current witness
#         if owner in misses.keys():
#             # Has the count increased?
#             if witness['total_missed'] > misses[owner]:
#                 # Update the misses collection
#                 record = {
#                   'date': datetime.now(),
#                   'witness': owner,
#                   'increase': witness['total_missed'] - misses[owner],
#                   'total': witness['total_missed']
#                 }
#                 db.witness_misses.insert(record)
#                 # Update the misses in memory
#                 misses[owner] = witness['total_missed']
#         else:
#             misses.update({owner: witness['total_missed']})



def update_witnesses():
    now = datetime.now().date()
    scantime = datetime.now()
    users = rpc.lookup_miner_accounts('', 100)
    pprint("[PPY] - Update Witnesses (" + str(len(users)) + " accounts)")
    # db.witness.remove({})
    for user in users:
        account, accountid = user;
        witness = rpc.get_miners([accountid])
        # Convert to Numbers
        for key in ['total_votes', 'total_missed']:
            witness[0][key] = float(witness[0][key])
        witness[0].update({
            'account': account
        })
        pprint(witness[0])
        # db.witness.update({'_id': account}, {'$set': witness[0]}, upsert=True)

def run():
    update_witnesses()
    # check_misses()

if __name__ == '__main__':
    # Start job immediately
    run()
    # Schedule it to run every 1 minute
    scheduler = BackgroundScheduler()
    scheduler.add_job(run, 'interval', minutes=1, id='run')
    scheduler.start()
    # Loop
    try:
        while True:
            sys.stdout.flush()
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
