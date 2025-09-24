from abc import ABC, abstractmethod


def get_all_subclasses(cls):
    subclasses = set()

    def recurse(subclass):
        for sub in subclass.__subclasses__():
            subclasses.add(sub)
            recurse(sub)

    recurse(cls)
    return subclasses


def get_controller_choices(controller_class):
    """
    Returns a list of tuples containing a class's fully-qualified name and its short name.
    """
    choices = []
    for subclass in get_all_subclasses(controller_class):
        full_name = f"{subclass.__module__}.{subclass.__name__}"
        choices.append((full_name, subclass.name()))
    return sorted(choices)


class BaseController(ABC):
    """
    Base controller class for workflows.
    This class can be extended to create specific controllers for workflows.
    """

    def __init__(self, administration=False):
        self.administration = administration

    @abstractmethod
    def name(cls) -> str:
        """
        Returns the name of the controller.
        """
        pass
