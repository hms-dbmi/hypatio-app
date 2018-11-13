# For signup steps that have already been completed.
SIGNUP_STEP_COMPLETED_STATUS = 'completed'

# For signup steps that a user must complete next.
SIGNUP_STEP_CURRENT_STATUS = 'current'

# For signup steps that a user will need to complete later.
SIGNUP_STEP_FUTURE_STATUS = 'future'

# For signup steps that will always be displayed no matter what actions are taken.
SIGNUP_STEP_PERMANENT_STATUS = 'permanent'

class DataProjectPanel():
    """
    The base class that holds information needed to when displaying a panel
    on the DataProject page.
    """

    def __init__(self, title, bootstrap_color, template, additional_context=None):
        self.title = title
        self.bootstrap_color = bootstrap_color
        self.template = template
        self.additional_context = additional_context

class DataProjectInformationalPanel(DataProjectPanel):
    """
    This class holds information needed to display panels on the DataProject
    page that would not have any actions.
    """

    def __init__(self, title, bootstrap_color, template, additional_context=None):
        super().__init__(title, bootstrap_color, template, additional_context)

class DataProjectSignupPanel(DataProjectPanel):
    """
    This class holds information needed to display panels on the DataProject
    page that hold some kind of signup action that is required before a user
    can access any of the actionable panels.
    """

    def __init__(self, title, bootstrap_color, template, status, additional_context=None):
        super().__init__(title, bootstrap_color, template, additional_context)
        self.status = status

class DataProjectActionablePanel(DataProjectPanel):
    """
    This class holds information needed to display panels on the DataProject
    page that do have actions.
    """

    def __init__(self, title, bootstrap_color, template, additional_context=None):
        super().__init__(title, bootstrap_color, template, additional_context)
