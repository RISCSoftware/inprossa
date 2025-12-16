from BinPackingValidator import validate_solution
from structures_utils import *


LOOP_OF_DOOM_MAX_IT = 4
LOOP_OF_DOOM_UNSAT_MAX_IT = 2
MAX_NR_RESETS = 3
N_FAILED_GENERATIONS = 0
FAILED_GENERATIONS = [] # problem desc. indices of failed generation steps
def enter_variable_definitions_feedback_loop(node, raw_definitions, subproblem_description: str = None):
    for _ in range(MAX_NR_RESETS):
        nr_unsat_error = 0
        for i in range(LOOP_OF_DOOM_MAX_IT):
            # Incorrect return format for USE_ALL_AT_ONCE_AND_EXTRACT (# Objects # Constants ...)
            if raw_definitions is None:
                if constants.DEBUG_MODE_ON: print("Incorrect return format for USE_ALL_AT_ONCE_AND_EXTRACT")
                raw_definitions = (llm.send_prompt(
                    system_prompt=f"{get_system_prompt("format_sp")}\n{get_icl()}",
                    prompt="""Incorrect result format, it must be:
´´´python
# --- Objects ---
<solution> 

# --- Constants ---
<solution> 

# --- Decision Variables ---
<solution> 

# --- Constraints ---
<solution> 
´´´ where <solution> is a placeholder for the code. """ +
                           f"""Extend the following python code, include it, but you are strictly forbidden from modify it. Just add the missing sections:
                            ´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n""" +
                           load_sp_file("sp_all_at_once_shorter.txt") +
                           # Input variables (constants) problem description
                           d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
                           # Output variables (decision variables) - problem description
                           d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
                           # Global problem description
                           d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
                           # Sub problem description
                           d2_bin_packing_formalized_problem_description_inst2[3] + "\n" +
                           # Sub problem description
                           d2_bin_packing_formalized_problem_description_inst2[4] + "\n" +
                           # Sub problem description
                           d2_bin_packing_formalized_problem_description_inst2[5],
                    max_tokens=(800 if node.level == 4 else 500)
                ))
            # Extract correct partition of full formulation
            elif constants.USE_ALL_AT_ONCE_AND_EXTRACT:
                match node.level:
                    case 1:
                        if "objects" not in raw_definitions:
                            raw_definitions : dict = create_and_send_prompt_for_all_at_once_and_extract_approach(node)
                            continue
                        raw_definitions = raw_definitions["objects"]
                    case 2:
                        if len(node.variables_and_constants) == 0:
                            if "constants" not in raw_definitions:
                                raw_definitions = create_and_send_prompt_for_all_at_once_and_extract_approach(node)
                                continue
                            raw_definitions = raw_definitions["constants"]
                        else:
                            if "decision variables" not in raw_definitions:
                                raw_definitions = create_and_send_prompt_for_all_at_once_and_extract_approach(node)
                                continue
                            if USE_OPTDSL and "DSList" in raw_definitions["constraints"]:
                                if constants.DEBUG_MODE_ON: print(f"Function parameters must not have type DSList. But must be of a declared type.")
                                raw_definitions = (llm.send_prompt(
                                    system_prompt=get_system_prompt("format_all_sp") + "\n" + get_icl(),
                                    prompt=f"""´´´python 
                                                {node.get_partial_formulation_up_until_now()}
                                                # --- Decision Variables ---
                                                {raw_definitions["decision variables"]}
                                                # --- Constraints ---
                                                {raw_definitions["constraints"]}´´´\n\n""" +
                                           f"Error: function parameters must not have type DSList. But must be of a previously declared type or have a direct type declaration with DSList(length=<length>,elem_type=<type>)." +
                                           "Return the full encoding with constants, decision variables, constraints, objective.",
                                    max_tokens=2000
                                ))
                                raw_definitions = decompose_full_definition(raw_definitions)
                                continue
                            raw_definitions = raw_definitions["decision variables"]
                    case 3:
                        if "objective" not in raw_definitions:
                            raw_definitions = create_and_send_prompt_for_all_at_once_and_extract_approach(node)
                            continue
                        raw_definitions = raw_definitions["objective"]
                    case 4:
                        if "constraints" not in raw_definitions:
                            raw_definitions = create_and_send_prompt_for_all_at_once_and_extract_approach(node, subproblem_description=subproblem_description)
                            continue
                        raw_definitions = raw_definitions["constraints"]
                raw_definitions = node.prepend_section_title(raw_definitions)

            # Send prompt anew, no feedback loop
            if ("NTD" in raw_definitions or
                    "Minizinc Solver Error" in raw_definitions or
                    "Constraints FormatError" in raw_definitions or
                    "Constraints/Objective FormatError" in raw_definitions or
                    nr_unsat_error == LOOP_OF_DOOM_UNSAT_MAX_IT):
                if constants.DEBUG_MODE_ON: print(f"Checking node created for level {node.level}: {raw_definitions} encountered")
                raw_definitions = create_and_send_prompt_for_strictly_iterative_approach(node, subproblem_description=subproblem_description)
                nr_unsat_error = 0
                continue

            # Constants and dec. variables - responses need to be json
            if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2:
                if not is_valid_json(raw_definitions):
                    if constants.DEBUG_MODE_ON: print(f"Checking node created for level {node.level}: Constants not valid json.")
                    raw_definitions = (llm.send_prompt(
                        system_prompt=get_system_prompt("sp"),
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
                if len([item for item in json.loads(raw_definitions) if (item.get("variable_name", "").isupper() if len(node.variables_and_constants) == 0 else item.get("variable_name", "").islower())]) == 0:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=get_system_prompt("sp"),
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

            # Extracted objective and constraints + auxiliary vars
            execution_error = None
            if node.level == 3 or node.level == 4:
                decomposed_code = decompose_full_definition(raw_definitions)
                raw_definitions : str = ""
                if decomposed_code is None:
                    execution_error = "Constraints/Objective FormatError"
                if execution_error is None and decomposed_code is not None and "auxiliary variables" in decomposed_code:
                    raw_definitions += f"\n# --- Auxiliary Variables ---\n{decomposed_code["auxiliary variables"]}"
                if execution_error is None and node.name.lower() in decomposed_code:
                    # Generated code already in partial formulation (duplicate)
                    if decomposed_code[node.name.lower()] in node.get_partial_formulation_up_until_now():
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
                            system_prompt=(get_system_prompt(
                                "json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else (
                                get_system_prompt(
                                    "format_all_sp") if constants.USE_ALL_AT_ONCE_AND_EXTRACT else get_system_prompt(
                                    "format_sp"))) + "\n" + get_icl(),
                            prompt=f"´´´python\n" +
                                   (f"from z3 import * \n" if not constants.USE_OPTDSL else "") +
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
                        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
                            raw_definitions = decompose_full_definition(raw_definitions)

            # Check for syntactical correctness and handle execution error, if no "Constraints/Objective FormatError" has occurred yet
            if execution_error is None:
                execution_error = check_executability(node, raw_definitions)
            # Handle execution error
            if execution_error is not None:
                if constants.DEBUG_MODE_ON: print(f"Checking node created for level {node.level} not executable: {execution_error}\n")
                if ("NTD" in raw_definitions or
                        "Constraints FormatError" in raw_definitions or
                        "Constraints/Objective FormatError" in raw_definitions):
                    if constants.DEBUG_MODE_ON: print(
                        f"Checking node created for level {node.level}: {raw_definitions} encountered")
                    raw_definitions = create_and_send_prompt_for_strictly_iterative_approach(node,
                                                                                             subproblem_description=subproblem_description)
                    continue
                elif "Syntax Error" in execution_error:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=(get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else (get_system_prompt("format_all_sp") if constants.USE_ALL_AT_ONCE_AND_EXTRACT else get_system_prompt("format_sp"))) + "\n" + get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not constants.USE_OPTDSL else "") +
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
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
                        raw_definitions = decompose_full_definition(raw_definitions)
                elif "Semantic Error" in execution_error:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=(get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else (get_system_prompt("format_all_sp") if constants.USE_ALL_AT_ONCE_AND_EXTRACT else get_system_prompt("format_sp"))) + "\n" + get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not constants.USE_OPTDSL else "") +
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
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
                        raw_definitions = decompose_full_definition(raw_definitions)
                    nr_unsat_error += 1
                elif not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=( get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else get_system_prompt("format_sp")) + get_icl(),
                        prompt=f"´´´\njson\n{raw_definitions}´´´\n\n" +
                               f"The Json code above contains an error: {execution_error}" +
                               "Given this error message, improve the mentioned lines of the \"initialization\" and/or the \"variable_type\" field according to the error message, nothing else."
                               "Return the given json code with the corrections. Do not copy the in-context-training example. Do not return \"NTD\".",
                        max_tokens=800
                    ))
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                        raw_definitions)
                else:
                    raw_definitions = (llm.send_prompt(
                        system_prompt=( get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else (get_system_prompt("format_all_sp") if constants.USE_ALL_AT_ONCE_AND_EXTRACT else get_system_prompt("format_sp"))) + get_icl(),
                        prompt=f"´´´python\n" +
                               (f"from z3 import * \n" if not constants.USE_OPTDSL else "") +
                               f"{node.get_partial_formulation_up_until_now()}\n"
                               f"\n# --- Incorrect Code --- \n{raw_definitions}´´´\n\n" +
                               f"The section above contains an error: {execution_error}" +
                               "Given this error message, improve the mentioned lines of the section \"# --- Incorrect Code ---\" the pythonic OptDSL code snippet according to the error message, nothing else. Do not change the semantics of the code. Do not return NTD."
                               "Return your answer in the format\n" +
                               "´´´python\n" +
                               "# --- Incorrect Code ---\n" +
                               "<corrected code>\n" +
                               "\n´´´, where <corrected code> all lines underneath \"# --- Incorrect Code ---\" with the corrections.",
                        max_tokens=(1500 if node.level>=4 else 800)
                    ))
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                        raw_definitions)
            else:
                # Safety check: check if DSInts are correctly initialized according to lb and ub
                if node. level == 3 or node. level == 4 or node. level == 5:
                    pattern = re.compile(
                        r"""^\s*(?P<var>[A-Za-z_]\w*)\s*:\s*[A-Za-z_]\w*\s*\(
                             (?:.*?(?:\blb\s*=\s*(?P<lb>-?\d+))?)?
                             (?:.*?(?:\bub\s*=\s*(?P<ub>-?\d+))?)?
                           \)\s*=\s*(?P<val>-?\d+)\s*$""",
                        re.VERBOSE
                    )
                    for i, line in enumerate(raw_definitions.splitlines()):
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
                                                  get_system_prompt(
                                                      "json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else get_system_prompt(
                                                      "format_sp")) + "\n" + get_icl(),
                                prompt=f"´´´ python\n" +
                                       (f"from z3 import * \n" if not constants.USE_OPTDSL else "") +
                                       f"\n# --- Incorrect Code --- \n{raw_definitions} ´´´\n\n" +
                                       f"In line {i} a decision variable DSInt is not initialized incorrectly. Correct the initialization to lb <= {var} <= ub, {line}\n"
                                ,max_tokens=(800 if node.level == 4 else 500)
                            ))
                            if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                                raw_definitions)
                # Safety check: Prevent false-positive exec-run-through by sneakily never calling function
                if node.level == 4:
                    not_twice_appearing_func = check_functions_appear_twice(raw_definitions)
                    if len(not_twice_appearing_func) > 0:
                        if constants.DEBUG_MODE_ON: print(f"The following functions are defined but never called, {not_twice_appearing_func}")
                        raw_definitions = (llm.send_prompt(
                            system_prompt=(
                                get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else get_system_prompt("format_sp")) + "\n" + get_icl(),
                            prompt=f"´´´ python\n" +
                                   (f"from z3 import * \n" if not constants.USE_OPTDSL else "") +
                                   f"\n{node.get_partial_formulation_up_until_now()}\n{raw_definitions} ´´´\n\n" +
                                   f"The following functions are defined but never called, {not_twice_appearing_func}" +
                                   "Add the call of the mentioned functions to the code with the respective parameters. Do not return exactly the given code snippet.",
                            max_tokens=(800 if node.level == 4 else 500)
                        ))
                        if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                            raw_definitions)
                        continue
                return raw_definitions

        # Attempt reset
        llm.send_prompt_with_model_id(
            model_id=("qwen.qwen3-coder-30b-a3b-v1:0" if llm.model_id == "qwen.qwen3-coder-480b-a35b-v1:0" else "qwen.qwen3-coder-480b-a35b-v1:0"),
            #model_id=("eu.amazon.nova-lite-v1:0" if llm.model_id == "eu.amazon.nova-pro-v1:0" else "eu.amazon.nova-pro-v1:0"),
            #model_id=("eu.anthropic.claude-3-5-sonnet-20240620-v1:0" if llm.model_id == "eu.anthropic.claude-3-7-sonnet-20250219-v1:0" else "eu.anthropic.claude-3-7-sonnet-20250219-v1:0"),
            #model_id=("openai.gpt-oss-120b-1:0" if llm.model_id == "eu.amazon.nova-pro-v1:0" else "eu.amazon.nova-pro-v1:0"),
            prompt="",
            max_tokens=1
        )
        create_and_send_prompt_for_strictly_iterative_approach(node, subproblem_description=subproblem_description)
    return ""

def create_and_send_prompt_for_strictly_iterative_approach(node: TreeNode, execution_message : str = None, subproblem_description : str = None):
    response = ""
    '''
    # All at once
    response = llm.send_prompt(
        system_prompt=f"{get_system_prompt("format_sp")}\n{get_icl()}",
        prompt=load_sp_file("sp_all_at_once_shorter.txt") +
               # Input variables (constants) problem description
               d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
               # Output variables (decision variables) - problem description
               d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
               # Global problem description
               d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
               # Sub problem description
               d2_bin_packing_formalized_problem_description_inst2[3] + "\n" +
               # Sub problem description
               d2_bin_packing_formalized_problem_description_inst2[4] + "\n" +
               # Sub problem description
               d2_bin_packing_formalized_problem_description_inst2[5],
        max_tokens=2500
    )
    '''
    #if llm.model_id == "qwen.qwen3-coder-480b-a35b-v1:0":
    #    llm.model_id = "qwen.qwen3-coder-30b-a3b-v1:0"
    #else:
    #    llm.model_id = "qwen.qwen3-coder-480b-a35b-v1:0"
    # TEXTUAL DESCRIPTION
    if node.level == 0:
        response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("text_sp")}",
            prompt= load_sp_file("sp_text_repr.txt") +
            # Input variables (constants) problem description
            d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description_inst2[3],
            max_tokens=800
        )
    # OBJECTS (datatypes)
    elif node.level == 1:
        if execution_message is not None:
            response = llm.send_prompt(
                system_prompt=f"{get_system_prompt("sp")}\n{get_icl()}",
                prompt=
                # Send problematic code + execution_error_message from a previously failed run
                f"{response}\n\nTask:\n{execution_message}\nCorrect this error.")
        else:
            response = llm.send_prompt(
                system_prompt=f"{get_system_prompt("format_sp")}\n{get_icl()}",
                prompt=
                        # General
                        "Given the problem below:\n" +
                        "------------\n" +
                        # Input variables (constants) problem description
                        d2_bin_packing_formalized_problem_description_inst2[0]  + "\n" +
                        # Output variables (decision variables) - problem description
                        d2_bin_packing_formalized_problem_description_inst2[1]  + "\n" +
                        # Global problem description
                        d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
                        # Sub problem description
                        d2_bin_packing_formalized_problem_description_inst2[3] +
                        "------------\n" +
                        # Component specific instr.: object types, data types
                        f"Task: {load_sp_file("sp_objects.txt")}"
                ,max_tokens=1000
            )
    # CONSTANTS and DECISION VARIABLES
    elif node.level == 2:
        # CONSTANTS
        if isinstance(node, VariablesConstantsNode) and len(node.variables_and_constants) == 0:
            response = llm.send_prompt(
                system_prompt=f"{get_system_prompt("json_sp")}\n{get_icl()}",
                prompt=  # General instr.
                "Given the problem:\n" +
                "------------\n" +
                # Input variables (constants) problem description
                d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
                "------------\n" +
                # Given object types
                f"""Given the following python code snippet containing object types:
                ´´´python\n{"form z3 import *" if not USE_OPTDSL else ""}
                {node.get_partial_formulation_up_until_now()}´´´\n""" +
                # Component specific instr.: constants
                #f"\nTask:Take this text description of required constants for an optimization problem: {text_representation}",
                f"\nYour priority is to fulfill this task: {load_sp_file("sp_constants.txt")}\n"
                ,max_tokens=1000
            )
        else:
            response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("json_sp")}\n{get_icl()}",
            prompt= # General instr.
            "Given the problem:\n" +
            "------------\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description_inst2[1] +
            "------------\n" +
            # Given object types, constants:
            f"""Given the following python code snippet containing datatypes, constants:
            ´´´python\n{"form z3 import *" if not USE_OPTDSL else ""}
            {node.get_partial_formulation_up_until_now()}´´´\n""" +
            # Component specific instr.: decision variables
            f"\nYour priority is to fulfill this task: {load_sp_file("sp_decision_variables.txt")}\n"
            ,max_tokens=1000
        )
    # OBJ FUNCTION
    elif node.level == 3:
        response = llm.send_prompt(
        system_prompt=f"{get_system_prompt("format_sp")}\n{get_icl()}",
        prompt=
            "Given the problem:\n" +
            "------------\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
            "------------\n" +
            #"Given following constants and decision variables:\n" +
            f"""Given the following python code snippet containing datatypes, constants, decision variables and objective func.:
´´´python {"form z3 import *" if not USE_OPTDSL else ""}
{node.get_partial_formulation_up_until_now()}´´´\n""" +
#json.dumps(constants_variables_node.get_as_codeblock()) + "\n" +
            # Component specific instr.: obj. function
f"\nYour priority is to fulfill this task: :\n{load_sp_file("sp_obj_function.txt")}\n"
        ,max_tokens=800
    )
    # CONSTRAINT
    elif node.level == 4:
        if subproblem_description is None:
            raise ValueError("Subproblem description cannot be None")

        response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("format_sp")}\n{get_icl()}",
            prompt=
            "Given the problem:\n" +
            "------------\n" +
            # Sub problem description
            subproblem_description +
            "------------\n" +
            f"""Given the following python code snippet containing datatypes, constants, decision variables and objective func.:
            ´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n""" +
            f"\nTask:\n{load_sp_file("sp_constraints.txt")}\n"
            ,max_tokens=1000
        )
    return response

def create_and_send_prompt_for_all_at_once_and_extract_approach(node: TreeNode, subproblem_description : str = None):
    response = ""
    # TEXTUAL DESCRIPTION
    if node.level == 0:
        response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("text_sp")}",
            prompt= load_sp_file("sp_text_repr.txt") +
            # Input variables (constants) problem description
            d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description_inst2[3] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description_inst2[4] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description_inst2[5],
            max_tokens=800
        )
    # OBJECTS (datatypes)
    elif node.level == 1:
        response = llm.send_prompt(
            #system_prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}",
            prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}" +
                   load_sp_file("sp_all_at_once_shorter.txt") +
                   # Input variables (constants) problem description
                   d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
                   # Output variables (decision variables) - problem description
                   d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
                   # Global problem description
                   d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
                   # Sub problem description
                   d2_bin_packing_formalized_problem_description_inst2[3] + "\n" +
                   # Sub problem description
                   d2_bin_packing_formalized_problem_description_inst2[4] + "\n" +
                   # Sub problem description
                   d2_bin_packing_formalized_problem_description_inst2[5],
            max_tokens=2500
        )
    # CONSTANTS and DECISION VARIABLES
    elif node.level == 2:
        # CONSTANTS
        if isinstance(node, VariablesConstantsNode) and len(node.variables_and_constants) == 0:
            response = llm.send_prompt(
                #system_prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}",
                prompt=  # General instr.
                f"{get_system_prompt("format_all_sp")}\n{get_icl()}" +
                "Given the problem blow:\n" +
                # Given datatypes
                (f"Extend the following python code according to the decribed problem, include and use the given section objects but you are strictly forbidden from extending them. Below add only sections constants, decision variables and contraints yourself:´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n") +
                # All-at-once instruction
                load_sp_file("sp_all_at_once_shorter.txt") +
                # Input variables (constants) problem description
                d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
                # Output variables (decision variables) - problem description
                d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
                # Global problem description
                d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description_inst2[3] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description_inst2[4] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description_inst2[5]
                ,max_tokens=2500
            )
        else:
            response = llm.send_prompt(
            #system_prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}",
            prompt= # General instr.
            f"{get_system_prompt("format_all_sp")}\n{get_icl()}" +
            "Given the problem blow:\n" +
            # Given datatypes
            (f"Extend the following python code, include and use the given sections objects or constants but you are strictly forbidden from extending them. Below add only sections decision variables and contraints yourself:´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n") +
            # All-at-once instruction
            load_sp_file("sp_all_at_once_shorter.txt") +
            # Input variables (constants) problem description
            d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description_inst2[3] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description_inst2[4] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description_inst2[5]
            ,max_tokens=2500
        )
    # OBJ FUNCTION
    elif node.level == 3:
        response = llm.send_prompt(
        #system_prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}",
        prompt=# General instr.
                # Given datatypes, constants and decision variables
        f"{get_system_prompt("format_all_sp")}\n{get_icl()}" +
        (f"Extend the following python code, include but do not extend the sections objects, constants and decision variables:´´´python\n" +
        (f"from z3 import * \n" if not constants.USE_OPTDSL else "") +
        f"\n{node.get_partial_formulation_up_until_now()}´´´\n") +
        # All-at-once instruction
        load_sp_file("sp_all_at_once_shorter.txt") +
        # Input variables (constants) problem description
        d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
        # Output variables (decision variables) - problem description
        d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
        # Global problem description
        d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
        # Sub problem description
        d2_bin_packing_formalized_problem_description_inst2[3] + "\n" +
        # Sub problem description
        d2_bin_packing_formalized_problem_description_inst2[4] + "\n" +
        # Sub problem description
        d2_bin_packing_formalized_problem_description_inst2[5],
        max_tokens=2500
    )
    # CONSTRAINT
    elif node.level == 4:
        if subproblem_description is None:
            raise ValueError("Subproblem description cannot be None")

        response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}",
            prompt=# General instr.
            f"{get_system_prompt("format_all_sp")}\n{get_icl()}" +
            f"""Extend the following python code, include and use the given sections objects, constants and decision variables, but you are strictly forbidden from extending them. Add constraints, that are not defined yet:
            ´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n""" +
            # All-at-once instruction
            load_sp_file("sp_all_at_once_shorter.txt") +
            # Input variables (constants) problem description
            d2_bin_packing_formalized_problem_description_inst2[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description_inst2[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description_inst2[2] + "\n" +
            # Sub problem description
            subproblem_description,
            max_tokens=2500
        )
    return decompose_full_definition(response)

# Sends correct partial formulations generated by LLM, in the hopes the feedback creates a learning effect
def send_feedback(node: TreeNode, syntax: bool = True):
    if syntax:
        if DEBUG_MODE_ON: print("Sending feedback for a partial job well done.")
        _ = llm.send_prompt(
            prompt=
            f"""The following is an example for a syntactically valid {"full" if node.level == 4 else "partial"} formulation of a optimization problem in OptDSL.
        Learn from it the syntax of OptDSL, not its semantics. Apply the syntax knowledge in the future.
        ´´´ python
        {node.get_partial_formulation_up_until_now()}
        ´´´""",
            max_tokens=1)
    # semantics
    else:
        if DEBUG_MODE_ON: print("Sending feedback for a partial job well done.")
        _ = llm.send_prompt(
            prompt=
            f"""The following is an example for a, maybe not optimal, but syntactically valid {"full" if node.level == 4 else "partial"} OptDSL formulation of the optimization problem:
        {d2_bin_packing_formalized_problem_description_inst2}           
        Learn from it its syntax and semantics of OptDSL. Apply the syntax knowledge in the future. Provide diverse encodings in the future.
        ´´´ python
        {node.get_partial_formulation_up_until_now()}
        ´´´""",
            max_tokens=1)

def get_icl():
    if USE_OPTDSL:
        return load_sp_file("ICL_example_3.txt")
    else:
        return load_sp_file("ICL_datatypes.txt")

def get_system_prompt(key: str):
    key = f"{constants.CHOSEN_LANGUAGE}_{key}"
    if constants.USE_OPTDSL:
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

# --- Constants ---
<solution> 

# --- Decision Variables ---
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

        # --- Constants ---
        <solution> 

        # --- Decision Variables ---
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

d2_bin_packing_formalized_problem_description_inst1 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 5,
        "BOX_WIDTH": 10,
        "ITEMS": [
            {
                "name": "item1",
                "width": 10,
                "height": 5
            },
            {
                "name": "item2",
                "width": 2,
                "height": 2
            }
        ]
    }
    ´´´
    """,
    # Output
    """
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "is_objective": true,
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "is_objective": false,
            "mandatory_variable_name": "item_box_assignments",
            "suggested_shape": "array"
        },
        {
            "description": "Position x and y of each item within box",
            "is_objective": false,
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array"
        }
    ]
    ´´´
    """,
    # Global description
    """
    Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box 
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.
    """,
    # Subproblem description - part 1
    """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 2
    """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 3
    """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """
    ]
d2_bin_packing_formalized_problem_description_inst2 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 6,
        "BOX_WIDTH": 10,
        "ITEMS": [
            {
                "name": "item1",
                "width": 4,
                "height": 3
            },
            {
                "name": "item2",
                "width": 3,
                "height": 2
            },
            {
                "name": "item3",
                "width": 5,
                "height": 3
            },
            {
                "name": "item4",
                "width": 2,
                "height": 4
            },
            {
                "name": "item5",
                "width": 3,
                "height": 3
            },
            {
                "name": "item6",
                "width": 5,
                "height": 2
            }
        ]
    }
    ´´´
    """,
    # Output
    """
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "is_objective": true,
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "is_objective": false,
            "mandatory_variable_name": "item_box_assignments",
            "suggested_shape": "array"
        },
        {
            "description": "Position x and y of each item within box",
            "is_objective": false,
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array"
        }
    ]
    ´´´
    """,
    # Global description
    """
    Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box 
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.
    """,
    # Subproblem description - part 1
    """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 2
    """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 3
    """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """
    ]
d2_bin_packing_formalized_problem_description_inst3 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 5,
        "BOX_WIDTH": 12,
        "ITEMS": [
            {
                "name": "item1",
                "width": 4,
                "height": 3
            },
            {
                "name": "item2",
                "width": 1,
                "height": 2
            },
            {
                "name": "item3",
                "width": 5,
                "height": 3
            },
            {
                "name": "item4",
                "width": 4,
                "height": 2
            },
            {
                "name": "item5",
                "width": 1,
                "height": 3
            },
            {
                "name": "item6",
                "width": 5,
                "height": 2
            },
            {
                "name": "item7",
                "width": 9,
                "height": 5
            },
            {
                "name": "item8",
                "width": 3,
                "height": 5
            },
            {
                "name": "item9",
                "width": 5,
                "height": 1
            }
        ]
    }
    ´´´
    """,
    # Output
    """
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "is_objective": true,
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "is_objective": false,
            "mandatory_variable_name": "item_box_assignments",
            "suggested_shape": "array"
        },
        {
            "description": "Position x and y of each item within box",
            "is_objective": false,
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array"
        }
    ]
    ´´´
    """,
    # Global description
    """
    Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box 
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.
    """,
    # Subproblem description - part 1
    """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 2
    """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 3
    """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """
    ]
d2_bin_packing_formalized_problem_description_inst4 = [
    # Input
    """
    ´´´ json
    {
        "BOX_HEIGHT": 12,
        "BOX_WIDTH": 5,
        "ITEMS": [
            {
                "name": "item1",
                "width": 3,
                "height": 4
            },
            {
                "name": "item2",
                "width": 1,
                "height": 2
            },
            {
                "name": "item3",
                "width": 5,
                "height": 4
            },
            {
                "name": "item4",
                "width": 2,
                "height": 4
            },
            {
                "name": "item5",
                "width": 1,
                "height": 3
            },
            {
                "name": "item6",
                "width": 5,
                "height": 9
            },
            {
                "name": "item7",
                "width": 5,
                "height": 3
            },
            {
                "name": "item8",
                "width": 5,
                "height": 1
            }
        ]
    }
    ´´´
    """,
    # Output
    """
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "is_objective": true,
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "is_objective": false,
            "mandatory_variable_name": "item_box_assignments",
            "suggested_shape": "array"
        },
        {
            "description": "Position x and y of each item within box",
            "is_objective": false,
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array"
        }
    ]
    ´´´
    """,
    # Global description
    """
    Global problem:
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - the assigment of each item into a box 
        - the position (x and y) of each item within its assigned box. x and y have minimum values 0 and maximum infinity.
    """,
    # Subproblem description - part 1
    """Sub problem definition - items that go in the bin - part 1:
    The items that are put into a box, must fit exactly inside the box and must not stick out of the box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 2
    """Sub problem definition - items that go in the bin - part 2:
    Taking the given items that are put into a box, they must not overlap.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """,
    # Subproblem description - part 3
    """Sub problem definition - items that go in the bin - part 3:
    Taking the given items that are put into a box, one item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """
    ]
'''
knapsack = """This problem involves a collection of items, where each have a value and a weight. We have a scissor with value 15
and weight 12, a book with value 50 and weight 70, a laptop with value 80 and weight 100, a phone with value 80
and weight 20, a ruler with value 20 and weight 12, a pen with value 25 and weight 5. One or more items are chosen
and put into a schoolbag. The goal is to decide which items are chosen that a maximal accumulated value is achieved.
Sub problem definition - items that go in the bag:
In the bag only go items from the given collection, such that the cumulative weight of all chosen items must never exceed the maximum allowed weight of 110.
At the same time, we want to achieve a maximum of accumulated item value. The result are the chosen items."""
'''


def build_up_formulation_iteratively(llm):
    N_FAILED_GENERATIONS = 0

    # Root node - get textual description
    root_node = RootNode(save_nodes=False)
    '''response = create_and_send_prompt(root_node)
    root_node.set_content(response)
    '''
    # Query object types, data types
    datatypes_node = ObjectsNode(parent=root_node)
    if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
        response = create_and_send_prompt_for_all_at_once_and_extract_approach(datatypes_node)
    else:
        response = create_and_send_prompt_for_strictly_iterative_approach(datatypes_node)
    response = enter_variable_definitions_feedback_loop(datatypes_node, response)
    datatypes_node.set_content(response)
    #send_feedback(datatypes_node)
    print(f"*** Response, global problem/datatypes: {response}\n")
    if response == "":
        N_FAILED_GENERATIONS += 1
        print("Creating object types failed!")

    ### Query constants ######################################################################################
    constants_variables_node = VariablesConstantsNode(parent=datatypes_node)
    successfully_added = False
    i = 0
    while not successfully_added and i < LOOP_OF_DOOM_MAX_IT:
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            response = create_and_send_prompt_for_all_at_once_and_extract_approach(constants_variables_node)
        else:
            response = create_and_send_prompt_for_strictly_iterative_approach(constants_variables_node)
        response = enter_variable_definitions_feedback_loop(constants_variables_node, response)
        successfully_added = constants_variables_node.set_constants(response)
        i += 1
    #send_feedback(constants_variables_node)
    print(f"*** Response, constants: {response}\n")
    if response == "" or i == LOOP_OF_DOOM_MAX_IT:
        N_FAILED_GENERATIONS += 1
        print("Creating constants failed!")

    ### Query decision variables ######################################################################################
    successfully_added = False
    i = 0
    while not successfully_added and i < LOOP_OF_DOOM_MAX_IT:
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            response = create_and_send_prompt_for_all_at_once_and_extract_approach(constants_variables_node)
        else:
            response = create_and_send_prompt_for_strictly_iterative_approach(constants_variables_node)
        response = enter_variable_definitions_feedback_loop(constants_variables_node, response)
        successfully_added = constants_variables_node.set_variables(response, d2_bin_packing_formalized_problem_description_inst2[1])
        i += 1
    #send_feedback(constants_variables_node)
    print(f"*** Response (decision) variables: {response}\n")
    if response == "" or i == LOOP_OF_DOOM_MAX_IT:
        N_FAILED_GENERATIONS += 1
        print("Creating decision variables failed!")

    # Wiser to use for z3 only
    # Query objective function
    obj_function_node = ObjectiveNode(parent=constants_variables_node)
    if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
        response = create_and_send_prompt_for_all_at_once_and_extract_approach(obj_function_node)
    else:
        response = create_and_send_prompt_for_strictly_iterative_approach(obj_function_node)
    response = enter_variable_definitions_feedback_loop(obj_function_node, response, d2_bin_packing_formalized_problem_description_inst2[2])

    # Create connection between objective and given objective decision variable
    objective_var_name = [variable["mandatory_variable_name"] for variable in json.loads(
        remove_programming_environment(d2_bin_packing_formalized_problem_description_inst2[1])) if
                          variable["is_objective"]][0]

    obj_function_node.set_content(f"\nobjective = {objective_var_name}\n" + response)
    print(f"*** Obj. function: {response}\n")
    if response == "":
        N_FAILED_GENERATIONS += 1
        print("Creating objective function failed!")
    send_feedback(obj_function_node)

    # Query constraints
    constraints_node = ConstraintsNode(parent=obj_function_node) #if USE_OPTDSL else ConstraintsNode(parent=obj_function_node)
    for i in range(3,len(d2_bin_packing_formalized_problem_description_inst2)):
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            response = create_and_send_prompt_for_all_at_once_and_extract_approach(constraints_node, subproblem_description=d2_bin_packing_formalized_problem_description_inst2[i])
        else:
            response = create_and_send_prompt_for_strictly_iterative_approach(constraints_node, subproblem_description=d2_bin_packing_formalized_problem_description_inst2[i])
        response = enter_variable_definitions_feedback_loop(constraints_node, response, subproblem_description=d2_bin_packing_formalized_problem_description_inst2[i])
        constraints_node.set_content(response)
        print(f"*** Constraints: {response}\n")
        if response == "":
            N_FAILED_GENERATIONS += 1
            print("Creating constraints failed!")
        if i == len(d2_bin_packing_formalized_problem_description_inst2)-1: send_feedback(constraints_node)
        
    # Validate minizinc solution
    task = {
        "input": json.loads(remove_programming_environment(d2_bin_packing_formalized_problem_description_inst2[0])),
        "output": json.loads(remove_programming_environment(d2_bin_packing_formalized_problem_description_inst2[1]))
    }
    try:
        validate_solution(constraints_node.solution_model, task)
    except AssertionError as e:
        validation_res = f"Failed to validate solution: {e}"
    except Exception:
        validation_res = f"Evaluation failed."
    else:
        validation_res = f"Successfully validated solution."
    constraints_node.save_child_to_file(validation_res)

    if constants.DEBUG_MODE_ON: print(f"""Full formulation:
{constraints_node.get_partial_formulation_up_until_now()}
**************************
Total failed steps: {N_FAILED_GENERATIONS}, {constraints_node.n_failed_generations}
Objective value: {constraints_node.objective_val}
Solve time (sec): {constraints_node.solve_time}
Solution model: {constraints_node.solution_model}
{validation_res}
**************************
----------------------------------------------------------------------------""")
    if N_FAILED_GENERATIONS == 0 and "Successfully" in validation_res and constraints_node.objective_val is not None:
        send_feedback(constraints_node, syntax=False)


if __name__ == "__main__":
    llm = constants.LLM
    build_up_formulation_iteratively(llm)
