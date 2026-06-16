import json
import re

from LLM_Client.AwsClient import AwsClient
from structures_utils import load_sp_file, TreeNode, is_valid_json, \
    decompose_full_definition, check_executability, check_functions_appear_twice, VariablesConstantsNode, \
    remove_programming_environment, initial_clean_up, safety_check_contains_func_that_just_returns_var
from constants import DEBUG_MODE_ON, USE_OPTDSL, CHOSEN_LANGUAGE

LOOP_OF_DOOM_UNSAT_MAX_IT = 2
LOOP_OF_DOOM_MAX_IT = 4
MAX_NR_RESETS = 3
N_FAILED_GENERATIONS = 0

def enter_feedback_loop(node, raw_formulation, llm, full_problem_description: list[str] = None, subproblem_description: str = None):
    """
    Performs feedback loop for LOOP_OF_DOOM_MAX_IT * MAX_NR_RESETS times or until raw_formulation is syntactically valid.
    Args:
        node (TreeNode): current node in tree for which raw_formulation was created
        raw_formulation (str): partial OptDSL formulation or json specification (for variable specifications) created for node
        llm : LLM client
        full_problem_description (list) : full problem description (incl. concrete values for one instance)
        subproblem_description (str) : description of one specific subproblem
    """
    execution_error = None
    for _ in range(MAX_NR_RESETS):
        nr_unsat_error = 0
        for i in range(LOOP_OF_DOOM_MAX_IT):
            # Check raw_formulation is not None
            if raw_formulation is None:
                raw_formulation = (llm.send_prompt(
                    system_prompt=f"{_get_system_prompt("format_sp")}\n{_get_icl()}",
                    prompt="""Incorrect result format, it must be:
´´´python
# --- Objects ---
<solution>

# --- Constants and Decision Variables ---
<solution>

# --- Objective ---

# --- Constraints ---
<solution>
´´´ where <solution> is a placeholder for the code. """ +
                           f"""Extend the following python code, include it, but you are strictly forbidden from modify it. Just add the missing sections:
´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n""" +
                           load_sp_file("sp_all_at_once_shorter.txt") +
                           # Input variables (constants) problem description
                           full_problem_description[0] + "\n" +
                           # Output variables (decision variables) - problem description
                           full_problem_description[1] + "\n" +
                           # Global problem description
                           full_problem_description[2] + "\n" +
                           # Sub problem description
                           full_problem_description[3] + "\n" +
                           # Sub problem description
                           full_problem_description[4] + "\n" +
                           # Sub problem description
                           full_problem_description[5],
                    max_tokens=(800 if node.level == 4 else 500)
                ))

            # Send prompt anew, no reentering the feedback loop
            if ("NTD" in raw_formulation or
                    "Minizinc Solver Error" in raw_formulation or
                    (execution_error is not None and "Constraints FormatError" in execution_error) or
                    (execution_error is not None and "Constraints/Objective FormatError" in execution_error) or
                    raw_formulation.strip() == "" or
                    nr_unsat_error == LOOP_OF_DOOM_UNSAT_MAX_IT):
                if DEBUG_MODE_ON: print(
                    f"Checking node created for level {node.level}: {raw_formulation}\nNTD, solver error, format error or end of loop of doom encountered")
                raw_formulation = create_and_send_prompt(node,
                                                         full_problem_description=full_problem_description,
                                                         subproblem_description=subproblem_description,
                                                         llm=llm)
                execution_error = None
                nr_unsat_error = 0

            # Constants and dec. variables: check valid json + contains at least 1 variable
            if node.level == 2:
                # Check if formulation for variables is valid json
                if not is_valid_json(raw_formulation):
                    if DEBUG_MODE_ON: print(
                        f"Checking node created for level {node.level}: Constants not valid json.")
                    raw_formulation = (llm.send_prompt(
                        system_prompt=_get_system_prompt("sp"),
                        prompt=raw_formulation + "\n\n" +
                               """The code above is either not json or incorrect json. Correct it to compilable json code.
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
                               5. No additional properties allowed.""",
                        max_tokens=1000
                    ))
                    continue

                # Check if there are any constants/decision variables, there must be at least 1 each
                filtered_constants_variables = [item for item in json.loads(raw_formulation) if (
                item.get("variable_name", "").isupper() if len(node.variables_and_constants) == 0 else item.get(
                        "variable_name", "").islower())]
                if len(filtered_constants_variables) == 0:
                    raw_formulation = (llm.send_prompt(
                        system_prompt=_get_system_prompt("sp"),
                        prompt="""The code answer you gave, did not contain any variables of the required type {constants, decision variables}. Create them now.
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
                                   5. No additional properties allowed.""",
                        max_tokens=1000
                    ))
                    continue
                # safety check: constants that are DSLists must have the same length in the encoding as in the given input data
                if filtered_constants_variables[0]["variable_name"].isupper():
                    execution_error, potentially_new_formulation = _safety_check_DSLists_must_have_same_length_as_input(
                        llm, filtered_constants_variables,
                        execution_error, full_problem_description, raw_formulation, node.level)
                    if execution_error is not None:
                        raw_formulation = potentially_new_formulation
                        execution_error = None
                        continue

            # Extract objective and constraints + auxiliary vars
            execution_error = None
            if node.level == 3 or node.level == 4:
                execution_error, raw_formulation = _extract_required_parts(raw_formulation, execution_error, node)
                # Safety check: function does not consist only of a return of a variable
                if safety_check_contains_func_that_just_returns_var(raw_formulation):
                    execution_error = "Error: The function within this code does not include any calculation, but only returns an unmodified input variable. Encode the calculation of the objective function mentioned in the last prompt."

            # Check for syntactical correctness and handle execution error, if no "Constraints/Objective FormatError" has occurred yet
            if execution_error is None:
                execution_error = check_executability(node, raw_formulation)
            # Handle execution error
            if execution_error is not None:
                # Execution error occured and end of loop-of-doom-retries reached -> switch model or abort
                if i == LOOP_OF_DOOM_MAX_IT-1: continue

                if "type error" in execution_error and "\\/" in execution_error:
                    execution_error = "Incompatible types used in one of the or-expressions in the code beneath \"# --- Incorrect Code ---\". Check and correct the or-expressions, only boolean can be used with or-expressions."
                elif "type error" in execution_error and "/\\" in execution_error:
                    execution_error = "Incompatible types used in one of the and-expressions in the code beneath \"# --- Incorrect Code ---\". Check and correct the and-expressions, only boolean can be used with and-expressions."

                if DEBUG_MODE_ON: print(
                    f"Checking node created for level {node.level} not executable: {execution_error}\n")
                if ("NTD" in raw_formulation or
                        (execution_error is not None and "Constraints FormatError" in execution_error) or
                        (execution_error is not None and "Constraints/Objective FormatError" in execution_error)):
                    if DEBUG_MODE_ON: print(
                        f"Checking node created for level {node.level}: {raw_formulation}\nNTD, Constraints FormatError or Constraints/Objective ForamtErrorencountered")
                    raw_formulation = create_and_send_prompt(node,
                                                             full_problem_description=full_problem_description,
                                                             subproblem_description=subproblem_description,
                                                             llm=llm)
                    execution_error = None
                    continue
                elif "Syntax Error" in execution_error:
                    raw_formulation = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                                "format_sp")) + "\n" + _get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not USE_OPTDSL else "") +
                               f"\n# --- Incorrect Code --- \n{raw_formulation}´´´\n\n" +
                               f"The section above contains a syntax error: {execution_error}" +
                               "Given this error message, improve the mentioned lines of the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet according to the error message, nothing else. Do not change the semantics of the code. Do not return \nNTD\n."
                               """Return your answer in the format
´´´python
# --- Incorrect Code ---
<corrected code>
´´´, where <corrected code> is the section \"# --- Incorrect Code ---\" with the corrections.
                               """,
                        max_tokens=(1000 if node.level == 4 else 800)
                    ))
                elif "Semantic Error" in execution_error:
                    raw_formulation = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                                "format_sp")) + "\n" + _get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not USE_OPTDSL else "") +
                               f"\n# --- Incorrect Code --- \n{raw_formulation}´´´\n\n" +
                               f"The section above contains a semantic error: {execution_error}" +
                               "Given this error message, improve the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet according to the error message, nothing else." +
                               f"The semantics of the section \"# --- Incorrect Code ---\" must be in line with the following description:\n{raw_formulation if subproblem_description is None else subproblem_description}" +
                               """
Define more bounds for variables. Reduce the number of temporary variables.
Return your answer in the format
´´´python
# --- Incorrect Code ---
<corrected code>
´´´, where <corrected code> is the section \"# --- Incorrect Code ---\" with the corrections.
                               """,
                        max_tokens=(1000 if node.level == 4 else 800)
                    ))
                    nr_unsat_error += 1
                elif "redundancy" in execution_error:
                    raw_formulation = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                                "format_sp")) + _get_icl(),
                        prompt=execution_error +
                               f"Problem description is: {subproblem_description}" +
                               # Component specific instr.: object types, data types
                               f"Task: {load_sp_file("sp_constraints.txt")}"
                               f"Given the following code snippet" +
                               f"´´´python\n" +
                               (f"from z3 import * \n" if not USE_OPTDSL else "") +
                               f"{node.get_partial_formulation_up_until_now()}\n"
                               f"´´´\n\n" +
                               "Return your answer in the format\n" +
                               "´´´python\n" +
                               f"# --- {node.name.lower()} ---\n" +
                               "<code>\n",
                        max_tokens=(1500 if node.level >= 4 else 800)
                    ))
                elif "Memory violation" in execution_error:
                    raw_formulation = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                            "format_sp")) + _get_icl(),
                        prompt=f"´´´python\n" +
                               f"{node.get_partial_formulation_up_until_now()}\n"
                               f"\n# --- Incorrect Code --- \n{raw_formulation}´´´\n\n" +
                               f"Improve the code of the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet as follows: Inline expressions and list accesses instead of creating temporary variables. Reduce the number of temporary variables. Increase efficiency of constraints and reduce constraint length." +
                               "Nothing else. Do not change the semantics of the code. Do not return NTD."
                               "Return your answer in the format\n" +
                               "´´´python\n" +
                               "# --- Incorrect Code ---\n" +
                               "<corrected code>\n" +
                               "\n´´´, where <corrected code> all lines underneath \"# --- Incorrect Code ---\" with the corrections.",
                        max_tokens=(1500 if node.level >= 4 else 800)
                    ))
                # Error in constants or decision variable declaration/initialization
                elif node.level == 2:
                    raw_formulation = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                            "format_sp")) + _get_icl(),
                        prompt=f"´´´\njson\n{raw_formulation}´´´\n\n" +
                               f"The Json code above contains an error: {execution_error}" +
                               "Given this error message, improve the mentioned lines of the \"initialization\" and/or the \"variable_type\" field according to the error message, nothing else."
                               "Return the given json code with the corrections. Do not copy the in-context-training example. Do not return \"NTD\".",
                        max_tokens=800
                    ))
                else:
                    raw_formulation = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                                "format_sp")) + _get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not USE_OPTDSL else "") +
                               f"{node.get_partial_formulation_up_until_now()}\n"
                               f"\n# --- Incorrect Code --- \n{raw_formulation}´´´\n\n" +
                               f"The code snipped above contains the following error: \"{execution_error}\"" +
                               "Improve the mentioned lines of the section \"# --- Incorrect Code ---\" - code snippet according to the error message, nothing else. Do not change the semantics of the code. Do not return NTD."
                               "Return your answer in the format\n" +
                               "´´´python\n" +
                               "# --- Incorrect Code ---\n" +
                               "<corrected code>\n" +
                               "\n´´´, where <corrected code> are all lines underneath \"# --- Incorrect Code ---\" including the corrections.",
                        max_tokens=(1500 if node.level >= 4 else 800)
                    ))
            # Syntactically valid formulation
            else:
                # Safety check: check if DSInts are correctly initialized according to lb and ub
                if node.level == 3 or node.level == 4 or node.level == 5:
                    potentially_new_formulation = _safety_check_form_not_present_in_tree(llm, node,
                                                                                         raw_formulation)
                    if potentially_new_formulation:
                        raw_formulation = potentially_new_formulation
                        execution_error = None
                        continue

                # Safety check: Check if full formulation up until now already exists in ToT
                if node.level == 3 or node.level == 4 or node.level == 5:
                    potentially_new_formulation = _safety_check_form_not_present_in_tree(llm, node,
                                                                                         raw_formulation)
                    if potentially_new_formulation:
                        raw_formulation = potentially_new_formulation
                        execution_error = None
                        continue

                # Safety check: Prevent false-positive exec-run-through by sneakily never calling function
                if node.level == 4:
                    potentially_new_formulation = _safety_check_non_called_functions(llm, node,
                                                                                     raw_formulation)
                    if potentially_new_formulation:
                        raw_formulation = potentially_new_formulation
                        execution_error = None
                        continue

                return raw_formulation

        # Switch models
        llm.switch_model_id(
            model_id=(
                "qwen.qwen3-coder-30b-a3b-v1:0" if llm.model_id == "qwen.qwen3-coder-480b-a35b-v1:0" else "qwen.qwen3-coder-480b-a35b-v1:0"),
        )
        create_and_send_prompt(node,
                               full_problem_description=full_problem_description,
                               subproblem_description=subproblem_description, llm=llm)
    return None

def create_and_send_prompt(node: TreeNode,
                           llm,
                           execution_message: str = None,
                           full_problem_description: list[str] = None,
                           subproblem_description: str = None):
    """
    Creates and sends prompt for partial formulation, given execution message,
    node.get_partial_formulation_up_until_now, and problem formulation, depending on node.level
    Args:
         node (TreeNode): current node of formulation
         llm: LLModel client
         execution_message (str, optional): message to send to execution message.
         full_problem_description (list[str], optional): description of problem.
         subproblem_description (list[str], optional): description of subproblem.
    Returns:
        str: answer from LLM given the created prompt
    """
    response = ""
    # TEXTUAL DESCRIPTION
    if node.level == 0:
        response = llm.send_prompt(
            system_prompt=f"{_get_system_prompt("text_sp")}",
            prompt=load_sp_file("sp_text_repr.txt") +
                   # Input variables (constants) problem description
                   full_problem_description[0] + "\n" +
                   # Output variables (decision variables) - problem description
                   full_problem_description[1] + "\n" +
                   # Global problem description
                   full_problem_description[2] + "\n" +
                   # Sub problem description
                   full_problem_description[3],
            max_tokens=800
        )
    # OBJECTS (datatypes)
    elif node.level == 1:
        if execution_message is not None:
            response = llm.send_prompt(
                system_prompt=f"{_get_system_prompt("sp")}\n{_get_icl()}",
                prompt=
                # Send problematic code + execution_error_message from a previously failed run
                f"{response}\n\nTask:\n{execution_message}\nCorrect this error.")
        else:
            response = llm.send_prompt(
                system_prompt=f"{_get_system_prompt("format_sp")}\n{_get_icl()}",
                prompt=
                # General
                "Given the problem below:\n" +
                "------------\n" +
                # Input variables (constants) problem description
                "Input - Constants Specification:\n" + full_problem_description[0] +
                # Output variables (decision variables) - problem description
                "Output - Decision Variables Specification:\n" + full_problem_description[1] +
                # Global problem description
                "\n" + full_problem_description[2] +
                # Sub problem descriptions
                "\n".join([full_problem_description[i] for i in range(3, len(full_problem_description))]) +
                "\n------------\n" +
                # Component specific instr.: object types, data types
                f"Task: {load_sp_file("sp_objects.txt")}"
                , max_tokens=1000
            )
    # DECISION VARIABLES
    elif node.parent.level == 2.5:
        response = llm.send_prompt(
            system_prompt=f"{_get_system_prompt("json_sp")}\n{_get_icl()}",
            prompt=  # General instr.
            "Given the decision variable specification below:\n" +
            "------------\n" +
            # Output variables (decision variables) - problem description
            full_problem_description[1] +
            "------------\n" +
            # Given object types, constants:
            f"""Given the following python code snippet containing datatypes, constants:
                        ´´´{"form z3 import *" if not USE_OPTDSL else ""}
                        {node.get_partial_formulation_up_until_now()}´´´\n""" +
            # Component specific instr.: decision variables
            f"\nYour priority is to fulfill this task: {load_sp_file("sp_decision_variables.txt")}\n"
            , max_tokens=1000
        )
    # CONSTANTS and DECISION VARIABLES
    elif node.level == 2:
        # CONSTANTS
        if isinstance(node, VariablesConstantsNode) and len(node.variables_and_constants) == 0:
            response = llm.send_prompt(
                system_prompt=f"{_get_system_prompt("json_sp")}\n{_get_icl()}",
                prompt=  # General instr.
                "Given the constants specification below:\n" +
                "------------\n" +
                # Input variables (constants) problem description
                full_problem_description[0] + "\n" +
                "------------\n" +
                # Given object types
                f"Given the following python code snippet containing object types:\n" +
                f"´´´\n{"form z3 import *" if not USE_OPTDSL else ""}\n" +
                f"{node.get_partial_formulation_up_until_now()}´´´\n" +
                # Component specific instr.: constants
                # f"\nTask:Take this text description of required constants for an optimization problem: {text_representation}",
                f"\nYour priority is to fulfill this task: {load_sp_file("sp_constants.txt")}\n"
                , max_tokens=1500
            )
        else:
            response = llm.send_prompt(
                system_prompt=f"{_get_system_prompt("json_sp")}\n{_get_icl()}",
                prompt=  # General instr.
                "Given the problem:\n" +
                "------------\n" +
                # Output variables (decision variables) - problem description
                full_problem_description[1] +
                "------------\n" +
                # Given object types, constants:
                f"Given the following OptDSL code snippet containing datatypes, constants:\n" +
                f"{node.get_partial_formulation_up_until_now()}´´´\n" +
                # Component specific instr.: decision variables
                f"\nYour priority is to fulfill this task: {load_sp_file("sp_decision_variables.txt")}\n"
                , max_tokens=1500
            )
    # OBJ FUNCTION
    elif node.level == 3:
        response = llm.send_prompt(
            system_prompt=f"{_get_system_prompt("format_sp")}\n{_get_icl()}",
            prompt=
            "Given the problem description:\n" +
            "------------\n" +
            # Global problem description
            full_problem_description[2] + "\n" +
            "------------\n" +
            # "Given following constants and decision variables:\n" +
            f"Given the following python code snippet containing datatypes, constants, decision variables and objective func.:\n" +
            f"´´´{"form z3 import *" if not USE_OPTDSL else ""}\n" +
            f"{node.get_partial_formulation_up_until_now()}´´´\n" +
            # json.dumps(constants_variables_node.get_as_codeblock()) + "\n" +
            # Component specific instr.: obj. function
            f"\nYour priority is to fulfill this task: :\n{load_sp_file("sp_obj_function.txt")}\n"
            , max_tokens=800
        )
    # CONSTRAINT
    elif node.level >= 4:
        if subproblem_description is None:
            raise ValueError("Subproblem description cannot be None")

        response = llm.send_prompt(
            system_prompt=f"{_get_system_prompt("format_sp")}\n{_get_icl()}",
            prompt=
            "Given the subproblem description:\n" +
            "------------\n" +
            # Sub problem description
            subproblem_description +
            "------------\n" +
            f"Given the following python code snippet containing datatypes, constants, decision variables and objective func.:\n" +
            f"´´´{"form z3 import *" if not USE_OPTDSL else ""}\n" +
            f"{node.get_partial_formulation_up_until_now()}´´´\n" +
            f"\nTask:\n{load_sp_file("sp_constraints.txt")}\nNever return an empty answer!"
            , max_tokens=1000
        )
    return response

def send_prompt_with_system_prompt(prompt: str, llm, temperature = None):
    """
    Send prompt together with a system prompt
    Args:
        prompt (str): prompt text
        llm: LLModel client
        temperature (float, optional): temperature, defaults to 0.7
    """
    return llm.send_prompt(
        system_prompt=f"{_get_system_prompt("format_sp")}\n{_get_icl()}",
        prompt=prompt,
        max_tokens=4000,
        temperature=temperature
    )

def send_prompt_without_system_prompt(prompt: str, llm, temperature = None):
    """
    Send prompt together (without any system prompt)
    Args:
        prompt (str): prompt text
        llm: LLModel
        temperature (float, optional): temperature, defaults to 0.7
    """
    return llm.send_prompt(
        prompt=prompt,
        max_tokens=4000,
        temperature=temperature
    )

def send_feedback(node: TreeNode, llm, full_problem_formulation: list[str] = None, syntax: bool = True, best_child_yet: bool = False):
    """
    Send correct partial/full formulations generated by LLM, in the hopes the syntactic/semantic feedback creates
    a learning effect for the future
    Args:
        node (TreeNode): node.
        llm: LLModel.
        full_problem_formulation (list[str], optional): list of full formulations.
        syntax (bool, optional): indicates if the feedback concerns syntax (true) or semantics (false).
        best_child_yet (bool): indicates if the formulation, sent in the feedback, was the best found yet.
    """
    if syntax:
        if DEBUG_MODE_ON: print(f"Sending feedback for a {"full" if node.level == 4 else "partial"} job well done.")
        _ = llm.send_prompt(
            prompt=
            f"""The following is an example for a syntactically valid {"full" if node.level == 4 else "partial"} formulation of a optimization problem in OptDSL.
        Learn from it the syntax of OptDSL only. Ignore its semantics. Apply the syntax knowledge in the future.
        ´´´ python
        {node.get_partial_formulation_up_until_now()}
        ´´´""",
            max_tokens=1)
    # semantics
    else:
        if full_problem_formulation is None: raise ValueError("Full problem formulation is required")
        if DEBUG_MODE_ON: print(f"Sending feedback for a {"full" if node.level == 4 else "partial"} job well done.")

        prompt = f"""The following is an example for a syntactically valid {"full" if node.level == 4 else "partial"} OptDSL formulation of the optimization problem:
{full_problem_formulation}
Learn from it its syntax and semantics of OptDSL. Apply the syntax knowledge in the future. Provide diverse encodings and try different encodings in the future.
´´´ python
{node.get_partial_formulation_up_until_now()}
´´´"""
        prompt += "\nThis encoding provided the best objective value and best solve_time yet, but always strive for improvement in optimal value and solve time." if best_child_yet else "\nAlthough this encoding is semantically correct, it is not optimal or fast. Strive for optimality and efficiency (low solve time) in the future. Try an entire different approach!"

        _ = llm.send_prompt(
            prompt=prompt,
            max_tokens=1)

def send_polish_feedback(encoding_1: str, encoding_2: str, encoding_1_time: float, encoding_2_time: float, llm):
    """
    Send continuous feedback to LLM containing a comparison of given an encoding_1 and encoding_2 (incl. their solvetimes),
    in order for the LLM to learn performance-aiding qualities. Used in AlgoPolish.
    Args:
        encoding_1 (str): Original encoding.
        encoding_2 (str): AlgoPolished encoding.
        encoding_1_time (float): Solvetime in seconds of the original encoding.
        encoding_2_time (float): Solvetime in seconds of the AlgoPolished encoding.
        llm: LLModel client
    """
    if DEBUG_MODE_ON: print("Sending feedback for comparing one fast and one slower encoding.")
    _ = llm.send_prompt(
        prompt=
        f"""The following is an example for a syntactically valid refactoring from [Old code] to [Refactored code]. Nevertheless, try different approaches in the future.
[Snippet_1]
´´´ python
{encoding_1}
´´´

[Snippet_2]
´´´ python
{encoding_2}
´´´
[Snippet_1] requires {encoding_1_time} and [Snippet_2] requires {encoding_2_time} ms to solve. {"[Snippet_1] provides faster results than [Snippet_2]" if encoding_1_time>encoding_2_time else "[Snippet_2] provides faster results than [Snippet_1]"} Compare the encodings and learn unique coding characteristics from the faster one ({"[Snippet_1]" if encoding_1_time > encoding_2_time else "[Snippet_2]"}). Process the information, what characteristics improved the solving speed. In the future improve your own answers according to the learned characteristics. Always strive for improvement.""",
        max_tokens=1)

# -------------- HELPERS ----------------
def _extract_required_parts(raw_formulation: str, execution_error: str | None, node: TreeNode):
    """
        Check format of raw formulation and extract required parts, depending on current node.
        Args:
            raw_formulation (str): raw OptDSL formulation to check.
            execution_error (str): execution error will be "Constraints/Objective FormatError", in case of format violation.
            node (TreeNode): current TreeNode object, that eventually will contain the formulation.
    """
    decomposed_code = decompose_full_definition(raw_formulation)
    raw_formulation: str = ""
    if decomposed_code == {} or decomposed_code is None:
        execution_error = "Constraints/Objective FormatError"
    if execution_error is None and decomposed_code is not None and "auxiliary variables" in decomposed_code:
        raw_formulation += f"\n# --- Auxiliary Variables ---\n{decomposed_code["auxiliary variables"]}"
    if execution_error is None and node.name.lower() in decomposed_code:
        # Generated code already in partial formulation (duplicate)
        if "incorrect code" in decomposed_code and len(decomposed_code["incorrect code"]) > 0 and \
            decomposed_code[
                "incorrect code"] in node.get_partial_formulation_up_until_now():
            execution_error = f"Returned result code is already in given code (redundancy)! Encode exactly the subproblem and do not return code that is already given."
        raw_formulation += f"\n# --- {node.name.lower()} ---\n{decomposed_code[node.name.lower()]}"
        raw_formulation = raw_formulation.replace(f"# --- Incorrect Code ---\n", "")
    elif execution_error is None and "incorrect code" in decomposed_code:
        # Generated code already in partial formulation (duplicate)
        if decomposed_code["incorrect code"] in node.get_partial_formulation_up_until_now():
            execution_error = f"Returned result code is already in given code (redundancy)! Encode exactly the subproblem and do not return code that is already given."
        raw_formulation += f"\n# --- {node.name.lower()} ---\n{decomposed_code["incorrect code"]}"
    else:
        execution_error = "Constraints/Objective FormatError"
    raw_formulation.replace(f"# --- Incorrect Code ---\n", "")
    return execution_error, raw_formulation

def _safety_check_DStypes_correctly_initialized(llm: AwsClient, raw_formulation: str, node: TreeNode):
    """
    Check that DSInts and DSFloats are correctly initialized (concerning syntax) with lower and upper bound.
    Args:
        llm (AwsClient): LLM client for correction prompt.
        raw_formulation (str): raw OptDSL formulation to check.
        node (TreeNode): current TreeNode object, that eventually will contain the formulation.
    """
    pattern = re.compile(
        r"""^\s*(?P<var>[A-Za-z_]\w*)\s*:\s*[A-Za-z_]\w*\s*\(
                 (?:.*?(?:\blb\s*=\s*(?P<lb>-?\d+))?)?
                 (?:.*?(?:\bub\s*=\s*(?P<ub>-?\d+))?)?
               \)\s*=\s*(?P<val>-?\d+)\s*$""",
        re.VERBOSE
    )
    for j, line in enumerate(raw_formulation.splitlines()):
        m = pattern.match(line)
        if not m:
            continue
        var = m.group('var')
        lb = m.group('lb')
        ub = m.group('ub')
        val = m.group('val')
        if (lb is not None and val < lb) or (ub is not None and val > ub):
            return (llm.send_prompt(
                system_prompt=(
                              _get_system_prompt(
                                  "json_sp") if node.level == 2 else _get_system_prompt(
                                  "format_sp")) + "\n" + _get_icl(),
                prompt=f"´´´ python\n" +
                       (f"from z3 import * \n" if not USE_OPTDSL else "") +
                       f"\n# --- Incorrect Code --- \n{raw_formulation} ´´´\n\n" +
                       f"In line {j} a decision variable DSInt is not initialized incorrectly. Correct the initialization to lb <= {var} <= ub, {line}\n"
                , max_tokens=(800 if node.level == 4 else 500)
            ))
    return None

def _safety_check_DSLists_must_have_same_length_as_input(llm, filtered_constants_variables: list,
                                                         execution_error: str | None,
                                                         full_problem_description: list,
                                                         raw_formulation: str, node_level: int):
    """
    Check that the list lengths of LLM-defined constants-lists and user-specified constants-lists are equal,
    otherwise send to LLM for correction.
    Args:
        llm (AwsClient): LLM for correction prompt
        filtered_constants_variables (list): List of constants defined by LLM
        execution_error (str): if list lengths do not align, is set to "Incorrect length of constant."
        full_problem_description (list[str]): description of problem.
        raw_formulation (str): raw OptDSL formulation to check.
        node_level (int): level of current node in tree, to determine system prompt in case of correction prompt.
    """
    for variable in filtered_constants_variables:
        initialization = initial_clean_up(variable["initialization"])
        if "DSList" in initialization:
            if int(re.search(r"length\s*=\s*(\d+)", initialization).group(1)) != len(
                json.loads(remove_programming_environment(full_problem_description[0]))[
                    variable["variable_name"]]):
                if DEBUG_MODE_ON: print(f"Incorrect length of {variable["variable_name"]}.")
                raw_formulation = remove_programming_environment(llm.send_prompt(
                    system_prompt=(_get_system_prompt(
                        "json_sp") if node_level == 2 else _get_system_prompt(
                        "format_sp")) + _get_icl(),
                    prompt=f"´´´\njson\n{raw_formulation}´´´\n\n" +
                           f"The Json code above contains an error: Incorrect length of {variable["variable_name"]}. It should have been {len(json.loads(remove_programming_environment(full_problem_description[0]))[variable["variable_name"]])}, not {int(re.search(r"length\s*=\s*(\d+)", initialization).group(1))}. Correct it.\n" +
                           "Given this error message, improve the mentioned lines of the \"initialization\" and/or the \"variable_type\" field according to the error message and the problem description, nothing else." +
                           f"The problem description is: {full_problem_description[0]}\n"
                           "Return the given json code with the corrections. Do not copy the in-context-training example. Do not return \"NTD\".",
                    max_tokens=1500
                ))
                execution_error = "Incorrect length of constant."
                break
            else:
                execution_error = None
    return execution_error, raw_formulation

def _safety_check_form_not_present_in_tree(llm: AwsClient, node: TreeNode, raw_formulation: str):
    """
    Check that raw_formulation is not already present in the tree, otherwise send to LLM for correction.
    Args:
        llm (AwsClient): AwsClient for LLM correction prompt.
        node (TreeNode): current TreeNode object, that eventually will contain the formulation.
        raw_formulation (str): raw OptDSL formulation to check.
    """
    siblings = node.get_siblings()
    strippedCurrentFormulation = TreeNode.strip_comments(
        node.get_partial_formulation_up_until_now() + "\n\n" + raw_formulation).lower()
    if (siblings is not None and
        (node.level == 3 or node.level == 4 or node.level == 5) and
        any(strippedCurrentFormulation in s.lower() for s in siblings)):
        print("Duplicate encountered - trying again ...")
        raw_formulation = (llm.send_prompt(
            system_prompt=(_get_system_prompt(
                "json_sp") if node.level == 2 else _get_system_prompt(
                "format_sp")) + "\n" + _get_icl(),
            prompt=f"´´´python\n" +
                   (f"from z3 import * \n" if not USE_OPTDSL else "") +
                   f"\n{raw_formulation} ´´´\n\n" +
                   "You recently provided exectly this piece of formulation, refactor it so it is different. You may change algorithm, intermediate variables etc. but the semantics must not change.",
            max_tokens=(800 if node.level == 4 else 500)
        ))
        return raw_formulation
    return None

def _safety_check_non_called_functions(llm: AwsClient, node: TreeNode, raw_formulation: str):
    """
    Check that all defined functions in the raw_formulation are also called, otherwise send to LLM for correction.
    Args:
        llm (AwsClient): AwsClient for LLM correction prompt, if required.
        node (TreeNode): current TreeNode object, that eventually will contain the formulation.
        raw_formulation (str): raw OptDSL formulation to check.
    """
    not_twice_appearing_func = check_functions_appear_twice(raw_formulation)
    if len(not_twice_appearing_func) > 0:
        if DEBUG_MODE_ON: print(
            f"The following functions are defined but never called, {not_twice_appearing_func}. Add the missing function calls.")
        raw_formulation = (llm.send_prompt(
            system_prompt=(
                              _get_system_prompt(
                                  "json_sp") if node.level == 2 else _get_system_prompt(
                                  "format_sp")) + "\n" + _get_icl(),
            prompt=f"´´´python\n" +
                   (f"from z3 import * \n" if not USE_OPTDSL else "") +
                   f"\n{node.get_partial_formulation_up_until_now()}\n{raw_formulation} ´´´\n\n" +
                   f"The following functions are defined but never called, {not_twice_appearing_func}" +
                   "Add the missing function calls to the code with the correct parameters. Do not return exactly the given code snippet.",
            max_tokens=(800 if node.level == 4 else 500)
        ))
        return raw_formulation
    return None

def _get_icl():
    """
    Load a part of the system prompt containing an in-context learning example and a formal description of OptDSL.
    """
    return load_sp_file("ICL_example.txt")

def _get_system_prompt(key: str):
    """
    Get the system prompt for the given key/purpose
    """
    key = f"{CHOSEN_LANGUAGE}_{key}"
    system_prompt = {
        "text_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into text description. The result must contain correct definitions only.",
        "optdsl_format_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem into valid OptDSL, use the EBNF grammar in the system prompt. \n1.The result must be code only. \n2.No explanations. \n3.Python comments are allowed. \n4. Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6.Return you answer in the following format: ´´´python <solution> ´´´ where <solution> is a placeholder for the code. Use in-context-learning examples, do not take its variables directly but learn. \n7. Do not hallucinate. \n8. Do not exceed the max_tokens. \n9. Never leave placeholder for the user to fill out, everything must be strictly defined by you.\n10. If you encountered a similar problem before, provide a different formulation while being syntactically valid.",
        "optdsl_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem into valid OptDSL. \n1.The result must be code only. \n2.No explanations. \n3.Python comments are allowed. \n4.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. Use in-context-learning examples, do not take its variables directly but learn. \n6.Return \"NTD\", if there is empty output. \n7. Do not hallucinate. \n8. Do not exceed the max_tokens. 9. Never leave placeholder for the user to fill out, everything must be strictly defined by you.",
        "optdsl_json_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem into valid OptDSL. \n1.The result must be a json that partly contains code. \n2.No explanations. \n3.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. Use in-context-learning examples. \n6. Do not exceed the max_tokens. 7. Never leave placeholder for the user to fill out, everything must be strictly defined by you.\n8. If you encountered a similar problem before, try to be creative about the formulation while being syntactically valid."
    }
    return system_prompt.get(key)
