#
# Created on Thu Apr 22 2021
# Matteo Bjornsson
#
import io
from zipfile import ZipFile


def return_zipped_bytes(file_name: str) -> bytes:
    """
    TODO: write function description
    """
    # buffer the zip file contents as a BytesIO object
    bytes_buffer = io.BytesIO()
    with ZipFile(bytes_buffer, "w") as zip:
        # write the file to the buffer
        zip.write(file_name)
    # return the file position to the start (otherwise 'read()' returns nothing)
    bytes_buffer.seek(0)
    return bytes_buffer.read()


def insert_lines_at_keyword(file_path: str, lines: list, keyword: str) -> None:
    with open(file_path, "r+") as filehandler:
        file_lines = filehandler.readlines()
        index = get_keyword_index(file_lines, keyword)
        for line in lines:
            file_lines.insert(index + 1, line)
        filehandler.seek(0)
        filehandler.writelines(file_lines)
        filehandler.truncate()


def get_keyword_index(string_list: list, keyword: str) -> int:
    for i, s in enumerate(string_list):
        if keyword in s:
            return i
    return -1


def delete_lines(file_path: str, line_list: list) -> None:
    with open(file_path, "r+") as filehandler:
        file_lines = filehandler.readlines()
        filehandler.seek(0)
        for line in file_lines:
            if line not in line_list:
                filehandler.write(line)
        filehandler.truncate()
