

STATUS = ['new', 'reserved', 'running', 'failover', 'switchover', 'suspended', 'completed',
          'interrupted', 'broken', 'branched']


RESERVABLE = ['new', 'suspended', 'interrupted', 'failover', 'switchover']
INTERRUPTABLE = ['running']
SWITCHOVER = ['reserved', 'broken', 'branched']
