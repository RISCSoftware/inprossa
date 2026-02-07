import ast
import json
import re

from structures_utils import load_sp_file, TreeNode, is_valid_json, \
    decompose_full_definition, check_executability, check_functions_appear_twice, VariablesConstantsNode, \
    remove_programming_environment, initial_clean_up
from constants import DEBUG_MODE_ON, USE_OPTDSL, CHOSEN_LANGUAGE

LOOP_OF_DOOM_UNSAT_MAX_IT = 2
LOOP_OF_DOOM_MAX_IT = 4
MAX_NR_RESETS = 3
N_FAILED_GENERATIONS = 0
FAILED_GENERATIONS = []  # problem desc. indices of failed generation steps


def enter_variable_definitions_feedback_loop(node, raw_definitions, llm, full_problem_description: list[str] = None, subproblem_description: str = None):
    execution_error = None
    for _ in range(MAX_NR_RESETS):
        nr_unsat_error = 0
        for i in range(LOOP_OF_DOOM_MAX_IT):
            # Incorrect return format for USE_ALL_AT_ONCE_AND_EXTRACT (# Objects # Constants ...)
            if raw_definitions is None:
                if DEBUG_MODE_ON: print("Incorrect return format for USE_ALL_AT_ONCE_AND_EXTRACT")
                raw_definitions = (llm.send_prompt(
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

            # Send prompt anew, no feedback loop
            if ("NTD" in raw_definitions or
                    "Minizinc Solver Error" in raw_definitions or
                    (execution_error is not None and "Constraints FormatError" in execution_error) or
                    (execution_error is not None and "Constraints/Objective FormatError" in execution_error) or
                    raw_definitions.strip() == "" or
                    nr_unsat_error == LOOP_OF_DOOM_UNSAT_MAX_IT):
                if DEBUG_MODE_ON: print(
                    f"Checking node created for level {node.level}: {raw_definitions}\nNTD, solver error, format error or end of loop of doom encountered")
                raw_definitions = create_and_send_prompt_for_strictly_iterative_approach(node,
                                                                                         full_problem_description=full_problem_description,
                                                                                         subproblem_description=subproblem_description,
                                                                                         llm=llm)
                execution_error = None
                nr_unsat_error = 0

            # Constants and dec. variables - responses need to be json
            if node.level == 2:
                if not is_valid_json(raw_definitions):
                    if DEBUG_MODE_ON: print(
                        f"Checking node created for level {node.level}: Constants not valid json.")
                    raw_definitions = (llm.send_prompt(
                        system_prompt=_get_system_prompt("sp"),
                        prompt=raw_definitions + "\n\n" +
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
                filtered_constants_variables = [item for item in json.loads(raw_definitions) if (
                item.get("variable_name", "").isupper() if len(node.variables_and_constants) == 0 else item.get(
                        "variable_name", "").islower())]
                if len(filtered_constants_variables) == 0:
                    raw_definitions = (llm.send_prompt(
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
                if filtered_constants_variables[0]["variable_name"].isupper() and full_problem_description[0] != []:
                    for variable in filtered_constants_variables:
                        initialization = initial_clean_up(variable["initialization"])
                        if ("DSList" in initialization):
                            if int(re.search(r"length\s*=\s*(\d+)", initialization).group(1)) != len(json.loads(remove_programming_environment(full_problem_description[0]))[variable["variable_name"]]):
                                if DEBUG_MODE_ON: print(f"Incorrect length of {variable["variable_name"]}.")
                                raw_definitions = remove_programming_environment(llm.send_prompt(
                                    system_prompt=(_get_system_prompt(
                                        "json_sp") if node.level == 2 else _get_system_prompt(
                                        "format_sp")) + _get_icl(),
                                    prompt=f"´´´\njson\n{raw_definitions}´´´\n\n" +
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
                    if execution_error is not None:
                        continue

            # Extracted objective and constraints + auxiliary vars
            execution_error = None
            if node.level == 3 or node.level == 4:
                decomposed_code = decompose_full_definition(raw_definitions)
                if decomposed_code == {}:
                    decompose_full_definition(raw_definitions)
                raw_definitions: str = ""
                if decomposed_code is None:
                    execution_error = "Constraints/Objective FormatError"
                if execution_error is None and decomposed_code is not None and "auxiliary variables" in decomposed_code:
                    raw_definitions += f"\n# --- Auxiliary Variables ---\n{decomposed_code["auxiliary variables"]}"
                if execution_error is None and node.name.lower() in decomposed_code:
                    # Generated code already in partial formulation (duplicate)
                    if "incorrect code" in decomposed_code and len(decomposed_code["incorrect code"]) > 0 and decomposed_code["incorrect code"] in node.get_partial_formulation_up_until_now():
                        execution_error = f"Returned result code is already in given code (redundancy)! Encode exactly the subproblem and do not return code that is already given."
                    raw_definitions += f"\n# --- {node.name.lower()} ---\n{decomposed_code[node.name.lower()]}"
                    raw_definitions = raw_definitions.replace(f"# --- Incorrect Code ---\n", "")
                elif execution_error is None and "incorrect code" in decomposed_code:
                    # Generated code already in partial formulation (duplicate)
                    if decomposed_code["incorrect code"] in node.get_partial_formulation_up_until_now():
                        execution_error = f"Returned result code is already in given code (redundancy)! Encode exactly the subproblem and do not return code that is already given."
                    raw_definitions += f"\n# --- {node.name.lower()} ---\n{decomposed_code["incorrect code"]}"
                else:
                    execution_error = "Constraints/Objective FormatError"
                if node.level == 3:
                    if len(raw_definitions.splitlines()) <= 6:
                        raw_definitions = (llm.send_prompt(
                            system_prompt=(_get_system_prompt(
                                "json_sp") if node.level == 2 else _get_system_prompt(
                                    "format_sp")) + "\n" + _get_icl(),
                            prompt=f"´´´python\n" +
                                   (f"from z3 import * \n" if not USE_OPTDSL else "") +
                                   f"\n# --- Incorrect Code --- \n{raw_definitions}´´´\n\n" +
                                   f"The section above contains a function \"calculate_objective\" with an invalid objective value calculation, replace it with a valid calculation according to the description." +
                                   f"Description: {subproblem_description}"
                                   """Return your answer in the format
                                   ´´´python
                                   # --- Incorrect Code ---
                                   <corrected code>
                                   ´´´, where <corrected code> is the section \"# --- Incorrect Code ---\" with the corrections.
                                   """,
                            max_tokens=(1000 if node.level == 4 else 800)
                        ))
                raw_definitions.replace(f"# --- Incorrect Code ---\n", "")
                # Safety check: function does not consist only of a return of a variable
                if _contains_func_that_just_returns_var(raw_definitions):
                    execution_error = "Error: The function within this code does not include any calculation, but only returns an unmodified input variable. Encode the calculation of the objective function mentioned in the last prompt."

            # Check for syntactical correctness and handle execution error, if no "Constraints/Objective FormatError" has occurred yet
            if execution_error is None:
                execution_error = check_executability(node, raw_definitions)
            # Handle execution error
            if execution_error is not None:
                if DEBUG_MODE_ON: print(
                    f"Checking node created for level {node.level} not executable: {execution_error}\n")
                if ("NTD" in raw_definitions or
                        (execution_error is not None and "Constraints FormatError" in execution_error) or
                        (execution_error is not None and "Constraints/Objective FormatError" in execution_error)):
                    if DEBUG_MODE_ON: print(
                        f"Checking node created for level {node.level}: {raw_definitions}\nNTD, Constraints FormatError or Constraints/Objective ForamtErrorencountered")
                    raw_definitions = create_and_send_prompt_for_strictly_iterative_approach(node,
                                                                                             full_problem_description=full_problem_description,
                                                                                             subproblem_description=subproblem_description,
                                                                                             llm=llm)
                    execution_error = None
                    continue
                elif "Syntax Error" in execution_error:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                                "format_sp")) + "\n" + _get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not USE_OPTDSL else "") +
                               f"\n# --- Incorrect Code --- \n{raw_definitions}´´´\n\n" +
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
                    raw_definitions = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                                "format_sp")) + "\n" + _get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not USE_OPTDSL else "") +
                               f"\n# --- Incorrect Code --- \n{raw_definitions}´´´\n\n" +
                               f"The section above contains a semantic error: {execution_error}" +
                               "Given this error message, improve the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet according to the error message, nothing else." +
                               f"The semantics of the section \"# --- Incorrect Code ---\" must be in line with the following description:\n{raw_definitions if subproblem_description is None else subproblem_description}" +
                               """Return your answer in the format
                               ´´´python
                               # --- Incorrect Code ---
                               <corrected code>
                               ´´´, where <corrected code> is the section \"# --- Incorrect Code ---\" with the corrections.
                               """,
                        max_tokens=(1000 if node.level == 4 else 800)
                    ))
                    nr_unsat_error += 1
                elif "redundancy" in execution_error:
                    raw_definitions = (llm.send_prompt(
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
                    raw_definitions = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                            "format_sp")) + _get_icl(),
                        prompt=f"´´´python\n" +
                               f"{node.get_partial_formulation_up_until_now()}\n"
                               f"\n# --- Incorrect Code --- \n{raw_definitions}´´´\n\n" +
                               f"Improve the code of the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet as follows: Inline expressions and list accesses instead of creating temporary variables. Reduce the number of temporary variables. Increase efficiency of constraints and reduce constraint length." +
                               "Nothing else. Do not change the semantics of the code. Do not return NTD."
                               "Return your answer in the format\n" +
                               "´´´python\n" +
                               "# --- Incorrect Code ---\n" +
                               "<corrected code>\n" +
                               "\n´´´, where <corrected code> all lines underneath \"# --- Incorrect Code ---\" with the corrections.",
                        max_tokens=(1500 if node.level >= 4 else 800)
                    ))
                elif node.level == 2:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                            "format_sp")) + _get_icl(),
                        prompt=f"´´´\njson\n{raw_definitions}´´´\n\n" +
                               f"The Json code above contains an error: {execution_error}" +
                               "Given this error message, improve the mentioned lines of the \"initialization\" and/or the \"variable_type\" field according to the error message, nothing else."
                               "Return the given json code with the corrections. Do not copy the in-context-training example. Do not return \"NTD\".",
                        max_tokens=800
                    ))
                else:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=(_get_system_prompt(
                            "json_sp") if node.level == 2 else _get_system_prompt(
                                "format_sp")) + _get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not USE_OPTDSL else "") +
                               f"{node.get_partial_formulation_up_until_now()}\n"
                               f"\n# --- Incorrect Code --- \n{raw_definitions}´´´\n\n" +
                               f"The section above contains an error: {execution_error}" +
                               "Given this error message, improve the mentioned lines of the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet according to the error message, nothing else. Do not change the semantics of the code. Do not return NTD."
                               "Return your answer in the format\n" +
                               "´´´python\n" +
                               "# --- Incorrect Code ---\n" +
                               "<corrected code>\n" +
                               "\n´´´, where <corrected code> all lines underneath \"# --- Incorrect Code ---\" with the corrections.",
                        max_tokens=(1500 if node.level >= 4 else 800)
                    ))
            else:
                # Safety check: check if DSInts are correctly initialized according to lb and ub
                if node.level == 3 or node.level == 4 or node.level == 5:
                    pattern = re.compile(
                        r"""^\s*(?P<var>[A-Za-z_]\w*)\s*:\s*[A-Za-z_]\w*\s*\(
                                 (?:.*?(?:\blb\s*=\s*(?P<lb>-?\d+))?)?
                                 (?:.*?(?:\bub\s*=\s*(?P<ub>-?\d+))?)?
                               \)\s*=\s*(?P<val>-?\d+)\s*$""",
                        re.VERBOSE
                    )
                    for j, line in enumerate(raw_definitions.splitlines()):
                        m = pattern.match(line)
                        if not m:
                            continue
                        var = m.group('var')
                        lb = m.group('lb')
                        ub = m.group('ub')
                        val = m.group('val')
                        if (lb is not None and val < lb) or (ub is not None and val > ub):
                            raw_definitions = (llm.send_prompt(
                                system_prompt=(
                                                  _get_system_prompt(
                                                      "json_sp") if node.level == 2 else _get_system_prompt(
                                                      "format_sp")) + "\n" + _get_icl(),
                                prompt=f"´´´ python\n" +
                                       (f"from z3 import * \n" if not USE_OPTDSL else "") +
                                       f"\n# --- Incorrect Code --- \n{raw_definitions} ´´´\n\n" +
                                       f"In line {j} a decision variable DSInt is not initialized incorrectly. Correct the initialization to lb <= {var} <= ub, {line}\n"
                                , max_tokens=(800 if node.level == 4 else 500)
                            ))

                # Safety check: Prevent false-positive exec-run-through by sneakily never calling function
                if node.level == 4:
                    not_twice_appearing_func = check_functions_appear_twice(raw_definitions)
                    if len(not_twice_appearing_func) > 0:
                        if DEBUG_MODE_ON: print(
                            f"The following functions are defined but never called, {not_twice_appearing_func}. Add the missing function calls.")
                        raw_definitions = (llm.send_prompt(
                            system_prompt=(
                                              _get_system_prompt(
                                                  "json_sp") if node.level == 2 else _get_system_prompt(
                                                  "format_sp")) + "\n" + _get_icl(),
                            prompt=f"´´´ python\n" +
                                   (f"from z3 import * \n" if not USE_OPTDSL else "") +
                                   f"\n{node.get_partial_formulation_up_until_now()}\n{raw_definitions} ´´´\n\n" +
                                   f"The following functions are defined but never called, {not_twice_appearing_func}" +
                                   "Add the missing function calls to the code with the correct parameters. Do not return exactly the given code snippet.",
                            max_tokens=(800 if node.level == 4 else 500)
                        ))
                        continue
                return raw_definitions

        # Attempt reset
        llm.send_prompt_with_model_id(
            model_id=(
                "qwen.qwen3-coder-30b-a3b-v1:0" if llm.model_id == "qwen.qwen3-coder-480b-a35b-v1:0" else "qwen.qwen3-coder-480b-a35b-v1:0"),
            # model_id=("eu.amazon.nova-lite-v1:0" if llm.model_id == "eu.amazon.nova-pro-v1:0" else "eu.amazon.nova-pro-v1:0"),
            # model_id=("eu.anthropic.claude-3-5-sonnet-20240620-v1:0" if llm.model_id == "eu.anthropic.claude-3-7-sonnet-20250219-v1:0" else "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"),
            # model_id=("openai.gpt-oss-120b-1:0" if llm.model_id == "eu.amazon.nova-pro-v1:0" else "eu.amazon.nova-pro-v1:0"),
            prompt="",
            max_tokens=1
        )
        create_and_send_prompt_for_strictly_iterative_approach(node,
                                                               full_problem_description=full_problem_description,
                                                               subproblem_description=subproblem_description, llm=llm)
    return ""


def create_and_send_prompt_for_strictly_iterative_approach(node: TreeNode,
                                                           llm,
                                                           execution_message: str = None,
                                                           full_problem_description: list[str] = None,
                                                           subproblem_description: str = None):
    response = ""
    # if llm.model_id == "qwen.qwen3-coder-480b-a35b-v1:0":
    #    llm.model_id = "qwen.qwen3-coder-30b-a3b-v1:0"
    # else:
    #    llm.model_id = "qwen.qwen3-coder-480b-a35b-v1:0"
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
                full_problem_description[0] + "\n" +
                # Output variables (decision variables) - problem description
                full_problem_description[1] + "\n" +
                # Global problem description
                full_problem_description[2] + "\n" +
                # Sub problem description
                full_problem_description[3] +
                "------------\n" +
                # Component specific instr.: object types, data types
                f"Task: {load_sp_file("sp_objects.txt")}"
                , max_tokens=1000
            )
    # DECISION VARIABLES
    elif node.parent.level == 2.5:
        response = llm.send_prompt(
            system_prompt=f"{_get_system_prompt("json_sp")}\n{_get_icl()}",
            prompt=  # General instr.
            "Given the problem:\n" +
            "------------\n" +
            # Output variables (decision variables) - problem description
            full_problem_description[1] +
            "------------\n" +
            # Given object types, constants:
            f"""Given the following python code snippet containing datatypes, constants:
                        ´´´python\n{"form z3 import *" if not USE_OPTDSL else ""}
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
                "Given the problem:\n" +
                "------------\n" +
                # Input variables (constants) problem description
                full_problem_description[0] + "\n" +
                "------------\n" +
                # Given object types
                f"""Given the following python code snippet containing object types:
                    ´´´python\n{"form z3 import *" if not USE_OPTDSL else ""}
                    {node.get_partial_formulation_up_until_now()}´´´\n""" +
                # Component specific instr.: constants
                # f"\nTask:Take this text description of required constants for an optimization problem: {text_representation}",
                f"\nYour priority is to fulfill this task: {load_sp_file("sp_constants.txt")}\n"
                , max_tokens=1000
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
                f"""Given the following python code snippet containing datatypes, constants:
                ´´´python\n{"form z3 import *" if not USE_OPTDSL else ""}
                {node.get_partial_formulation_up_until_now()}´´´\n""" +
                # Component specific instr.: decision variables
                f"\nYour priority is to fulfill this task: {load_sp_file("sp_decision_variables.txt")}\n"
                , max_tokens=1000
            )
    # OBJ FUNCTION
    elif node.level == 3:
        response = llm.send_prompt(
            system_prompt=f"{_get_system_prompt("format_sp")}\n{_get_icl()}",
            prompt=
            "Given the problem:\n" +
            "------------\n" +
            # Global problem description
            full_problem_description[2] + "\n" +
            "------------\n" +
            # "Given following constants and decision variables:\n" +
            f"""Given the following python code snippet containing datatypes, constants, decision variables and objective func.:
    ´´´python {"form z3 import *" if not USE_OPTDSL else ""}
    {node.get_partial_formulation_up_until_now()}´´´\n""" +
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
            "Given the problem:\n" +
            "------------\n" +
            # Sub problem description
            subproblem_description +
            "------------\n" +
            f"""Given the following python code snippet containing datatypes, constants, decision variables and objective func.:
                ´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n""" +
            f"\nTask:\n{load_sp_file("sp_constraints.txt")}\nNever return an empty answer!"
            , max_tokens=1000
        )
    return response

def send_prompt_with_system_prompt(prompt: str, llm):
    return llm.send_prompt(
        system_prompt=f"{_get_system_prompt("format_sp")}\n{_get_icl()}",
        prompt=prompt,
        max_tokens=4000
    )

# Sends correct partial formulations generated by LLM, in the hopes the feedback creates a learning effect
def send_feedback(node: TreeNode, llm, full_problem_formulation: list[str] = None, syntax: bool = True, best_child_yet: bool = False):
    if syntax:
        if DEBUG_MODE_ON: print("Sending feedback for a partial job well done.")
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
        if DEBUG_MODE_ON: print("Sending feedback for a partial job well done.")

        prompt = f"""The following is an example for a, maybe not optimal, but syntactically valid {"full" if node.level == 4 else "partial"} OptDSL formulation of the optimization problem:
{full_problem_formulation}
Learn from it its syntax and semantics of OptDSL. Apply the syntax knowledge in the future. Provide diverse encodings in the future.
´´´ python
{node.get_partial_formulation_up_until_now()}
´´´"""
        prompt += "\nThis encoding provided the best objective value yet, but always strive for improvement." if best_child_yet else "\nAlthough this encoding is semantically correct, it is not optimal. Strive for optimality in the future."
        _ = llm.send_prompt(
            prompt=prompt,
            max_tokens=1)

def send_polish_feedback(old_encoding: str, refactored_encoding: str, llm, syntax: bool = True):
    if DEBUG_MODE_ON: print("Sending feedback for a partial job well done.")
    _ = llm.send_prompt(
        prompt=
        f"""The following is an example for a syntactically valid refactoring.
[Old code]
´´´ python
{old_encoding}
´´´
[Refactored code]
´´´ python
{refactored_encoding}
´´´""",
        max_tokens=1)

def _get_icl():
    if USE_OPTDSL:
        return load_sp_file("ICL_example_3.txt")
    else:
        return load_sp_file("ICL_datatypes.txt")

def _get_system_prompt(key: str):
    key = f"{CHOSEN_LANGUAGE}_{key}"
    if USE_OPTDSL:
        system_prompt = {
            "text_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into text description. The result must contain correct definitions only.",
            "optdsl_format_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem into valid OptDSL, use the EBNF grammar in the system prompt. \n1.The result must be code only. \n2.No explanations. \n3.Python comments are allowed. \n4. Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6.Return you answer in the following format: ´´´python <solution> ´´´ where <solution> is a placeholder for the code. Use in-context-learning examples, do not take its variables directly but learn. \n7. Do not hallucinate. \n8. Do not exceed the max_tokens. \n9. Never leave placeholder for the user to fill out, everything must be strictly defined by you.\n10. If you encountered a similar problem before, provide a different formulation while being syntactically valid.",
            "optdsl_format_all_sp": """
You are an optimization problem formulation expert that encodes specific parts of the problem from below into OptDSL.
1.The result must be code only.
2.No explanations.
3.Python comments are allowed.
4. Avoid lengthy comments, keep it short.
5.The result must contain correct definitions only.
6.Return you answer in the following format:
´´´python
# --- Objects ---
<solution>

# --- Constants and Decision Variables ---
<solution>

# --- Objective ---
<solution>

# --- Constraints ---
<solution>
´´´ where <solution> is a placeholder for the code. Use in-context-learning examples, do not take its variables directly but learn.
7.Return \"NTD\", if there is empty output.
8. Do not hallucinate.
9. Do not exceed the max_tokens.
10. Never leave placeholder for the user to fill out, everything must be strictly defined by you.
            """,
            "optdsl_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem into valid OptDSL. \n1.The result must be code only. \n2.No explanations. \n3.Python comments are allowed. \n4.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. Use in-context-learning examples, do not take its variables directly but learn. \n6.Return \"NTD\", if there is empty output. \n7. Do not hallucinate. \n8. Do not exceed the max_tokens. 9. Never leave placeholder for the user to fill out, everything must be strictly defined by you.",
            "optdsl_json_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem into valid OptDSL. \n1.The result must be a json that partly contains code. \n2.No explanations. \n3.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. Use in-context-learning examples. \n6. Do not exceed the max_tokens. 7. Never leave placeholder for the user to fill out, everything must be strictly defined by you.\n8. If you encountered a similar problem before, try to be creative about the formulation while being syntactically valid.",
            "optdsl_json_schema_sp": """You are an optimization problem formulation expert that encodes specific parts of the problem from below into OptDSL. 1.The result must be a json that partly contains code. \n2.No explanations. \n3.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. The result must adhere to this json schema:
            {
              "$schema": "https://json-schema.org/draft/2020-12/schema",
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "description": {
                    "type": "string",
                    "description": "A compact, concise description of the variable"
                  },
                  "initialization_left": {
                    "type": "string",
                    "description": "The OptDSL variable initialization code that is at left side of the equals. Constants naming convention: capital letters only."
                  },
                  "initialization_right": {
                    "type": "string",
                    "description": "The OptDSL variable initialization code that is at right side of the equals as string code block. It must not contain json or dict but OptDSL code as string"
                  }
                },
                "required": ["description", "initialization"],
                "additionalProperties": false
              }
            }
            The structure must fulfill following requirements:
            1. "<initialization_left> = <initialization_right>" must be valid pythonic OptDSL code."""
        }
        return system_prompt.get(key)
    else:
        system_prompt = {
            "text_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into a textual description. The  The result must contain correct definitions only. Define textual requirements for that specific problem part that a future encoding must fulfill. Avoid redundancies.",
            "z3py_format_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python. 1.The result must be python code only. \n2.No explanations. \n3.Python comments are allowed. \n4. Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6.Return you answer in the following format: ´´´python <solution> ´´´ where <solution> is a placeholder for the code. \n7. Remember that each constraint must be added to a s = Optimize(). Use given datatypes, IntVal, StringVal etc. Use IntVal, StringVal etc. Use in-context-learning examples, do not take its variables directly but learn. \n8.Return \"NTD\", if there is empty output. \n9. Do not hallucinate. \n10. Do not exceed the max_tokens. 11. Never leave placeholder for the user to fill out, everything must be strictly defined by you. Avoid redundancies.",
            "z3py_format_all_sp": """
        You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python.
        1. The result must be code only.
        2. No explanations.
        3. Python comments are allowed.
        4. Avoid lengthy comments, keep it short.
        5. The result must contain correct definitions only.
        6. Return you answer in the following format:
        ´´´python
        # --- Objects ---
        <solution>

        # --- Constants and Decision Variables ---
        <solution>

        # --- Objective ---
        <solution>

        # --- Constraints ---
        <solution>
        ´´´ where <solution> is a placeholder for the code.
        7. Return \"NTD\", if there is empty output.
        8. Do not hallucinate.
        9. Do not exceed the max_tokens.
        10. Never leave placeholder for the user to fill out, everything must be strictly defined by you.""",
            "z3py_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python. 1.The result must be python code only. \n2.No explanations. \n3.Python comments are allowed. \n4.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6. Remember that constraint must be added to a s = Optimize(). Use given datatypes, IntVal, StringVal etc. \nUse IntVal, StringVal etc. Use in-context-learning examples, do not take its variables directly but learn. \n7.Return \"NTD\", if there is empty output. \n9. Do not hallucinate. \n10. Do not exceed the max_tokens. 11. Never leave placeholder for the user to fill out, everything must be strictly defined by you. Avoid redundancies.",
            "z3py_json_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python. 1.The result must be a json that partly contains code. \n2.No explanations. \n3.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6. Remember that each constraint must be added to a s = Optimize().  Use given datatypes, IntVal, StringVal etc. Use in-context-learning examples. \n10. Do not exceed the max_tokens. 11. Never leave placeholder for the user to fill out, everything must be strictly defined by you. Avoid redundancies.",
            "z3py_json_schema_sp": """You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python. 1.The result must be a json that partly contains code. \n2.No explanations. \n3.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. The result must adhere to this json schema:
            {
              "$schema": "https://json-schema.org/draft/2020-12/schema",
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "description": {
                    "type": "string",
                    "description": "A compact, concise description of the variable"
                  },
                  "initialization_left": {
                    "type": "string",
                    "description": "The python variable initialization z3 code that is at left side of the equals. Constants naming convention: capital letters only."
                  },
                  "initialization_right": {
                    "type": "string",
                    "description": "the python variable initialization z3 code that is at right side of the equals as string code block. It must not contain json or dict but z3py code as string"
                  }
                },
                "required": ["description", "initialization"],
                "additionalProperties": false
              }
            }
            The structure must fulfill following requirements:
            1. "<initialization_left> = <initialization_right>" must be valid python z3py code."""
        }
        return system_prompt.get(key)

def _contains_func_that_just_returns_var(func_code: str) -> bool:
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
