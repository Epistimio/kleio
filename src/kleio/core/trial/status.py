

STATUS = ['new', 'reserved', 'running', 'failover', 'switchover', 'suspended',
          'completed',
          'interrupted', 'broken']


RESERVABLE = ['new', 'suspended', 'interrupted', 'failover', 'switchover']
INTERRUPTABLE = ['running']
SWITCHOVER = ['reserved', 'broken']
