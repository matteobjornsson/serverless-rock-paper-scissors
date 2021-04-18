from zipfile import ZipFile
import io
import boto3



lambda_function_filename = 'lambda_function_handler.py'
lambda_handler_name = 'lambda_function_handler.lambda_handler'
lambda_role_name = 'rps-lambda-role'
lambda_function_name = 'rps-lambda-function'

iam_resource = boto3.resource('iam')
lambda_client = boto3.client('lambda')

# zip a given file, return file as bytes
def zip_file(file_name: str) -> bytes:
    # buffer the zip file contents as a BytesIO object
    zip_package = io.BytesIO()
    with ZipFile(zip_package, 'w') as zip:
        # write the file to the buffer
        zip.write(file_name)
    # return the file position to the start (otherwise 'read()' returns nothing)
    zip_package.seek(0)
    return zip_package.read()

