STATUS = ['new', 'reserved', 'running', 'failover', 'switchover', 'suspended', 'completed',
          'interrupted', 'broken', 'branched', 'acknowledged']

RESERVABLE = ['new', 'suspended', 'interrupted', 'failover', 'switchover']
INTERRUPTABLE = ['running']
SWITCHOVER = ['reserved', 'broken', 'branched']
ACKNOWLEDGEABLE = ['broken']
