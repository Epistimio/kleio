# Athena
Experiment management for machine learning

# Introduction

## What defines experiments and trials

```bash
$ python main.py --lr 0.001 --momentum 0.9 --epochs 100
```

```bash
$ athena -n lenet-mnist python main.py --lr~0.001 --momentum~0.9 --epochs 100
```

# Experiment version control

## Conflicts

1. New hyperparameter
2. Missing hyperparameter
3. Code change (git hash commit)
4. CLI change
5. Script config change

### Specific to Oríon
1. Changed prior
2. Algorithm change

## Adapters

What would be the role of adapters in experiment management? It seems more related to Oríon.

# Reproducibility

Containers?

# Integration with Oríon

Should we use a different database?
On one hand, we already have all the data inside the experiment manager, 
but on the other hand Oríon's data should be fairly small so duplication
should not be a significant problem. Also, reusing the same database makes it 
difficult to disentangle both libraries.

Could be a bare ```Experiment``` inside the experiment manager, and a plugin is
provided which reuses this ```Experiment``` in one that is extended for Oríon's purpose.
We could then add other conflicts which are specific to Oríon.
