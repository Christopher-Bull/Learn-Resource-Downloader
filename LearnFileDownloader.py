"""
A script to download all resources from selected courses off Learn.

Follow the prompts to select and download Learn resources from your
desired courses.
This project builds upon code written by Shawn Richards. Without Shawn's
extensive base code, this project would never have been started. Thanks
Shawn.

Disclaimer: Please note that the Learn website is subject to change,
which can cause this code to break. If this happens, feel free to dig into
this code and try figure out what URLs need parsing to get the code
working again. If you are willing to do so, I highly recommend the
following resources:
- RegularExpressions101, a free online regex debugger:
    https://regex101.com/
- Episodes 37-39 of the 'Python 3 Basics Tutorial Series' by sentdex:
    https://www.youtube.com/playlist?list=PLQVvvaa0QuDe8XSftW-RAxdo6OmaeL85M
"""

import os
import http.cookiejar as cookielib
import urllib.parse as urllib
import urllib.request as urllib2
import re
import shutil
from sys import stderr
from getpass import getpass
from codecs import lookup as lookup_codec
from extension_map import FILE_EXT_MAP

__author__ = "Christopher Bull, Shawn Richards"
__date__ = "30/08/2020"  # in "dd/mm/yyyy" format
__version__ = "2.0.1"
__status__ = "Prototype"

DEBUG = True

MAX_FILE_NAME_LEN = 259
PATH_STORAGE_FN = "OrigFNames.txt"
MAX_FOLDER_NAME_LEN = MAX_FILE_NAME_LEN - len(PATH_STORAGE_FN) - 1 # -1 accounts for slash divider

forbidden_fn_chars_re = re.compile(r'[:\*\?"<>\|]')


def get_encoding(content_type, url):
    """Attempt to get the encoding type of the downloaded file"""
    encoding_matches = re.findall(r"charset=(.*)?", content_type)
    if len(encoding_matches) > 0:
        encoding = encoding_matches[0]
        if len(encoding_matches) > 1:
            print("\nWarning: more than one encoding type declared!", file=stderr)
            print(f"Will attempt to use the first type found ({encoding})\n", file=stderr)
    else:
        print(f"Error: content_type = '{content_type}', attempting to decode with latin-1", file=stderr)
        print(url, file=stderr)
        encoding = 'latin-1'
    return encoding
    


class learnUserObj(object):
    """
    Learn User Class
    
    A class to manage user credentials, logging into Learn, and
    downloading webpages and other files from Learn.
    
    Parameters
    ----------
    login : str
        Learn username.
    password : str
        Learn password.
    """
    
    def __init__(self, login, password):
        self.login = login
        self.password = password

        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cj)
        )
        user_agent = ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.1.4322)")
        self.opener.addheaders = [
            ('User-agent', user_agent)
        ]
        
        self.loginToLearn()

        
    def loginToLearn(self):
        """
        Handle Learn login.

        Populate the cookie jar and log into Learn
        """
        LEARN_LOGIN_URL = "https://learn.canterbury.ac.nz/login/index.php"
        
        #Get the login token
        decoded_webpage = self.openWebpage("https://learn.canterbury.ac.nz")
        
        form_re = re.compile(r'(<form class="m-t-1"(?:.*\n)*.*</form>)')
        form_section = form_re.search(decoded_webpage).group(1)

        token_re = re.compile(r'<input type="hidden" name="logintoken" value="(\w*)">')
        login_token = token_re.search(form_section).group(1)
        
        login_data = urllib.urlencode({
            'username' : self.login,
            'password' : self.password,
            'logintoken' : login_token
        }).encode('utf-8')
        
        #Login (setting cookies)
        decoded_webpage = self.openWebpage(LEARN_LOGIN_URL, login_data)

    
    def openWebpage(self, url, data=None):
        """
        Return the decoded webpage from `url`
        
        Parameters
        ----------
        url : str
            The unencoded URL of the server to contact.
        data : bytes, optional
            Additional data to send to the server (default is None).
        
        Returns
        -------
        str
            The decoded webpage received from the server.
        
        Raises
        ------
        UnicodeDecodeError
            If the received webpage could not be decoded.
        """
        
        response = self.opener.open(url, data)
        encoding = get_encoding(response.info()['Content-Type'], url)
        encoded_webpage = b''.join(response.readlines())
        
        try:
            decoded_webpage = encoded_webpage.decode(encoding)
        except UnicodeDecodeError as e:
            print("\Error, could not decode the following:")
            print(encoded_webpage)
            raise e
        else:
            return decoded_webpage
    
    
    def get_header(self, url):
        """return the header for the file at `url`"""
        response = self.opener.open(url)
        return response.info()

        
    def downloadFile(self, url, dest_folder, learn_name):
        """Download file retrieved from `url` to `dest_folder`."""
        response = self.opener.open(url)
        
        filename = self.get_filename(response, learn_name)
        print(f"Downloading '{filename}'")

        media_type, encoding = self.get_content_type(response)
        if media_type in FILE_EXT_MAP:
            if not FILE_EXT_MAP[media_type] == None:
                is_known_type = True
            else:
                is_known_type = False
        else:
            is_known_type = False
        
        if is_known_type:
            ext = FILE_EXT_MAP[media_type]
            full_fn = f"{filename}.{ext}"
        else:
            print(f"\nA file of the unknown type '{content_type}' was ",
                  f"found.\nIt will be saved as '{filename}' without an ",
                  "extension. If possible, please identify the correct ",
                  "file extension and add it to the file type map.\n", file=stderr)
            full_fn = filename
        
        amp_re = re.compile(r'&amp;?')
        dest_folder = amp_re.sub('&', dest_folder)
        dest_folder = urllib.unquote(dest_folder)
        
        dest_folder = os.path.abspath(dest_folder)
        dest = os.path.abspath(f"{dest_folder}/{full_fn}")
        
        rel_path = os.path.relpath(dest)
        rel_path2 = os.path.relpath(forbidden_fn_chars_re.sub('', rel_path))
        
        if not rel_path == rel_path2:
            print("\nWarning! The following characters cannot be used in file and folder names:", file=stderr)
            print(r"    \ / : * ? < > |", file=stderr)
            print(f"The file named '{rel_path}' has been renamed to '{rel_path2}' accordingly.\n", file=stderr)
            
            rel_dest_folder = os.path.relpath(dest_folder)
            rel_dest_folder2 = forbidden_fn_chars_re.sub('', rel_dest_folder)
            dest_folder = os.path.abspath(rel_dest_folder2)
            full_fn = forbidden_fn_chars_re.sub('', full_fn)
            dest = os.path.abspath(f"{dest_folder}/{full_fn}")
        
        orig_path = dest
        if len(dest_folder) > MAX_FOLDER_NAME_LEN:
            dest_folder = dest_folder[:MAX_FOLDER_NAME_LEN]
            dest = os.path.abspath(f"{dest_folder}/{full_fn}")
            
        if len(dest) > MAX_FILE_NAME_LEN:
            renamed_file = "rn"
            
            i = 1
            while os.path.exists(f"{dest_folder}/{renamed_file}{i}"):
                i += 1;
                
            if is_known_type:
                full_fn = f"{renamed_file}{i}.{ext}"
            else:
                full_fn = f"{renamed_file}{i}"
            
            dest = os.path.abspath(f"{dest_folder}/{full_fn}")

        if not os.path.exists(dest_folder):
            if not DEBUG:
                os.makedirs(dest_folder)
            
        if orig_path != dest:
            print(f"Warning! File name too long:\n'{orig_path}' shortened to '{dest}'", file=stderr)
            storage_file_path = os.path.abspath(
                f"{dest_folder}/{PATH_STORAGE_FN}")
            with open(storage_file_path, 'a') as path_file:
                print(f"'{dest}' ==> '{orig_path}'", file=path_file)
            
        if not DEBUG:
            with open(dest, 'w+b') as out_file:
                shutil.copyfileobj(response, out_file)
    
    
    def get_content_type(self, response):
        """Return the Content-Type field of the `response`"""
        content_type = response.info()['Content-Type']
        content_re = re.compile(r'([^;\s]*)(?:\s*;.*charset=(.*?)(?:\s|;|$))?')
        content_match = content_re.search(content_type)
        media_type, encoding = content_match.group(1,2)
        return (media_type, encoding)
    
    
    def get_filename(self, response, learn_name):
        """Return filename in Content-Disposition field of `response`"""
        content_disposition = response.info()['Content-Disposition']
        fn_re = re.compile(r'filename="(.*?)\.\w*"')
        amp_re = re.compile(r'&amp;?')
        if content_disposition == None:
            filename = learn_name
        else:
            filename = fn_re.search(content_disposition).group(1)
        filename = urllib.unquote(filename)
        filename = amp_re.sub('&', filename)
        return filename



def extract_between_res(html_txt, start_re, end_re):
    """Return the text between `start_re` and `end_re` in `html_txt`."""
    start_match = start_re.search(html_txt)
    if start_match != None:
        start_index = start_match.end()
    
        end_match = end_re.search(html_txt, start_index)
        if end_match != None:
            end_index = end_match.start()
            
        else:
            return None
    else:
        return None

    return html_txt[start_index:end_index]


def extract_course_codes_and_ids(learnUser):
    """
    Return a dict mapping course codes to their Learn ID numbers.
    
    Return a dictionary mapping the course codes found on the user's Learn
    login to their respective Learn ID numbers.
    """
    
    webpage = learnUser.openWebpage("https://learn.canterbury.ac.nz/")
    
    course_list_str_start = r'(<li class="dropdown nav-item">\s+<a .*>\s+My Courses\s+</a>)'
    course_list_str_end = r'(</li>)'
    course_str = r'<a class="dropdown-item" role="menuitem" href=".*?id=(\d*)" title="((?:[A-Z]{4}\d{3})(?:-[A-Z]{4}\d{3})*).*?">(.*?)</a>'
    
    course_list_re_start = re.compile(course_list_str_start)
    course_list_re_end = re.compile(course_list_str_end)
    course_re = re.compile(course_str)
    
    course_list_txt = extract_between_res(webpage, course_list_re_start, 
                                          course_list_re_end)
    
    groups = course_re.findall(course_list_txt)
    
    courses = {}
    for (course_id, course_code, course_name) in groups:
        courses[course_code] = (course_id, course_name)
    
    return courses


def get_resource_url(course_id_number):
    """Return the url to the resources page"""
    return f"https://learn.canterbury.ac.nz/course/resources.php?id={course_id_number}"

        
def extract_download_info(courseResourceText):
    """
    Extract the file and folder URLs from the resources page.
    
    Return a list of URLs for all the files on the relevant course
    resources page, and another for all the folders.
    
    Parameters
    ----------
    courseResourceText : str
        The HTML text from the relevant course's resources page on Learn.
    
    Returns
    -------
    tuple of list of list of str
        A 2-element tuple containing the file and folder URL lists.
    
    """
    item_array = []

    table_str_s = r'<div role="main"><span id="maincontent"></span><table class="generaltable mod_index">'
    table_str_e = r'</table>\n*</div>'
    cell_str = r'<td class="cell c1" style="text-align:left;">(.*?)</td>'
    text_str = r'href="(.*)".*src=".*/(?:icon|f/(\w+))".*alt="([\w|\s]*)" />\s?(.+)</a>'
    
    table_re_s = re.compile(table_str_s)
    table_re_e = re.compile(table_str_e)
    cell_re = re.compile(cell_str)
    text_re = re.compile(text_str)
    
    table_text = extract_between_res(courseResourceText, table_re_s, table_re_e)
    cell_texts = cell_re.findall(table_text)
    
    for cell_text in cell_texts:
        text_match = text_re.search(cell_text)
        url, file_type, item_type, learn_name = text_match.group(1,2,3,4)
        
        type = get_type(item_type, file_type, url)
        
        item_array.append((type, url, learn_name))
            
    return item_array


def get_type(item_type, file_type, url):
    """Return the type of file/item"""
    if file_type == '':
            print(f"A non-file item of type '{item_type}' was found")
            
    if item_type == "File":
        type = "file"
            
    elif item_type == "Folder":
        type = "folder"
        
    elif item_type == "URL":
        type = "url"
        
    elif item_type == "Page":
        type = "page"
    
    elif item_type == "Course Material":
        type = "material"
        
    else:
        print(f"An item of unknown type '{item_type}' was found, this item will be ignored!")
        type = None
    
    return type


def extract_pdf_url(learnUser, url):
    """Extract the download link for a PDF file."""
    learn_url_re = re.compile('https://learn\.canterbury\.ac\.nz/.*')
    
    if learn_url_re.match(url):
        dl_page_text = learnUser.openWebpage(url)
        with open('ouput.txt', 'w') as opfile:
            print(dl_page_text.encode('cp850','replace').decode('cp850'), file=opfile)
        dl_url_re = re.compile(
            'Click <a href="(.*?)">(.*?)\.pdf</a> link to download the file\.'
            )
        dl_url_match = dl_url_re.search(dl_page_text)
        dl_url = dl_url_match.group(1)
        
    else:
        dl_url = url
        
    return dl_url

        
# def extractDownloadLinksFromFolder(learnUser, folderPageURL):
#     """Extract download links for all items in a folder."""
#     downloadLinksArray = []
#     folderPageText = learnUser.openWebpage(folderPageURL)
# 
#     re_str_1 = r'<div role="main">((?:.*\n)*?</div></div>)</div>'
#     re_str_2 = r'<li><span class="fp-filename-icon"><a href="(.*?)">.*?<span class="fp-filename">(.*?\.\w+).*?</li>'
#     re1 = re.compile(re_str_1)
#     re2 = re.compile(re_str_2)
#     
#     file_list_match = re_str_1.search(folderPageText)
#     file_list_text = file_list_match.group(1)
#     
#     
#     
#     try:
#         matches = bad_re.findall(folderPageText)
#         if len(matches) > 1:
#             print("\nWarning, more than one match found,",
#                   "only the first match will be used.",
#                   "This may be incorrect and should be double checked!\n")
#         [(folder_name, files, base_url, download_ext)] = matches
#     except TypeError as e:
#         print("\nAn error occured while trying to parse")
#         print(folderPageText)
#         print("with")
#         print(bad_re.pattern)
#         raise e
# 
#     downloadURL = base_url + "?id=" + download_ext
#     fileName = folder_name + ".zip"
#     downloadLinksArray.append([downloadURL, fileName])
#     
#     return downloadLinksArray


def download_file(learnUser, url, target_dest, learn_name):
    """Download a file from learn"""
    header = learnUser.get_header(url)
    content_type = header['Content-Type']
    content_re = re.compile(r'([^;\s]*)(?:\s*;.*charset=(.*?)(?:\s|;|$))?')
    content_match = content_re.search(content_type)
    media_type, encoding = content_match.group(1,2)
    if media_type == "text/html":
        dl_url = extract_pdf_url(learnUser, url)
    else:
        dl_url = url
    dest_folder = f"{target_dest}/Single Files/{learn_name}"
    learnUser.downloadFile(dl_url, dest_folder, learn_name)
    
    
def download_folder(learnUser, url, target_dest, learn_name):
    """Download a folder from learn"""
    print(f"\nExtracting download links for files nested in '{target_dest}' folder")
    folder_re = re.compile(r'<form.*?action="(.*?)" >\n.*?name="id" value="(\d+)">')
    folder_text = learnUser.openWebpage(url)
    folder_match = folder_re.search(folder_text)
    
    base_url, download_ext = folder_match.group(1,2)
    dl_url = base_url + "?id=" + download_ext
    
    dest_folder = f"{target_dest}/{learn_name}"
    learnUser.downloadFile(dl_url, dest_folder, learn_name)


def download_url(learnUser, url, target_dest, learn_name):
    """Download a pdf file from learn"""
    dl_page_text = learnUser.openWebpage(url)
    dl_re = re.compile(r'<div role="main">.*?<h2>(.*?)</h2>.*?href="(.*?)"')
    dl_match = dl_re.search(dl_page_text)
    title, target = dl_match.group(1, 2)
    
    target_dest = f"{target_dest}/Single Files/"
    dest = os.path.relpath(f"{target_dest}/{title}.url")
    dest2 = os.path.relpath(forbidden_fn_chars_re.sub('', dest))
    
    if dest != dest2:
        print("\nWarning! The following characters cannot be used in file and folder names:", file=stderr)
        print(r"    \ / : * ? < > |", file=stderr)
        print(f"The file named '{dest}' has been renamed to '{dest2}' accordingly.\n", file=stderr)
    
    abs_target_dest = os.path.abspath(target_dest)
    if not os.path.exists(abs_target_dest):
            os.makedirs(abs_target_dest)
    
    dest = os.path.abspath(dest2)
    
    with open(dest, 'w') as out_file:
        print(f"[InternetShortcut]\nURL={target}", file=out_file)


def download_page(learnUser, url, target_dest, learn_name):
    """Download a page from learn"""
    target_dest = f"{target_dest}/Single Files/"
    learnUser.downloadFile(url, target_dest, learn_name)


def download_resource_page(learnUser, target_dest, courseResourceURL):
    """Download all files and folders found on the resources page."""
    print("Extracting file and folder links from Resource Page")
    resource_page = learnUser.openWebpage(courseResourceURL)
    item_array = extract_download_info(resource_page)
    
    for (item_type, item_url, item_name) in item_array:
        print(f"downloading {item_name}")
        if item_type == "file":
            download_file(learnUser, item_url, target_dest, item_name)
        elif item_type == "folder":
            download_folder(learnUser, item_url, target_dest, item_name)
        elif item_type == "url":
            download_url(learnUser, item_url, target_dest, item_name)
        elif item_type == "page":
            download_page(learnUser, item_url, target_dest, item_name)
        else:
            pass # ignore items of unknown type


def main():
    learnUsername = input("Username: ")
    learnPassword = getpass()

    print("Logging you into learn...")
    learnUser = learnUserObj(learnUsername, learnPassword)
    print("Login successful")

    print("Extracting course names from learn...")
    courses = extract_course_codes_and_ids(learnUser)
    
    print("\nFound the following courses:")
    course_list = list(courses)
    course_list.sort()
    for (i, course) in enumerate(course_list, start=1):
        print(f"{i}:\t{course}")
    print()

    print("Which courses do you want to download resources for?")
    selected_courses = input("Please enter the corresponding course numbers separated by commas (e.g. '1,4,5'): ")
    
    courseNames = []
    courseResourceURLs = []
    course_numbers = selected_courses.split(',')
    for course_number in course_numbers:
        course_code = course_list[int(course_number)-1] #Must convert course_number to an int as it is still a str. Also must account for list indexing from 1
        course_id, course_name = courses[course_code]
        courseNames.append(course_name)
        courseResourceURLs.append(get_resource_url(course_id))
    
    destination_folder = input("Where do you want to save the files? ")
    
    # Begin download process
    
    for (courseName, courseResourceURL) in zip(courseNames, courseResourceURLs):
        print(f"\n========Finding files for {courseName}========")
        target_dest = os.path.abspath(destination_folder + '/' + courseName)
        print(f"Downloading resources to '{target_dest}'")
        download_resource_page(learnUser, target_dest, courseResourceURL)
        print(f"Finished downloading files for {courseName}\n")

    print("\nFinished!")
    
    
   
        
    

if __name__ == '__main__':
    main()
