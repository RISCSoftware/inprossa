"""Defines a generic machine class."""


class GenericMachine:
    """
    Base class for all machines in the pipeline.

    Is a machine that takes a list of input_type
    and produces a list of output_type."""

    def __init__(self,
                 id: str,
                 input_type: type = None,
                 output_type: type = None):
        self.id = id
        self.input_type = input_type
        self.output_type = output_type

    def output_length(self,
                      input_length: int,
                      existing_output_length: int
                      ) -> int:
        """
        Returns the length of the output list based on the input length,
        and the existing output length.

        Should be overridden by subclasses.
        """
        raise NotImplementedError(
            "This method should be overridden by subclasses.")
