# DBMI Data Portal aka Hypatio
The DBMI Data Portal, codenamed Hypatio, is a data sharing and data challenge platform built and maintained by the DBMI Tech Core. It was built to make it easier to manage access to sensitive data sets by providing downloaders with a UI to request access and data owners with a UI to review and approve those requests.

Throughout the documentation, any mention of the word *"project"* refers to the `DataProject` model which describes any data set, data challenge, or software tool that is listed on the DBMI Data Portal.

## Infrastructure
### AWS stack overview
Hypatio is hosted on DBMI's 68 AWS account. CodePipelines exist to look for pushes to the `development` and `master` branches, build the code with CodeBuild, and deploy the Hypatio docker container to a new task in ECS using a custom Lambda function.

### Microservices
Hypatio uses three custom DBMI microservices:

- **DBMIAuthN**: Users get sent there to login. We use Auth0 to manage logins (it accepts HMS SAML logins) and create JWTs for our authentication backend.

- **DBMIAuthZ**: Where we store permissions users have to each project and admin permissions. The reason we use decided to put our permissions in this separate app is so that permissions could centralized and leveraged for other DBMI tools outside of Hypatio.

- **DBMIReg**: Where we store user profile information (job title, address, phone number). Centralized in case other DBMI tools collect profile data too. Allows us to understand our user base across all our apps.

All three microservices run on the EC2 and ECS clusters as Hypatio.

### Data set hosting and downloading
The files that authorized users of Hypatio can download are hosted in S3 on DBMI's 68 AWS account. Files for the DEV system are stored in the `dbmi-hypatio-dev` bucket, while PROD uses `dbmi-hypatio-prod`. Inside each bucket, folders separate files for each DataProject. These files must be described in `HostedFile` objects in the app's database -- more on that below.

## App overview
### Django apps
- `contact` - Powers the Contact Us form that appears at the top of the Hypatio UI.

- `hypatio` - The base app, containing mostly just URL routing and some helper methods to integrate with various DBMI microservices.

- `manage` - Contains views and API endpoints for project admins to manage their various projects.

- `profile` - Profile management for users.

- `projects` - Views, models, API endpoints, and helper methods to facilitate user interaction with projects hosted on Hypatio.

### Naming files
- `admin.py` - Where models are configured for access in the Django admin.

- `api.py` - Where API endpoints should go.

- `forms.py` - Where Django forms are defined.

- `models.py` - Where database models are defined.

- `panels.py` - Specifically for projects, we define here a few classes to describe how UI elements should be configured on project pages.

- `tests.py` - Where unit tests go.

- `urls.py` - Where URL routing is defined.

- `utils.py` - Helper methods that views or API methods might need.

- `views.py` - Where views are defined.

- `(xyz)_extras.py` - Where filters for django templates are defined.

### Sharing data sets.
The HostedFile model describes each file that users can download. Key fields include:

- `file_location`: The folder within the S3 bucket.

- `file_name`: The filename within the folder.

- `long_name` and `description`: How the file should be displayed to users.

- `enabled`: if set to false, users will not be able to download the file at any time.

- `opened_time` and `closed_time`: If `enabled` is true, this window of time allows the file to only be listed to users and available for downloading between a certain period of time.

- `hostedfileset`: Files can be grouped together for a clearer visual display to users. A HostedFileSet object must exist and be connected to the same the DataProject.

- `order`: A manual way to set what the order (lowest number appearing first) of the files should be within the hostedfileset and project.

## User documentation
Please visit the following link to read and edit documentation tailored for users and administrators of Hypatio: <https://docs.google.com/document/d/17h99OVvY1VyzJb-CqWrf4uqQMYUsB-iakV0NKOZv8OQ/edit?usp=sharing>.