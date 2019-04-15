# cpsc558-minimal-ftp
Project for CPSC 558 Adv. Computer Networks course. Minimal FTP implementation.

### Run Server
`python3 ftpserver.py`

### Run Client
* Make sure to have the IP address of the server.
* The server must be running prior to running the client.
`python3 ftpclient.py xxx.xxx.xxx.xxx`

### Supported Commands
* get filename.ext
* put filename.ext
* cd relative/path/
* ls
* pwd
