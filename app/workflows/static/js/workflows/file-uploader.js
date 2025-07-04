class FileUploader {

    /**
     * Constructor for the FileUploader class.
     * @param {string} uploadUrl - The URL to which the file will be uploaded.
     * @param {HTMLFormElement} form - The form element containing the file input.
     * @param {HTMLInputElement} fileInput - The file input element from which the file will be uploaded.
     * @param {HTMLInputElement} filenameInput - The text input element for the filename.
     * @param {Array} allowedMediaTypes - An array of allowed media types for the file upload.
     * @param {function} onProgress - Callback function to handle upload progress. Accepts two parameters: `loaded` and `total`.
     * @param {function} onComplete - Callback function to handle upload completion.
     * @param {function} onError - Callback function to handle errors during the upload process. Accepts an `Error` object as a parameter.
     * @throws {Error} Throws an error if the provided elements are not valid HTML elements or if the file input is invalid.
     */
    constructor(uploadUrl, form, fileInput, filenameInput, allowedMediaTypes, onProgress, onComplete, onError) {
        this.uploadUrl = uploadUrl;

        // Validate HTML elements
        if (!(form instanceof HTMLFormElement)) {
            throw new Error("Invalid form element provided");
        }
        if (!(fileInput instanceof HTMLInputElement) || fileInput.type !== 'file') {
            throw new Error("Invalid file input element provided");
        }
        if (!(filenameInput instanceof HTMLInputElement) || filenameInput.type !== 'text') {
            throw new Error("Invalid filename input element provided");
        }
        this.form = form;
        this.fileInput = fileInput;
        this.filenameInput = filenameInput;
        this.allowedMediaTypes = allowedMediaTypes || [];
        this.onProgress = onProgress || function() {};
        this.onComplete = onComplete || function() {};
        this.onError = onError || function() {};

        // Set the filename input value to the file name
        this.fileInput.addEventListener('change', () => {
            const file = this.getFile();
            if (file) {
                this.filenameInput.value = file.name.replace(/\\/g, '/').replace(/.*\//, '');
            } else {
                this.filenameInput.value = '';
            }
        });
    }

    /**
     * Serialize all form data into an object, removing the file input
     * @returns {FormData} The form data without the file input
     */
    prepareFormData() {

        // Serialize the form data
        var formData = new FormData(this.form);

        // Remove file from serialized data
        formData.delete("file");

        // Add content type
        formData.append("content_type", this.getFile().type);

        return formData;
    }

    /**
     * Returns the file object from the file input.
     * @returns {File} The file object from the file input
     */
    getFile() {

        const file = this.fileInput.files[0];
        if (!file) {
            throw new Error("No file selected");
        }
        return file;
    }

    /**
     * Fetches and returns the value to use for the CSRF token in requests.
     * @return {string} The CSRF token value
     */
    getCsrfToken() {
        const csrfTokenInput = this.form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (!csrfTokenInput) {
            throw new Error("CSRF token input not found in the form");
        }
        return csrfTokenInput.value;
    }

    /**
     * Takes a FormData object and convers it to a URL-encoded string.
     * @param {FormData} formData - The FormData object to convert
     * @returns {string} The URL-encoded string representation of the FormData
     */
    formDataToUrlEncoded(formData) {
        // Convert FormData to URL-encoded string
        const formDataEntries = Array.from(formData.entries());
        return formDataEntries.map(([key, value]) => {
            return encodeURIComponent(key) + '=' + encodeURIComponent(value);
        }).join('&');
    }

    /**
     * Makes the initial request to the server to get the requisite data
     * needed to upload the file directly to S3.
     */
    upload() {

        // Ensure the file input is valid
        if (!this.fileInput || this.fileInput.files.length === 0) {
            throw new Error("No file selected for upload");
        }

        // Ensure the file is one of the allowed media types
        const file = this.getFile();
        if (this.allowedMediaTypes.length > 0 && !this.allowedMediaTypes.includes(file.type)) {
            throw new Error(`File type ${file.type} is not allowed. Allowed types: ${this.allowedMediaTypes.join(', ')}`);
        }

        // Prepare form data without the file input
        const formData = this.prepareFormData();

        // Convert FormData to URL-encoded string
        const formDataString = this.formDataToUrlEncoded(formData);

        fetch(this.uploadUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: formDataString
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json(); // Parse the response as JSON
        })
        .then(data => {

            // Parse URL and request fields
            const uploadUrl = this.getFileUploadUrl(data);
            const uploadFields = this.getFileUploadFields(data);
            const fileData = this.getFileData(data);

            // Upload the file to S3
            return this.uploadFile(uploadUrl, uploadFields, fileData, formData);
        })
        .catch(error => {
            console.error('Fetch error:', error);

            // Call the error callback if provided
            if (this.onError) this.onError(error);
        });
    }

    /**
     * Parses the response from the upload API endpoint and returns the URL
     * to upload the file to.
     * @param {Object} response - The response from the upload API endpoint
     * @return {string} The URL to upload the file to
     */
    getFileUploadUrl(response) {
        if (!response || !response.hasOwnProperty('post') || !response['post'].hasOwnProperty('url')) {
            throw new Error("Invalid response from upload API endpoint, must include 'post.url' property");
        }
        return response["post"]["url"];
    }

    /**
     * Parses the response from the upload API endpoint and returns the fields
     * to be included in the upload request.
     * @param {Object} response - The response from the upload API endpoint
     * @return {FormData} The fields to include in the upload request
     */
    getFileUploadFields(response) {
        if (!response || !response.hasOwnProperty('post') || !response["post"].hasOwnProperty('fields')) {
            throw new Error("Invalid response from upload API endpoint, must include 'post.fields' property");
        }

        // Create a new FormData object to hold the fields
        const uploadData = new FormData();
        for (const key in response["post"]["fields"]) {
            if (response["post"]["fields"].hasOwnProperty(key)) {
                uploadData.append(key, response["post"]["fields"][key]);
            }
        }
        return uploadData;
    }

    /**
     * Parses the response from the upload API endpoint and returns the
     * file data for the file to be uploaded.
     * @param {Object} response - The response from the upload API endpoint
     * @return {FormData} The data about the file to be uploaded
     */
    getFileData(response) {
        if (!response || !response.hasOwnProperty('file')) {
            throw new Error("Invalid response from upload API endpoint, must include 'file' property");
        }

        // Create a new FormData object to hold the fields
        const fileData = new FormData();
        for (const key in response["file"]) {
            if (response["file"].hasOwnProperty(key)) {
                fileData.append(key, response["file"][key]);
            }
        }

        // Add the filesize to the file data
        const file = this.getFile();
        fileData.append('filesize', file.size);

        // Add the media type to the file data
        fileData.append('media_type', file.type);

        // Return the file data
        return fileData;
    }

    /**
     * Uploads the file to S3 using the data received from the initial request.
     * @param {str} uploadUrl - The URL to upload the file to
     * @param {FormData} uploadData - The fields to include in the upload request
     * @param {FormData} fileData - The data about the file to be uploaded
     * @param {FormData} formData - The original form data
     * @return {void}
     */
    uploadFile(uploadUrl, uploadData, fileData, formData) {

        // Add the file.
        uploadData.append('file', this.getFile(), fileData["filename"]);

        const xhr = new XMLHttpRequest();
        this.xhr = xhr;
        xhr.open('POST', uploadUrl);

        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {

                // Call the progress callback if provided
                if (this.onProgress) this.onProgress(event.loaded, event.total);
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                this.completeUpload(fileData);
            } else {
                this.onError(new Error(`Upload failed with status ${xhr.status}`));
            }
        };

        xhr.onerror = () => this.onError(new Error('Upload failed'));
        xhr.send(uploadData);
    }

    /**
     * Allows the user to abort the upload process.
     */
    abortUpload() {
        if (this.xhr && this.xhr.readyState !== XMLHttpRequest.DONE) {
            this.xhr.abort();
            console.log('Upload aborted');
        } else {
            console.log('No upload in progress to abort');
        }
    }

    /**
     * This method informs the server that the file upload is complete and
     * makes the necessary updates to the workflow.
     * @param {FormData} fileData - The data about the file that was uploaded
     * @return {void}
     */
    completeUpload(fileData) {

        // Convert FormData to URL-encoded string
        const fileDataString = this.formDataToUrlEncoded(fileData);

        fetch(this.uploadUrl, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: fileDataString
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Call the complete callback if provided
            if (this.onComplete) this.onComplete();
        })
        .catch(error => {
            console.error('Error completing upload:', error);

            // Call the error callback if provided
            this.onError(error);
        });
    }
}
