# DBMI Data Portal aka Hypatio
The DBMI Data Portal, codenamed Hypatio, is a data sharing and data challenge platform built and maintained by the DBMI Tech Core. It was built to make it easier to manage access to sensitive data sets by providing downloaders with a UI to request access and data owners with a UI to review and approve those requests.

Throughout the documentation, any mention of the word *"project"* refers to the `DataProject` model which describes any data set, data challenge, or software tool that is listed on the DBMI Data Portal.

## Table of Contents
**[Infrastructure](#infrastructure)**<br>
**[App overview](#app-overview)**<br>
**[Local development](#local-development)**<br>
**[DataProject management](#dataproject-management)**<br>

## Infrastructure
### AWS stack overview
Hypatio is hosted on DBMI's 68 AWS account. CodePipelines exist to look for pushes to the `development` and `master` branches, build the code with CodeBuild, and deploy the Hypatio docker container to a new task in ECS using a custom Lambda function.

### Microservices
Hypatio uses a few custom DBMI microservices:

- **DBMI-AuthN**: Users get sent there to login. We use Auth0 to manage logins (it accepts HMS SAML logins) and create JWTs for our authentication backend.

- **DBMI-AuthZ**: Where we store permissions users have to each project and admin permissions. The reason we use decided to put our permissions in this separate app is so that permissions could centralized and leveraged for other DBMI tools outside of Hypatio.

- **DBMI-Reg**: Where we store user profile information (job title, address, phone number). Centralized in case other DBMI tools collect profile data too. Allows us to understand our user base across all our apps.

- **DBMI-Fileservice**: Takes user submissions for challenges and puts them into S3 while tracking metadata about the files.

All these microservices run on the same EC2 and ECS clusters as Hypatio.

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

### Sharing data sets
The HostedFile model describes each file that users can download. Key fields include:

- `file_location`: The folder within the S3 bucket.

- `file_name`: The filename within the folder.

- `long_name` and `description`: How the file should be displayed to users.

- `enabled`: if set to false, users will not be able to download the file at any time.

- `opened_time` and `closed_time`: If `enabled` is true, this window of time allows the file to only be listed to users and available for downloading between a certain period of time.

- `hostedfileset`: Files can be grouped together for a clearer visual display to users. A HostedFileSet object must exist and be connected to the same the DataProject.

- `order`: A manual way to set what the order (lowest number appearing first) of the files should be within the hostedfileset and project.

### Permissions
Permissions to each DataProject are stored in the **DBMI-AuthZ** app database, with the item = `Hypatio.{DataProject_ProjectKey}` and the permission = `VIEW` or `MANAGE`.

## Local development
### Running the hypatio-stack
Because Hypatio uses several micro-services, we need a docker-compose to start all of them up locally. Ask a DBMI Tech-Core developer for the `hypatio-stack` (not in GitHub right now). `hypatio-stack` is a Hypatio-specific version of Bryan's generic `stack` (should be a DBMI git repo for this). This stack includes some custom shell commands built by Bryan to simplify various docker processes.

Setting up your hypatio-stack:

- You'll need a `stack.env` file in your `hypatio-stack` folder which holds some secrets shared by all the micro-services.

- Clone all of the micro-service repos and switch to their develop branches. 

- Review the `docker-compose.yml` file and update all the local paths (the volume ones, in particular) to where you have cloned all of the micro-services' repos.

- Create a Python virtualenv for hypatio-stack, enter the virtualenv, and `cd` into the `hypatio-stack` directory. Then install requirements with `pip install -r requirements.txt`. 

- Finally, run `docker-compose build` and then `docker-compose up`.

### Where is the database?
`hypatio-stack` creates a `stackdb` MySQL database server docker with databases for each of the apps. It will run all the Django migrations for all of those apps too. 

The `stackdb` will be mounted as a volume, which if you're on a Mac will be stored in the Docker host VM on your Mac (see <https://timonweb.com/posts/getting-path-and-accessing-persistent-volumes-in-docker-for-mac/> for more info on what that means). 

Basically, this just means that the database will persist on your laptop so you don't lose all your data if your stackdb container is deleted/recreated, which is nice.

### Giving yourself admin access to each app
Most of our micro-services look to **DBMI-AuthZ** to grant you access to their Django admins. Use a SQL client of your preference (Sequel Pro is a good free option for Mac) and go into the AuthZ database. Create an `authorization_userpermission` record with permission = `ADMIN`, item = `DBMI`, and user_email = to your HMS email. You will need this record to access the AuthZ admin.

If needed, you can also create yourself as a superuser in all of the apps by bashing into each container and running the Django createsuper user command. Repeat these steps for `hypatio`, `dbmi-fileservice`, `dbmi-reg`, `dbmi-authz`, `dbmi-reg` if you choose to do this:

- With your `hypatio-stack` virtualenv activated, bash into each container by using the convenience method provided by the stack: `stack shell {CONTAINER NAME}`. 

- `cd app`, `python manage.py createsuperuser`, and follow the prompts. Use your HMS email as your username.

### Creating migrations
To create Django migration files and run them, bash into the Hypatio container with `stack shell hypatio`, `cd app`, `python manage.py makemigrations`, and `python manage.py migrate`. Because the stack has the source files mounted as a volume, the migrations you created within the container will appear in your local directory too and be available to commit to git.

### Where are the emails going?
`hypatio-stack` uses a mail client to intercept emails before they get sent. You can reach it by going to `localhost:8018` (or whatever port it is configured with in the docker-compose).

## DataProject management
### Granting MANAGE permissions to project managers
When you want someone to be able to access the management pages for projects, they will need to have a DBMI-AuthZ record with `Hypatio.{project_key}` and `MANAGE` for the email address they use to access Hypatio.

### Adding new DataProjects
To list a new project on Hypatio, create a new `DataProject` object in the Django admin. The `project_key` field becomes a part of the URL for that page. The `description` field allows for HTML to be entered, allowing project descriptions to be more engaging. The `project_supervisors` field holds a comma separated list (no spaces) of email addresses of people who should receive email notifications related to the project (e.g. when a user requests access or when someone submits a question via Contact Us).

### Adding a new agreement form
To allow some custom behavior for agreement forms (e.g. display extra form fields depending on prior answers), we create .html files for each agreement form and store them in the static directory. Once you have the HTML file ready, create a new `AgreementForm` object in the Django admin and use the `form_file_path` field to indicate where in the static directory the HTML file is. Go back to your `DataProject` object and select the new agreement form in the many to many field. An agreement form can be used for many data projects.

The `AgreementForm.external_link` field should only be used when the agreement form lives on another website and you simply want to force users to see that link and click on it before they can access the project. 

### Adding a new challenge task
Some projects are actually data challenges (e.g. most of the N2C2). The project requires users to form teams (toggle `has_teams` in the `DataProject`) and later submit solutions via an upload form. Like with agreement forms, create an HTML file in the static directory for every new task, and create a `ChallengeTask` object that has that path. Ensure that the `enabled` flag is set to true even if you have an opened and closed time. That time window specifies when users can submit solutions. 

### Documentation for project managers
Please visit the following link to read and edit documentation tailored for project managers of Hypatio: <https://docs.google.com/document/d/17h99OVvY1VyzJb-CqWrf4uqQMYUsB-iakV0NKOZv8OQ/edit?usp=sharing>.