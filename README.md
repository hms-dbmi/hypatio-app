# DBMI Data Portal aka Hypatio
The DBMI Data Portal, codenamed Hypatio, is a data sharing and data challenge platform built and maintained by the DBMI Tech Core.

## Developer documentation
### Infrastructure
TODO

### Data hosting
TODO

### Django apps
- `contact` - powers the Contact Us form that appears at the top of the Hypatio UI.

- `hypatio` - the base app, containing mostly just URL routing and some helper methods to integrate with various DBMI microservices.

- `manage` - contains views and API endpoints for project admins to manage their various projects.

- `profile` - profile management for users.

- `projects` - views, models, API endpoints, and helper methods to facilitate user interaction with projects hosted on Hypatio.

### Naming files
- `admin.py` - where models are configured for access in the Django admin.

- `api.py` - where API endpoints should go.

- `forms.py` - where Django forms are defined.

- `models.py` - where database models are defined.

- `panels.py` - specifically for projects, we define here a few classes to describe how UI elements should be configured on project pages.

- `tests.py` - where unit tests go.

- `urls.py` - where URL routing is defined.

- `utils.py` - helper methods that views or API methods might need.

- `views.py` - where views are defined.

- `(xyz)_extras.py` - where filters for django templates are defined.

## User documentation
Please visit the following link to read and edit documentation tailored for users and administrators of Hypatio: <https://docs.google.com/document/d/17h99OVvY1VyzJb-CqWrf4uqQMYUsB-iakV0NKOZv8OQ/edit?usp=sharing>.