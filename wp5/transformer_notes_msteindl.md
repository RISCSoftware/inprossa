## Prompt

Build a very small jax transformer:
- < 10 M params
- in Flax
- using as much library code as possible
- that encodes a list of tokens, each of dim=6
  - dim 0: 1 if token for value estimation output, 0 otherwise
  - dim 1: 1 if bin token, 0 otherwise
  - dim 2: remaining size of this bin
  - dim 3: 1 if item token, 0 otherwise
  - dim 4: size of the item
  - dim 5: 1 if this is the next item to assign, 0 otherwise
- output of bin tokens: map to 1 scalar
- output of item tokens: discard (can be same head as bin token output)
- apply softmax across item token outputs (item selection proba)

## Prompt

I need the transformer for bin packing in MCTS (via mctx package). How large should the transformer be? How many Params does alpha zero have in comparison?
Another requirement is that I need the transformer in Jax. Either natively, or easy to reimplement.

## Answer

- For a bin-packing task (1D, 2D, or 3D), use a transformer between 1M and 10M parameters
- 4 to 6 layer Transformer Encoder with a small hidden dimension (e.g., $d_{model} = 128$ or $256$).
- In mctx, your bottleneck is the latency of the neural network forward pass during the search.
- AlphaZero (Chess/Go) uses a 24M to 65M params ResNet
- GitHub Jax implementations
  - kvfrans/jaxtransformer
  - cgao96/nanoGPT.jax
  - maxencefaldor/nanoGPT-JAX
  - erfanzar/EasyDeL
  - AakashKumarNain/nanoGPTJAX

| Implementation | Library Base | Style | Best for... |
|---|---|---|---|
| nanoGPT.jax | Flax | GPT-2 | Rapid prototyping & readability. |
| EasyDeL | Flax | Qwen/Llama | Production-grade modern features. |
| Gemma-JAX | Flax | Gemma | Google-native, highly optimized. |
| NanoGPTJAX | Pure JAX | Modern GPT | Absolute maximum performance/customization. |

## Prompt

Similar to the othello env in wp5/pgx, create a bin packing env in wp5/wp5 that is jax jit-able and parallelizable.
You are not allowed to refer to any pgx code, but you can copy paste.
Bin size is always 1.
There is a specified min and max item size.
There is a fixed number of max items, e.g. 128 (important for later action size).
In init, First create full bins as follows.
- Roll the the number of items and repetitions per bin, e.g. ((2, 4), (2, 5), (3, 3)) means first bin has 2 items and is repeated 4 times, etc.
- Create full bins by splitting the interval [0, 1]. Must satisfy min and max item size. Apply repetitions.
- If we exceed max items, randomly delete bins.
Then unassign all items and forget initial bins. This completes init.
- observation
  - tuple of space left in remaining boxes in desc. order, e.g. (1.0, 0.7, 0.3, 0.0)
  - size of unassigned items in desc. order, e.g. (0.3, 0.3, 0.2, 0.15)
- Action: Assign next item (in order) to a box. action space = enumerated max item size (max bins = max items).
- Observation and action space array sizes must be compatible to BinPackingNet
- Write a demo function to init and step a vector of environments in parallel
- Focus on the environment for now.

## Prompt

Similar pgx/examples/alphazero/train.py, create an alphazero training routine in mcts/bin_packing/train.py
- use the net at mcts/bin_packing/net.py
- use the env at mcts/bin_packing/env.py

Recall this from the env:
Bin size is always 1.
There is a specified min and max item size.
There is a fixed number of max items, e.g. 128 (important for later action size).
- observation
  - tuple of space left in remaining boxes in desc. order, e.g. (1.0, 0.7, 0.3, 0.0)
  - size of unassigned items in desc. order, e.g. (0.3, 0.3, 0.2, 0.15)
- Action: Assign next item (in order) to a box. action space = enumerated max item size (max bins = max items).
- Observation and action space array sizes must be compatible to BinPackingNet

Recall this from the transformer:
- < 10 M params
- in Flax
- using as much library code as possible
- that encodes a list of tokens, each of dim=6
  - dim 0: 1 if token for value estimation output, 0 otherwise
  - dim 1: 1 if bin token, 0 otherwise
  - dim 2: remaining size of this bin
  - dim 3: 1 if item token, 0 otherwise
  - dim 4: size of the item
  - dim 5: 1 if this is the next item to assign, 0 otherwise
- output of bin tokens: map to 1 scalar
- output of item tokens: discard (can be same head as bin token output)
- apply softmax across bin token outputs (bin selection proba)

Before you start:
- Is the current code consistent?
- Do you have all specs that you need?



## Prompt

Does the pgx example at pgx/examples/alphazero/train.py require the init of env to be jit-compilable?
So env init could not load a set of random instances from the file system?
