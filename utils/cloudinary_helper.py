import os
import time
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def upload_private_resume(file_stream, original_filename):
    """
    Uploads a resume file to Cloudinary as an authenticated (private) resource.
    Returns the public_id and secure_url on success, or raises an exception.
    """
    try:
        file_stream.seek(0)
        response = cloudinary.uploader.upload(
            file_stream,
            resource_type="raw",
            type="upload",  # Default unguessable public URLs

            folder="smartcampus/resumes",
            use_filename=True,
            unique_filename=True,
            original_filename=original_filename
        )
        print(f"Cloudinary upload response: {response}")
        return {
            "public_id": response.get("public_id"),
            "url": response.get("secure_url"),
            "format": response.get("format"),
            "bytes": response.get("bytes")
        }
    except Exception as e:
        raise Exception(f"Cloudinary upload failed: {str(e)}")

def get_signed_url(public_id, resource_type="raw"):
    """
    Generates a URL for an uploaded resource.
    We now use resource_type='raw' and type='upload' to ensure browser compatibility.
    """
    if public_id.startswith("local:"):
        return f"/api/resume/local/{public_id[6:]}"

    try:
        kwargs = {
            "resource_type": resource_type,
            "type": "upload"
        }

        url, options = cloudinary.utils.cloudinary_url(
            public_id,
            **kwargs
        )
        return url
    except Exception as e:
        raise Exception(f"Failed to generate signed URL: {str(e)}")

def delete_resume(public_id, resource_type="image"):
    """
    Deletes a resume from Cloudinary or local storage.
    """
    if public_id.startswith("local:"):
        from flask import current_app
        import os
        filename = public_id[6:]
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        return {"result": "ok"}

    try:
        response = cloudinary.uploader.destroy(
            public_id,
            resource_type=resource_type,
            type="authenticated"
        )
        return response
    except Exception as e:
        raise Exception(f"Cloudinary deletion failed: {str(e)}")
