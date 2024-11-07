import re
import os
import requests
import requests_cache

requests_cache.install_cache("requests_cache", expire_after=3600 * 24)

JUNK_TAGS = [
    "documentclass",
    "importmodule",
    "tociftopnotes",
    "libinput",
    "mhgraphics",
    "nvideonugget",
    "symdecl",
]

JUNK_BEGIN_END_TAGS = [
    "center",
    "column",
    "columns",
    "document",
    "frame",
    "itemize",
    "nparagraph",
    "slideshow",
]


def clear_cache():
    requests_cache.clear()


def get_raw_stex_url(archive: str, filename: str):
    return f"https://gl.mathhub.info/{archive}/-/raw/main/source/{filename}"


def get_raw_stex(archive: str, filename: str):
    url = get_raw_stex_url(archive, filename)
    return requests.get(url).text

def save_content_to_file(content: str, archive: str, filename: str, course_id: str):
    # Dynamically create directory based on course_id (e.g., course_notes/LBS)
    # directory = os.path.join(
    #     os.path.abspath(os.path.dirname(__file__)), "/course_notes", course_id
    # )
    current_dir = os.getcwd()
    directory = current_dir+'\course_notes'

    os.makedirs(directory, exist_ok=True)

    # List existing .tex files in the directory and create a simple numeric filename
    existing_files = sorted([f for f in os.listdir(directory) if f.endswith(".tex")])
    file_number = len(existing_files) + 1
    combined_filename = f"{str(file_number).zfill(2)}.tex"
    
    filepath = os.path.join(directory, combined_filename)

    # Write the content to the file
    with open(filepath, "w") as file:
        file.write(f"CourseId: {course_id}\n")
        file.write(f"Archive: {archive}\n")
        file.write(f"Filepath: {filename}\n\n")
        file.write(content)

    print(f"Content saved to {filepath}")


def transform_line(line: str, debug=False):
    line = line.strip()
    if line.startswith("%"):
        return None
    for tag in JUNK_TAGS:
        if line.startswith("\\" + tag):
            return f"%% removed: {line}" if debug else None
    return line


def cleanup_stex(text: str):
    return "\n".join(
        [
            transform_line(line)
            for line in text.split("\n")
            if transform_line(line) is not None
        ]
    )


def replace_inputref_line(fallback_archive: str, line: str, course_id: str) -> str:
    match = re.match(r"\\inputref\*?(?:\[(.*?)\])?\{(.*?)\}", line)
    if match:
        archive, filename = match.groups()
        if archive is None:
            archive = fallback_archive
        content = get_recursive_stex(archive, filename + ".tex", course_id)
        save_content_to_file(content, archive, filename, course_id)
        return f"File: [{archive}]{{{filename}}}\n"
    
    match = re.match(r"\\libinput\{(.*?)\}", line)
    if match:
        filename = match.group(1)
        content = get_recursive_stex(fallback_archive, filename + ".tex", course_id)
        save_content_to_file(content, fallback_archive, filename, course_id)
        return f"File: [{fallback_archive}]{{{filename}}}\n"

    match = re.match(r"\\mhinput\{(.*?)\}", line)
    if match:
        filename = match.group(1)
        content = get_recursive_stex(fallback_archive, filename + ".tex", course_id)
        save_content_to_file(content, fallback_archive, filename, course_id)
        return f"File: [{fallback_archive}]{{{filename}}}\n"

    return line


def replace_inputref(archive: str, text: str, course_id: str) -> str:
    lines = text.split("\n")
    processed_lines = [
        replace_inputref_line(archive, line, course_id) for line in lines
    ]
    return "\n".join(processed_lines)


def get_recursive_stex(archive: str, filename: str, course_id: str) -> str:
    stex = cleanup_stex(get_raw_stex(archive, filename))
    return replace_inputref(archive, stex, course_id)


if __name__ == "__main__":

    # LBS
    # course_id = "LBS"
    # archive =  "courses/FAU/LBS/course"
    # filename = "course/notes/notes.tex" 
    # AI -1
    # course_id = "AI-1"
    # archive =  "courses/FAU/AI/course"
    # filename  = "course/notes/notes1.tex"
   

    # AI -2
    # course_id = "AI-2"
    # archive =  "courses/FAU/AI/course"
    # filename  = "course/notes/notes2.tex"
     
    # # IWGS -1
    course_id = "IWGS-1"
    archive =  "courses/FAU/IWGS/course"
    filename  = "course/notes/notes-part1.tex"

    # # IWGS -2
    # course_id = "IWGS-2"
    # archive =  "courses/FAU/IWGS/course"
    # filename  = "course/notes/notes-part2.tex"

    clear_cache()
    get_recursive_stex(archive, filename, course_id)
