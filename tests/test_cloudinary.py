import os
import cloudinary
import cloudinary.api
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

try:
    print('Listing authenticated resumes...')
    res = cloudinary.api.resources(type='authenticated', prefix='smartcampus/resumes/', max_results=10)
    for r in res.get('resources', []):
        print(f"Public ID: {r['public_id']}, Type: {r['type']}, Format: {r['format']}")
        
        # Try to rename to upload type
        try:
            rename_res = cloudinary.uploader.rename(
                r['public_id'],
                r['public_id'],
                from_type='authenticated',
                to_type='upload',
                overwrite=True
            )
            print(f"Renamed {r['public_id']} to upload type successfully!")
        except Exception as rename_err:
            print(f"Rename failed for {r['public_id']}: {rename_err}")
            
except Exception as e:
    print('Error:', e)
