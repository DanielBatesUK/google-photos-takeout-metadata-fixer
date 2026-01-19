import os
import re
import json
from datetime import datetime, timezone
import subprocess
import time
import shutil
import pprint


# Paths and filenames
INPUT_PATH = r"C:\path\to\extracted\Takeout\Google Photos"
OUTPUT_PATH = r"S:\path\for\fixed\photos"
EXIFTOOL_PATH = r"C:\path\to\exiftool.exe"
EXIFTOOL_ARGUMENTS_FILE =r"C:\path\to\save\exiftool_arguments.txt"
EXIFTOOL_OUTPUT_LOG_FILE =r"C:\path\to\save\exiftool_output_log.txt"
EXIFTOOL_OUTPUT_ERRORS_FILE =r"C:\path\to\save\exiftool_output_errors.txt"
MEDIA_FILES_DICTIONARY_FILE = r"C:\path\to\save\media_files_dictionary.txt"
OS_SEPARATOR  = os.sep


# Define supported media extensions
PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}


# Replace last occurrence
def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)


# Get first part of file name before '.'
def file_name_first_part(file_path):
    file_name = os.path.basename(file_path)
    if '.' not in file_name: return file_name
    file_name = file_name.split('.', 1)[0]
    return file_name


# Is file a photo or video
def photo_or_video(file_path):
    if os.path.splitext(file_path.lower())[1] in PHOTO_EXTENSIONS:
        return 'photo'
    else:
        return 'video'


# Output pretty dictionary to file (don't really need this, I only used for testing)
def output_dict_to_file(data, output_filename):
    try:
        with open(output_filename, "w", encoding="utf-8") as file:
            pprint.pprint(data, stream=file, indent=2, width=999)
        file.close()
        print(f"Dictionary saved to: {output_filename}")
    except OSError as e:
        print(f"File error: {e}")


# Return total execution time
def total_execution_time(elapsed):
    hours = int(elapsed) // 3600
    minutes = (int(elapsed) % 3600) // 60
    seconds = int(elapsed) % 60
    if hours > 0:
        return f"Total execution time: {hours}h {minutes}m {seconds}s"
    elif minutes > 0:
         return f"Total execution time: {minutes}m {seconds}s"
    else:
        return f"Total execution time: {seconds}s"


# Scan directory for media files
def scan_directory(base_path):
    media_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            ext = os.path.splitext(file.lower())[1]
            if ext in PHOTO_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                media_files.append(os.path.join(root, file))
    return media_files


# Find media file's sidecar JSON
def find_sidecar_json(media_path):
    dir_name = os.path.dirname(media_path)
    media_path = rreplace(media_path, '-edited', '', 1)
    media_file_name = os.path.basename(media_path)
    media_file_directory = dir_name + OS_SEPARATOR
    media_file_name_without_extension = os.path.splitext(media_file_name)[0]
    media_file_path_without_extension = media_file_directory + media_file_name_without_extension
    # Supplemental metadata handling
    supplemental_meta_text = '.supplemental-metadata'
    supplemental_file_name_length = len(media_file_name + '.json')
    supplemental_name_allowance = 51 - supplemental_file_name_length
    if supplemental_name_allowance <= 1:
        supplemental_name_allowance = 1
    # Possible paths
    dot_json_path = media_path + '.json'
    supplemental_json_path = media_path + supplemental_meta_text[:supplemental_name_allowance] + '.json'
    no_extension_json_path = media_file_path_without_extension + '.json'
    # Check common patterns
    candidates = [
        dot_json_path,
        supplemental_json_path,
        no_extension_json_path,
        rreplace(dot_json_path, '-', '', 1),
        rreplace(supplemental_json_path, '-', '', 1),
        rreplace(no_extension_json_path, '-', '', 1)
    ]
    # Check for the usual suspects
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    # Last resort - Brute force time
    match = re.search(r"^(.*?)(\(\d+\))?(_exported.*)?$", file_name_first_part(media_file_name), re.IGNORECASE)
    test_file_name = match.group(1)
    for f in os.listdir(dir_name):
        if f.startswith(test_file_name[:46]) and f.endswith('.json'):
            return os.path.join(dir_name, f)
    # Oh well - we tried
    return None


# Create media files dictionary
def create_media_files_dictionary(files, output_to_file = False):
    print('Scanning files and looking for JSON sidecar...')
    found_count = 0
    not_found_count = 0
    media_files_dict = {}
    # Create media files dict
    for file in files:
        json_path = find_sidecar_json(file)
        if json_path:
            media_files_dict.update({file : {'file_type': photo_or_video(file), 'file_path': file, 'json_path': json_path}})
            found_count += 1
        else:
            print(f"{file} -> **** NOT FOUND ****")
            media_files_dict.update({file : None})
            not_found_count += 1
        print(f"Total files: {(found_count + not_found_count)}, JSON sidecar found: {found_count}, JSON sidecar not found: {not_found_count}", end='\r')
        #break # TESTING ONE FILE - COMMENT OUT OR REMOVE
    print()
    # Output dict to file
    if output_to_file:
        print('Writing JSON sidecar dictionary to a file...')
        output_dict_to_file(media_files_dict, MEDIA_FILES_DICTIONARY_FILE)
    # Return dictionary
    return media_files_dict


# Get json data from sidecar file
def get_json_data(file):
    # Load JSON file
    with open(file['json_path'], "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    json_file.close()
    # Get data time from json
    if "photoTakenTime" in data and "timestamp" in data["photoTakenTime"]:
        timestamp = int(data["photoTakenTime"]['timestamp'])
    elif "creationTime" in data and "timestamp" in data["creationTime"]:
        timestamp = int(data["creationTime"]['timestamp'])
    else:
        timestamp = 0
    date_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(f"%Y:%m:%d %H:%M:%S")
    filename_date_time = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(f"%Y_%m_%d_%H%M%S")
    # Get GPS data from json
    # Lat
    if "geoData" in data and "latitude" in data["geoData"]:
        gps_latitude = float(data["geoData"]['latitude'])
    else:
        gps_latitude = 0.0
    # Long
    if "geoData" in data and "longitude" in data["geoData"]:
        gps_longitude = float(data["geoData"]['longitude'])
    else:
        gps_longitude = 0.0
    # Alt
    if "geoData" in data and "altitude" in data["geoData"]:
        gps_altitude = float(data["geoData"]['altitude'])
    else:
        gps_altitude = 0.0
    # Return results
    return {'date_time':date_time, 'filename_date_time': filename_date_time, 'gps_latitude':gps_latitude, 'gps_longitude':gps_longitude, 'gps_altitude':gps_altitude}


# Generate exiftool arguments
def create_exiftool_arguments(media_files_dictionary, output_to_file = False):
    print('Generating exiftool arguments with JSON sidecar data...')
    argument_counts = 0
    exiftool_arguments = ""
    for file in media_files_dictionary.values():
        argument_counts += 1
        file_data = get_json_data(file)
        if file['file_type'] == 'photo':
            # Photo arguments
            exiftool_arguments += f"-o\n{OUTPUT_PATH}\n-progress\n-DateTimeOriginal={file_data['date_time']}\n-CreateDate={file_data['date_time']}\n-ModifyDate={file_data['date_time']}\n-FileModifyDate={file_data['date_time']}\n-GPSLatitude={file_data['gps_latitude']}\n-GPSLongitude={file_data['gps_longitude']}\n-GPSAltitude={file_data['gps_altitude']}\n-FileName={file_data['filename_date_time']}_%f.%e\n-d\n%Y-%m-%d %H.%M.%S\n{file['file_path']}\n-execute\n"
        else:
            # Video arguments
            exiftool_arguments += f"-o\n{OUTPUT_PATH}\n-progress\n-DateTimeOriginal={file_data['date_time']}\n-MediaCreateDate={file_data['date_time']}\n-TrackCreateDate={file_data['date_time']}\n-CreateDate={file_data['date_time']}\n-ModifyDate={file_data['date_time']}\n-FileModifyDate={file_data['date_time']}\n-GPSLatitude={file_data['gps_latitude']}\n-GPSLongitude={file_data['gps_longitude']}\n-GPSAltitude={file_data['gps_altitude']}\n-FileName={file_data['filename_date_time']}_%f.%e\n-d\n%Y-%m-%d %H.%M.%S\n{file['file_path']}\n-execute\n"
        print(f"Created {argument_counts} of {len(media_files_dictionary)} exiftool arguments", end='\r')
    print()
    # Output arguments to file
    if output_to_file:
        with open(EXIFTOOL_ARGUMENTS_FILE, "w", encoding="utf-8") as file:
            file.write(exiftool_arguments)
        file.close()
    return exiftool_arguments


# Execute exiftool commands
def execute_exiftool(exiftool_arguments):
    print('Executing exiftool; this could take some time...')
    exiftool_arguments += f"\n-stay_open\nFalse\n" # Used to close exiftool when finished
    # Execute exiftool
    exiftool_command = [EXIFTOOL_PATH, "-stay_open", "True", "-progress",  "-ignoreMinorErrors", "-@", "-"]
    exiftool = subprocess.Popen(exiftool_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    # Send all arguments at once
    stdout, stderr = exiftool.communicate(exiftool_arguments)
    # Write logs
    with open(EXIFTOOL_OUTPUT_LOG_FILE, "w", encoding="utf-8") as file:
        file.write(stdout)
    with open(EXIFTOOL_OUTPUT_ERRORS_FILE, "w", encoding="utf-8") as file:
        file.write(stderr)
    print("ExifTool finished")


# fix png files that look like jpeg files
def fix_png_like_jpeg(media_files_dictionary):
    print(f"Fixing png files that look like jpegs...")
    # Scan exiftool errors file
    print(f"Scanning exiftools error file...")
    pngs_like_jpegs_list = []
    pngs_like_jpegs_count = 0
    with open(EXIFTOOL_OUTPUT_ERRORS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            if match := re.search(r"^(Error: Not a valid PNG \(looks more like a JPEG\) - )(.+)$", line, re.IGNORECASE):
                pngs_like_jpegs_list.append(os.path.normpath(match.group(2)))
                pngs_like_jpegs_count += 1
                print(f"Found {pngs_like_jpegs_count} pngs that look like jpegs errors", end='\r')
    print()
    file.close()
    # Copy png files as jpeg
    print(f"Copying png files as jpeg files...")
    copied_count = 0
    exiftool_arguments = ""
    for file in pngs_like_jpegs_list:
        file_data = get_json_data(media_files_dictionary[file])
        destination_file = f"{OUTPUT_PATH}{OS_SEPARATOR}{file_data['filename_date_time']}_{os.path.splitext(os.path.basename(file))[0]}.jpg"
        shutil.copyfile(file, destination_file)
        exiftool_arguments += f"-overwrite_original\n-progress\n-DateTimeOriginal={file_data['date_time']}\n-CreateDate={file_data['date_time']}\n-ModifyDate={file_data['date_time']}\n-FileModifyDate={file_data['date_time']}\n-GPSLatitude={file_data['gps_latitude']}\n-GPSLongitude={file_data['gps_longitude']}\n-GPSAltitude={file_data['gps_altitude']}\n{destination_file}\n-execute\n"
        copied_count += 1
        print(f"Copied and created exiftool commands for {copied_count} files of {pngs_like_jpegs_count}.", end='\r')
    print()
    with open(EXIFTOOL_ARGUMENTS_FILE, "w", encoding="utf-8") as file:
        file.write(exiftool_arguments)
    file.close()
    # Execute exiftool
    print(f"Executing exiftool on copied pngs that look like jpegs...")
    execute_exiftool(exiftool_arguments)
    print (f"Finished converting pngs that look like jpegs.") 


# Main
def main():
    start_time = time.time()
    media_files_list = scan_directory(INPUT_PATH) # Scan media files
    media_files_dictionary = create_media_files_dictionary(media_files_list, True) # Generate media files sidecar JSON dictionary
    exiftool_arguments = create_exiftool_arguments(media_files_dictionary, True) # Generate exiftool arguments
    execute_exiftool(exiftool_arguments) # Execute exiftool using arguments
    fix_png_like_jpeg(media_files_dictionary) # Rename png files that look like jpeg files
    end_time = time.time()
    print(total_execution_time(int(end_time - start_time)))


# Run main() 
if __name__ == "__main__":
    main()
