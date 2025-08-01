### Translator from 'Python-lik' instructions to Minizinc

It is able to transform nested 'for' loops and 'if' statements. Into a sequence of arrays and constraints in minizinc.

#### Limitations
It cannot handle:
- functions
- "elif" statements
- floats

#### Issues
How to handle when a variable is not defined in one branch of the if statement
 - one of the options is to ignore it (current)
 - another option is to force it to be an absurd value

 Unclear how to define variables that are used without previous assignment
 - I guess we should force declaration if that is the case (indicating type and range)
    - one option for doing this is through a comment # declar x: int/float/int 1..4/3.0..4.5
    - other is to have a dictionary with such information