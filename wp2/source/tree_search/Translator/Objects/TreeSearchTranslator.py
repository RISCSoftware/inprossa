"""
First tree search implementation
"""
import ast
from typing import Callable, Any, Iterable, Tuple, List, Optional
#from Translator.Objects.Predicate import Predicate
#from Translator.Objects.CodeBlock import CodeBlock
#from Translator.Objects.MiniZincObject import MiniZincObject
#from Translator.Objects.Constant import Constant
#from Translator.Objects.DSTypes import DSRecord, DSType
from Translator.Objects import TreeSearchException


class State:
    """
    Represents a search state, in this case a variable assignment
    """
    def __init__(self, variables: Any, depth: int = -1, value: int = -1):
        self.variables = variables
        self.depth = depth
        self.value = value


class Node:
    """
    Simple tree search node
    """

    def __init__(
        self,
        state: Any,
        parent: Optional["Node"] = None,
        action: Optional[Any] = None,
        path_cost: float = 0.0,
    ):
        self.state = state
        self.parent = parent
        self.action = action
        self.path_cost = path_cost
        self.depth = 0 if parent is None else parent.depth + 1

    def expand(self, successors_fn: Callable[[Any], Iterable[Tuple[Any, Any, float]]]) -> List["Node"]:
        """
        Expand node using successors_fn.

        successors_fn(state) -> iterable of (next_state, action, cost)
        """
        return [
            Node(state=s, parent=self, action=a, path_cost=self.path_cost + c)
            for (s, a, c) in successors_fn(self.state)
        ]

    def path(self) -> List["Node"]:
        """Return list of nodes from root to this node (inclusive)."""
        node, p = self, []
        while node is not None:
            p.append(node)
            node = node.parent
        return list(reversed(p))

    def states_path(self) -> List[Any]:
        """Return list of states from root to this node."""
        return [n.state for n in self.path()]

    def __lt__(self, other: "Node") -> bool:
        return self.path_cost < other.path_cost

    def __repr__(self) -> str:
        return f"Node(state={self.state!r}, cost={self.path_cost}, depth={self.depth})"


class Variable:
    """
    Represents a decision variable.

    Consideration: Use `Variable` from MiniZinc translator? I don't know, if this is a good idea or not.
    
    """
    def __init__(self, lb, ub, name = None):
        self.lower_bound = lb
        self.upper_bound = ub
        self.initialized = False
        self.name = name

class TreeSearchTranslator:
    """
    Top-level orchestrator:
    In this version, the code of the Python problem 
    """
    def __init__(self, code):
        self.code = code
        self.constants = dict()
        self.variables = dict()
        self.variable_definitions = {}

        self.types = dict()
        self.predicates = dict()
        self.records = dict()
        self.top_level_stmts = []
        # TODO currently no objective handling, this must somehow be considered in the search
        self.objective = None

    def unroll_translation(self):
        """Returns the compiled code that corresponds to the given Python code."""
        self.parse()
        return self.compile()
    
    def parse(self):
        """
        Parse the input code collection functions as predicates
        and creating a list of top-level statements.
        """
        
        tree = ast.parse(self.code)
        for node in tree.body:
            if isinstance(node, ast.AnnAssign) and node.target.id.isupper():
                # this is a constant, which we may need for variable definitions
                if isinstance(node.value, ast.Constant):
                    self.constants[node.target.id] = node.value.value
            if isinstance(node, ast.AnnAssign) and node.target.id.islower():
                # this is a variable definition
                print(f"variables: {node.target.id}")
                self.variable_definitions[node.target.id] = node

            # 1) type definitions -> MiniZinc type definitions
            if (isinstance(node, ast.Assign) and
                isinstance(node.value, ast.Call) and  # right-hand side is a call
                isinstance(node.value.func, ast.Name) and
                node.value.func.id.startswith("DS")):
                pass
            # 2) class definitions -> MiniZincObject
            elif isinstance(node, ast.ClassDef):
                pass
            # 3) function definitions -> Predicates
            elif isinstance(node, ast.FunctionDef):
                self.predicates[node.name] = node
                pass
            else:
                pass
        return self

    def compile(self):
        """Execute top-level block with access to registered predicates"""
        # generate all variables
        for k, ast_node in self.variable_definitions.items():
            annotation = ast_node.annotation
            n_variables = None
            if len(annotation.args) != 2:
                raise Exception("Length of annotation != 2.")
            if isinstance(annotation.args[0], ast.Name):
                name = annotation.args[0].id
                n_variables = self.constants[name]
            if isinstance(annotation.args[0], ast.Constant):
                n_variables = annotation.args[0].value

            print(f"{k}: {n_variables}")
            if n_variables is None:
                raise Exception("Number of variables is not given!")
            
            # parse type
            domain_definition = annotation.args[1]
            lb = None
            ub = None
            if isinstance(domain_definition, ast.Call):
                if domain_definition.func.id == "DSInt":
                    if isinstance(domain_definition.args[0], ast.Constant):
                        lb = domain_definition.args[0].value
                    elif isinstance(domain_definition.args[0], ast.Name):
                        name = domain_definition.args[0].id
                        lb = self.constants[name].value_structure
                    if isinstance(domain_definition.args[1], ast.Name):
                        name = domain_definition.args[1].id
                        ub = self.constants[name]
                    elif isinstance(domain_definition.args[1], ast.Constant):
                        ub = domain_definition.args[1].value

            if lb is None or ub is None:
                raise TreeSearchException("No lower or upper bound is given!")

            self.variables[k] = {
                'values': [None for x in range(n_variables)],
                'domain': [(lb, ub) for _ in range(n_variables)],
                'assigned': [False for _ in range(n_variables)]
            }

        print("VARIABLES", self.variables)

        # This is not really a good solution
        exec(self.code, self.__dict__)

        root_state = State(self.variables)
        bfs(root_state, self.goal_state, self.successors)


    def goal_state(self, state):
        """Checks that every variable is assigned"""
        for v in state.variables:
            for a in state.variables[v]['assigned']:
                if not a: return False
        return True

    def successors(self, state: State):
        """Generates all new child states for a state"""
        current_depth = state.depth

        current_variables = state.variables

        new_depth = current_depth + 1

        for va in current_variables:
            if new_depth < len(current_variables[va]['values']):
                for v in range(current_variables[va]['domain'][new_depth][0], current_variables[va]['domain'][new_depth][1]):
                    new_variables = {
                        va: {
                        'values': current_variables[va]['values'][:],
                        'domain': current_variables[va]['domain'],
                        'assigned': current_variables[va]['assigned'][:]
                        }
                    }
                    new_variables[va]['values'][new_depth] = v
                    new_variables[va]['assigned'][new_depth]= True
                    feasible = True
                    for n, f in self.predicates.items():
                        try:
                            self.__dict__[n](new_variables['assignments']['values'])
                        except Exception as ex:
                            #print("exception", ex)
                            feasible = False
                        
                        if feasible:
                            yield (State(new_variables, new_depth, v), (new_depth, v), 0)


def bfs(start_state: Any, goal_test: Callable[[Any], bool], successors_fn: Callable[[Any], Iterable[Tuple[Any, Any, float]]]) -> Optional[Node]:
    """Breadth-first search (returns first found goal Node or None)."""
    root = Node(start_state)
    if goal_test(root.state):
        return root

    frontier: List[Node] = [root]
    explored = set()

    while frontier:
        node = frontier.pop(0)
        explored.add(node.state)
        for child in node.expand(successors_fn):
            if child.state in explored or any(n.state == child.state for n in frontier):
                continue
            if goal_test(child.state):
                print(child.state.variables)
                #return child
            frontier.append(child)
    return None

def dfs():
    """
    Not yet implemented!
    """

def cost_search():
    """
    Not yet implemented!
    """
