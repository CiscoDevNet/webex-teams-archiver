import re
import requests
import collections
import os
import shutil
import concurrent.futures
import asyncio
from webexteamssdk import WebexTeamsAPI
from .jinja_env import env as jinja_env

# TODO: compress folder on completion
# TODO: support for custom timestamp

class WebexTeamsArchiver(object):
    def __init__(self, access_token: str):
        """Initializes object that can be used to archive a Webex Teams room.

        Args:
            access_token (str): User's personal Webex Teams API bearer token.
            
        Raises:
            webexteamssdkException: An error occurred calling the Webex Teams API.
        """
        assert isinstance(access_token, str)

        self.access_token = access_token
        self.sdk = WebexTeamsAPI(self.access_token)

    def file_details(self, url: str):
        """Retrieves the file details using the Webex Teams attachments endpoint.

        Args:
            url (str): The URL of the file found in the files list in the message.

        Raises:
            requests.exceptions.RequestException: Error retrieving file details.
            IndexError: Regex failure.
        """
        assert isinstance(url, str)

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        r = requests.head(url, headers=headers)
        r.raise_for_status()
        
        File = collections.namedtuple("File", ["content_disposition", "content_length", "content_type", "filename"])

        filename_re = re.search(r"filename=\"(.*?)\"", r.headers["Content-Disposition"], re.I)

        f = File(r.headers["Content-Disposition"], 
                 r.headers["Content-Length"], 
                 r.headers["Content-Type"],
                 filename_re.group(1))

        return f   

    def archive_room(self, room_id: str, overwrite_folder: bool = True, delete_folder: bool = False, 
                     reverse_order: bool = True, download_attachments: bool = True, download_workers: int = 15, 
                     text_format: bool = True, html_format: bool = True) -> str:
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

        Returns:
            A message saying the room has been archived.

        Raises:
            IOError: An error occurred trying to create files/folders.
            shutil.Error: Error occurred copying files or deleting the `room_id` folder on completion.
            ValueError: If both `text_format` and `html_format` are False.
            webexteamssdkException: An error occurred calling the Webex Teams API.
        """
        assert isinstance(room_id, str)
        assert isinstance(overwrite_folder, bool)
        assert isinstance(delete_folder, bool)
        assert isinstance(reverse_order, bool)
        assert isinstance(download_attachments, bool)
        assert isinstance(download_workers, int)
        assert isinstance(text_format, bool)
        assert isinstance(html_format, bool)

        if not text_format and not html_format:
            raise ValueError("At least one of text_format or html_format must be True.")

        self._setup_folder(room_id, overwrite_folder, download_attachments, html_format)
        try:
            self._archive(room_id, overwrite_folder, reverse_order, download_attachments, download_workers, text_format, html_format)
        except Exception:
            self._tear_down_folder(room_id)
            raise

        if delete_folder:
            self._tear_down_folder(room_id)
        
        return "Room has been archived!"

    def _archive(self, room_id, overwrite_folder, reverse_order, download_attachments, download_workers, text_format, html_format):
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

        loop = asyncio.get_event_loop()
        try:
            if html_format:
                write_to_html_file = loop.create_task(self._create_html_transcript(room_id, processed_messages, files, people, repeat_indeces, reverse_order))
                loop.run_until_complete(write_to_html_file)

            if text_format:
                write_to_txt_file = loop.create_task(self._create_text_transcript(room_id, processed_messages, files, reverse_order))
                loop.run_until_complete(write_to_txt_file)

            if download_attachments:
                download_files = loop.create_task(self._download_files(room_id, files, download_workers))
                loop.run_until_complete(download_files)
            
        finally:
            loop.close()

    def _setup_folder(self, room_id, overwrite_folder, download_attachments, html_format):
        """Creates a folder `room_id` to store archive."""

        if os.path.isdir(room_id) and overwrite_folder:
            shutil.rmtree(room_id, ignore_errors=False)
        
        os.makedirs(room_id)

        if download_attachments:
            os.makedirs(f"{room_id}/files")

        if html_format:
            os.makedirs(f"{room_id}/css/")
            os.makedirs(f"{room_id}/css/fonts/")

            basepath = os.path.dirname(os.path.realpath(__file__)) + "/static/"
            for basename in os.listdir(basepath):
                if basename.endswith('.css'):
                    if os.path.isfile(basepath+basename):
                        shutil.copy2(basepath+basename, f"{room_id}/css/")
                if basename.startswith("collab-ui-icons"):
                    if os.path.isfile(basepath+basename):
                        shutil.copy2(basepath+basename, f"{room_id}/css/fonts/")
    
    def _tear_down_folder(self, room_id):
        """Deletes the `room_id` folder in case an exception was raised."""
        if os.path.isdir(room_id):
            shutil.rmtree(room_id, ignore_errors=False)

    def _gather_room_information(self, room_id, reverse_order):
        """Calls Webex Teams APIs to get room information and messages."""
        self.room = self.sdk.rooms.get(room_id)
        self.room_creator = self.sdk.people.get(self.room.creatorId)
        self.messages = self.sdk.messages.list(room_id)

    async def _create_text_transcript(self, room_id, messages, files, reverse_order):
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

    async def _create_html_transcript(self, room_id, messages, files, people, repeat_indeces, reverse_order):    
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

    async def _download_files(self, room_id, files, workers=15):
        """Downloads files given list of URLs."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            result = {executor.submit(self._download_file, room_id, url, files[url].filename): url for url in files}
            
            # Do this to check if any downloads failed.
            for future in concurrent.futures.as_completed(result):
                future.result()

    def _download_file(self, room_id, url, filename):
        """Download file from Webex Teams."""
        # https://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        with requests.get(url, headers=headers, stream=True) as r:
            with open(f"./{room_id}/files/{filename}", 'wb') as f:
                shutil.copyfileobj(r.raw, f)