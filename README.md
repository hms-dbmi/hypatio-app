# DBMI Data Portal aka Hypatio
The DBMI Data Portal, codenamed Hypatio, is a data sharing and data challenge platform built and maintained by the DBMI Tech Core. It was built to make it easier to manage access to sensitive data sets by providing downloaders with a UI to request access and data owners with a UI to review and approve those requests.

Throughout the documentation, any mention of the word "project" refers to the `DataProject` model which describes any data set, data challenge, or software tool that is listed on the DBMI Data Portal.

## Developer documentation
### Infrastructure
TODO

### Data set hosting and downloading
The files that authorized users of Hypatio can download are hosted in S3 on DBMI's 68 AWS account. Files for the DEV system are stored in the `dbmi-hypatio-dev` bucket, while PROD uses `dbmi-hypatio-prod`. Inside each bucket, folders separate files for each DataProject.

The HostedFile model describes each file that users can download. Key fields include:

- `file_location`: the folder within the S3 bucket.

- `file_name`: the filename within the folder.

- `long_name` and `description`: how the file should be displayed to users.

- `enabled`: if set to false, users will not be able to download the file at any time.

- `opened_time` and `closed_time`: if `enabled` is true, this window of time allows the file to only be listed to users and available for downloading between a certain period of time.

- `hostedfileset`: files can be grouped together for a clearer visual display to users. A HostedFileSet object must exist and be connected to the same the DataProject.

- `order`: a manual way to set what the order (lowest number appearing first) of the files should be within the hostedfileset and project.

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