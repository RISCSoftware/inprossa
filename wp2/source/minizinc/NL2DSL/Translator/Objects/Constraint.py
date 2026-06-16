

# Class to represent a MiniZinc constraint
class Constraint:
    def __init__(self, expression="", conditions=None):
        # Avoid shared list default
        self.conditions = [] if conditions is None else list(conditions)
        self.expression = expression

    def add_condition(self, condition):
        self.conditions.append(condition)
        return self

    def as_bool_expr(self):
        """
        Return this constraint as a boolean expression
        (no 'constraint ' prefix).
        """
        if not self.conditions:
            return f"{self.expression}"
        conds = " /\\ ".join(self.conditions)
        return f"({conds} -> {self.expression})"

    def __str__(self):
        if self.conditions == []:
            return f"constraint {self.expression}"
        else:
            # Join conditions with '/\' (and) for MiniZinc syntax
            conditions_str = " /\\ ".join(self.conditions)
            return f"constraint {conditions_str} -> {self.expression}"
