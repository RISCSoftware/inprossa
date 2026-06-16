import argparse

import constants
from constants import DEBUG_MODE_ON
from input_reader import InputReader
from model_reuser import ModelReuser
from structures_utils import TreeNode, VariablesConstantsNode, State, initial_clean_up
from tree_search_base import TreeBase


class DfsTree(TreeBase):
    NR_MIN_VALID_CHILDREN = constants.NR_MAX_CHILDREN
    NR_MAX_CHILDREN = constants.NR_MAX_CHILDREN + 5

    def dfs(self, cur_node: TreeNode):
        """
        Create a Tree of Thoughts with depth first search recursively from current node to depth = 4.
        Args:
            cur_node (TreeNode): current node which is the base for the next node.
        """
        if (cur_node.state == State.FAILED
                or cur_node.n_failed_generations != 0
                or (cur_node.is_terminal and cur_node.last_in_progress)):
            return
        while (cur_node.level == 0 and (self.input_variable_spec and self.output_variable_spec) and len(cur_node.get_correct_children()) < 1 or
               (cur_node.level == 0 and (not self.input_variable_spec or not self.output_variable_spec) and len(cur_node.get_correct_children()) < DfsTree.NR_MIN_VALID_CHILDREN and len(cur_node.children) < DfsTree.NR_MAX_CHILDREN) or
               cur_node.level == 1 and self.input_variable_spec and self.output_variable_spec and len(cur_node.get_correct_children()) < 1 or
               (cur_node.level == 1 and (not self.input_variable_spec or not self.output_variable_spec) and len(cur_node.get_correct_children()) < DfsTree.NR_MIN_VALID_CHILDREN and len(cur_node.children) < DfsTree.NR_MAX_CHILDREN) or
               (cur_node.level == 2 and len(cur_node.children) < DfsTree.NR_MIN_VALID_CHILDREN and len(cur_node.children) < DfsTree.NR_MAX_CHILDREN) or #get_correct_children()
               (cur_node.level >= 3 and len(cur_node.children) < DfsTree.NR_MIN_VALID_CHILDREN and len(cur_node.children) < DfsTree.NR_MAX_CHILDREN)):
            if DEBUG_MODE_ON: print(f"""
.....................................................
Given:
{cur_node.get_partial_formulation_up_until_now()}
Create {len(cur_node.get_correct_children())}. node at level {cur_node.level+1}
.....................................................
""")
            new_child_node = None
            match cur_node.level:
                case 0:
                    new_child_node = self.create_objects_node(cur_node)
                case 1:
                    new_child_node = self.create_constants_node(cur_node)
                case 2:
                    if (isinstance(cur_node, VariablesConstantsNode) and
                            not cur_node.all_variables_created):
                        new_child_node = self.create_decision_variables(cur_node)
                    else:
                        new_child_node = self.create_objective_node(cur_node)
                case 3:
                    new_child_node = self.create_constraints_node(cur_node, cur_node.level+1)
                case _:
                    if cur_node.last_in_progress:
                        return
                    new_child_node = self.create_constraints_node(cur_node, cur_node.level+1)

            if DEBUG_MODE_ON: print(f"Successfully created node: {new_child_node.id}")
            if new_child_node.state == State.CORRECT: self.dfs(new_child_node)

    def create_full_tree_with_dfs(self):
        """
        Create a Tree of Thoughts with depth first search recursively to depth = 4.
        """
        self.dfs(self.root)
        print(f"""
*-*-*-*-*-*-*-*-*-*-*-**-*-*-*-*-*-*-*-*-*-*-*
Nr. syntactically invalid formulations: {self.nr_syntactically_invalid_leaves}
Nr. sematically invalid formulations: {self.nr_semantically_invalid_leaves}
Nr. valid formulations: {self.nr_valid_leaves}
*-*-*-*-*-*-*-*-Best Child*-*-*-*-*-*-*-*-*-*
Objective val: {self.best_child.objective_val}
Solve time: {self.best_child.solve_time}
Encoding: {initial_clean_up(self.best_child.partial_formulation_up_until_now)}
*-*-*-*-*-*-*-*-*-*-*-**-*-*-*-*-*-*-*-*-*-*-*""")

        # Write correctness results to file
        self._save_correctness_results()
        return self.root


def main():
    parser = argparse.ArgumentParser(description="Tree of Thoughts generation script with DFS algorithm")
    parser.add_argument("--for_each_constraint_one_node", default=False, type=bool, help="Constraints are put individually into nodes.")
    parser.add_argument("--problem_instance", "-pi", help="problem instance filepath")
    parser.add_argument("--input_mode",
                        "-m",
                        choices=["flex_objects_fixed_input_values",
                                 "flex_objects_flex_input_values",
                                 "fixed_objects_fixed_object_types",
                                 "fixed_objects_fixed_input_values",
                                 "fixed_objects_fixed_output_values",
                                 "fixed_objects_fixed_inoutput_values",
                                 "reuse_model_fixed_inoutput_values"],
                        help="Input mode: how input and output variables are provided.")
    parser.add_argument("--problem_description", "-pd", help="problem description filepath")
    parser.add_argument("--reusable_model_file_path", "-r", help="filepath to collection of reusable OptDSL-models")
    parser.add_argument("--new_instance_filename", "-nc", help="filepath to collection of reusable OptDSL-models")

    args = parser.parse_args()
    args.for_each_constraint_one_node = constants.CONSTRAINT_NODES if not args.for_each_constraint_one_node else args.for_each_constraint_one_node

    llm = constants.get_LLM_client()

    objects = None
    intput_variable_spec = None
    output_variable_spec = None

    # Reuse model, insert new instance values and execute
    if args.input_mode == "reuse_model_fixed_inoutput_values":
        ModelReuser.use_given_models_with_input(args.reusable_model_file_path, args.new_instance_filename)
        return

    # Generate full formulation (non-reusable version) - Constant translation done by LLM
    elif args.input_mode == "flex_objects_flex_input_values" or args.input_mode == "flex_objects_fixed_input_values":
        problem_description = InputReader.read_problem_description_from_file(
            args.problem_instance,
            args.problem_description,
            args.input_mode)

    # Generate partial formulation (reusable version) - Constant/Decision variable translation done automatically script
    else:
        objects, intput_variable_spec, output_variable_spec, problem_description = InputReader.read_problem_description_and_generateDSLcode_from_file(
            args.problem_instance,
            args.problem_description,
            args.input_mode)

    tree = DfsTree(llm,
                   problem_description=problem_description,
                   save_model=constants.SAVE_MODEL,
                   save_nodes=constants.SAVE_NODES,
                   objects_spec=objects,
                   input_variable_spec=intput_variable_spec,
                   output_variable_spec=output_variable_spec,
                   for_each_constraint_one_node=args.for_each_constraint_one_node,
                   semantic_feedback_enabled=(args.input_mode != "flex_objects_flex_input_values" and args.input_mode != "flex_objects_fixed_input_values"))
    tree.create_full_tree_with_dfs()


if __name__ == "__main__":
    main()
