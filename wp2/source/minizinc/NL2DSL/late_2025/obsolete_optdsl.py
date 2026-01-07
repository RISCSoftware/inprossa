from structures_utils import *

LOOP_OF_DOOM_COUNTER = 0
LOOP_OF_DOOM_MAX_IT = 5
MAX_NR_RESETS = 2
def enter_variable_definitions_feedback_loop(node, raw_definitions: str):
    for _ in range(MAX_NR_RESETS):
        for _ in range(LOOP_OF_DOOM_MAX_IT):
            # NTD = Nothing To Do, is only allowed in object types node
            if "NTD" in raw_definitions:
                if CONSTANTS.DEBUG_MODE_ON: print(f"Checking node created for level {node.level}: NTD encountered")
                raw_definitions = llm.send_prompt(
                    system_prompt=f"{system_prompt["optdsl_sp"]}\n{incontextlearning_examples["optdsl"]}",
                    prompt=
                            "DO NOT RETURN NTD.\n" +
                            # General instr.
                            global_problem_system_prompt[0] +
                            # Component specific instr.: constants
                            "Use one or more of the following datatypes:\n" +
                            datatypes_node.content + "\n" +
                            "\nTask:\n" + global_problem_system_prompt[2] if node.level == 2 else global_problem_system_prompt[3] + "\n" +
                            # Global problem description
                            d2_bin_packing_formalized_problem_description[0] + "\n" +
                            # Sub problem description
                            d2_bin_packing_formalized_problem_description[1]
                    ,
                    max_tokens=800
                )
                continue

            # Constant and Decision variable nodes need to be json format
            if node.level == 2 and not is_valid_json(raw_definitions):
                if CONSTANTS.DEBUG_MODE_ON: print(f"Checking node created for level {node.level}: Constants not valid json.")
                raw_definitions = remove_programming_environment(llm.send_prompt(
                    system_prompt=f"{system_prompt["optdsl_sp"]}\n{incontextlearning_examples["optdsl"]}",
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
                            2. <initialization> is the OptDSL variable declaration and initialization code block, fully with assignments, of the variable in variable field.
                            3. <description> is a placeholder for a compact, concise description of the variable.
                            4. No additional properties allowed.""",
                    max_tokens=800
                ))
                continue
            # Check executability for partial formulation
            execution_error = check_executability(node, raw_definitions)
            if execution_error is not None:
                if CONSTANTS.DEBUG_MODE_ON: print(f"Checking node created for level {node.level} not executable: Error: {execution_error}\n")
                raw_definitions = remove_programming_environment(llm.send_prompt(
                    system_prompt=system_prompt["optdsl_json_sp"],
                    prompt="´´´" + raw_definitions + "´´´\n\n" +
                           f"The section above contains an error: {execution_error}" +
                            "You must return rewrite the problematic code. Do not return exactly the given code snippet.",
                    max_tokens=800
                ))
            else:
                return raw_definitions
        # Attempt reset
        llm.send_prompt(
            prompt="Do reset on yourself. Delete your cache.",
            max_tokens=1
        )
        create_and_send_prompt(node)
    return ""

def create_and_send_prompt(node: TreeNode, execution_message : str = None):
    response = ""
    # TEXTUAL DESCRIPTION
    if node.level == 0:
        description = llm.send_prompt(
            system_prompt=f"{system_prompt["text_sp"]}\n{incontextlearning_examples["optdsl"]}",
            prompt="""Create a very short, concise textual description of possible object types for a software engineer.
                                Nothing else, no variables, no instances, no input, no output, no constraints""" +
                   # Input variables (constants) problem description
                   d2_bin_packing_formalized_problem_description[0] + "\n" +
                   # Output variables (decision variables) - problem description
                   d2_bin_packing_formalized_problem_description[1] + "\n" +
                   # Global problem description
                   d2_bin_packing_formalized_problem_description[2] + "\n" +
                   # Sub problem description
                   d2_bin_packing_formalized_problem_description[3],
            max_tokens=200
        )
    # OBJECTS (datatypes)
    elif node.level == 1:
        if execution_message is not None:
            response = llm.send_prompt(
                system_prompt=f"{system_prompt["optdsl_sp"]}",
                prompt=
                # General instr.
                global_problem_system_prompt[0] + "\nTask:\n" +
                # Add execution_error_message from a previously failed run
                f"{response}\n{execution_message}\nCorrect this error.")
        else:
            response = llm.send_prompt(
                system_prompt=f"{system_prompt["optdsl_format_sp"]}\n{incontextlearning_examples["optdsl"]}",
                prompt=
                        # General instr.
                        global_problem_system_prompt[0] + "\nTask:\n" +
                        # Add execution_error_message from a previously failed run
                        (f"{response}\n{execution_message}\nCorrect this error." if execution_message is not None else
                        f"Task: {global_problem_system_prompt[1]}" +
                        #Component specific instr.: object types, data types
                        # Global problem description
                        d2_bin_packing_formalized_problem_description[2] + "\n" +
                        # Sub problem description
                        d2_bin_packing_formalized_problem_description[3]),
                max_tokens=500
            )
    # CONSTANTS and DECISION VARIABLES
    elif node.level == 2:
        # CONSTANTS
        if isinstance(node, VariablesConstantsNode) and len(node.variables_and_constants) == 0:
            response = llm.send_prompt(
                system_prompt=f"{system_prompt["optdsl_json_sp"]}\n{incontextlearning_examples["optdsl"]}",
                prompt=  # General instr.
                global_problem_system_prompt[0] +
                # Given datatypes
                (f"Use one or more of the following datatypes:´´´python{datatypes_node.content}´´´\n" if datatypes_node.content is not None else "There are no datatypes described.") +
                # Component specific instr.: constants
                #f"\nTask:Take this text description of required constants for an optimization problem: {text_representation}",
                "\nTask:" + global_problem_system_prompt[2] + "\n" +
                # Input variables (constants) problem description
                d2_bin_packing_formalized_problem_description[0] #+ "\n" +
                # Global problem description
                #d2_bin_packing_formalized_problem_description[2] + "\n" +
                # Sub problem description
                #d2_bin_packing_formalized_problem_description[3]
                ,max_tokens=700
            )
        else:
            response = llm.send_prompt(
            system_prompt=f"{system_prompt["optdsl_json_sp"]}\n{incontextlearning_examples["optdsl"]}",
            prompt= # General instr.
            global_problem_system_prompt[0] +
            # Given datatypes
            (f"Use one or more of the following datatypes:´´´python{datatypes_node.content}´´´\n" if datatypes_node.content is not None else "There are no datatypes described.") +
            #f"\nTask:Take this text description of required decision variables for an optimization problem: {text_representation}\n\n{global_problem_system_prompt[3]}",
            # Component specific instr.: decision variables
            "\nTask:\n" + global_problem_system_prompt[3] + "\n" +
            # Output variables (decision variables) - problem description
            d2_bin_packing_formalized_problem_description[1]  # + "\n" +
            # Global problem description
            #d2_bin_packing_formalized_problem_description[2] + "\n" +
            # Sub problem description
            #d2_bin_packing_formalized_problem_description[3]
            ,max_tokens=900
        )
    # OBJ FUNCTION
    elif node.level == 3:
        response = llm.send_prompt(
        system_prompt=f"{system_prompt["optdsl_format_sp"]}\n{incontextlearning_examples["optdsl"]}",
        prompt=# General instr.
                # Given datatypes
                (f"Use one or more of the following datatypes:´´´python{datatypes_node.content}´´´\n" if datatypes_node.content is not None else "There are no datatypes described.") +
                # Given constants and decision variables
                "Given following constants and decision variables:\n" +
                json.dumps(constants_variables_node.get_as_codeblock()) + "\n" +
                # Component specific instr.: obj. function
                "\nTask:\n" + global_problem_system_prompt[4] + "\n" +
                # Global problem description
                d2_bin_packing_formalized_problem_description[2] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description[3],
        max_tokens=300
    )
    # CONSTRAINT
    elif node.level == 4:
        response = llm.send_prompt(
        system_prompt=system_prompt["optdsl_format_sp"],
        prompt=# General instr.
                # Given datatypes
                (("Use one or more of the following datatypes:\n" + datatypes_node.content + "\n") if datatypes_node.content is not None else "There are no datatypes described.") +
                # Given constants and decision variables
                "Given following constants and decision variables:\n" +
                json.dumps(constants_variables_node.get_as_codeblock()) + "\n" +
                "Given following objective function:\n" +
                obj_function_node.content + "\n" +
                # Component specific instr.: constraints
                "\nTask:\n" + global_problem_system_prompt[5] + "\n" +
                # Global problem description
                # d2_bin_packing_formalized_problem_description[2] + "\n" +
                # Sub problem description
                d2_bin_packing_formalized_problem_description[3],
        max_tokens=1000
    )
    return response

incontextlearning_examples = {
    "optdsl": """
OptDSL
You are a helpful model which is a optimization problem formulation expert. Given an optimization problem description, you provide a translation from natural language to the pythonic modelling domain specific language OptDSL for said optimization problem that matches exactly the description. This translation must yield syntactically and semantically correct OptDSL code.

OptDSL is a python-like (pythonic) high-level constraint modelling language for formulizing optimization problems in a programmatical fashion. Eventually, OptDSL is translated into Minizinc. OptDSL adheres to following rules:
1.	OptDSL is python where constants have python native primitive types int, float. For strings do not use str, but float. Decision variables must be of primitive type DSInt, DSFloat or DSBool, or of complex type DSList or DSRecord.
2.  With DSRecord you can create object types which can be used to type a variable. There are not Python Class Constructors! When initializing a variable with an object type, see Initialization of DSRecord - Option 1 and Initialization of DSRecord - Option 2 for reference.
3.  Object type creation with DSRecord and initialization of a variable with an object type must be two seperate steps. For object type creation and variable initialization, each attribute needs to be explicitly set manually with accessing each attribute or initializing it as dict or json.
4.  Never use DSRecord as variable type directly.
5.	A DSList must be declared and later may be initialized using a python list.
6.	Indices in a DSList start at 1, not 0. Consequently, when iterating with a variable through a list we need, LIST_LEN = <length of list> + 1 for i in range(1, LIST_LEN) for a DSList list.
7.  DSList must not be used as a type directly for a variable but serves for creating list object types. If you need a list, then first create an object with DSList and than use that object type to initialize a variable/constant.
8.  DSList has two mandatory attributes: \"length\" and \"elem_type\".
9.  If the length of a list is required, define the length of that list as the hard-coded number.
10.	Do not use python complex types set and dict.
11.	Constants are variables with names in capital letters.
12.	Constant definitions must indicate their type.
13.	Constraints are defined within a python function. Define input and output parameter. There must at least be one input and one output parameter. All constants and decision variables that are required for constraint formulation and are defined at root, must be given as input parameters.
14.	After each function definition, immediately call that function with the correct input parameters.
15.	Constraints are defined as asserts, like in a test. For constraint definition use equality, inequality and relation expressions. Make use of the python-built-in function any() and all() in combination with assert, if applicable.
16.	Create temporal, auxiliary variables where you require them.
17. Do not use Python len() Function.
18.	The rest of the syntax is python entirely.
19.	Allowed operators: all, any, >=, <=, ==, !=, <, >

In-context learning example for complex type DSList:
DSList represents the list type, where the first mandatory parameter is size of the list given as an integer, while the mandatory second parameter represents the type of the list items.
SpecialList = DSList(length = 5, elem_type=int)
a: SpecialList = [1, 2, 3, 4, 5]

In-context learning example for complex type DSRecord:
Car = DSRecord({
"length": DSInt(0, MAX_CAR_LENGTH),
"included_tires": DSInt(0, MAX_TIRE_NR)
})
# Initialization of DSRecord - Option 1:
car : Car = {
                "length": 15,
                "included_tires": 4
            }
# Initialization of DSRecord - Option 2:
car : Car
car.length = 15
car.included_tires = 4

In-context learning example for primitive typeDSInt:
DSInt represents the integer type, where the first parameter is the lower bound, while the second parameter represents the upper bound.
DSInt(0, MAX_VALUE)


In-context learning full translation example for OptDSL - START
Global problem:
Prompt:
´´´ json
{
    "input" = {
        "MAX_ALLOWED_WEIGHT": 110,
        "ITEMS": [
            {
                "name": "item1"
                "value": 15,
                "weight": 12
            },
            {
                "name": "item2",
                "value": 50,
                "weight": 70
            },
            {
                "name": "item3",
                "value": 80,
                "weight": 100
            },
            {
                "name": "item4",
                "value": 80,
                "weight": 20
            },
            {
                "name": "item5",
                "value": 20,
                "weight": 12
            },
            {
                "name": "item6",
                "value": 25,
                "weight": 5
            }
        ]
    },
    "output": [
        {
            "description": "Chosen Items"
            "shape": "boolean array"
        },
        {
            "description": "Accumulated Value, which is the objective to maximize"
            "shape": "integer"
        }
    ]
}
´´´
This problem involves a collection of items, where each have a value and a weight. We have a scissor with value 15 
and weight 12, a book with value 50 and weight 70, a laptop with value 80 and weight 100, a phone with value 80 
and weight 20, a ruler with value 20 and weight 12, a pen with value 25 and weight 5. One or more items are chosen 
and put into a schoolbag. The goal is to decide which items are chosen that a maximal accumulated value is achieved.
Sub problem definition - items that go in the bag:
In the bag only go items from the given collection, such that the cumulative weight of all chosen items must never exceed the maximum allowed weight of 110.
At the same time, we want to achieve a maximum of accumulated item value. The result are the chosen items.

Expected result:
´´´
Item = DSRecord({
    "value": int,
    "weight": DSInt()
})

ITEM1 : Item = {"value": 15, "weight": 12}
ITEM2 : Item = {"value": 50, "weight": 70}
ITEM3 : Item
ITEM3.value = 80
ITEM3.weight = 100
ITEM4 : Item
ITEM4.value = 80
ITEM4.weight = 20
ITEM5 : Item
ITEM5.value = 20
ITEM5.weight = 12
ITEM6 : Item
ITEM6.value = 25
ITEM6.weight = 5
Items = DSList(length = 6, elem_type = Item)
ITEMS : Items = [ITEM1, ITEM2, ITEM3, ITEM4, ITEM5, ITEM6]
N_ITEMS : int = 7
MAX_WEIGHT : int = 110
ChosenItemsArray = DSList(6, DSBool())
chosen_items : ChosenItemsArray

def pack_item(items: Items, chosen_items: ChosenItemsArray):
    accumulated_weight = 0
    objective: int = 0
    for i, item in enumerate(items):
        if chosen_items[i]:
            accumulated_weight = accumulated_weight + item.weight
            objective = objective - item.value
    return accumulated_weight

accumulated_weight = pack_item(ITEMS, chosen_items)

assert accumulated_weight > 0
assert accumulated_weight < MAX_WEIGHT
´´´
    In-context learning full translation example for OptDSL - END
    """
}

system_prompt = {
    "text_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into text description. The result must contain correct definitions only. Remember that each constant, variable and constraint must be added to a s = Optimize().",
    "optdsl_format_sp": "You are an optimization problem formulation expert that encodes specific parts of the problem from below into OptDSL. 1.The result must be code only. \n2.No explanations. \n3.Python comments are allowed. \n4. Avoid lengthy comments, keep it short. \n5.The result must contain correct definitions only. \n6.Return you answer in the following format: ´´´python <solution> ´´´ where <solution> is a placeholder for the code. Use in-context-learning examples, do not take its variables directly but learn. \n7.Return \"NTD\", if there is empty output. \n8. Do not hallucinate. \n9. Do not exceed the max_tokens. 10. Never let leave placeholder for the user to fill out, everything must be strictly defined by you.",
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

global_problem_system_prompt = ["""
    Given the problem description below:
    """,
    # Step 1 - OBJECTS (datatypes)
    """Define required object types (see OptDSL in-context-learning-example), if there are any needed as pythonic OptDSL code.
    Be very careful with this step, only define records if needed for the described problem. If that is the case return empty output.
    1. If that is the case return empty output. But if possible, do create object types.
    2. If tuples will be required in the future, create object types instead.
    3. If a parameter has a complex object-like structure create a fitting object types for it.
    4. If a output or result has a complex object-like structure create a fitting object types for it.
    5. Do not define CONSTANTS.
    6. Do not define instances.
    7. Do not define any decision variables or variables.
    8. Do not define constraints.
    9. Do not define functions.
    10. Use float instead of str.
    11. Do not return json.
    You are strongly encouraged to use types.
    """,
    # Step 2 - CONSTANTS
    """
    Create constants from the given parameters and pack them into a Json:
    1. Names for constants are in capital letters only.
    2. Use the given object types! Apply them correctly. Do not use Python Class Constructors! When initializing a variable with an object type, see Initialization of DSRecord - Option 1 and Initialization of DSRecord - Option 2 for reference.
    3. If there are one or more constants in the \"sub problem definitions\" that are not defined yet, then define them. 
    4. The collection of the resulting constants must be complete and represent all described CONSTANTS.
    5. Above each constant put a python comment with a description of that constant.
    6. There must be one or more CONSTANTS.
    7. Do not define any constraints.
    8. The result must be minimal but most of all, semantically correct in respect to the description.
    9. The result must not be "NTD".
    10. Do not define decision variables.
    11. The result must not contain any of the given object types.
    12. The result must be a Json.
    
    Return you answer in the following format:
    [{
         "description":<description>,
         "variable_name":<variable_name>,
         "initialization":<initialization>
    }]
    The structure must fulfill following requirements:
    1. <variable_name> is the OptDSL variable described in description. The variable name that represents a variable that will later be used. Constants naming convention: capital letters only.
    2. <initialization> is the OptDSL variable declaration and initialization code block, fully with assignments, of the variable in variable field.
    3. <description> is a placeholder for a compact, concise description of the variable.
    4. No additional properties allowed.
    """,
    # Step 3 - DECISION VARIABLES
    """Identify all auxiliary variables and decision variables as OptDSL code. Expected outputs or results are decision variables.
    The result must fulfill following rules:
    1. Utilize the given object types! Apply them correctly! Do not use Python Class Constructors! When initializing a variable with an object type, see Initialization of DSRecord - Option 1 and Initialization of DSRecord - Option 2 for reference.
    2. If in the \"sub problem definition\" there can one or more decision variables be found that are not defined yet, then define them. 
    3. Do not define multiple semantically identical instances of the same variable. 
    4. All variables and all decision variables must be defined.
    5. Above each variable put a python comment with a description of that variable.
    6. There must be one or more decision variables.
    7. Do not return given object type definitions.
    8. The result must not contain any constraints.
    9. Do not return any CONSTANTS.
    10. The resulting code must be minimal but most of all, semantically correct in respect to the description.
    11. The result must not be "NTD".
    
    Return you answer in the following format:
    [{
         "description":<description>,
         "variable_name":<variable_name>,
         "initialization":<initialization>
    }]
    The structure must fulfill following requirements:
    1. <variable_name> is the OptDSL variable described in description. The variable name that represents a variable that will later be used. Constants naming convention: capital letters only.
    2. <initialization> is the OptDSL variable declaration and initialization code block, fully with assignments, code of the variable in variable field. Also add the addition to s in this block.
    3. <description> is a placeholder for a compact, concise description of the variable.
    4. No additional properties allowed.
    """,
    # Step 4 - OBJ FUNCTION
    """Define the objective function as OptDSL code.
    1. The result must not be \"NTD\".
    2. Must not contain given constants declarations.
    3. Must not contain given decision variable declarations.
    4. Do NOT define constraints.
    5. Do not return json.
    6. The objective function must be defined in OptDSL.
    7. max(objective) is the objective function to maximize a parameter variable \"objective\", while -max has the opposite effect.
    8. The objective must be calculated somehow.""",
    # Step 5 - CONSTRAINTS
    """Define the constraints within a function as OptDSL code. The constraints are given as \"sub problem definitions\"."
    There may also be defined input and output parameters. Input parameters are constants and decision variables needed for the constraints or freedoms.
    Freedoms are decision variables or variables. Use temporary variables, if required within the function.
    The output parameter must not be a constraint but a variable.
    1. The result must not be \"NTD\".
    2. Must not contain given constants declarations.
    3. Must not contain given decision variable declarations.
    4. Must not contain given objective function.
    5. Add required auxiliary variables, that are not defined yet.
    6. If specific constants and decision variables are required for the formulation of the subproblems, that are not defined yet, then define them specifically.
    7. Extract every for-loop into an individual function. Make sure that input parameter are correct. Also define a function-output.
    8. After each function definition, immediately call that function with the correct input parameters.
    9. Do not return json.
    """,
    # Final remark
    "Only return code snippets. No explanation. Do not print one solution multiple times. If the solution is shorter than max_token, so be it."]

'''
d2_bin_packing_formalized_problem_description = ["""
    Global problem:
    ´´´ json
    {
        "parameter" = {
            "BOX_HEIGHT": "6",
            "BOX_WIDTH": "10",
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
        },
        "output": [
            {
                "description": "Number of used boxes, where the objective is use the minimum possible number of boxes to put all items in."
                "shape": "integer"
            },
            {
                "description": "Item-box-assigment"
                "shape": "array"
            },
            {
                "description": "Position x and y of each item within box"
                "shape": "array of objects or multiple arrays"
            }
            ""
        ]
    }
    ´´´
    This problem involves a collection of items, where each have a value and a weight. We have 6 different items given in the parameters.
    We have a infinite number of boxes with width BOX_WIDTH and height BOX_HEIGHT. All items need to be packed into minimal number of such boxes.
    The result and expected output is:
        - number of actually used boxes
        - the assigment of each item into a box and 
        - the position (x and y) of each item within its assigned box.
    """,
    """Sub problem definition - items that go in the bin:
    Taking the given items that are put into a box must fit exactly inside a box. 
    They must not stick out of the box and must not overlap.
    One item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """]
'''
d2_bin_packing_formalized_problem_description = [
    # Input
    """
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
    ´´´json
    [
        {
            "description": "Item-box-assigment"
            "shape": "array"
        },
        {
            "description": "Position x and y of each item within box"
            "shape": "array of objects or multiple arrays"
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
    # Subproblem description
    """Sub problem definition - items that go in the bin:
    Taking the given items that are put into a box must fit exactly inside a box. 
    They must not stick out of the box and must not overlap.
    One item can be exactly in one box.
    The result and expected output is the assigment of each item into a box and the position of each item within its assigned box.
    """]



if __name__ == "__main__":
    llm = CONSTANTS.LLM

    ### Query object types, data types ######################################################################
    execution_message = None
    datatypes_node = ObjectsNode()
    while True:
        response = create_and_send_prompt(datatypes_node, execution_message)
        if "=" in response and "NTD" not in response:
            execution_message = check_executability_of_raw_response(response)
            if execution_message is None:
                datatypes_node.set_content(response)
                break
            else:
                if CONSTANTS.DEBUG_MODE_ON: print(f"Checking node created for level 1 (objects/datatypes): {execution_message}")
        else:
            datatypes_node.set_content("")
            break
    print(f"*** Response, global problem/datatypes: {response}\n")

    ### Query constants ######################################################################################
    constants_variables_node = VariablesConstantsNode(parent=datatypes_node)
    successfully_added = False
    while not successfully_added:
        response = create_and_send_prompt(constants_variables_node)
        response = enter_variable_definitions_feedback_loop(constants_variables_node, remove_programming_environment(response))
        successfully_added = constants_variables_node.set_constants(json.loads(response))
    print(f"*** Response, constants: {response}\n")

    ### Query decision variables ######################################################################################
    successfully_added = False
    while not successfully_added:
        response = create_and_send_prompt(constants_variables_node)
        response = enter_variable_definitions_feedback_loop(constants_variables_node, remove_programming_environment(response))
        successfully_added = constants_variables_node.set_variables(json.loads(response))
    print(f"*** Response (decision) variables: {response}\n")

    # Query objective function
    obj_function_node = ObjectiveNode(parent=constants_variables_node)
    response = create_and_send_prompt(obj_function_node)
    response = enter_variable_definitions_feedback_loop(obj_function_node, remove_programming_environment(response))
    obj_function_node.set_content(response)
    print(f"*** Obj. function: {response}\n")

    # Query constraints
    constraints_node = ConstraintsNode(parent=obj_function_node)
    response = create_and_send_prompt(constraints_node)
    response = enter_variable_definitions_feedback_loop(constraints_node, remove_programming_environment(response))
    obj_function_node.set_content(response)
    print(f"*** Obj. function: {response}\n")
