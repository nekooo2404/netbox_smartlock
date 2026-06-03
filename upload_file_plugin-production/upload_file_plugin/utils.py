from .models import UploadedFile
from django.db.models import QuerySet

def get_serialized_uploaded_files_for_objects(object_ids: list, model_name: str) -> list:
    """
    Retrieves and serializes uploaded file information from the database
    for a given list of object IDs and model name.
    """

    # Validation
    if not isinstance(object_ids, list) or not object_ids:
        # logging.warning("objectIdList is empty or not a list in get_serialized_uploaded_files_for_objects.")
        return []

    try:
        object_ids = [int(obj_id) for obj_id in object_ids]
    except ValueError:
        # logging.error("All elements in objectIdList must be integers in get_serialized_uploaded_files_for_objects.")
        return []

    if not isinstance(model_name, str) or not model_name:
        # logging.warning("modelName is empty or not a string in get_serialized_uploaded_files_for_objects.")
        return []

    # Select from database
    try:
        uploaded_files: QuerySet[UploadedFile] = UploadedFile.objects.filter(
            object_id__in=object_ids,
            model_name=model_name
        )
    except Exception as e:
        import logging
        logging.error(f"Database query failed in get_serialized_uploaded_files_for_objects: {str(e)}")
        return []

    serialized_files = []
    for file_obj in uploaded_files:
        serialized_files.append({
            'id': file_obj.pk,
            'object_id': file_obj.object_id,
            'model_name': file_obj.model_name,
            'file_name': file_obj.file_name,
        })

    return serialized_files
