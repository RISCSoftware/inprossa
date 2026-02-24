We want to apply neural guided MCTS on 1D bin packing. Assume all containers have the same size.
- How to encode instance data, partial solutions, and objective?
- How to encode actions? Should an action be "assign item x to container y"? Is this typcial?
- State: The partial assignment of item to boxes?
- Objective: The sum of all empty space in all used containers? Sth better?
- How to train?
  - (a) Train in a fixed instance (the one we want to solve) only by repeated "play".
  - (b) Train in random instances of random input data size
