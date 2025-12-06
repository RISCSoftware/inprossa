import json
import re
import sys
import traceback
from collections import Counter
from enum import Enum

from sentence_transformers import util

import constants
from sentence_transformers import *

from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from constants import SYSTEM_PROMPT_FOLDER, DEBUG_MODE_ON, USE_TYPING, USE_PYDANTIC
import logging

from minizinc_solver import MiniZincSolver

logger = logging.getLogger(__name__)

USE_OPTDSL = constants.USE_OPTDSL
CHOSEN_LANGUAGE = constants.CHOSEN_LANGUAGE

class State(Enum):
    UNINITIALIZED = 1
    CORRECT = 2
    FAILED  = 3

class TreeNode:
    MAX_LEVEL = 4
    MAX_CANDIDATES = 4

    def __init__(self, name = "", parent = None, level: int = 0):
        self.name = name
        self.content = f"# -- {self.name} --\n"
        self.parent = parent
        self.id = f"{self.parent.id+"|" if self.parent is not None else ""}L{level}-N{len(self.parent.children) if self.parent is not None else "0"}"
        if self.parent is not None : self.parent.append_child(self)
        self.children = []
        self.is_terminal = False
        self.level = level
        self.state = State.UNINITIALIZED
        self.visits = 0  # Visit count
        self.wins = 0  # Win count
        self.objective_val = None
        self.solve_time = None
        self.solution_model = None
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now if self.parent is not None else ""

    def append_child(self, child):
        self.children.append(child)

    def get_correct_children(self):
        return [child for child in self.children if child.state == State.CORRECT]

    def get_partial_formulation_up_until_now(self):
        return self.partial_formulation_up_until_now

    def set_content(self, content):
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT: content = remove_duplicate_lines(build_code(self), content)
        if content.strip() == "":
            self.state = State.FAILED
        else:
            self.state = State.CORRECT
        self.content += "\n\n" + content.strip()
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now + "\n\n" + self.content


    def prepend_section_title(self, block):
        return f"# --- {self.name} ---\n" + block

class RootNode(TreeNode):
    def __init__(self, name = "", parent = None, ):
        super().__init__(name, parent)

    def set_content(self, content):
        if "--- Objects ---".lower() not in content.lower() or "--- Constants ---".lower() not in content.lower() or "--- Decision variables ---".lower() not in content.lower() or "--- Objective function ---".lower() not in content.lower() or "--- Constraints ---".lower() not in content.lower():
            return False
        blocks = {}
        current_key = None

        for line in content.splitlines():
            # Detect a block header, e.g. "--- Datatypes ---"
            m = re.match(r'^---\s*(.+?)\s*---$', line)
            if m:
                current_key = m.group(1).strip().lower()  # use lower case key
                blocks[current_key] = []
            else:
                if current_key is not None:
                    blocks[current_key].append(line)

        # Convert lists into single strings
        for k in blocks:
            blocks[k] = "\n".join(blocks[k]).strip()

        self.content = blocks
        self.state = State.CORRECT
        return True

class ObjectsNode(TreeNode):
    def __init__(self, name = "", parent = None):
        super().__init__("Objects", parent, level=1)

    def get_textual_repr(self):
        return self.parent.content()

class VariablesConstantsNode(TreeNode):
    def __init__(self, name = "", parent = None):
        self.variables_and_constants = []
        self.all_variables_created = False
        super().__init__("Constants", parent, level=2)

    def set_constants(self, incomming_constants):
        if not is_valid_json(incomming_constants):
            return False
        if not constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            # Filter constants
            filtered_constants_only = [item for item in json.loads(incomming_constants) if item.get("variable_name", "").isupper()]
            # TODO add sanity check, nr of input parameter == len(filtered_constants_only)
            # Safety check: There must be at least one constant (input)
            if len(filtered_constants_only) == 0:
                if constants.DEBUG_MODE_ON: print(f"Checking node created for level 2 (constants): No uppercase constants found.")
                self.state = State.FAILED
                return False
            self.variables_and_constants.extend(remove_duplicate_variables(filtered_constants_only))
            self.content = self.get_as_codeblock()
        else:
            self.content += incomming_constants
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now + "\n\n" + self.content
        self.state = State.CORRECT
        return True

    def set_variables(self, variables):
        if not is_valid_json(variables):
            return False
        if not constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            # Filter decision variables
            filtered_decision_variables_only = [item for item in json.loads(variables) if item.get("variable_name", "").islower()]

            # Safety check: There must be at least one decision variable (output)
            if len(filtered_decision_variables_only) == 0:
                if constants.DEBUG_MODE_ON: print(
                    f"Checking node created for level 3 (decision variables): No lower case variables found.")
                self.state = State.FAILED
                return False
            self.variables_and_constants.extend(remove_duplicate_variables(filtered_decision_variables_only))
            self.define_list_lengths()
            self.content = f"\n\n# --- {self.name} ---\n" + self.get_as_codeblock()
        else:
            self.content += "\n\n" + variables
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now + "\n\n" + self.content
        self.state = State.CORRECT
        self.all_variables_created = True
        return True

    def define_list_lengths(self):
        for constant in self.variables_and_constants:
            if "type" in constant and "DSList" in constant["type"]:
                match = re.search(r"length=(\d+)", constant["type"])
                if match:
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

    def prepend_section_title(self, block):
        if self.content == "":
            return f"# --- {self.name} ---\n" + block
        else:
            return f"# --- Decision variables ---\n" + block

    def get_as_codeblock(self):
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
    def __init__(self, name = "", parent = None):
        super().__init__("Constraints", parent, level=4)
        self.is_terminal = True

def is_valid_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except ValueError:
        return False

def build_code(node):
    if node is None or node.level == 0:
        return ""

    return build_code(node.parent) + "\n\n" + node.content

def check_executability(node: TreeNode, raw_code : str):
    # Construct partial/full formulation up until now, depending on current level
    if USE_OPTDSL:
        variable_block = f"\n{node.get_partial_formulation_up_until_now()}\n"
    else:
        variable_block = f"from z3 import * \n{node.get_partial_formulation_up_until_now()}\n"

    num_lines_without_raw_code = len(variable_block.splitlines())
    # Prepare raw constants/variable definitions and add to partial formulation (up until now)
    if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2:
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
        if len(node.variables_and_constants) == 0:
            raw_code = [item for item in raw_code if
                        item.get("variable_name", "").isupper()]
        else:
            raw_code = [item for item in raw_code if
                        item.get("variable_name", "").islower()]
        if raw_code == "": return "Error - Invalid result: Result is empty."
        for definition in raw_code:
            # Safety check: check if right hand side is json code
            if "[{" in str(definition["initialization"]):
                return f"Error: {definition["initialization"]}\ninitialization of equation is not valid {CHOSEN_LANGUAGE} code. Invalid type, must not be json or dict."
            variable_block += f"{definition["initialization"]}\n"
    elif not constants.USE_ALL_AT_ONCE_AND_EXTRACT:
    # Prepare raw obj. function or constraints and add to partial formulation (up until now)
        # Safety check: no json has be returned instead of code
        if is_valid_json(raw_code) or raw_code.startswith("{") or raw_code.startswith("["):
            return f"Error: Result must not be json objects, valid {constants.CHOSEN_LANGUAGE} code."

        #raw_code = initial_clean_up(raw_code)

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

        variable_block += raw_code
    else:
        variable_block += raw_code

    # Execute code block of partial/full formulation
    try:
        if USE_OPTDSL:
            # Syntax CHECK
            code_obj = compile(variable_block, "<string>", "exec")
            model = MiniZincTranslator(variable_block).unroll_translation()
            try:
                # Semantic CHECK
                return check_solver_executability(model, node)
            except Exception as e:
                return str(e)
        else:
            exec(variable_block, {})
    except SyntaxError as e:
        return f"Syntax Error \"{e.msg}\" in line {e.lineno}, at offset {e.offset}: {e.text.rstrip() if e.text else None}"
    except Exception as e:
        logger.exception(e)
        if "unexpected indent" in str(e):
            return f"Constraints/Objective FormatError"
        exc_type, exc_value, exc_tb = sys.exc_info()
        stack_trace_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        # Filter error for z3
        m = re.search(r'(?s).*?(File\s+"<string>",\s*line\s*\d+)(?!.*File\s+"<string>",\s*line\s*\d+)', stack_trace_str)
        error_message = str(e)
        if m:
            m = re.search(r'File\s+"<string>",\s*line\s*(\d+)', m.group(1))
            line_no = int(m.group(1))
            lines = variable_block.splitlines()
            line_with_error = lines[line_no-1]
            return f"{error_message} in line {line_no}: {line_with_error}\n"
        # Filter error from optdsl-translator
        m = re.search(r"(?m)^(?P<type>[\w\.]+(?:Error|Exception)):\s*(?P<msg>.*)$", stack_trace_str)
        if m:
            exc_type = m.group("type")
            exc_msg = m.group("msg")
            if exc_msg == 'Unknown type string: DSList':
                return f"Error: Variable list object type definition must adhere to the EBNF\ngrammar <variable_name> : \"DSList\" \"(\" FunArgs([\"length\", \"elem_type\"]) \")\"."
            elif exc_msg == 'Unknown type string: DSInt':
                return f"Error: Variable object type definition must adhere to the EBNF\n<variable_name> : grammar \"DSInt\" \"(\" FunArgs([\"lb\", \"ub\"]) \")\"."
            elif exc_msg == 'Unknown type string: DSFloat':
                return f"Error: Variable object type definition must not have type DSFloat, but must adhere to the EBNF grammar \"DSFloat\" \"(\" FunArgs([\"lb\", \"ub\"]) \")\"."
            elif exc_msg == 'Unknown type string: DSBool':
                return f"Error: Variable object type definition must not have type DSBool, but must adhere to the EBNF grammar \"DSBool\" \"(\" \")\"."
            elif exc_msg == 'Unknown type string: DSRecord':
                return f"Error: Variable object type definition must not have type DSRecord, but must adhere to the EBNF grammar \"DSRecord\" \"(\" \"{{\" RecordField (\",\" RecordField)* \"}}\" \")\"."
            elif exc_msg == "'int' object is not subscriptable":
                return f"Error: Do not perform calculations within index brackets. Instead, calculate it as temporary variable and then use it for accessing the list index."
            elif "attr='append', ctx=Load())," in exc_msg:
                return f"Error - Do not use function calls append() and extend() for DSList."
            elif "Only returning names or tuple of names is supported." in exc_msg:
                return f"Error - Functions may only return names or tuple of names is supported. Returning None is not supported."
            elif "ValueError: Variable" in exc_msg and "has incompatible types in if-else branches:" in exc_msg:
                return "Do not extract assert-expression into temporary variables, but inline the expression within assert directly."
            return f"{exc_type} - {exc_msg}, occurring at: {error_message.replace("Error processing statement: ", "")}\n"

        return str(e)
    return None

def check_solver_executability(model: str, node: TreeNode):
    # Safety check: replace python True/False with lower case equivalent for OptDSL
    model = model.replace("True", "true").replace("False", "false")
    solution, solve_time = MiniZincSolver().solve_with_python_minizinc(model)
    if solution is None:
        print("Solver failed: Invalid encoding yielded invalid solution.")
        return f"Semantic Error, correct semantics."
    elif "unknown" in str(solution).lower() or "unsatisfiable" in str(solution).lower():
        print("Solver yields UNSAT or Unknown.")
        return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" causes the solver to yield unsatisfiable, but it should be satisfiable."
    else:
        if "_objective" in solution:
            node.objective_val = solution["_objective"]
            node.solve_time = solve_time
            node.solution_model = solution
            print(f"Solution for objective is: {solution["_objective"]}")
        else:
            print("Solver succeeded, but no _objective is available.")

# ----------- HELPERS -----------

def initial_clean_up(raw_response: str) -> str:
    raw_response = remove_programming_environment(raw_response)

    # Convert typing-package (Annotated) specific parts to OptDSL
    if USE_TYPING: raw_response = convert_typing_to_OptDSL(raw_response)
    # Convert pydantic-package (Field, Annotated) specific parts to OptDSL
    elif USE_PYDANTIC: raw_response = convert_pydantic_to_OptDSL(raw_response)
    return raw_response

def remove_programming_environment(raw_response: str, node = None) -> str:
    # Remove any line that starts with "from z3" (even with leading spaces)
    cleaned = re.sub(r'^\s*from z3.*$', '', raw_response, flags=re.MULTILINE)

    cleaned = cleaned.replace("OptDSL", "")
    cleaned = cleaned.replace("json", "")
    cleaned = cleaned.replace("´´´python", "")
    cleaned = cleaned.replace("´´´", "")
    cleaned = cleaned.replace("```python", "")
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL)
    cleaned = "\n".join(line for line in cleaned.splitlines() if "import" not in line)
    cleaned = "\n".join(line for line in cleaned.splitlines() if "return None" not in line and "return" != line)

    # Remove already existing code
    #if node is not None: cleaned = remove_duplicate_lines(build_code(node), cleaned)
    return cleaned

def convert_to_DSList(match: re.Match) -> str:
    elem_type = match.group("elem_type")
    match elem_type:
        case "int":
            elem_type = "DSInt()"
        case "float":
            elem_type = "DSFloat()"
        case "bool":
            elem_type = "DSBool()"
    mx = match.group("max")
    return f"DSList(length={mx}, elem_type={elem_type})"
def convert_typing_to_OptDSL(code: str) -> str:
    pattern = re.compile(
        r"""Annotated\s*\[\s*
           list\s*\[\s*(?P<elem_type>[^\]\[]+)\s*\]\s*,\s*
           Len\s*\(\s*(?P<min>\d+)\s*,\s*(?P<max>\d+)\s*\)\s*
           \]""",
        re.VERBOSE
    )
    return re.sub(pattern, convert_to_DSList, code)


def convert_to_DSInt_DSFloat(m: re.Match) -> str:
    elem_type = m.group("type")
    match elem_type:
        case "int":
            elem_type = "DSInt"
        case "float":
            elem_type = "DSFloat"
    ge = m.group("ge")
    le = m.group("le")
    return f"{elem_type} (lb={ge}, ub={le})"
def convert_object_type_ref_to_DS(m: re.Match) -> str:
    elem_type = m.group("type")
    return elem_type
def convert_pydantic_to_OptDSL(code: str) -> str:
    # Convert to DSBool()
    code = code.replace("Annotated[bool, Field()]", "DSBool()")

    # Convert to DSInt() and DSFloat()
    pattern = re.compile(r"Annotated\[\s*(?P<type>\w+)\s*,\s*Field\s*\([^)]*?ge\s*=\s*(?P<ge>\d+)\s*,\s*le\s*=\s*(?P<le>\d+)[^)]*\)\s*\]", re.VERBOSE)
    code = re.sub(pattern, convert_to_DSInt_DSFloat, code)

    # Convert to DSList()
    code = convert_typing_to_OptDSL(code)

    # Convert annotated object type ref to OptDS
    pattern = re.compile(r"Annotated\[\s*(?P<type>\w+)\s*,\s*Field\s*\(\)\s*\]", re.VERBOSE)
    code = re.sub(pattern, convert_object_type_ref_to_DS, code)
    return code

def load_sp_file(file_path):
    file_path = SYSTEM_PROMPT_FOLDER + file_path
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def decompose_full_definition (full_definition: str):
    if ("# --- Objects ---".lower() in full_definition.lower() or
           "# --- Constants ---".lower() in full_definition.lower() or
           "# --- Objective ---".lower() in full_definition.lower() or
           "# --- Decision variables ---".lower() in full_definition.lower() or
           "# --- Constraints ---".lower() in full_definition.lower() or
           "# --- Incorrect Code ---".lower() in full_definition.lower()):
        full_definition = remove_programming_environment(full_definition)
        blocks = {}
        current_key = None
        temp = []

        for line in full_definition.splitlines():
            # Detect a block header, e.g. "--- Datatypes ---"
            m = re.match(r'^# ---\s*(.+?)\s*---$', line)
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
    names = find_function_names(code_str)
    appears_less_than_twice = []
    for name in names:
        if len(re.findall(r'\b' + re.escape(names[0]) + r'\b', code_str)) <= 1:
            appears_less_than_twice.append(name)
    return appears_less_than_twice
def find_function_names(code_str):
    pattern = r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
    names = re.findall(pattern, code_str, flags=re.MULTILINE)
    return names

model = SentenceTransformer("all-MiniLM-L6-v2")
def remove_duplicate_variables(variable_definitions):
    filtered_out_duplicates = []
    for i in range(len(variable_definitions)):
        found_duplicate = False
        for j in range(i + 1, len(variable_definitions)):
            emb1 = model.encode(variable_definitions[i]["variable_name"], convert_to_tensor=True)
            emb2 = model.encode(variable_definitions[j]["variable_name"], convert_to_tensor=True)
            if util.cos_sim(emb1, emb2) > 0.925:
                found_duplicate = True
                break
        if not found_duplicate:
            filtered_out_duplicates.append(variable_definitions[i])
        else:
            if constants.DEBUG_MODE_ON:
                print(f"Duplicate variables detected: {variable_definitions[i]} - {variable_definitions[j]}")
    return filtered_out_duplicates

def remove_duplicate_lines(variable_block: str, raw_code: str):
    # Split each string into lines (preserving distinct lines)
    lines1 = variable_block.splitlines()
    lines2 = raw_code.splitlines()

    # Use sets to find which lines are common
    set1 = set(lines1)
    set2 = set(lines2)
    common = set1.intersection(set2)

    # If you want to preserve original order (from str1) of the common lines:
    return "\n".join([line for line in lines2 if line not in common])

