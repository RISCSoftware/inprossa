"""
Create a function that given:
- the name of a variable
- a dictionary with machines as keys and a 2-integer tuple as value:
    - the first element is the number of inputs that went into the machine
    - the second element is the number of outputs that came out of the machine.
It returns the new name of the given variable after these changes
"""

import re


def rewrite_variable_name(variable_name: str, machine_info: dict) -> str:
    """
    Rewrite the variable name based on the machine information.

    :param variable_name: The original variable name.
    :param machine_info: A dictionary with machine names as keys and
    a tuple of (inputs, outputs) as values.
    :return: The rewritten variable name.
    """
    # the machine name this variable is associated with
    # is the first part of the variable name before a space
    machine_name = variable_name.split(" ")[0]
    if machine_name not in machine_info:
        # print(f"Warning: Machine '{machine_name}' not found in machine_info.
        # Returning original variable name.")
        pass
    else:
        # numbers to be changed always appear between square brackets
        # e.g. "machine_name [2] [3]"
        # by default, the number will correspond to an input
        # if it´s written just after "output" it will be an output,
        # e.g. "machine_name [2] output [3]"
        # or if it´s the second position in a vector it will be an output
        # e.g. "machine_name [2,3]"

        inputs, outputs = machine_info[machine_name]

        # identify numbers inside the square brackets
        # check if they correspond to inputs or outputs
        # and rewrite the variable name accordingly
        # with machine_info = (1, 3)
        # e.g. "machine_name [5] [9]" -> "machine_name [4] [6]"
        # or "machine_name [5] output [9]" -> "machine_name [4] output [6]"

        # Find all bracketed numbers like [5], [2,3], etc.
        pattern = r"\[(.*?)\]"
        parts = re.split(pattern, variable_name)

        rewritten_parts = []
        is_output_context = False
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # non-bracketed text
                rewritten_parts.append(part)
                if 'output' in part:
                    is_output_context = True
            else:
                # inside brackets
                numbers = part.split(',')
                new_numbers = []
                for j, num_str in enumerate(numbers):
                    try:
                        original = int(num_str.strip())
                    except ValueError:
                        new_numbers.append(num_str)
                        continue

                    # determine whether to treat this as input or output
                    if is_output_context or j > 0:
                        new_num = original - outputs
                    else:
                        new_num = original - inputs
                    new_numbers.append(str(new_num))
                # Reassemble the bracketed section
                rewritten_parts.append(f"[{','.join(new_numbers)}]")
                is_output_context = False  # reset after processing a bracket

        return ''.join(rewritten_parts)


if __name__ == "__main__":
    # Example usage
    machine_info = {
        "cutterA": (1, 3),
        "sawB": (2, 5)
    }

    print(rewrite_variable_name("cutterA [5] [9]",
                                machine_info))
    # → "cutterA [4] [6]"

    print(rewrite_variable_name("cutterA [5] ad ff a output [9]",
                                machine_info))
    # → "cutterA [4] output [6]"

    print(rewrite_variable_name("sawB [6,9]",
                                machine_info))
    # → "sawB [4,4]"
