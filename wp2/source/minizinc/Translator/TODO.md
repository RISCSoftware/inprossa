Figure information to save about:
- objects (distinguishing between types and classes?)
- constants
- predicates
- variables : [diccionary names to types/classes]


To give the type of a variable we use
x: MyType
if no type is specified "int" is assumed

To save the types after reading them, maybe it's best as diccionaries

When a variable is updated, we add one to the counter of versions and create an assertion to impose the new value

When a part of a list or a named tuple is updated, we add one to the version counter, in the new version assert all not modified parts to be the same as in the prev version and the modified part is asserted to be equal to the specified value


