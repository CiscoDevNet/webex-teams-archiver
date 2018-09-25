"""Webex Teams Room Archiver.

Copyright (c) 2018 Cisco and/or its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import re
import requests
import os
import shutil
import tarfile
import concurrent.futures
from collections import namedtuple
from webexteamssdk import WebexTeamsAPI
from .jinja_env import env as jinja_env

__all__ = ['WebexTeamsArchiver', 'File']

File = namedtuple("File", 
                  ["content_disposition", "content_length", "content_type", "filename"])


class WebexTeamsArchiver:
    """Initializes object that can be used to archive a Webex Teams room.

    Args:
        access_token (str): User's personal Webex Teams API bearer token.
        
    Raises:
        webexteamssdkException: An error occurred calling the Webex Teams API.
    """
    def __init__(self, access_token: str) -> None:
        self.access_token = access_token
        self.sdk = WebexTeamsAPI(self.access_token)

    def file_details(self, url: str) -> File:
        """Retrieves the file details using the Webex Teams attachments endpoint.

        Args:
            url (str): The URL of the file found in the files list in the message.

        Raises:
            requests.exceptions.RequestException: Error retrieving file details.
            IndexError: Regex failure.
        """
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        r = requests.head(url, headers=headers)
        r.raise_for_status()
        
        filename_re = re.search(r"filename=\"(.+?)\"", r.headers["Content-Disposition"], re.I)

        f = File(r.headers["Content-Disposition"], 
                 r.headers["Content-Length"], 
                 r.headers["Content-Type"],
                 filename_re.group(1))

        return f   

    def archive_room(self, room_id: str, overwrite_folder: bool = True, delete_folder: bool = False, 
                     reverse_order: bool = True, download_attachments: bool = True, download_workers: int = 15, 
                     text_format: bool = True, html_format: bool = True, timestamp_format: str = '%Y-%m-%dT%H:%M:%S') -> str:
        """Archives a Webex Teams room. This creates a file called `room_id`.tgz with the following contents:
                `room_id`.txt - Text version of the conversations (if `text_format` is True)
                `room_id`.html - HTML version of the conversations (if `html_format` is True)
                files/ - Attachments added to the room (if `download_attachments` is True)

        Args:
            room_id (str): ID of the room to archive.
            overwrite_folder (bool): Overwrite the archive folder if it already exists. Default: True.
            delete_folder (bool): Delete the archive folder when done. Default: False.
            reverse_order (bool): Order messages by most recent on the bottom. Default: True.
            download_attachments (bool): Download attachments sent to the room. Default: True.
            download_workers (int): Number of download workers for downloading files. Default: 15.
            text_format (bool): Create a text version of the archive. Default: True.
            html_format (bool): Create an HTML version of the archive. Default: True.
            timestamp_format (str): Timestamp strftime format. Default: %Y-%m-%dT%H:%M:%S

        Returns:
            A message saying the room has been archived.

        Raises:
            IOError: An error occurred trying to create files/folders.
            shutil.Error: Error occurred copying files or deleting the `room_id` folder on completion.
            ValueError: If both `text_format` and `html_format` are False.
            webexteamssdkException: An error occurred calling the Webex Teams API.
        """
        
        if not text_format and not html_format:
            raise ValueError("At least one of text_format or html_format must be True.")

        # Message timestamp format
        def datetime_format(date, format=timestamp_format):
            return date.strftime(format)
        jinja_env.filters['datetime_format'] = datetime_format

        self._setup_folder(room_id, overwrite_folder, download_attachments, html_format)
        try:
            self._archive(room_id, reverse_order, download_attachments, download_workers, text_format, html_format, timestamp_format)
            self._compress_folder(room_id)
        except Exception:
            self._tear_down_folder(room_id)
            raise

        if delete_folder:
            self._tear_down_folder(room_id)
        
        return "Room has been archived!"

    def _archive(self, room_id, reverse_order, download_attachments, download_workers, text_format, html_format, timestamp_format):
        """Collects room information, including attachments, using Webex Teams APIs and writes them to text/html files."""

        self._gather_room_information(room_id, reverse_order)

        people = {}
        files = {}
        processed_messages = []
        repeat_indeces = []
        previous_person_email = ""
        previous_msg_datetime = ""

        for index, msg in enumerate(self.messages):
            processed_messages.append(msg)

            if index > 0 and msg.personEmail == previous_person_email and (previous_msg_datetime-msg.created).seconds < 60:
                repeat_indeces.append(index)
            
            previous_person_email = msg.personEmail
            previous_msg_datetime = msg.created

            if msg.personEmail not in people:
                people[msg.personEmail] = self.sdk.people.get(msg.personId)

            if msg.files:
                for url in msg.files:
                    file_metadata = self.file_details(url)
                    if url not in files:
                        files[url] = file_metadata

        if reverse_order:
            repeat_indeces = [len(processed_messages)-i for i in repeat_indeces]
            processed_messages = list(reversed(processed_messages))

        if html_format:
            self._create_html_transcript(room_id, processed_messages, files, people, repeat_indeces)

        if text_format:
            self._create_text_transcript(room_id, processed_messages, files)

        if download_attachments:
            self._download_files(room_id, files, download_workers)

            
    def _setup_folder(self, room_id, overwrite_folder, download_attachments, html_format):
        """Creates a folder `room_id` to store archive."""

        if os.path.isdir(room_id) and overwrite_folder:
            shutil.rmtree(room_id, ignore_errors=False)
        
        os.makedirs(room_id)

        if download_attachments:
            os.makedirs(f"{room_id}/files")

        if html_format:
            basepath = os.path.dirname(os.path.realpath(__file__))

            shutil.copytree(f"{basepath}/static/css", f"{room_id}/css")
            shutil.copytree(f"{basepath}/static/fonts", f"{room_id}/fonts")
    
    def _tear_down_folder(self, room_id):
        """Deletes the `room_id` folder in case an exception was raised."""
        
        if os.path.isdir(room_id):
            shutil.rmtree(room_id, ignore_errors=False)

    def _gather_room_information(self, room_id, reverse_order):
        """Calls Webex Teams APIs to get room information and messages."""
        
        self.room = self.sdk.rooms.get(room_id)
        self.room_creator = self.sdk.people.get(self.room.creatorId)
        self.messages = self.sdk.messages.list(room_id)

    def _create_text_transcript(self, room_id, messages, files):
        """Writes room messages to a text file."""
        
        template = jinja_env.get_template("default.txt")
        text_transcript = template.render(
            room=self.room,
            room_creator=self.room_creator,
            messages=messages,
            files=files,
        ) 

        with open(f"./{room_id}/{room_id}.txt", "w") as fh:
            fh.write(text_transcript)

    def _create_html_transcript(self, room_id, messages, files, people, repeat_indeces):    
        """Writes room messages to an HTML file."""
        
        template = jinja_env.get_template("default.html")
        html = template.render(
            room=self.room,
            room_creator=self.room_creator,
            messages=messages,
            files=files,
            people=people,
            repeat_indeces=repeat_indeces,
        ) 
        
        with open(f"./{room_id}/{room_id}.html", "w") as fh:
            fh.write(html)

    def _download_files(self, room_id, files, workers):
        """Downloads files given list of URLs."""
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            result = {executor.submit(self._download_file, room_id, url, files[url].filename): url for url in files}
            
            # Do this to check if any downloads failed.
            for future in concurrent.futures.as_completed(result):
                future.result()

    def _download_file(self, room_id, url, filename):
        """Download file from Webex Teams."""
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        # https://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py
        with requests.get(url, headers=headers, stream=True) as r:
            with open(f"./{room_id}/files/{filename}", 'wb') as f:
                shutil.copyfileobj(r.raw, f)

    def _compress_folder(self, room_id):
        """Compress `room_id` folder as `room_id`.tgz"""

        # https://stackoverflow.com/questions/2032403/how-to-create-full-compressed-tar-file-using-python
        with tarfile.open(f"{room_id}.tgz", "w:gz") as tar:
            tar.add(f"{room_id}")