import ast
from datetime import datetime
import json
import math
import os
import re
import sys
import traceback
from enum import Enum
import constants


from BinPackingValidator import check_satisfiability_given
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from constants import SYSTEM_PROMPT_FOLDER, DEBUG_MODE_ON, USE_TYPING, USE_PYDANTIC
import logging

from solver import MiniZincSolver

logger = logging.getLogger(__name__)

USE_OPTDSL = constants.USE_OPTDSL
CHOSEN_LANGUAGE = constants.CHOSEN_LANGUAGE
model = None

def use_heavy_module_sentence_transformers():
    from sentence_transformers import SentenceTransformer
    global model
    model = SentenceTransformer("all-MiniLM-L6-v2")

class State(Enum):
    UNINITIALIZED = -1
    CORRECT = 0
    FAILED  = 1

class Type(Enum):
    UNMODIFIED = "unmodified"
    MUTATED = "muted"
    MERGED = "merged"


class TreeNode:
    MAX_LEVEL = 4
    MAX_CANDIDATES = 2
    FILE_NAME = "data.json"

    def __init__(self, name = "", parent = None, level: float = 0, save_nodes: bool = False, save_model:bool = False):
        self.name = name
        self.content = ""
        self.parent = parent
        node_id = f"L{level}-N{len(self.parent.children) if self.parent is not None else "0"}"
        self.id = f"{self.parent.id+"|" if self.parent is not None else ""}{node_id}"
        self.path = self.parent.path + f"/{node_id}" if self.parent is not None else node_id
        if self.parent is not None : self.parent.append_child(self)
        self.save_nodes = (self.parent.save_nodes if self.parent is not None else save_nodes)
        self.save_model = (self.parent.save_model if self.parent is not None else save_model)
        self.children = []
        self.is_optimal = False
        self.is_terminal = False
        self.level = level
        self.state = State.UNINITIALIZED
        self.objective_val = None
        self.solve_time = None
        self.solution_model = None
        self.validated = False
        self.n_failed_generations = parent.n_failed_generations if self.parent is not None else 0
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now if self.parent is not None else ""
        # MCTS specific
        self.visits = 0
        self.wins = 0.0

    def save_child_to_file(self, final_evaluation_result: str = None, problem_description: str = None, filename: str = f'optDSL_model_{datetime.now().strftime("%Y-%m-%d_%H")}.json'):
        if self.state == State.CORRECT and final_evaluation_result is not None and "Successfully" in final_evaluation_result:
            self.validated = True
            if self.save_model and self.is_terminal and self.last_in_progress and problem_description is not None:
                self.save_model_to_file(final_evaluation_result, problem_description, filename)
        if not self.save_nodes or (self.level >= 4 and not final_evaluation_result): return
        data = {
            "id": self.id,
            "state": self.state.value,
            "n_failed_generations": self.n_failed_generations,
            "content": self.variables_and_constants if self.level == 2 else self.content,
            "partial_formulation_up_until_now": self.partial_formulation_up_until_now if not final_evaluation_result else initial_clean_up(self.get_partial_formulation_up_until_now()),
            "objective_val": self.objective_val,
            "solution_model": self.solution_model,
            "solve_time": self.solve_time,
            "is_solver_optimal": self.is_optimal
        }
        if final_evaluation_result: data.update({"final_evaluation_result": final_evaluation_result})
        file_path = f"{self.path}/{self.FILE_NAME}"
        folder = os.path.dirname(file_path)
        os.makedirs(folder, exist_ok=True) # create folder (+ parent folders) if not existent
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def save_model_to_file(self, final_evaluation_result, problem_description: str, filename: str = f'optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H")}.json'):
        curNode = self
        while curNode.parent.level != 3:
            curNode = curNode.parent
        data = {
            "problem_description": problem_description,
            "llm_generated_objects": initial_clean_up(curNode.parent.parent.parent.llm_generated_objects) if curNode.parent.parent.parent.llm_generated_objects is not None else "",
            "script_generated_objects": curNode.parent.parent.parent.script_generated_objects if curNode.parent.parent.parent.script_generated_objects is not None else "",
            "constants": [constant for constant in curNode.parent.parent.variables_and_constants if constant["variable_name"].isupper()],
            "decision_variables": [constant for constant in curNode.parent.parent.variables_and_constants if constant["variable_name"].islower()],
            "objective": initial_clean_up(curNode.parent.content),
            "constraints": initial_clean_up(self.content),
            "full_formulation": initial_clean_up(self.get_partial_formulation_up_until_now()),
            "objective_val": self.objective_val,
            "solution_model": self.solution_model,
            "solve_time": self.solve_time,
            "is_solver_optimal": self.is_optimal,
            "final_evaluation_result": final_evaluation_result
        }
        # Append new model to existing collection
        if os.path.exists(filename):
            with open(filename, "r") as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        existing_data.append(data)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4)

    def increment_n_failed_generations(self):
        """
            Increment number of failed LLM formulation generations.
        """
        self.n_failed_generations += 1
        self.state = State.FAILED

    def append_child(self, child):
        """
        Append a child node to the current node. Max. possilbe children is constants.NR_MAX_CHILDREN.
        Args:
            child (TreeNode): child to be appended.
        """
        self.children.append(child)

    def get_correct_children(self):
        """
        Get syntactically/semantically correct child nodes from current node.
        """
        return [child for child in self.children if (child.state == State.CORRECT and child.n_failed_generations == 0)]

    def get_partial_formulation_up_until_now(self):
        """
        Get formulation from root up to current node.
        """
        return self.partial_formulation_up_until_now

    def set_content(self, content):
        """
        Set content of current node.
        Args:
            content (str): content of current node.
        """
        if isinstance(self, ObjectsNode) and "# --- Objects ---\n" not in content: content =  "# --- Objects ---\n" + content

        self.content += "\n\n"
        content = remove_programming_environment(content.strip())
        self.content += content

        self.partial_formulation_up_until_now += "\n\n" + content
        if content.strip() == "":
            self.increment_n_failed_generations()
        else:
            if self.state == State.UNINITIALIZED: self.state = State.CORRECT
        if self.save_nodes: self.save_child_to_file()


    def get_siblings(self):
        """
        Get tree siblings of current node.
        """
        curNode = self
        while (not isinstance(curNode, RootNode)):
            curNode = curNode.parent
        return self.collect_siblings([], curNode)

    def collect_siblings(self, siblings: list, curNode):
        """
        Collect siblings of current node across tree recursively.
        Args:
            siblings (list): siblings of current node.
            curNode (TreeNode): current node.
        """
        if curNode is not self and curNode.level == self.level:
            siblings.append(curNode.formulation_with_stripped_comments())
        if curNode.level == 4:
            return siblings
        else:
            for child in curNode.children:
                siblings = self.collect_siblings(siblings, child)
        return siblings

    def formulation_with_stripped_comments(self):
        """
        Remove all comments from partial_formulation_up_until_now and return it.
        """
        return TreeNode.strip_comments(self.get_partial_formulation_up_until_now())

    @staticmethod
    def strip_comments(code: str):
        """
        Remove python comments from pythonic formulation "code".
        Args:
            code (str): python/pythonic formulation
        """
        code = re.sub(r'(?m)^ *#.*\n?', '', str(code))
        return "\n".join(line for line in code.split("\n") if line)

    ################# MCST specific ####################
    def is_fully_expanded(self):
        return len(self.children) >= TreeNode.MAX_CANDIDATES

    def best_child(self, c=1.4):
        for child in self.children:
            if child.visits == 0:
                return child

        def ucb(child):
            exploit = child.wins / child.visits
            explore = c * math.sqrt(math.log(self.visits) / child.visits)
            return exploit + explore

        return min(self.children, key=ucb)


class RootNode(TreeNode):
    def __init__(self, name = "", parent = None, save_nodes: bool = False, save_model:bool = False):
        super().__init__(name, parent, save_nodes=save_nodes, save_model=save_model)
        use_heavy_module_sentence_transformers()

class ObjectsNode(TreeNode):
    def __init__(self, name = "", parent = None):
        super().__init__("Objects", parent, level=1)
        self.llm_generated_objects = None
        self.script_generated_objects = None

    def set_llm_generated_objects(self, llm_generated_objects):
        """
        Set LLM-generated object type OptDSL formulation, used for flexible shapes methodology.
        """
        self.llm_generated_objects = llm_generated_objects

    def set_script_generated_objects(self, script_generated_objects):
        """
        Set script-generated object type OptDSL formulation, used for fixed shapes methodology.
        """
        self.script_generated_objects = script_generated_objects

class VariablesConstantsNode(TreeNode):
    def __init__(self, name = "", parent = None):
        self.variables_and_constants = []
        self.all_variables_created = False
        super().__init__("Constants and Decision Variables", parent, level=2)

    def set_constants(self, incomming_constants):
        """
        Set constants in node as json (self.variables_and_constants),
        while also defining the json definitions as OptDSL formulation block (self.content).
        Args:
            incomming_constants (str): json-string representing variable definitions.
        """
        self.content = "# --- Constants ---\n"
        if not is_valid_json(incomming_constants):
            self.state = State.FAILED
            return False
        if incomming_constants.strip() == "":
            self.state = State.FAILED

        # Filter constants
        filtered_constants_only = [item for item in json.loads(incomming_constants) if item.get("variable_name", "").isupper()]

        # Safety check: There must be at least one constant (input)
        if len(filtered_constants_only) == 0:
            if constants.DEBUG_MODE_ON: print(f"Checking node created for level 2 (constants): No uppercase constants found.")
            self.state = State.FAILED
            return False

        self.variables_and_constants.extend(filtered_constants_only)
        self.content += self.get_as_codeblock()
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now + "\n\n" + self.content

        # Only check satisfiability for constants if mode is "fixed_objects_fixed_input_values", "fixed_objects_fixed_inoutput_values"
        if "variable_instance" in self.variables_and_constants[0]: check_satisfiability_given(self.variables_and_constants)

        self.state = State.CORRECT
        if self.save_nodes: self.save_child_to_file()
        return True

    def set_variables(self, variables, expected_output_variables):
        """
        Set decision variables in node as json (self.variables_and_constants),
        while also defining the json definitions as OptDSL formulation block (self.content).
        Args:
            variables (str): json-string representing variable definitions.
            expected_output_variables (str): list of expected output variables names.
        """
        if not is_valid_json(variables):
            return False

        if variables.strip() == "":
            self.state = State.FAILED

        # Filter decision variables
        filtered_decision_variables_only = [item for item in json.loads(variables) if item.get("variable_name", "").islower()]

        # Safety check: There must be at least one decision variable (output)
        if len(filtered_decision_variables_only) == 0:
            if constants.DEBUG_MODE_ON: print(
                f"Checking node created for level 3 (decision variables): No lower case variables found.")
            return False

        # Safety check: All expected output variable names must be defined
        if expected_output_variables:
            variable_names = [item["variable_name"] for item in filtered_decision_variables_only]
            for expected_variable in (json.loads(remove_programming_environment(expected_output_variables))):
                if expected_variable["mandatory_variable_name"] not in variable_names:
                    if DEBUG_MODE_ON: print(f"Expected variable not defined: {expected_variable["mandatory_variable_name"]}")
                    return False

        self.variables_and_constants.extend(remove_duplicate_variables(filtered_decision_variables_only,0.925))
        self.define_list_lengths()
        self.variables_and_constants = remove_duplicate_variables(self.variables_and_constants, 1)
        self.content = f"\n\n# --- {self.name} ---\n" + self.get_as_codeblock()
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now + "\n\n" + self.content
        if self.state == State.UNINITIALIZED: self.state = State.CORRECT
        self.all_variables_created = True
        if self.save_nodes: self.save_child_to_file()
        return True

    def define_list_lengths(self):
        """
        Manually define list lengths as OptDSL constants, as LLM tends to forget.
        """
        for constant in self.variables_and_constants:
            if "initialization" in constant and ("DSList" in constant["initialization"] or "list[" in constant["initialization"]):
                match = re.search(r"length=(\d+)", constant["initialization"])
                if not match: match = re.search(r"Len\s*\(\s*\d+\s*,\s*(?P<max>\d+)\s*\)\s*", constant["initialization"])
                if match:
                    if f"N_{constant["variable_name"].upper()} : int = " in constant["initialization"]: continue
                    length_value = int(match.group(1))
                    self.variables_and_constants.append(
                        {
                            "description": f"Length of {constant["variable_name"]}",
                            "variable_name": f"N_{constant["variable_name"]}",
                            "type": "int",
                            "initialization": f"N_{str(constant["variable_name"]).upper()} : int = {length_value}"
                        }
                    )
                else:
                    if DEBUG_MODE_ON: print("Warning: DSList has no length defined.")

    def get_as_codeblock(self):
        """
        From the object-, constants- (json) and decision variable definitions (json) create an OptDSL formulation block.
        """
        variable_block = ""
        encountered_decision_variables = False
        for definition in self.variables_and_constants:
            if definition["variable_name"].islower() and encountered_decision_variables:
                variable_block += f"\n\n# --- Decision variables ---\n"
                encountered_decision_variables = True
            variable_block += f"{definition["initialization"]}\n"
        return variable_block

class ObjectiveNode(TreeNode):
    def __init__(self, name = "", parent = None):
        super().__init__("Objective", parent, level=3)

class ConstraintsNode(TreeNode):
    def __init__(self, name = "", parent = None, level: int = None):
        if level is None: level = 4
        super().__init__("Constraints", parent, level=level)
        self.is_terminal = True
        self.last_in_progress = False
        if self.parent.level > 3:
            self.content += self.parent.content
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now
        self.content += f"# -- {self.name} --\n"

def is_valid_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except ValueError:
        return False

def _build_code(node):
    """
    Recursively collect the OptDSL formulation components from node to root to one formulation.
    Args:
        node(TreeNode): node to collect formulation component from
    """
    if node is None or node.level == 0:
        return ""

    return _build_code(node.parent) + "\n\n" + node.content

def check_executability(node: TreeNode, raw_code : str):
    """
        Check executability with security checks and OptDSL-translator and MiniZinc solver, if those two tools do not throw any error,
        we consider the formulation as executable.
        Args:
             node (TreeNode): current node in ToT, saves solver metadata (e.g. solvetime, objective value, etc.).
             raw_code (str): raw code to check.
    """
    # Construct partial/full formulation up until now, depending on current level
    variable_block = f"\n{node.get_partial_formulation_up_until_now()}\n"

    # Prepare raw constants/variable definitions and add to partial formulation (up until now)
    if node.level == 2:
        raw_code = json.loads(raw_code)
        if not isinstance(raw_code, list):
            return """Error, invalid type of definitions. Must be a array of json objects.
The response must exactly adhere to the following format, no outer wrappers:
Return you answer in the following format:
[{
     "description":<description>,
     "variable_name":<variable_name>,
     "type":<variable_type>,
     "initialization":<initialization>
}]
The structure must fulfill following requirements:
1. <description> is a placeholder for a compact, concise description of the variable.
2. <variable_name> is the unique variable identifier described in description, that will later be used for creating decision variables and constraints. Constants naming convention: capital letters only.
3. <initialization> is the OptDSL variable declaration and initialization code block, fully with assignments, of the variable in variable field. Must be valid OptDSL code.
4. <variable_type> is the type of the variable. The variable type is either an object, a primitive python type (e.g. int, float) or an inlined DSList declaration. It can be found in the initialization after the double colon as the type of the variable.
5. No additional properties allowed.
"""
        # Remove upper or lower case for constants and variables respectively
        if isinstance(node, VariablesConstantsNode) and len(node.variables_and_constants) == 0:
            raw_code = [item for item in raw_code if
                        item.get("variable_name", "").isupper()]
        else:
            raw_code = [item for item in raw_code if
                        item.get("variable_name", "").islower()]
        if raw_code == "": return "Error - Invalid result: Result is empty."
        for definition in raw_code:
            #if "Annotated[list[" in definition["type"] and re.search(r'Annotated\[\s*list\[\s*(?P<elem_type>int|float|bool)\s*]\s*,\s*Len\(\s*\d+\s*,\s*(?P<max>\d+)\s*\)\s*]', definition["type"]):
            #    return f"Error: {definition["type"]}\n, for this list elem_type must have a type of typing.Annotated with a pydantic.Field of type int, float, bool. Including lower (ge) and upper bounds (le). Demonstration example for a list of integers: Annotated[list[Annotated[int, Field(lb=-10,ub=10)]], Len(2,2)]"
            variable_block += f"{definition["initialization"]}\n"
    else:
    # Prepare raw obj. function or constraints and add to partial formulation (up until now)
        # Safety check: no json has be returned instead of code
        if is_valid_json(raw_code) or raw_code.startswith("{") or raw_code.startswith("["):
            return f"Error: Result must not be json objects, valid {constants.CHOSEN_LANGUAGE} code."

        # Safety check: no json has be returned instead of code
        if is_valid_json(raw_code) or raw_code.startswith("{") or raw_code.startswith("["):
            return f"""Error: Result must not be json objects, valid {constants.CHOSEN_LANGUAGE} code.
The response must exactly adhere to the following format, no outer wrappers:
Return you answer in the following format:
[{{
    "description":<description>,
    "variable_name":<variable_name>,
    "type":<variable_type>,
    "initialization":<initialization>
}}]
The structure must fulfill following requirements:
1. <description> is a placeholder for a compact, concise description of the variable.
2. <variable_name> is the unique variable identifier described in description, that will later be used for creating decision variables and constraints. Constants naming convention: capital letters only.
3. <initialization> is the OptDSL variable declaration and initialization code block, fully with assignments, of the variable in variable field. Must be valid OptDSL code.
4. <variable_type> is the type of the variable. The variable type is either an object, a primitive python type (e.g. int, float) or an inlined DSList declaration. It can be found in the initialization after the double colon as the type of the variable.
5. No additional properties allowed."""

        # Result must not be empty
        if raw_code == "": return "Error - Invalid result: Result is empty."

        # Safety check: check if calculate_objective function defined and calculated objective is assigned to a variable "objective" at some point
        if node.level == 3:
            if "def calculate_objective" not in raw_code:
                return """The result does not contain 'calculate_objective'. Add a function calculate_objective that contains the calculation of the objective value.
Return you answer in the following format:
´´´python
# --- Objective ---
def calculate_objective (...):
<solution>
objective = calculate_objective(...)
<decision_variable> = objective
minimize(objective)
´´´ replace <solution> with the code. <solution> must not be empty. And replace decision_variable with a given decision variable, which represents the objective"""
            if not constants.ALGOPOLISH_ACTIVE and "objective =" not in raw_code and "objective :" not in raw_code:
                return "Add the assignment \"objective = <variable>\", replace <variable> with the decision variable that represents the objective, nothing else."

        # Safety check: check that there are no non-constants in range
        m = re.search(r"(.*)(range\(\s*(?=[^,]+[a-z])[^,]+,\s*[^)]+|range\(\s*[^,]+,\s*(?=[^) ]+[a-z])[^)]+\))", raw_code)
        if m:
            if "#" not in m.group(1):
                return f"Error - range incorrectly used. Use range(<val_1>,<val_2>) where val_1 and val_2 must be a constant variable or a integer value: {m.group(2)}"
        variable_block += raw_code

    # Execute code block of partial/full formulation
    return execute_code_block(variable_block, node, include_solver_execution=(node.level >= 3))


def execute_code_block(variable_block: str, node, include_solver_execution: bool = False):
    """
        Check executability with security checks and OptDSL-translator and MiniZinc solver, if those two tools do not throw any error,
        we consider the formulation as executable.
        Args:
             variable_block (str): Raw full OptDSL-formulation (roughly checked by security checks for non-empty, range-valid-formulation, format validity etc.).
             include_solver_execution (bool): if true, also check executabilty by solver.
    """
    variable_block = initial_clean_up(variable_block)
    try:
        if USE_OPTDSL:
            # Syntax CHECK
            compile(variable_block, "<string>", "exec")
            model = MiniZincTranslator(variable_block).unroll_translation()
            try:
                # Semantic CHECK
                if include_solver_execution:
                    solution = _check_solver_executability(model, node)
                    if solution is None: return solution
                    if ("type error in operator application for `'*''. No matching operator found with left-hand side type `array[int] of bool' and right-hand side type `int" in solution or
                        "type error in operator application for `'*''. No matching operator found with left-hand side type `array[int] of bool' and right-hand side type `int" in solution or
                        "type error in operator application for `'*''. No matching operator found with left-hand side type `array[int] of int' and right-hand side type `int'" in solution):
                        return "Do not use list comprehension. Do not use any list multiplication operator on arrays. Code like `[1] * 5` and `[True for _ in range(1, 5)]` is illegal. Do not use function calls append() and extend() for DSList. Do not set default values."
                    if "Error" in solution:
                        return solution.split("\n")[0]
                    if "result of evaluation is undefined: parameter out of range: declared domain of `ITEMS[20].width' is 1..10, but assigned value is 49" in solution:
                        m=1
                    return solution
            except Exception as e:
                return str(e)
        else:
            exec(variable_block, {})
    except SyntaxError as e:
        if "Annotated" in variable_block:
            return "Tuple is not supported. Use typing.Annotated with pydantic.Field of type int, float, int or one of the given object types in \"--- Objects ---\", or complex type list as typing."
        return f"Syntax Error \"{e.msg}\" in line {e.lineno}, at offset {e.offset}: {e.text.rstrip() if e.text else None}"
    except Exception as e:
        logger.exception(e)
        if "unexpected indent" in str(e):
            return f"Constraints/Objective FormatError"
        exc_type, exc_value, exc_tb = sys.exc_info()
        stack_trace_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))

        # Filter error from optdsl-translator
        m = re.search(r"(?m)^(?P<type>[\w.]+(?:Error|Exception)):\s*(?P<msg>.*)$", stack_trace_str)
        if m:
            exc_type = m.group("type")
            exc_msg = m.group("msg")
            if "KeyError" in exc_msg:
                return exc_msg + " Did you forget to put a decision variable as function parameter?"
            elif exc_msg == 'Unknown type string: DSList':
                return f"Error: Variable list object type definition must adhere to the EBNF\ngrammar <variable_name> : \"DSList\" \"(\" FunArgs([\"length\", \"elem_type\"]) \")\"."
            elif exc_msg == "'int' object is not subscriptable":
                return f"Error: Do not perform calculations within index brackets. Instead, calculate it as temporary variable and then use it for accessing the list index."
            elif "attr='append', ctx=Load())," in exc_msg:
                return f"Error - Do not use function calls append() and extend() for lists."
            elif "Only returning names or tuple of names is supported." in exc_msg:
                return f"Error - Functions support returning names or tuple of names only. Either do not call return at all, or only return names or tuple of names. Do not return calculation expressions. Do not use \"return\\n\". Do not use \"\\n return <bool>\\n\", where <bool> is True or False."
            elif "tuple[" in exc_msg:
                return "Tuple is not supported. Use typing.Annotated with pydantic.Field of type int, float, int or one of the given object types in \"--- Objects ---\", or complex type list as typing.Annotated of typing."
            elif "incompatible types" in exc_msg:
                return f"For assert expressions, do not extract calculations or single object-fields. Inline them!"
            elif "ValueError: Variable" in exc_msg and "has incompatible types in if-else branches:" in exc_msg:
                return "Do not extract assert-expression into temporary variables, but inline the expression within assert directly."
            elif "ListComp" in exc_msg:
                return "Do not use list comprehension or any list multiplication operator. Do not use function calls append() and extend() for DSList."
            elif "Unsupported statement: Break()" in exc_msg:
                return "Do not use break statement."
            elif "undefined identifier `None" in exc_msg:
                return "Do not use None."
            elif "Unsupported statement: Pass()" in exc_msg:
                return "Constraints/Objective FormatError"
            elif "Subscript(value=Name(id='Annotated', ctx=Load())," in exc_msg:
                return "Use typing.Annotated with pydantic.Field of type int, float, int or one of the given object types in \"--- Objects ---\", or complex type list as typing.Annotated of typing. E.g. Annotated[list[Annotated[int, Field(strict=True)]], Len(5,5)]"
            elif "Unknown type string:" in exc_msg:
                return f"Do not use non-existent variables or object types: {exc_msg}."
            elif "not defined in variable table" in exc_msg:
                return f"Check if variable exists at root level at all and if in function, check if has been passed as parameter: {exc_msg}."
            elif "Error processing statement:" in exc_msg:
                return f"{exc_msg}"
            return f"{exc_type} - {exc_msg}, occurring at: {exc_msg.replace("Error processing statement: ", "")}\n"
        return str(e)

def _check_solver_executability(model: str, node):
    """
    Check that MiniZinc model can be executed and solved with a MiniZinc solver.
    Args:
        model (str): MiniZinc model.
        node (TreeNode): current node in ToT, saves solver metadata (e.g. solvetime, objective value, etc.).
    """
    # Safety check: replace python True/False with lower case equivalent for OptDSL
    model = model.replace("True", "true").replace("False", "false")

    if isinstance(node, TreeNode):
        solution, solve_time = MiniZincSolver().solve_with_command_line_minizinc(model, node.last_in_progress if node.is_terminal else False)
    else:
        solution, solve_time = MiniZincSolver().solve_with_command_line_minizinc(model, True)

    if "Memory violation detected (stack overflow)" in solution:
        return "Memory violation detected (stack overflow)."
    elif "Error" in solution:
        return solution
    elif "type error" in solution:
        return "Minizinc Solver Error"
    elif solution is None:
        print("Solver failed: Invalid encoding yielded invalid solution.")
        return f"Semantic Error, correct the semantics."
    elif "unknown" == str(solution).lower():
        return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" yields no answer at all. Define more variable bounds. Recheck the semantics."
    elif constants.SOLVER == "gecode" and "unknown" in str(solution).lower(): # comment in if solver is gecode
        if node.level == 3:
            return None
        else:
            return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" yields no answer at all. Define more variable bounds."
    elif "unsatisfiable" in str(solution).lower():
        print("Solver yields UNSAT or Unknown.")
        return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" causes the solver to yield unsatisfiable, but it should be satisfiable."
    else:
        if "objective" in solution:
            if constants.DEBUG_MODE_ON: print(f"Solution for objective is: {solution["objective"]}")
            node.objective_val = solution["objective"][len(solution["objective"]) - 1]
        elif constants.ALGOPOLISH_ACTIVE and constants.OBJECTIVE_VARIABLE_NAME in solution:
            node.objective_val = solution[constants.OBJECTIVE_VARIABLE_NAME][len(solution[constants.OBJECTIVE_VARIABLE_NAME])-1]

        node.solve_time = solve_time
        node.solution_model = solution
        if "unknown" in str(solution).lower():
            node.is_optimal = False
        else:
            node.is_optimal = True
        return None

def check_solver_executability_for_plain_model(model: str):
    """
    Check executability with MiniZinc solver for MiniZinc model alone (without saving solving metadata to a node).
    """
    # Safety check: replace python True/False with lower case equivalent for OptDSL
    model = model.replace("True", "true").replace("False", "false")

    solution, solve_time = MiniZincSolver().solve_with_command_line_minizinc(model, True)
    # Check for errors
    if "Error" in solution:
        return solution, None, None
    elif "type error" in solution:
        return "Minizinc Solver Error", None, None
    elif solution is None:
        print("Solver failed: Invalid encoding yielded invalid solution.")
        return f"Semantic Error, correct the semantics.", None, None
    elif "unsatisfiable" in str(solution).lower():
        print("Solver yields UNSAT or Unknown.")
        return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" causes the solver to yield unsatisfiable, but it should be satisfiable.", None, None
    else:
        if constants.ALGOPOLISH_ACTIVE and constants.OBJECTIVE_VARIABLE_NAME in solution:
            print(f"Solution for objective is: {solution[constants.OBJECTIVE_VARIABLE_NAME]}")
            return solution[constants.OBJECTIVE_VARIABLE_NAME][len(solution[constants.OBJECTIVE_VARIABLE_NAME])-1], solve_time, solution
        elif "objective" in solution:
            print(f"Solution for objective is: {solution["objective"]}")
            return solution["objective"][
                len(solution["objective"]) - 1], solve_time, solution
        else:
            print("Solver succeeded, but no _objective is available.")
        return None, solve_time, solution


# ----------- HELPERS -----------

def initial_clean_up(raw_response: str, to_typing: bool = False) -> str:
    """
    Cleans up OptDSL code, removes markdown codeblock environments and converts pydantic and
    typing specific elements to OptDSL code or vice-versa.
    Args:
        raw_response (str): raw OptDSL formulation with markdown-codeblock-env and/or pydantic/typing specific elements.
        to_typing (bool): True, if caller desires to convert OptDSL-specific types back to pydantic elements. Otherwise vice-versa.
    """
    raw_response = remove_programming_environment(raw_response)

    if to_typing:
        raw_response = _convert_OptDSL_to_pydantic(raw_response)
    else:
        # Convert typing-package (Annotated) specific parts to OptDSL
        if USE_TYPING: raw_response = _convert_typing_to_OptDSL(raw_response)
        # Convert pydantic-package (Field, Annotated) specific parts to OptDSL
        elif USE_PYDANTIC: raw_response = _convert_pydantic_to_OptDSL(raw_response)
    return raw_response

def remove_programming_environment(raw_response: str) -> str:
    """
    Removes markdown codeblock environments.
    Args:
        raw_response(str): raw OptDSL formulation from LLM containing markdown code blocks.
    """
    cleaned = raw_response

    if "OptDSL" in cleaned: cleaned = cleaned.replace("OptDSL", "")
    if "json" in cleaned: cleaned = cleaned.replace("json", "")
    if "python" in cleaned: cleaned = cleaned.replace("python", "")
    cleaned = cleaned.replace("´´´", "")
    cleaned = cleaned.replace("```", "")
    if "<reasoning>" in cleaned: cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL)
    if "import" in cleaned: cleaned = "\n".join(line for line in cleaned.splitlines() if "import" not in line)
    if "return\n" in cleaned or "return None" in cleaned: cleaned = "\n".join(line for line in cleaned.splitlines() if "return None" not in line and "return" != line)

    return cleaned.strip()

def _convert_to_DSList(match: re.Match) -> str:
    if match:
        elem_type = match.group("elem_type")
        match elem_type:
            case "int":
                elem_type = "DSInt()"
            case "float":
                elem_type = "DSFloat()"
            case "bool":
                elem_type = "DSBool()"
            case _:
                if "Annotated" in elem_type and "list" in elem_type:
                    elem_type = _convert_typing_to_OptDSL(elem_type)
                if "Annotated" in elem_type:
                    elem_type = _convert_pydantic_to_OptDSL(elem_type)

        mx = match.group("max")
        return f"DSList(length={mx}, elem_type={elem_type})"
    return ""

def _convert_typing_to_OptDSL(code: str, nested: bool = False) -> str:
    if nested:
        regex = r"Annotated\[list\[(?P<elem_type>[^\]]+\],\s*Len\(\d+,\s*\d+\)])],\s*Len\(\d+,\s*(?P<max>\d+)\)\]"
    else:
        # Replace all Annotated[list] with pydantic.Field
        code = re.sub(re.compile(r"Annotated\[list\[(?P<elem_type>[^\]]+?)\],\s*Len\(\s*[^,]+\s*,\s*(?P<max>[^\)]+)\s*\)\]", re.VERBOSE), _convert_to_DSList, code)
        # Replace all Annotated[list] with DS-types
        regex = r"Annotated\[list\[(?P<elem_type>(?:[^\[\]]+|\[[^\[\]]*\])*)\],\s*Len\(\d+,\s*(?P<max>\d+)\)\]"
    pattern = re.compile(
        regex,
        re.VERBOSE
    )
    return re.sub(pattern, _convert_to_DSList, code)

def _convert_pydantic_to_OptDSL(code: str) -> str:
    # Convert to DSBool()
    code = code.replace("Annotated[bool, Field()]", "DSBool()")
    code = code.replace("Annotated[bool, Field(strict=True)]", "DSBool()")

    # Convert to DSInt() and DSFloat()
    pattern = re.compile(r"Annotated\[\s*(?P<type>int|float)\s*,\s*Field\(\s*(?:strict\s*=\s*True\s*)?(?:\s*,\s*)?(?:ge\s*=\s*(?P<ge>(?:[^,\(\)]+|\([^\(\)]*\))+))?(?:(?:\s*,\s*)?le\s*=\s*(?P<le>(?:[^,\(\)]+|\([^\(\)]*\))+))?\s*\)\s*\]", re.VERBOSE)
    code = re.sub(pattern, _convert_to_DSInt_DSFloat, code)

    # Convert nested Annotated Lists to DSList()
    code = _convert_typing_to_OptDSL(code, nested=True)

    # Convert non-nested Annotated to DSList()
    code = _convert_typing_to_OptDSL(code)

    # Convert annotated object type ref to OptDS
    pattern = re.compile(r"Annotated\[\s*(?P<type>\w+)\s*,\s*Field\s*\(\)\s*]", re.VERBOSE)
    code = re.sub(pattern, _convert_object_type_ref_to_DS, code)
    return code

def _convert_to_DSInt_DSFloat(match: re.Match) -> str:
    if match:
        elem_type = match.group("type")
        match elem_type:
            case "int":
                elem_type = "DSInt"
            case "float":
                elem_type = "DSFloat"
        gd = match.groupdict()
        if gd.get('ge') is not None and gd.get('le') is not None:
            return f"{elem_type}(lb={gd['ge']}, ub={gd['le']})"
        elif gd.get('ge') is not None:
            return f"{elem_type}(lb={gd['ge']})"
        elif gd.get('le') is not None:
            return f"{elem_type}(ub={gd['le']})"
        else:
            return f"{elem_type}()"
    return ""

def _convert_object_type_ref_to_DS(match: re.Match) -> str:
    if match:
        elem_type = match.group("type")
        return elem_type
    return ""

def _convert_OptDSList_to_typing_list(regex, code: str) -> str:
    pattern = re.compile(
        regex,
        re.VERBOSE
    )
    return re.sub(pattern, _convert_to_typing_list, code)

def _convert_to_typing_list(match: re.Match) -> str:
    if match:
        elem_type = match.group("elem_type")
        length = match.group("length")
        if "DSList" in elem_type or "DSInt" in elem_type or "DSFloat" in elem_type or "DSBool" in elem_type:
            elem_type = _convert_OptDSL_to_pydantic(elem_type)
        return f"Annotated[list[{elem_type}], Len({length}, {length})]"
    else:
        return match.group(0)

def _convert_object_OptDSList_to_typing_list(match: re.Match):
    if match:
        elem_type = match.group("elem_type")
        length = match.group("length")
        if "Annotated" in elem_type:
            return match.group(0)
        else:
            return f"Annotated[list[{elem_type}], Len({length}, {length})]"
    else:
        return match.group(0)

def _convert_to_pydantic_int_float(match: re.Match) -> str:
    if match:
        elem_type = match.group("type")
        match elem_type:
            case "DSInt":
                elem_type = "int"
            case "DSFloat":
                elem_type = "float"
        gd = match.groupdict()
        if gd.get('lb') is not None and gd.get('ub') is not None:
            return f"Annotated[{elem_type}, Field(strict=True, ge={gd['lb']}, le={gd['ub']})]"
        elif gd.get('lb') is not None:
            return f"Annotated[{elem_type}, Field(strict=True, ge={gd['lb']})]"
        elif gd.get('ub') is not None:
            return f"Annotated[{elem_type}, Field(strict=True, le={gd['ub']})]"
        else:
            return f"Annotated[{elem_type}, Field(strict=True)]"
    return ""

def _convert_OptDSL_to_pydantic(code: str) -> str:
    # Convert from DSBool() to Annotated[bool..]
    code = code.replace("DSBool()", "Annotated[bool, Field()]")
    code = code.replace("DSBool()", "Annotated[bool, Field(strict=True)]")

    # Convert from pydantic int / float to DSInt() and DSFloat()
    pattern = re.compile(
        r"(?P<type>DSInt|DSFloat)\((?:lb\s*=\s*(?P<lb>[^,\)]+)(?:\s*,\s*)?)?(?:ub\s*=\s*(?P<ub>[^,\)]+)(?:\s*,\s*)?)?\s*\)",
        re.VERBOSE)
    code = re.sub(pattern, _convert_to_pydantic_int_float, code)

    # Convert nested DSList() to Annotated Lists
    code = _convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>[^,]+)\s*,\s*elem_type\s*=(?P<elem_type>DSList[^]\r\n]+\]\))\)", code)
    code = _convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>[^,]+)\s*,\s*elem_type\s*=(?P<elem_type>DSList[^)\r\n]+\))\)", code)

    # Convert non-nested DSList() to Annotated Lists
    code = _convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>[^,]+)\s*,\s*elem_type\s*=\s*(?P<elem_type>[^]\r\n]+\])\)", code)
    code = _convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>[^,]+)\s*,\s*elem_type\s*=\s*(?P<elem_type>.+?)\s*\)", code)

    # Convert non-nested DSList() with object-type to Annotated
    pattern = re.compile(
        r"DSList\(\s*length\s*=\s*(?P<length>[^,]+)\s*,\s*elem_type\s*=\s*(?P<elem_type>[^)]+)\)",
        re.VERBOSE
    )
    code = re.sub(pattern, _convert_object_OptDSList_to_typing_list, code)
    return code

def load_sp_file(file_path):
    """
    Load system prompt file.
    Args:
        file_path: Path to system prompt file.
    """
    file_path = SYSTEM_PROMPT_FOLDER + file_path
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def decompose_full_definition (full_definition: str):
    """
    Decompose full raw formulation from LLM into different components according to format convention
    for OptDSL formulations taken for this framework.
    Args:
        full_definition (str): full raw formulation from LLM
    """
    if ("# --- Objects ---".lower() in full_definition.lower() or
           "# --- Constants ---".lower() in full_definition.lower() or
           "# --- Decision variables ---".lower() in full_definition.lower() or
           "# --- Constants and Decision Variables ---".lower() in full_definition.lower() or
           "# --- Objective ---".lower() in full_definition.lower() or
           "# --- Constraints ---".lower() in full_definition.lower() or
           "# --- Incorrect Code ---".lower() in full_definition.lower()):
        full_definition = remove_programming_environment(full_definition)
        blocks = {}
        current_key = None
        temp = []

        for line in full_definition.splitlines():
            # Detect a block header, e.g. "--- Datatypes ---"
            m = re.match(r'^\s*#\s*---\s*(\w+(?:\s+\w+)*)\s*---', line)
            if m:
                current_key = m.group(1).strip().lower()  # use lower case key
                blocks[current_key] = []
            else:
                if current_key is not None:
                    if len(temp) > 0:
                        blocks[current_key] = temp + blocks[current_key]
                        temp = []
                    blocks[current_key].append(line)
                else:
                    if len(line) > 0: temp.append(line)

        # Convert lists into single strings
        for k in blocks:
            blocks[k] = "\n".join(blocks[k]).strip()
        return blocks
    return None

def check_functions_appear_twice(code_str):
    """
    Find function names and check that each function name appears at least twice, ensuring that every defined function is also called.
    Args:
        code_str(str): OptDSL formulation code.
    """
    names = _find_function_names(code_str)
    appears_less_than_twice = []
    for name in names:
        if len(re.findall(r'\b' + re.escape(names[0]) + r'\b', code_str)) <= 1:
            appears_less_than_twice.append(name)
    return appears_less_than_twice

def _find_function_names(code_str):
    pattern = r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
    names = re.findall(pattern, code_str, flags=re.MULTILINE)
    return names

def safety_check_contains_func_that_just_returns_var(func_code: str) -> bool:
    """
    Checks if function consists of more than one return statement of one variable using AST
    """
    # parse the code into an AST
    try:
        tree = ast.parse(func_code)
    except SyntaxError:
        return False

    func_defs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]

    for func in func_defs:
        # exclude docstrings and comments
        body = [node for node in func.body
                if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))]

        # check it's one statement that is a return which returns a single name (variable)
        if len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Name):
            return True
    return False


def remove_duplicate_variables(variable_definitions, threshold: float):
    """
    Iterate through all variables and remove semantic duplicates using sentence-transformer tool to identify semantic similarity.
    Args:
        variable_definitions (list): list of variable names
        threshold (float): threshold for semantic similarity
    """
    from sentence_transformers import util
    filtered_out_duplicates = []
    for i in range(len(variable_definitions)):
        found_duplicate = False
        for j in range(i + 1, len(variable_definitions)):
            emb1 = model.encode(variable_definitions[i]["variable_name"], convert_to_tensor=True)
            emb2 = model.encode(variable_definitions[j]["variable_name"], convert_to_tensor=True)
            if util.cos_sim(emb1, emb2) > threshold:
                found_duplicate = True
                break
        if not found_duplicate:
            filtered_out_duplicates.append(variable_definitions[i])
        else:
            if constants.DEBUG_MODE_ON:
                print(f"Duplicate variables detected: {variable_definitions[i]}")
    return filtered_out_duplicates

def split_at_outer_equals(s: str):
    """
    Splits string code at leftmost outer equals, if present, used to get left or right part of initialization.
    Args:
        s (str): String to split, if possible.
    """
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "=" and depth == 0:
            left = s[:i].rstrip()
            right = s[i + 1:].lstrip()
            return left, right
    return s, ""
