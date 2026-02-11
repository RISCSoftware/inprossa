import random
from datetime import datetime
import json
import math
import os
import re
import sys
import traceback
from enum import Enum

from sentence_transformers import util

import constants
from sentence_transformers import *

from BinPackingValidator import check_satisfiability_given
from Translator.Objects.MiniZincTranslator import MiniZincTranslator
from constants import SYSTEM_PROMPT_FOLDER, DEBUG_MODE_ON, USE_TYPING, USE_PYDANTIC
import logging

from solver import MiniZincSolver

logger = logging.getLogger(__name__)

USE_OPTDSL = constants.USE_OPTDSL
CHOSEN_LANGUAGE = constants.CHOSEN_LANGUAGE

class State(Enum):
    UNINITIALIZED = -1
    CORRECT = 0
    FAILED  = 1

class Type(Enum):
    UNMODIFIED = "unmodified"
    MUTETED = "muted"
    MERGED = "merged"

class PolishModel:
    FILE_NAME = "data.json"

    @staticmethod
    def calculate_fitness(objective_val: float, solve_time: float, objective: str, constraints: str) -> float:
        return objective_val + solve_time/60 + ((len(objective) + len(constraints)) / 10000)

    def __init__(self, model: dict, id: int = 0, save_model:bool = False):
        self.model = model
        self.problem_description = model["problem_description"]
        self.llm_generated_objects = model["llm_generated_objects"]
        self.script_generated_objects = model["script_generated_objects"]
        self.constants = model["constants"]
        self.decision_variables = model["decision_variables"]
        self.objective = model["objective"]
        self.constraints = model["constraints"]
        self.objective_val = model["objective_val"]
        self.full_formulation = model["full_formulation"]
        self.solution_model = model["solution_model"]
        self.solve_time = model["solve_time"]
        self.fitness = 0
        self.id = f"{id if id is not None else random.randint(0, 100)}"
        self.path = f"/{self.id}"
        self.save_model = save_model
        self.state = State.UNINITIALIZED
        self.validated = False
        self.type = Type.UNMODIFIED

    def set_type(self, type: Type):
        self.type = type
        self.id = f"{type}_{self.id}"

    def get_as_dict(self):
        return {
            "problem_description": self.problem_description,
            "llm_generated_objects": initial_clean_up(self.llm_generated_objects),
            "script_generated_objects": self.script_generated_objects,
            "constants": self.constants,
            "decision_variables": self.decision_variables,
            "objective": initial_clean_up(self.objective),
            "constraints": initial_clean_up(self.constraints),
            "full_formulation": self.full_formulation,
            "objective_val": self.objective_val,
            "solution_model": self.solution_model,
            "solve_time": self.solve_time,
            "final_evaluation_result": ""
        }

    def calculate_and_set_fitness(self):
        self.fitness = PolishModel.calculate_fitness(self.objective_val, self.solve_time, self.objective, self.constraints)

    def save_model_to_file(self, final_evaluation_result, filename: str = f'mutated_optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H")}.json'):
        data = {
            "problem_description": self.problem_description,
            "llm_generated_objects": self.llm_generated_objects,
            "script_generated_objects": self.script_generated_objects,
            "constants": self.constants,
            "decision_variables": self.decision_variables,
            "objective": self.objective,
            "constraints": self.constraints,
            "full_formulation": self.full_formulation,
            "objective_val": self.objective_val,
            "solution_model": self.solution_model,
            "solve_time": self.solve_time,
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

    def get_variables_codeblock(self):
        block = "# --- Objects ---\n"
        block += f"{self.llm_generated_objects}\n"
        for object_name, object_spec in self.script_generated_objects.items():
            block += object_spec + "\n"
        block += "\n# --- Constants and Decision Variables ---\n"
        for constant in self.constants:
            block += constant["initialization"] + "\n"
        for constant in self.decision_variables:
            block += constant["initialization"] + "\n"
        return block

    def set_content(self, content, failed: bool = False):
        self.full_formulation = ""
        content = remove_programming_environment(content.strip())
        self.full_formulation += content

        if content.strip() == "" or failed:
            self.state = State.FAILED
            self.full_formulation += 1
        else:
            if self.state == State.UNINITIALIZED: self.state = State.CORRECT


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
        if final_evaluation_result is not None and "Successfully" in final_evaluation_result:
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
            "solve_time": self.solve_time
        }
        if final_evaluation_result: data.update({"final_evaluation_result": final_evaluation_result})
        file_path = f"{self.path}/{self.FILE_NAME}"
        folder = os.path.dirname(file_path)
        os.makedirs(folder, exist_ok=True) # create folder (+ parent folders) if not existent
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def save_model_to_file(self, final_evaluation_result, problem_description: str, filename: str = f'optDSL_models_{datetime.now().strftime("%Y-%m-%d_%H")}.json'):
        curNode = self
        while(curNode.parent.level != 3):
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

    def append_child(self, child):
        self.children.append(child)

    def get_correct_children(self):
        return [child for child in self.children if (child.state == State.CORRECT and child.n_failed_generations == 0)]

    def get_partial_formulation_up_until_now(self):
        return self.partial_formulation_up_until_now

    def set_content(self, content, failed: bool = False):
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT: content = remove_duplicate_lines(build_code(self), content)
        if isinstance(self, ObjectsNode) and "# --- Objects ---\n" not in content: content =  "# --- Objects ---\n" + content

        self.content += "\n\n"
        content = remove_programming_environment(content.strip())
        self.content += content

        self.partial_formulation_up_until_now += "\n\n" + content
        if content.strip() == "":
            self.state = State.FAILED
            self.n_failed_generations += 1
        else:
            if self.state == State.UNINITIALIZED: self.state = State.CORRECT
        if self.save_nodes: self.save_child_to_file()

    def prepend_section_title(self, block):
        return f"# --- {self.name} ---\n" + block

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

    def set_content(self, content, failed: bool = False):
        # Check if at least one section header is present
        if "--- Objects ---".lower() not in content.lower() or "--- Decision variables ---".lower() not in content.lower() or "--- Constants and Decision Variables ---".lower() not in content.lower() or "--- Objective function ---".lower() not in content.lower() or "--- Constraints 1 ---".lower() not in content.lower():
            self.state = State.FAILED
            self.n_failed_generations += 1
            return False

        # Extract code according to section headers
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

        self.content += f"# --- {self.name} ---\n"
        self.content += blocks
        self.state = State.CORRECT
        return True

class ObjectsNode(TreeNode):
    def __init__(self, name = "", parent = None):
        super().__init__("Objects", parent, level=1)
        self.llm_generated_objects = None
        self.script_generated_objects = None

    def set_llm_generated_objects(self, llm_generated_objects):
        self.llm_generated_objects = llm_generated_objects

    def set_script_generated_objects(self, script_generated_objects):
        self.script_generated_objects = script_generated_objects

    def get_textual_repr(self):
        return self.parent.content()

class VariablesConstantsNode(TreeNode):
    def __init__(self, name = "", parent = None):
        self.variables_and_constants = []
        self.all_variables_created = False
        super().__init__("Constants and Decision Variables", parent, level=2)

    def set_constants(self, incomming_constants):
        self.content = "# --- Constants ---\n"
        if not is_valid_json(incomming_constants):
            self.state = State.FAILED
            return False
        if incomming_constants.strip() == "":
            self.state = State.FAILED
        if not constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            # Filter constants
            filtered_constants_only = [item for item in json.loads(incomming_constants) if item.get("variable_name", "").isupper()]
            # TODO add sanity check, nr of input parameter == len(filtered_constants_only)
            # Safety check: There must be at least one constant (input)
            if len(filtered_constants_only) == 0:
                if constants.DEBUG_MODE_ON: print(f"Checking node created for level 2 (constants): No uppercase constants found.")
                self.state = State.FAILED
                return False
            self.variables_and_constants.extend(filtered_constants_only)
            self.content += self.get_as_codeblock()
        else:
            self.content += incomming_constants
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now + "\n\n" + self.content

        # Only check satisfiability for constants if mode is "fixed_objects_fixed_input_values", "fixed_objects_fixed_inoutput_values"
        if "variable_instance" in self.variables_and_constants[0]: check_satisfiability_given(self.variables_and_constants)

        self.state = State.CORRECT
        if self.save_nodes: self.save_child_to_file()
        return True

    def set_variables(self, variables, expected_output_variables):
        if not is_valid_json(variables):
            return False

        if variables.strip() == "":
            self.state = State.FAILED
        elif not constants.USE_ALL_AT_ONCE_AND_EXTRACT:
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
        else:
            self.content += "\n\n" + variables
        self.partial_formulation_up_until_now = self.parent.partial_formulation_up_until_now + "\n\n" + self.content
        if self.state == State.UNINITIALIZED: self.state = State.CORRECT
        self.all_variables_created = True
        if self.save_nodes: self.save_child_to_file()
        return True

    def define_list_lengths(self):
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

    def get_textual_repr(self):
        return self.parent.parent.content()

class ObjectiveNode(TreeNode):
    def __init__(self, name = "", parent = None):
        super().__init__("Objective", parent, level=3)

    def get_textual_repr(self):
        return self.parent.parent.parent.content()

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

    def get_textual_repr(self):
        return self.parent.parent.parent.parent.content()

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
        if isinstance(node, VariablesConstantsNode) and len(node.variables_and_constants) == 0:
            raw_code = [item for item in raw_code if
                        item.get("variable_name", "").isupper()]
        else:
            raw_code = [item for item in raw_code if
                        item.get("variable_name", "").islower()]
        if raw_code == "": return "Error - Invalid result: Result is empty."
        for definition in raw_code:
            if "Annotated[list[" in definition["type"] and re.search(r'Annotated\[\s*list\[\s*(?P<elem_type>int|float|bool)\s*]\s*,\s*Len\(\s*\d+\s*,\s*(?P<max>\d+)\s*\)\s*]', definition["type"]):
                return f"Error: {definition["type"]}\n, for this list elem_type must have a type of typing.Annotated with a pydantic.Field of type int, float, bool. Including lower (ge) and upper bounds (le). Demonstration example for a list of integers: Annotated[list[Annotated[int, Field(lb=-10,ub=10)]], Len(2,2)]"
            variable_block += f"{definition["initialization"]}\n"
    elif not constants.USE_ALL_AT_ONCE_AND_EXTRACT:
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

        # Safety check: check if calculated objective is assigned to a variable "objective" at some point
        if node.level == 3 and "objective =" not in raw_code and "objective :" not in raw_code:
            return "Add an assigment, where the decision variable that represents the objective is assigned to a variable \"objective\". Nothing else."

        # Safety check: check that there are no non-constants in range
        m = re.search(r"(.*)(range\(\s*(?=[^,]+[a-z])[^,]+,\s*[^)]+|range\(\s*[^,]+,\s*(?=[^) ]+[a-z])[^)]+\))", raw_code)
        if m:
            if "#" not in m.group(1):
                return f"Error - range() must contain constant variable or integer values only: {m.group(2)}"

        variable_block += raw_code
    else:
        variable_block += raw_code

    # Execute code block of partial/full formulation
    variable_block = initial_clean_up(variable_block)
    try:
        if USE_OPTDSL:
            # Syntax CHECK
            compile(variable_block, "<string>", "exec")
            model = MiniZincTranslator(variable_block).unroll_translation()
            try:
                # Semantic CHECK
                if node.level >= 3: return check_solver_executability(model, node)
            except Exception as e:
                return str(e)
        else:
            exec(variable_block, {})
    except SyntaxError as e:
        if "Annotated" in variable_block:
            return "Tuple is not supported. Use typing.Annotated with pydantic.Field of type int, float, int or object type, or complex type list as typing.Annotated of typing.Annotated with pydantic.Field of type int, float, int or object type, or DSRecord"
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
        m = re.search(r"(?m)^(?P<type>[\w.]+(?:Error|Exception)):\s*(?P<msg>.*)$", stack_trace_str)
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
                return f"Error - Functions support returning names or tuple of names only. Either do not call return or only return names or tuple of names, no integer values or dummies. Also is the number of output parameters correct?"
            elif "tuple[" in exc_msg:
                return "Tuple is not supported. Use typing.Annotated with pydantic.Field of type int, float, int or object type, or complex type list as typing.Annotated of typing.Annotated with pydantic.Field of type int, float, int or object type, or DSRecord"
            elif "incompatible types" in exc_msg:
                return f"For assert expressions, do not extract calculations or single object-fields. Inline them!"
            elif "\\/" in exc_msg:
                return "Incorrect types used in one of the or-expressions in the code beneath \"# --- Incorrect Code ---\". Check and correct the or-expressions, only boolean can be used with and-/or-expressions."
            elif "/\\" in exc_msg:
                return "Incorrect types used in one of the and-expressions in the code beneath \"# --- Incorrect Code ---\". Check and correct the and-expressions, only boolean can be used with and-/or-expressions."
            elif "ValueError: Variable" in exc_msg and "has incompatible types in if-else branches:" in exc_msg:
                return "Do not extract assert-expression into temporary variables, but inline the expression within assert directly."
            return f"{exc_type} - {exc_msg}, occurring at: {error_message.replace("Error processing statement: ", "")}\n"

        return str(e)
    return None

def check_executability_for_polish(raw_code : str, model: PolishModel):
    if "Annotated[list[" in raw_code and re.search(r'Annotated\[\s*list\[\s*(?P<elem_type>int|float|bool)\s*]\s*,\s*Len\(\s*\d+\s*,\s*(?P<max>\d+)\s*\)\s*]', raw_code):
        return f"Error: {raw_code}\n, for this list elem_type must have a type of typing.Annotated with a pydantic.Field of type int, float, bool. Including lower (ge) and upper bounds (le). Demonstration example for a list of integers: Annotated[list[Annotated[int, Field(lb=-10,ub=10)]], Len(2,2)]"

    # Safety check: no json has be returned instead of code
    if is_valid_json(raw_code) or raw_code.startswith("{") or raw_code.startswith("["):
        return f"Error: Result must not be json objects, valid {constants.CHOSEN_LANGUAGE} code."

    # Result must not be empty
    if raw_code == "": return "Error - Invalid result: Result is empty."

    # Safety check: check that there are no non-constants in range
    m = re.search(r"range\(\s*(?=[^,]+[a-z])[^,]+,\s*[^)]+|range\(\s*[^,]+,\s*(?=[^) ]+[a-z])[^)]+\)", raw_code)
    if m:
        return f"Error - range() must contain constant variable or integer values only: {m.group(0)}"

    # Execute code block of partial/full formulation
    variable_block = initial_clean_up(raw_code)
    try:
        if USE_OPTDSL:
            # Syntax CHECK
            compile(variable_block, "<string>", "exec")
            minizinc_model = MiniZincTranslator(variable_block).unroll_translation()
            try:
                # Semantic CHECK
                return check_solver_executability(minizinc_model, model)
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
        m = re.search(r"(?m)^(?P<type>[\w.]+(?:Error|Exception)):\s*(?P<msg>.*)$", stack_trace_str)
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
                return f"Error - Functions support returning names or tuple of names only. Either do not call return or only return names or tuple of names, no integer values or dummies. Also is the number of output parameters correct?"
            elif "tuple[" in exc_msg:
                return "Tuple is not supported. Use typing.Annotated with pydantic.Field of type int, float, int or object type, or complex type list as typing.Annotated of typing.Annotated with pydantic.Field of type int, float, int or object type, or DSRecord"
            elif "incompatible types" in exc_msg:
                return f"For assert expressions, do not extract calculations or single object-fields. Inline them!"
            elif "\\/" in exc_msg:
                return "Incorrect types used in one of the or-expressions in the code beneath \"# --- Incorrect code ---\". Check and correct the or-expressions, only boolean can be used with and-/or-expressions."
            elif "/\\" in exc_msg:
                return "Incorrect types used in one of the and-expressions in the code beneath \"# --- Incorrect code ---\". Check and correct the and-expressions, only boolean can be used with and-/or-expressions."
            elif "ValueError: Variable" in exc_msg and "has incompatible types in if-else branches:" in exc_msg:
                return "Do not extract assert-expression into temporary variables, but inline the expression within assert directly."
            return f"{exc_type} - {exc_msg}, occurring at: {error_message.replace("Error processing statement: ", "")}\n"

        return str(e)
    return None

def check_solver_executability(model: str, node):
    # Safety check: replace python True/False with lower case equivalent for OptDSL
    model = model.replace("True", "true").replace("False", "false")
    if isinstance(node, TreeNode):
        solution, solve_time = MiniZincSolver().solve_with_command_line_minizinc(model, node.last_in_progress if node.is_terminal else False)
    else:
        solution, solve_time = MiniZincSolver().solve_with_command_line_minizinc(model, True)
    if "Memory violation detected (stack overflow)." in solution:
        return "Memory violation detected (stack overflow)."
    elif "Error" in solution:
        return solution
    elif "type error" in solution:
        return "Minizinc Solver Error"
    elif solution is None:
        print("Solver failed: Invalid encoding yielded invalid solution.")
        return f"Semantic Error, correct the semantics."
    elif "unknown" in str(solution).lower():
        if node.level == 3:
            return None
        else:
            return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" yields no answer at all."
    elif "unsatisfiable" in str(solution).lower():
        print("Solver yields UNSAT or Unknown.")
        return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" causes the solver to yield unsatisfiable, but it should be satisfiable."
    else:
        if "objective" in solution:
            node.objective_val = solution["objective"][len(solution["objective"])-1]
            node.solve_time = solve_time
            node.solution_model = solution
            print(f"Solution for objective is: {solution["objective"]}")
        else:
            if "nr_used_boxes" in solution:
                node.objective_val = solution["nr_used_boxes"][len(solution["nr_used_boxes"])-1]
            node.solve_time = solve_time
            node.solution_model = solution
            print("Solver succeeded, but no _objective is available.")
        return None

def check_solver_executability_for_plain_model(model: str):
    # Safety check: replace python True/False with lower case equivalent for OptDSL
    model = model.replace("True", "true").replace("False", "false")
    solution, solve_time = MiniZincSolver().solve_with_command_line_minizinc(model, True)
    if "Error" in solution:
        return solution, None, None
    elif "type error" in solution:
        return "Minizinc Solver Error", None, None
    elif solution is None:
        print("Solver failed: Invalid encoding yielded invalid solution.")
        return f"Semantic Error, correct the semantics.", None, None
    elif "unknown" in str(solution).lower():
        return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" yields no answer at all.", None, None
    elif "unsatisfiable" in str(solution).lower():
        print("Solver yields UNSAT or Unknown.")
        return f"Semantic Error, the code underneath \"# --- Incorrect Code ---\" causes the solver to yield unsatisfiable, but it should be satisfiable.", None, None
    else:
        if "objective" in solution:
            print(f"Solution for objective is: {solution["objective"]}")
            return solution["objective"][len(solution["objective"])-1], solve_time, solution
        else:
            print("Solver succeeded, but no _objective is available.")
        return None, None, None


# ----------- HELPERS -----------

def initial_clean_up(raw_response: str, to_typing: bool = False) -> str:
    raw_response = remove_programming_environment(raw_response)

    if to_typing:
        raw_response = convert_OptDSL_to_pydantic(raw_response)
    else:
        # Convert typing-package (Annotated) specific parts to OptDSL
        if USE_TYPING: raw_response = convert_typing_to_OptDSL(raw_response)
        # Convert pydantic-package (Field, Annotated) specific parts to OptDSL
        elif USE_PYDANTIC: raw_response = convert_pydantic_to_OptDSL(raw_response)
    return raw_response

def remove_programming_environment(raw_response: str, node = None) -> str:
    cleaned = raw_response

    # Remove any line that starts with "from z3" (even with leading spaces)
    if "from z3" in cleaned: cleaned = re.sub(r'^\s*from z3.*$', '', raw_response, flags=re.MULTILINE)

    if "OptDSL" in cleaned: cleaned = cleaned.replace("OptDSL", "")
    if "json" in cleaned: cleaned = cleaned.replace("json", "")
    if "python" in cleaned: cleaned = cleaned.replace("python", "")
    cleaned = cleaned.replace("´´´", "")
    cleaned = cleaned.replace("```", "")
    if "<reasoning>" in cleaned: cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.DOTALL)
    if "import" in cleaned: cleaned = "\n".join(line for line in cleaned.splitlines() if "import" not in line)
    if "return\n" in cleaned or "return None" in cleaned: cleaned = "\n".join(line for line in cleaned.splitlines() if "return None" not in line and "return" != line)

    return cleaned.strip()

def convert_to_DSList(match: re.Match) -> str:
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
                    elem_type = convert_typing_to_OptDSL(elem_type)
                if "Annotated" in elem_type:
                    elem_type = convert_pydantic_to_OptDSL(elem_type)

        mx = match.group("max")
        return f"DSList(length={mx}, elem_type={elem_type})"
    return ""
def convert_typing_to_OptDSL(code: str, nested: bool = False) -> str:
    if nested:
        regex = r"Annotated\[list\[(?P<elem_type>[^\]]+\],\s*Len\(\d+,\s*\d+\)])],\s*Len\(\d+,\s*(?P<max>\d+)\)"
    else:
        regex = r"Annotated\[list\[(?P<elem_type>[^\]]+?)\],\s*Len\(\d+,\s*(?P<max>\d+)\)\]"
    pattern = re.compile(
        regex,
        re.VERBOSE
    )
    return re.sub(pattern, convert_to_DSList, code)

def convert_to_DSInt_DSFloat(match: re.Match) -> str:
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
def convert_object_type_ref_to_DS(match: re.Match) -> str:
    if match:
        elem_type = match.group("type")
        return elem_type
    return ""
def convert_pydantic_to_OptDSL(code: str) -> str:
    # Convert to DSBool()
    code = code.replace("Annotated[bool, Field()]", "DSBool()")

    # Convert to DSInt() and DSFloat()
    pattern = re.compile(r"Annotated\[\s*(?P<type>int|float)\s*,\s*Field\(\s*(?:strict\s*=\s*True\s*\s*)?(?:\s*, \s*)?(?:ge\s*=(?P<ge>-?\d+(?:\.\d+)?))?(?:(?:\s*,\s*)?le\s*=(?P<le>-?\d+(?:\.\d+)?))?\s*\)\s*]", re.VERBOSE)
    code = re.sub(pattern, convert_to_DSInt_DSFloat, code)

    # Convert nested Annotated Lists to DSList()
    code = convert_typing_to_OptDSL(code, nested=True)

    # Convert non-nested Annotated to DSList()
    code = convert_typing_to_OptDSL(code)

    # Convert annotated object type ref to OptDS
    pattern = re.compile(r"Annotated\[\s*(?P<type>\w+)\s*,\s*Field\s*\(\)\s*]", re.VERBOSE)
    code = re.sub(pattern, convert_object_type_ref_to_DS, code)
    return code

def convert_to_typing_list(match: re.Match) -> str:
    if match:
        elem_type = match.group("elem_type")
        length = match.group("length")
        if "DSList" in elem_type or "DSInt" in elem_type or "DSFloat" in elem_type or "DSBool" in elem_type:
            elem_type = convert_OptDSL_to_pydantic(elem_type)
        return f"Annotated[list[{elem_type}], Len({length}, {length})]"
    else:
        return match.group(0)
def convert_OptDSList_to_typing_list(regex, code: str) -> str:
    pattern = re.compile(
        regex,
        re.VERBOSE
    )
    return re.sub(pattern, convert_to_typing_list, code)

def convert_object_OptDSList_to_typing_list(match: re.Match):
    if match:
        elem_type = match.group("elem_type")
        length = match.group("length")
        if "Annotated" in elem_type:
            return match.group(0)
        else:
            return f"Annotated[list[{elem_type}], Len({length}, {length})]"
    else:
        return match.group(0)

def convert_to_pydantic_int_float(match: re.Match) -> str:
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
def convert_OptDSL_to_pydantic(code: str) -> str:
    # Convert to Annotated[bool..]
    code = code.replace("DSBool()", "Annotated[bool, Field()]")

    # Convert from pydantic int / float to DSInt() and DSFloat()
    pattern = re.compile(
        r"(?P<type>DSInt|DSFloat)\((?:lb\s*=(?P<lb>-?\d+(?:\.\d+)?)(?:\s*,\s*)?)?(?:ub\s*=(?P<ub>-?\d+(?:\.\d+)?)(?:\s*,\s*)?)?\s*\)",
        re.VERBOSE)
    code = re.sub(pattern, convert_to_pydantic_int_float, code)

    # Convert nested DSList() to Annotated Lists
    code = convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>\d+)\s*,\s*elem_type\s*=(?P<elem_type>DSList[^]\r\n]+\]\))\)", code)
    code = convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>\d+)\s*,\s*elem_type\s*=(?P<elem_type>DSList[^)\r\n]+\))\)", code)

    # Convert non-nested DSList() to Annotated Lists
    code = convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>\d+)\s*,\s*elem_type\s*=\s*(?P<elem_type>[^]\r\n]+\])\)", code)
    code = convert_OptDSList_to_typing_list(
        r"DSList\(\s*length\s*=\s*(?P<length>\d+)\s*,\s*elem_type\s*=\s*(?P<elem_type>[^]\r\n]+)\)", code)

    # Convert non-nested DSList() with object-type to Annotated
    pattern = re.compile(
        r"DSList\(\s*length\s*=\s*(?P<length>\d+)\s*,\s*elem_type\s*=\s*(?P<elem_type>[^)]+)\)",
        re.VERBOSE
    )
    code = re.sub(pattern, convert_object_OptDSList_to_typing_list, code)
    return code

def load_sp_file(file_path):
    file_path = SYSTEM_PROMPT_FOLDER + file_path
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def load_algopolish_file(file_path) -> str:
    file_path = "prompts/algopolish/" + file_path
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def decompose_full_polished_definition (full_definition: str):
    if ("# --- Objects ---".lower() in full_definition.lower() or
           "# --- Constants ---".lower() in full_definition.lower() or
           "# --- Decision variables ---".lower() in full_definition.lower() or
           "# --- Constants and Decision Variables ---".lower() in full_definition.lower() or
           "# --- Objective ---".lower() in full_definition.lower() or
           "# --- Auxiliary Variables ---".lower() in full_definition.lower() or
           "# --- Constraints ---".lower() in full_definition.lower() or
           "# --- Incorrect Code ---".lower() in full_definition.lower()):
        full_definition = remove_programming_environment(full_definition)
        blocks = {}
        current_key = None
        temp = []

        for line in full_definition.splitlines():
            # Detect a block header, e.g. "--- Objects ---"
            m = re.match(r'^\s*#\s*---\s*(\w+(?:\s+\w+)*)\s*---', line)
            if m:
                if not ((m.group(1).strip().lower() == "constraints" or m.group(1).strip().lower() == "auxiliary variables")
                    and (current_key == "constraints" or current_key == "auxiliary variables")):
                    current_key = m.group(1).strip().lower()
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

def decompose_full_definition (full_definition: str):
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
def remove_duplicate_variables(variable_definitions, threshold: float):
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

def split_at_outer_equals(s: str):
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
