==================
webexteamsarchiver
==================


Example:

.. code-block:: python

    from webexteamsarchiver import WebexTeamsArchiver

    personal_token = "ABCdefg"
    archiver = WebexTeamsArchiver(personal_token)
    
    room_id = "Y2lzY29zcGFyazovL3VzL1JPT00v"
    archiver.archive_room(room_id)
    
Produces the following archive:

.. code-block:: bash

    $ ls 
    Y2lzY29zcGFyazovL3VzL1JPT00v.tgz
    Y2lzY29zcGFyazovL3VzL1JPT00v

    $ ls Y2lzY29zcGFyazovL3VzL1JPT00v
    Y2lzY29zcGFyazovL3VzL1JPT00v.html
    Y2lzY29zcGFyazovL3VzL1JPT00v.txt
    files/
    css/




*Copyright (c) 2016-2018 Cisco and/or its affiliates.*
