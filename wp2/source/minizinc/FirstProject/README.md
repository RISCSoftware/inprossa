### Minizinc issues

We cannot define functions. In particular, one cannot create a function that checks whether a list of pieces is valid, and expect to send to this function multiple arrays called by different names. But rather, for each name one needs to create a new file.

So we will need a language that translates descriptions of the machines to this files. Some name changes would be enough but it would be great to have a translator that can generate these files from descriptions of the machines.