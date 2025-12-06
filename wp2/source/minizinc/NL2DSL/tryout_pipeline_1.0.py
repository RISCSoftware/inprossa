import constants
from structures_utils import *


LOOP_OF_DOOM_COUNTER = 0
LOOP_OF_DOOM_MAX_IT = 5
MAX_NR_RESETS = 3
def enter_variable_definitions_feedback_loop(node, raw_definitions, subproblem_description: str = None):
    for _ in range(MAX_NR_RESETS):
        for i in range(LOOP_OF_DOOM_MAX_IT):
            # Incorrect return format for USE_ALL_AT_ONCE_AND_EXTRACT (# Objects # Constants ...)
            if raw_definitions is None:
                if constants.DEBUG_MODE_ON: print("Incorrect return format for USE_ALL_AT_ONCE_AND_EXTRACT")
                raw_definitions = remove_programming_environment(llm.send_prompt(
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
                           d2_bin_packing_formalized_problem_description[0] + "\n" +
                           # Output variables (decision variables) - problem description
                           d2_bin_packing_formalized_problem_description[1] + "\n" +
                           # Global problem description
                           d2_bin_packing_formalized_problem_description[2] + "\n" +
                           # Sub problem description
                           d2_bin_packing_formalized_problem_description[3] + "\n" +
                           # Sub problem description
                           d2_bin_packing_formalized_problem_description[4] + "\n" +
                           # Sub problem description
                           d2_bin_packing_formalized_problem_description[5],
                    max_tokens=(800 if node.level == 4 else 500)
                ), node=node)
            # Extract correct partition of full formulation
            elif constants.USE_ALL_AT_ONCE_AND_EXTRACT:
                match node.level:
                    case 1:
                        if "objects" not in raw_definitions:
                            raw_definitions = create_and_send_prompt_for_all_at_once_and_extract_approach(node)
                            continue
                        raw_definitions = raw_definitions["objects"]
                    case 2:
                        if node.content == "":
                            if "constants" not in raw_definitions:
                                raw_definitions = create_and_send_prompt_for_all_at_once_and_extract_approach(node)
                                continue
                            raw_definitions = raw_definitions["constants"]
                        else:
                            if "decision variables" not in raw_definitions:
                                raw_definitions = create_and_send_prompt_for_all_at_once_and_extract_approach(node)
                                continue
                            if USE_OPTDSL and "DSList" in raw_definitions["constraints"]:
                                if constants.DEBUG_MODE_ON: print(f"Error: function parameters must not have type DSList. But must be of a declared type.")
                                raw_definitions = remove_programming_environment(llm.send_prompt(
                                    system_prompt=get_system_prompt("format_all_sp") + "\n" + get_icl(),
                                    prompt=f"""´´´from z3 import * 
                                                {node.get_partial_formulation_up_until_now()}
                                                # --- Decision Variables ---
                                                {raw_definitions["decision variables"]}
                                                # --- Constraints ---
                                                {raw_definitions["constraints"]}´´´\n\n""" +
                                           f"Error: function parameters must not have type DSList. But must be of a previously declared type or have a direct type declaration with DSList(length=<length>,elem_type=<type>)." +
                                           "Return the full encoding with constants, decision variables, constraints, objective.",
                                    max_tokens=2000
                                ), node=node)
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

            if "NTD" in raw_definitions:
                if constants.DEBUG_MODE_ON: print(f"Checking node created for level {node.level}: NTD encountered")
                raw_definitions = create_and_send_prompt_for_strictly_iterative_approach(node)
                continue

            # Constants and dec. variables - responses need to be json format for USE_ALL_AT_ONCE_AND_EXTRACT
            if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 and not is_valid_json(raw_definitions):
                if constants.DEBUG_MODE_ON: print(f"Checking node created for level {node.level}: Constants not valid json.")
                raw_definitions = remove_programming_environment(llm.send_prompt(
                    system_prompt=get_system_prompt("sp"),
                    prompt=raw_definitions + "\n\n" +
                            """The code above is either not json or incorrect json. Correct it to compilable json code.
                            Return you answer in the following format:
                            [{
                                "description":<description>,
                                "variable_name":<variable_name>,
                                "initialization":<initialization>
                            }]
                            The structure must fulfill following requirements:
                            1. <variable_name> is the python variable described in description. The variable name that represents a variable that will later be used. Constants naming convention: capital letters only.
                            2. <initialization> is the python variable declaration and initialization code block, fully with assignments, of the variable in variable field.
                            3. <description> is a placeholder for a compact, concise description of the variable.
                            4. No additional properties allowed.""",
                    max_tokens=1000
                ))
                continue
            execution_error = check_executability(node, raw_definitions)
            if execution_error is not None:
                if constants.DEBUG_MODE_ON: print(f"Checking node created for level {node.level} not executable: Error: {execution_error}\n")
                if "Syntax Error" in execution_error:
                    raw_definitions = remove_programming_environment(llm.send_prompt(
                        system_prompt=(get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else (get_system_prompt("format_all_sp") if constants.USE_ALL_AT_ONCE_AND_EXTRACT else get_system_prompt("format_sp"))) + "\n" + get_icl(),
                        prompt=f"´´´from z3 import * \n{raw_definitions}´´´\n\n" +
                               f"The section above contains an error: {execution_error}" +
                               "You must rewrite the problematic code. Do not return exactly the given code snippet.",
                        max_tokens=(800 if node.level == 4 else 500)
                    ), node=node)
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                        raw_definitions)
                elif not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2:
                    raw_definitions = remove_programming_environment(llm.send_prompt(
                        system_prompt=( get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else get_system_prompt("format_sp")),
                        prompt=f"{raw_definitions}\n\n" +
                               f"The section above contains an error: {execution_error}" +
                               "You must rewrite the problematic code. Do not return exactly the given code snippet.",
                        max_tokens=(800 if node.level>=4 else 500)
                    ), node=node)
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                        raw_definitions)
                else:
                    raw_definitions = remove_programming_environment(llm.send_prompt(
                        system_prompt=( get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else (get_system_prompt("format_all_sp") if constants.USE_ALL_AT_ONCE_AND_EXTRACT else get_system_prompt("format_sp"))) + get_icl(),
                        prompt=f"´´´from z3 import * \n{node.get_partial_formulation_up_until_now()}\n{raw_definitions}´´´\n\n" +
                               f"The section above contains an error: {execution_error}" +
                               "You must rewrite the problematic code. Do not return exactly the given code snippet.",
                        max_tokens=(1500 if node.level>=4 else 500)
                    ), node=node)
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                        raw_definitions)
            else:
                # Safety check: Prevent false-positive exec-run-through by sneakily never calling function
                not_twice_appearing_func = check_functions_appear_twice(raw_definitions)
                if len(not_twice_appearing_func) > 0:
                    if constants.DEBUG_MODE_ON: print(f"The following functions are defined but never called, {not_twice_appearing_func}")
                    raw_definitions = remove_programming_environment(llm.send_prompt(
                        system_prompt=(
                            get_system_prompt("json_sp") if not constants.USE_ALL_AT_ONCE_AND_EXTRACT and node.level == 2 else get_system_prompt("format_sp")) + "\n" + get_icl(),
                        prompt=f"´´´from z3 import * \n{node.get_partial_formulation_up_until_now()}\n{raw_definitions} ´´´\n\n" +
                               f"The following functions are defined but never called, {not_twice_appearing_func}" +
                               "Add the call of the mentioned functions to the code with the respective parameters. Do not return exactly the given code snippet.",
                        max_tokens=(800 if node.level == 4 else 500)
                    ), node=node)
                    if constants.USE_ALL_AT_ONCE_AND_EXTRACT: raw_definitions = decompose_full_definition(
                        raw_definitions)
                    continue
                return raw_definitions
        # Attempt reset
        llm.send_prompt_with_model_id(
            model_id=("eu.amazon.nova-lite-v1:0" if "eu.amazon.nova-pro-v1:0" else ("eu.amazon.nova-pro-v1:0" if "eu.amazon.nova-lite-v1:0" else "eu.amazon.nova-lite-v1:0")),
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
               d2_bin_packing_formalized_problem_description[0] + "\n" +
               # Output variables (decision variables) - problem description
               d2_bin_packing_formalized_problem_description[1] + "\n" +
               # Global problem description
               d2_bin_packing_formalized_problem_description[2] + "\n" +
               # Sub problem description
               d2_bin_packing_formalized_problem_description[3] + "\n" +
               # Sub problem description
               d2_bin_packing_formalized_problem_description[4] + "\n" +
               # Sub problem description
               d2_bin_packing_formalized_problem_description[5],
        max_tokens=2500
    )
    '''
    # TEXTUAL DESCRIPTION
    if node.level == 0:
        response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("text_sp")}",
            prompt= load_sp_file("sp_text_repr.txt") +
            # Input variables (constants) problem description
            d2_bin_packing_formalized_problem_description[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description[2] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description[3],
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
                        "Given the problem blow:\n" +
                        # Component specific instr.: object types, data types
                        f"Task: {load_sp_file("sp_objects.txt")}" +
                        # Input variables (constants) problem description
                        d2_bin_packing_formalized_problem_description[0]  + "\n" +
                        # Output variables (decision variables) - problem description
                        d2_bin_packing_formalized_problem_description[1]  + "\n" +
                        # Global problem description
                        d2_bin_packing_formalized_problem_description[2] + "\n" +
                        # Sub problem description
                        d2_bin_packing_formalized_problem_description[3],
                max_tokens=1000
            )
    # CONSTANTS and DECISION VARIABLES
    elif node.level == 2:
        # CONSTANTS
        if isinstance(node, VariablesConstantsNode) and len(node.variables_and_constants) == 0:
            response = llm.send_prompt(
                system_prompt=f"{get_system_prompt("json_sp")}\n{get_icl()}",
                prompt=  # General instr.
                "Given the problem blow:\n" +
                # Given datatypes
                (f"Given the following python code containing datatypes:´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n") +
                # Component specific instr.: constants
                #f"\nTask:Take this text description of required constants for an optimization problem: {text_representation}",
                f"\nTask:{load_sp_file("sp_constants.txt")}\n" +
                # Input variables (constants) problem description
                d2_bin_packing_formalized_problem_description[0] #+ "\n" +
                # Global problem description
                #d2_bin_packing_formalized_problem_description[2] + "\n" +
                # Sub problem description
                #d2_bin_packing_formalized_problem_description[3]
                ,max_tokens=1000
            )
        else:
            response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("json_sp")}\n{get_icl()}",
            prompt= # General instr.
            "Given the problem blow:\n" +
            # Given datatypes
            (f"Given the following python code containing datatypes and constants:´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n") +
            #f"\nTask:Take this text description of required decision variables for an optimization problem: {text_representation}\n\n{global_problem_get_system_prompt(3)}",
            # Component specific instr.: decision variables
            f"\nTask:\n{load_sp_file("sp_decision_variables.txt")}\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description[1]  # + "\n" +
            # Global problem description
            #d2_bin_packing_formalized_problem_description[2] + "\n" +
            # Sub problem description
            #d2_bin_packing_formalized_problem_description[3]
            ,max_tokens=1000
        )
    # OBJ FUNCTION
    elif node.level == 3:
        response = llm.send_prompt(
        system_prompt=f"{get_system_prompt("format_sp")}\n{get_icl()}",
        prompt=# General instr.
                # Given datatypes, constants and decision variables
        (f"Given the following python code containing datatypes, constants and decision variables:´´´python\nfrom z3 import *\n{node.get_partial_formulation_up_until_now()}´´´\n") +
        #"Given following constants and decision variables:\n" +
        #json.dumps(constants_variables_node.get_as_codeblock()) + "\n" +
        # Component specific instr.: obj. function
                f"\nTask:\n{load_sp_file("sp_obj_function.txt")}\n" +
        # Global problem description
        d2_bin_packing_formalized_problem_description[2] + "\n" +
        # Sub problem description
        d2_bin_packing_formalized_problem_description[3],
        max_tokens=800
    )
    # CONSTRAINT
    elif node.level == 4:
        if subproblem_description is None:
            raise ValueError("Subproblem description cannot be None")

        response = llm.send_prompt(
            system_prompt=f"{get_system_prompt("format_sp")}\n{get_icl()}",
            prompt=# General instr.
                   # Given datatypes
            f"""Given the following python code containing datatypes, constants, decision variables and objective func.:
            ´´´python\n{node.get_partial_formulation_up_until_now()}´´´\n""" +
            # Given constants and decision variables
                    #"Given following constants and decision variables and given following objective function presented as z3py, :\n" +
                    #json.dumps(constants_variables_node.get_as_codeblock()) + "\n" +
            #"Given following objective function:\n" +
                    #obj_function_node.content + "\n" +
            # Component specific instr.: constraints
                    f"\nTask:\n{load_sp_file("sp_constraints.txt")}\n" +
            # Sub problem description
            subproblem_description,
            max_tokens=1000
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
            d2_bin_packing_formalized_problem_description[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description[2] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description[3] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description[4] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description[5],
            max_tokens=800
        )
    # OBJECTS (datatypes)
    elif node.level == 1:
        response = llm.send_prompt(
            #system_prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}",
            prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}" +
                   load_sp_file("sp_all_at_once_shorter.txt") +
                   # Input variables (constants) problem description
                   d2_bin_packing_formalized_problem_description[0] + "\n" +
                   # Output variables (decision variables) - problem description
                   d2_bin_packing_formalized_problem_description[1] + "\n" +
                   # Global problem description
                   d2_bin_packing_formalized_problem_description[2] + "\n" +
                   # Sub problem description
                   d2_bin_packing_formalized_problem_description[3] + "\n" +
                   # Sub problem description
                   d2_bin_packing_formalized_problem_description[4] + "\n" +
                   # Sub problem description
                   d2_bin_packing_formalized_problem_description[5],
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
                d2_bin_packing_formalized_problem_description[0] + "\n" +
                # Output variables (decision variables) - problem description
                d2_bin_packing_formalized_problem_description[1] + "\n" +
                # Global problem description
                d2_bin_packing_formalized_problem_description[2] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description[3] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description[4] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description[5]
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
            d2_bin_packing_formalized_problem_description[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description[2] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description[3] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description[4] + "\n" +
            # Sub problem description
            d2_bin_packing_formalized_problem_description[5]
            ,max_tokens=2500
        )
    # OBJ FUNCTION
    elif node.level == 3:
        response = llm.send_prompt(
        #system_prompt=f"{get_system_prompt("format_all_sp")}\n{get_icl()}",
        prompt=# General instr.
                # Given datatypes, constants and decision variables
        f"{get_system_prompt("format_all_sp")}\n{get_icl()}" +
        (f"Extend the following python code, include but do not extend the sections objects, constants and decision variables:´´´python\nfrom z3 import *\n{node.get_partial_formulation_up_until_now()}´´´\n") +
        # All-at-once instruction
        load_sp_file("sp_all_at_once_shorter.txt") +
        # Input variables (constants) problem description
        d2_bin_packing_formalized_problem_description[0] + "\n" +
        # Output variables (decision variables) - problem description
        d2_bin_packing_formalized_problem_description[1] + "\n" +
        # Global problem description
        d2_bin_packing_formalized_problem_description[2] + "\n" +
        # Sub problem description
        d2_bin_packing_formalized_problem_description[3] + "\n" +
        # Sub problem description
        d2_bin_packing_formalized_problem_description[4] + "\n" +
        # Sub problem description
        d2_bin_packing_formalized_problem_description[5],
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
            d2_bin_packing_formalized_problem_description[0] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description[1] + "\n" +
            # Global problem description
            d2_bin_packing_formalized_problem_description[2] + "\n" +
            # Sub problem description
            subproblem_description,
            max_tokens=2500
        )
    return decompose_full_definition(response)



def get_icl():
    if USE_OPTDSL:
        return load_sp_file("ICL_example.txt")
    else:
        return load_sp_file("ICL_datatypes.txt")

def get_system_prompt(key: str):
    key = f"{constants.CHOSEN_LANGUAGE}_{key}"
    if constants.USE_OPTDSL:
        system_prompt = {
            "text_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into text description. The result must contain correct definitions only. Remember that each constant, variable and constraint must be added to a s = Optimize().",
            "optdsl_format_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into OptDSL. 1.The result must be code only. \n2.No explanations. \n3.Python comments are allowed. \n4. Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6.Return you answer in the following format: ´´´python <solution> ´´´ where <solution> is a placeholder for the code. Use in-context-learning examples, do not take its variables directly but learn. \n7.Return \"NTD\", if there is empty output. \n8. Do not hallucinate. \n9. Do not exceed the max_tokens. 10. Never let leave placeholder for the user to fill out, everything must be strictly defined by you.",
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
10. Never let leave placeholder for the user to fill out, everything must be strictly defined by you.
            """,
            "optdsl_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into OptDSL. 1.The result must be code only. \n2.No explanations. \n3.Python comments are allowed. \n4.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. Use in-context-learning examples, do not take its variables directly but learn. \n6.Return \"NTD\", if there is empty output. \n7. Do not hallucinate. \n8. Do not exceed the max_tokens. 9. Never let leave placeholder for the user to fill out, everything must be strictly defined by you.",
            "optdsl_json_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into OptDSL. 1.The result must be a json that partly contains code. \n2.No explanations. \n3.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. Use in-context-learning examples. \n6. Do not exceed the max_tokens. 7. Never let leave placeholder for the user to fill out, everything must be strictly defined by you.",
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
            "z3py_format_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python. 1.The result must be python code only. \n2.No explanations. \n3.Python comments are allowed. \n4. Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6.Return you answer in the following format: ´´´python <solution> ´´´ where <solution> is a placeholder for the code. \n7. Remember that each constraint must be added to a s = Optimize(). Use given datatypes, IntVal, StringVal etc. Use IntVal, StringVal etc. Use in-context-learning examples, do not take its variables directly but learn. \n8.Return \"NTD\", if there is empty output. \n9. Do not hallucinate. \n10. Do not exceed the max_tokens. 11. Never let leave placeholder for the user to fill out, everything must be strictly defined by you. Avoid redundancies.",
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
        10. Never let leave placeholder for the user to fill out, everything must be strictly defined by you.""",
            "z3py_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python. 1.The result must be python code only. \n2.No explanations. \n3.Python comments are allowed. \n4.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6. Remember that constraint must be added to a s = Optimize(). Use given datatypes, IntVal, StringVal etc. \nUse IntVal, StringVal etc. Use in-context-learning examples, do not take its variables directly but learn. \n7.Return \"NTD\", if there is empty output. \n9. Do not hallucinate. \n10. Do not exceed the max_tokens. 11. Never let leave placeholder for the user to fill out, everything must be strictly defined by you. Avoid redundancies.",
            "z3py_json_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into z3 python. 1.The result must be a json that partly contains code. \n2.No explanations. \n3.Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6. Remember that each constraint must be added to a s = Optimize().  Use given datatypes, IntVal, StringVal etc. Use in-context-learning examples. \n10. Do not exceed the max_tokens. 11. Never let leave placeholder for the user to fill out, everything must be strictly defined by you. Avoid redundancies.",
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

d2_bin_packing_formalized_problem_description = [
    # Input
    """
    Input
    ´´´ json
    {
        "BOX_HEIGHT": 6,
        "BOX_WIDTH": 10,
        "ITEMS": [
            {
                "name": "item1"
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
    Output:
    ´´´json
    [
        {
            "description": "Number of boxes used in the end to pack all all items. Minimizing it is the objective.",
            "mandatory_variable_name": "nr_used_boxes",
            "suggested_shape": "integer"
        },
        {
            "description": "Which item is assigned to which box.",
            "mandatory_variable_name": "item_box_assignment",
            "suggested_shape": "array of objects or multiple arrays"
        },
        {
            "description": "Position x and y of each item within box",
            "mandatory_variable_name": "x_y_positions",
            "suggested_shape": "array of objects or multiple arrays"
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
        - the assigment of each item into a box and 
        - the position (x and y) of each item within its assigned box.
    """,
    # Subproblem description - part 1
    """Sub problem definition - items that go in the bin - part 1:
    Taking the given items that are put into a box, they must fit exactly inside a box and must not stick out of the box.
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
    # Root node - get textual description
    root_node = RootNode()
    '''response = create_and_send_prompt(root_node)
    root_node.set_content(response)
    '''
    # Query object types, data types
    datatypes_node = ObjectsNode(root_node)
    if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
        response = create_and_send_prompt_for_all_at_once_and_extract_approach(datatypes_node)
    else:
        response = remove_programming_environment(create_and_send_prompt_for_strictly_iterative_approach(datatypes_node))
    response = enter_variable_definitions_feedback_loop(datatypes_node, response)
    datatypes_node.set_content(response)
    print(f"*** Response, global problem/datatypes: {response}\n")

    ### Query constants ######################################################################################
    constants_variables_node = VariablesConstantsNode(parent=datatypes_node)
    successfully_added = False
    while not successfully_added:
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            response = create_and_send_prompt_for_all_at_once_and_extract_approach(constants_variables_node)
        else:
            response = remove_programming_environment(create_and_send_prompt_for_strictly_iterative_approach(constants_variables_node))
        response = enter_variable_definitions_feedback_loop(constants_variables_node, response)
        successfully_added = constants_variables_node.set_constants(response)
    print(f"*** Response, constants: {response}\n")

    ### Query decision variables ######################################################################################
    successfully_added = False
    while not successfully_added:
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            response = create_and_send_prompt_for_all_at_once_and_extract_approach(constants_variables_node)
        else:
            response = remove_programming_environment(create_and_send_prompt_for_strictly_iterative_approach(constants_variables_node))
        response = enter_variable_definitions_feedback_loop(constants_variables_node, response)
        successfully_added = constants_variables_node.set_variables(response)
    print(f"*** Response (decision) variables: {response}\n")

    # Wiser to use for z3 only
    # Query objective function
    if not USE_OPTDSL:
        obj_function_node = ObjectiveNode(parent=constants_variables_node)
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            response = create_and_send_prompt_for_all_at_once_and_extract_approach(obj_function_node)
        else:
            response = remove_programming_environment(create_and_send_prompt_for_strictly_iterative_approach(obj_function_node))
        response = enter_variable_definitions_feedback_loop(obj_function_node, response)
        obj_function_node.set_content(response)
        print(f"*** Obj. function: {response}\n")

    # Query constraints
    constraints_node = ConstraintsNode(parent=constants_variables_node) if USE_OPTDSL else ConstraintsNode(parent=obj_function_node)
    for i in range(3,6):
        if constants.USE_ALL_AT_ONCE_AND_EXTRACT:
            response = create_and_send_prompt_for_all_at_once_and_extract_approach(constraints_node, subproblem_description=d2_bin_packing_formalized_problem_description[i])
        else:
            response = remove_programming_environment(create_and_send_prompt_for_strictly_iterative_approach(constraints_node, subproblem_description=d2_bin_packing_formalized_problem_description[i]))
        response = enter_variable_definitions_feedback_loop(constraints_node, response, subproblem_description=d2_bin_packing_formalized_problem_description[i])
        constraints_node.set_content(response)
        print(f"*** Constraints: {response}\n")
        if response == "":
            print("Creating constraints failed!")


    if constants.DEBUG_MODE_ON: print(f"Full formulation:\n{constraints_node.get_partial_formulation_up_until_now()}")

if __name__ == "__main__":
    llm = constants.LLM
    build_up_formulation_iteratively(llm)
