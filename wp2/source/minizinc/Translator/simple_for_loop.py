import ast

code = """
x = 0
y = 1
end = 10
for t in range(1, end + 1):
    x = x + y
    y = x + 1
x = x + 1
"""

tree = ast.parse(code)

# Pretty-print the AST
print(ast.dump(tree, indent=4))  # Python 3.9+ only

for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        print("Found an assignment:")
        print(ast.dump(node, indent=4))
    if isinstance(node, ast.For):
        print("Found a for loop:")
        print(ast.dump(node, indent=4))
