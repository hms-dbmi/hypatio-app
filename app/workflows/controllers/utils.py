import inspect
import sys
from workflows.controllers.initializations import BaseStepInitializationController
from workflows.controllers.review import BaseStepReviewController

def get_all_subclasses(cls):
    subclasses = set()

    def recurse(subclass):
        for sub in subclass.__subclasses__():
            subclasses.add(sub)
            recurse(sub)

    recurse(cls)
    return subclasses

def get_step_initialization_controller_choices():
    choices = []
    for subclass in get_all_subclasses(BaseStepInitializationController):
        full_name = f"{subclass.__module__}.{subclass.__name__}"
        choices.append((full_name, subclass.__name__))
    return sorted(choices)

def get_step_review_controller_choices():
    choices = []
    for subclass in get_all_subclasses(BaseStepReviewController):
        full_name = f"{subclass.__module__}.{subclass.__name__}"
        choices.append((full_name, subclass.__name__))
    return sorted(choices)
