import csv
import json
import random
import string

from constants import RANDOM_SEED, RANDOM_STRING_LENGTH
from structures_utils import split_at_outer_equals, \
    initial_clean_up


class InputReader:


    @staticmethod
    def read_problem_description_from_file(input_var_file_path: str , problem_file_path: str, input_mode):
        """
        Problem description is read from file and later passed to LLM (full model formulation by LLM)
        If specification is given containing fields like "variable" and "objects", random value generation is supported
        """
        with open(input_var_file_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)
        if input_mode == "flex_objects_flex_input_values" and "input_variables" not in input_data:
            raise ValueError("Invalid instance input file: There must be a field \"input_variables\"")
        if "input_variables" in input_data:
            input_data = InputReader.generate_data(input_data)

        with open(problem_file_path, "r", encoding="utf-8") as f:
            problem_description_data = json.load(f)
        if ("output" not in problem_description_data or
                "global_problem" not in problem_description_data or
                "subproblems" not in problem_description_data):
            raise ValueError("Invalid instance input file: There must be a field \"output\", \"global_problem\" and \"subproblems\"")

        problem_description = [
            f'´´´ json\n{json.dumps(input_data, indent=4)}´´´',
            f'´´´ json\n{json.dumps(problem_description_data["output"], indent=4)}´´´',
            problem_description_data["global_problem"]
        ]
        problem_description.extend(problem_description_data["subproblems"])
        return problem_description

    @staticmethod
    def generate_data(input_data: dict):
        """
        Generate input specification for llm, by setting given values for the variables, importing data from a file or generating random values
        Args:
            input_data (dict): specification given by user (objects/shapes, input vars, output vars)
        """
        if "input_variables" not in input_data:
            raise ValueError("Invalid input data file: Variables must defined in a field \"variables\": {...}.")
        generated_input_data = {}
        for variable, meta in input_data["input_variables"].items():
            if "value" not in meta:
                raise ValueError("Invalid input data file: Variables must define a value and optionally a type.")
            if meta["value"] != "random" and ".csv" not in str(meta["value"]):
                generated_input_data.update({variable: meta["value"]})
                continue
            if "type" not in meta:
                raise ValueError("Invalid input data file: Variables must define a type and a value.")

            # Type = list
            if isinstance(meta["type"], dict):
                if "elem_type" not in meta["type"] or "length" not in meta["type"]:
                    raise ValueError(
                        "Invalid input data file: Variables of type list must define a elem_type and a length.")
                value = []
                if ".csv" in meta["value"]:
                    with open(meta["value"], mode="r", encoding="utf-8") as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            value.append(InputReader.generate_value(
                                meta["type"]["elem_type"], row, None, None, input_data["objects"]))
                else:
                    lower_bound = meta["type"]["minimum"] if "minimum" in meta["type"] else None
                    upper_bound = meta["type"]["maximum"] if "maximum" in meta["type"] else None
                    for _ in range(meta["type"]["length"]):
                        value.append(InputReader.generate_value(
                            meta["type"]["elem_type"], None, lower_bound, upper_bound, input_data["objects"]))
            # Type = int, float, string, object
            else:
                lower_bound = meta["minimum"] if "minimum" in meta else None
                upper_bound = meta["maximum"] if "maximum" in meta else None
                value = InputReader.generate_value(
                    meta["type"], meta["value"], lower_bound, upper_bound, input_data["objects"])
            generated_input_data.update({variable: value})
        return generated_input_data


    @staticmethod
    def read_problem_description_and_generateDSLcode_from_file(input_var_file_path: str, problem_file_path: str, input_mode):
        '''
            Depending on input_mode, the problem specification (by user) is read from file and
            one more of the following parts are hard-coded into dsl (partial model formulation by LLM/script)
                > object types / shapes
                > constants
                > decision variables
            Specification must be given containing fields like "input-variables", "output-variables" and "objects"
            Args:
                input_var_file_path (str): path to file containing user-given object type/ input variables/ output variables specification
                problem_file_path (str):  path to file containing user-given problem specification
                input_mode (str): input mode, indicates of DSL-code generation is done for
                                  object types and/or input variables and/or output variables
        '''
        with open(input_var_file_path, "r", encoding="utf-8") as f:
            input_data = json.load(f)

        # Check json fields existent according to input_mode
        if (input_mode == "fixed_objects_fixed_object_types") and "objects" not in input_data:
            raise ValueError("Invalid instance input file for chosen mode: There must be a field \"objects\"")
        if (input_mode == "fixed_objects_fixed_input_values" or
            input_mode == "fixed_objects_fixed_inoutput_values") and "input_variables" not in input_data:
            raise ValueError("Invalid instance input file for chosen mode: There must be a field \"input_variables\"")
        if (input_mode == "fixed_objects_fixed_output_values" or
            input_mode == "fixed_objects_fixed_inoutput_values") and "output_variables" not in input_data:
            raise ValueError("Invalid instance input file for chosen mode: There must be a field \"output_variables\"")
        if (input_mode == "fixed_objects_fixed_input_values" or
            input_mode == "fixed_objects_fixed_output_values" or
            input_mode == "fixed_objects_fixed_inoutput_values") and "objects" not in input_data:
            raise ValueError("Invalid instance input file for chose mode: There must be a field \"objects\"")

        # Generate DSL code according to specification (templates and instances - reusability)
        objects = None
        input_variables = None
        output_variables = None
        if "output_variables" in input_data:
            output_variables = InputReader.generate_output_data_as_DSL_code(input_data["output_variables"])
        if "input_variables" in input_data:
            input_variables = InputReader.generate_input_data_as_DSL_code(input_data["input_variables"], input_data["objects"])
        if "objects" in input_data:
            objects = InputReader.generate_objects_as_DSL_code(input_data["objects"])
        with open(problem_file_path, "r", encoding="utf-8") as f:
            problem_description_data = json.load(f)

        problem_description = [
            f'´´´ json\n{json.dumps(problem_description_data["input"], indent=4) if "input" in problem_description_data else ""}´´´',
            f'´´´ json\n{json.dumps(problem_description_data["output"], indent=4) if "output" in problem_description_data else ""}´´´',
            problem_description_data["global_problem"]
        ]
        problem_description.extend(problem_description_data["subproblems"])
        return objects, input_variables, output_variables, problem_description


    @staticmethod
    def generate_objects_as_DSL_code(input_data: dict):
        """
        Generate DSL code for object type definition
        Args:
            input_data (dict): full user-given specification
        Returns:
            list: object type declaration as OptDSL code
        """
        objects = {}
        for object_name, meta in input_data.items():
            boundaries = []
            objects_code: str = f"{object_name} = DSRecord({{{{"
            for i, attribute in enumerate(meta):
                lower_bound = attribute["minimum"] if "minimum" in attribute else None
                upper_bound = attribute["maximum"] if "maximum" in attribute else None
                code_piece = InputReader.generate_dsl_code(attribute["name"], attribute["type"], lower_bound, upper_bound, is_decision_var=True)
                code_piece = code_piece.split(" ", 1)
                objects_code += f"\"{code_piece[0]}\" {code_piece[1] if len(code_piece) > 1 else ""}"
                if 0 <= i < len(meta)-1: objects_code += ", "
                if lower_bound is not None:
                    boundaries.append(lower_bound)
                if upper_bound is not None:
                    boundaries.append(upper_bound)
            objects_code += "}})\n"
            objects.update({object_name: objects_code.format(*boundaries)})
        return objects

    @staticmethod
    def generate_output_data_as_DSL_code(output_data: dict):
        """
        Generate DSL code for decision variables declaration (output variables)
        Args:
            input_data (dict): full user-given specification
        Returns:
            list: variable specifications usable by LLM-Formulation-Generation Framework, each includes:
                  variable_name, variable type, current instance-value, code-template for variable initialization,
                  filled initialization-code template with current instance-value)
        """
        variables = []
        for variable, meta in output_data.items():
            if "type" not in meta:
                raise ValueError("Invalid input data file: Variables must define a type and a value.")

            instance =[]
            list_len = None
            # Type = list
            if isinstance(meta["type"], dict):
                if "elem_type" not in meta["type"] or "length" not in meta["type"]:
                    raise ValueError(
                        "Invalid input data file: Variables of type list must define a elem_type and a length.")
                lower_bound = meta["type"]["minimum"] if "minimum" in meta["type"] else None
                upper_bound = meta["type"]["maximum"] if "maximum" in meta["type"] else None
                code_piece = f"{variable} : DSList(length = {{}}, elem_type = {InputReader.generate_dsl_code(None, meta["type"]["elem_type"], lower_bound, upper_bound, True)})\n"
                code_piece += f"N_{variable.upper()} : int = {{}}"
                list_len = meta["type"]["length"]
            # Type = int, float, string, object
            else:
                lower_bound = meta["minimum"] if "minimum" in meta else None
                upper_bound = meta["maximum"] if "maximum" in meta else None
                code_piece = InputReader.generate_dsl_code(variable, meta["type"], lower_bound, upper_bound, True)
            if list_len is not None: # for list declaration
                instance.append(list_len)
            if lower_bound is not None:
                instance.append(lower_bound)
            if upper_bound is not None:
                instance.append(upper_bound)
            if list_len is not None: # for list length constant
                instance.append(list_len)
            variables.append({
                "description": "",
                "variable_name": variable,
                "type": split_at_outer_equals(code_piece)[0],
                "variable_instance": instance,
                "variable_dslcode_template": code_piece,
                "initialization": initial_clean_up(code_piece.format(*instance), to_typing=True)
            })
        return variables


    @staticmethod
    def generate_input_data_as_DSL_code(input_data: dict, input_objects: dict):
        """
        Generate DSL code for constants declaration and initialization (input variables)
        Args:
            input_data (dict): full user-given specification
            input_objects (dict): user-given input objects specification
        Returns:
            list: variable specifications usable by LLM-Formulation-Generation Framework, each includes:
                  variable_name, variable type, current instance-value, code-template for variable initialization,
                  filled initialization-code template with current instance-value)
        """
        variables = []
        for variable, meta in input_data.items():
            if "value" not in meta:
                raise ValueError("Invalid input data file: Variables must define a value and optionally a type.")
            if "type" not in meta:
                raise ValueError("Invalid input data file: Variables must define a type and a value.")

            # Type = list
            value = []
            if isinstance(meta["type"], dict):
                if "elem_type" not in meta["type"] or "length" not in meta["type"]:
                    raise ValueError(
                        "Invalid input data file: Variables of type list must define a elem_type and a length.")
                value = []
                lower_bound = meta["type"]["minimum"] if "minimum" in meta["type"] else None
                upper_bound = meta["type"]["maximum"] if "maximum" in meta["type"] else None
                # value = csv-file
                if isinstance(meta["value"], str) and ".csv" in meta["value"]:
                    with open(meta["value"], mode="r", encoding="utf-8") as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            value.append(InputReader.generate_value(
                                meta["type"]["elem_type"], row, None, None, input_objects))
                # value = custom value
                elif isinstance(meta["value"], list):
                    if len(meta["value"]) != meta["type"]["length"]:
                        raise ValueError("Invalid input data file: List-input-variable defined length and length of custom value do not match.")
                    value = meta["value"]
                # value = random
                else:
                    for _ in range(meta["type"]["length"]):
                        value.append(InputReader.generate_value(
                            meta["type"]["elem_type"], None, lower_bound, upper_bound, input_objects))
                code_piece = f"{variable} : DSList(length = {{}}, elem_type = {InputReader.generate_dsl_code(None, meta["type"]["elem_type"], lower_bound, upper_bound)}) = {{}}\n"
                code_piece += f"N_{variable.upper()} : int = {{}}"
                value = [meta["type"]["length"], value, meta["type"]["length"]]
            # Type = int, float, string, object
            else:
                lower_bound = meta["minimum"] if "minimum" in meta else None
                upper_bound = meta["maximum"] if "maximum" in meta else None
                value.append(InputReader.generate_value(
                    meta["type"], meta["value"], lower_bound, upper_bound, input_objects))
                code_piece = InputReader.generate_dsl_code(variable, meta["type"], lower_bound, upper_bound)
            variables.append({
                 "description": "",
                 "variable_name": variable.upper(),
                 "type": split_at_outer_equals(code_piece)[0],
                 "variable_instance": value,
                 "variable_dslcode_template": code_piece,
                 "initialization": initial_clean_up(code_piece.format(*value), to_typing=True)
            })
        return variables


    @staticmethod
    def update_data_by_instance(variables, new_instance, input_objects: dict, is_decision_var: bool = False):
        """
        Takes a list of variable specifications and a 2d bin packing instance.
        New values are generated or user-given and inserted into the template of each variable specification.
        Return: updated variable spec by model instance.
        """
        for i, variable in enumerate(variables):
            if is_decision_var:
                new_values = InputReader.generate_values_for_template(new_instance[variable["variable_name"]],
                                                                      input_objects,
                                                                      is_decision_var=is_decision_var)
            else:
                new_values = InputReader.generate_values_for_template(new_instance[variable["variable_name"].upper()],
                                                                      input_objects)
            try:
                variables[i].update({"variable_instance": new_values})
                variables[i].update({"initialization": variable["variable_dslcode_template"].format(*new_values)})
            except IndexError:
                print(f"Invalid new instance: Probably lower/upper bound of new instance and reused model for the constant {variable["variable_name"]} do not match.")
        return variables


    @staticmethod
    def generate_values_for_template(meta: dict, input_objects, is_decision_var: bool = False):
        """
        Creates random values/Gets user-given values for respective template to be inserted into:
        > constants: [list-length, (lower_bound, upper_bound), value, list-length]
        > decision variables: [lower_bound, upper_bound, list-length]
        """
        if "type" not in meta:
            raise ValueError("Invalid input data file: Variables must define a type and a value.")

        # Type = list
        value = []
        list_len = None
        if isinstance(meta["type"], dict):
            if "elem_type" not in meta["type"] or "length" not in meta["type"]:
                raise ValueError(
                    "Invalid input data file: Variables of type list must define a elem_type and a length.")
            val = []
            lower_bound = meta["type"]["minimum"] if "minimum" in meta["type"] else None
            upper_bound = meta["type"]["maximum"] if "maximum" in meta["type"] else None
            # value = csv-file
            if not is_decision_var and ".csv" in meta["value"]:
                with open(meta["value"], mode="r", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        val.append(InputReader.generate_value(
                            meta["type"]["elem_type"], row, None, None, input_objects))
            elif not is_decision_var:
                # value = custom value
                if isinstance(meta["value"], list):
                    if len(meta["value"]) != meta["type"]["length"]:
                        raise ValueError("Invalid input data file: List-input-variable defined length and length of custom value do not match.")
                    val = meta["value"]
                else:
                # value = random
                    for _ in range(meta["type"]["length"]):
                        val.append(InputReader.generate_value(
                            meta["type"]["elem_type"], None, lower_bound, upper_bound, input_objects))
            list_len = meta["type"]["length"]
        # Type = int, float, string, object
        else:
            lower_bound = meta["minimum"] if "minimum" in meta else None
            upper_bound = meta["maximum"] if "maximum" in meta else None
            if not is_decision_var:
                val = InputReader.generate_value(
                meta["type"], meta["value"], lower_bound, upper_bound, input_objects)

        if list_len is not None:  # for list declaration
            value.append(list_len)
        if is_decision_var:
            if lower_bound is not None:
                value.append(lower_bound)
            if upper_bound is not None:
                value.append(upper_bound)
        else:
            value.append(val)
        if list_len is not None:  # for list length constant
            value.append(list_len)
        return value

    @staticmethod
    def generate_dsl_code(variable: str = None, type: str = None, lower_bound = None, upper_bound = None, is_decision_var: bool = False):
        if not type:
            raise ValueError("Invalid input data file: Variables must define a type.")
        match type:
            case "int" | "integer":
                if not is_decision_var:
                    value = f"{variable.upper()} : int = {{}}"
                else:
                    if variable is None:
                        value = "DSInt("
                    else:
                        value = variable + " : DSInt("
                    if lower_bound is not None:
                        value += f"lb={{}}"
                    if lower_bound is not None and upper_bound is not None:
                        value += ", "
                    if upper_bound is not None:
                        value += f"ub={{}}"
                    value += ")"
            case "float":
                if not is_decision_var:
                    value = f"{variable.upper()} : float = {{}}"
                else:
                    if variable is None:
                        value = "DSFloat("
                    else:
                        value = f"{variable} : DSFloat("
                    if lower_bound is not None:
                        value += f"lb={{}}"
                    if lower_bound is not None and upper_bound is not None:
                        value += ", "
                    if upper_bound is not None:
                        value += f"ub={{}}"
                    value += ")"
            case "bool":
                if not is_decision_var:
                    value = f"{variable.upper()} : bool = {{}}"
                else:
                    if variable is None:
                        value = f"DSBool()"
                    else:
                        value = f"{variable} : DSBool()"
            case "string" | "str":
                if is_decision_var:
                    value = f"{variable} : str = {{}}"
                else:
                    value = f"{variable.upper()} : str = {{}}"
            case _:
                if variable is None:
                    value = f"{type}"
                else:
                    if is_decision_var:
                        value = f"{variable} : {type}"
                    else:
                        value = f"{variable.upper()} : {type} = {{}}"
        return value

    @staticmethod
    def generate_value(type: str, value, lower_bound, upper_bound, input_objects: dict):
        """
        Generate random value according to type, lower_bound, upper_bound OR
        get user-given value, check bound-comformity, convert to correct type
        Args:
            type (str): Type of variable
            value (str): Value of variable, can be "random" or a user-given value
            lower_bound (int): Lower bound of value
            upper_bound (int): Upper bound of value
            input_objects (dict): Dictionary of user-given object types
        Returns:
            A value conform to type and bounds
        """
        match type:
            case "int" | "integer":
                if value is not None and value != "random":
                    value = int(value)
                    if lower_bound is not None and upper_bound is not None:
                        assert lower_bound <= value <= upper_bound, f"Given value violates specified lower or upper bound: {value}"
                else:
                    # value = random
                    lower_bound = lower_bound if lower_bound is not None else 1
                    upper_bound = upper_bound if upper_bound is not None else RANDOM_SEED
                    value = random.randint(lower_bound, upper_bound)
            case "float":
                lower_bound = lower_bound if lower_bound is not None else -RANDOM_SEED
                upper_bound = upper_bound if upper_bound is not None else RANDOM_SEED
                if value is not None and value != "random":
                    value = float(value)
                    assert lower_bound <= value <= upper_bound, f"Given value violates specified lower or upper bound: {value}"
                else:
                    value = random.uniform(lower_bound, upper_bound)
            case "bool":
                if value == "random":
                    value = True
            case "string" | "str":
                if value == "random":
                    value = ''.join(random.choices(string.ascii_letters + string.digits, k=RANDOM_STRING_LENGTH))
            case _:
                object = {}
                for attribute in input_objects[type]:
                    if "name" not in attribute or "type" not in attribute:
                        raise ValueError("Invalid input data file: Object attributes/fields must define a name and a type.")
                    if value is not None and value != "random" and attribute["name"] not in value:
                        raise ValueError(
                            "Invalid input csv. file: Specified object attributes/fields and columns in csv do not match.")
                    lower_bound = attribute["minimum"] if "minimum" in attribute else None
                    upper_bound = attribute["maximum"] if "maximum" in attribute else None

                    if value is not None and value != "random":
                        object.update(
                            {attribute["name"]: InputReader.generate_value(attribute["type"], value[attribute["name"]],
                                                                           lower_bound,
                                                                           upper_bound,
                                                                           input_objects)})
                    else:
                        object.update(
                            {attribute["name"]: InputReader.generate_value(attribute["type"], None, lower_bound, upper_bound, input_objects)})
                value = object
        return value
