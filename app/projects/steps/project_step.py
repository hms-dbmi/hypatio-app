from abc import ABC, abstractmethod


class ProjectStep:

    template = None
    status = None
    agreement_form = None
    return_url = None
    model_name = None

    def __init__(self, title, project):
        self.title = title
        self.project = project

    def __str__(self):
        return "title : %s project : %s" % (self.title, self.project)


class ProjectStepInitializer(ABC):

    @staticmethod
    def get_step_status(context, step_name, step_complete):
        if step_complete:
            return 'completed_step'
        elif context['current_step'] is None:
            context['current_step'] = step_name
            return 'current_step'
        else:
            return 'future_step'

    @abstractmethod
    def update_context(self):
        pass
